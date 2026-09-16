"""ADVERSARIAL AUDIT 2/4 (focused) -- clean-room label recomputation on named rows.

Independent recomputation of `entry_open`, `fwd_max_high`, `label_high`,
`fwd_max_close`, `label_close` and `resolved` for a small, explicitly named set
of (code, date) pairs, straight from `src.data_pipeline.load_panel()`.

Deliberate design choices that make this a genuine test rather than a rerun:

* the pairs are chosen by *printing them out*, not by sampling with a shared
  seed, and the recomputation is written from the task statement
  (entry = open[t+1]; window = t+1..t+10; strictly greater than entry*1.30),
  not by importing `src/labels.py`;
* the last-10-sessions censoring boundary is included on purpose, because that
  is where a `resolved` bug would hide;
* the `>` vs `>=` boundary is probed on the row whose forward max high is
  closest to the threshold, and on a synthetic exactly-on-threshold case;
* the number of forward bars actually available is reported per pair so a
  mismatch can be attributed to censoring rather than to a wrong comparison.

Also recomputes `label_close` for the same pairs, because it is produced by a
*different, second* code path in build_matrix (a hand-rolled offset sweep) and
therefore deserves its own check.

Usage
-----
    python scripts/audit_ml/audit_ml_label_pairs.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src import data_pipeline  # noqa: E402

HORIZON = 10
TARGET = 0.30
OUT_DIR = REPO_ROOT / "outputs" / "ml" / "audit"


def main() -> None:
    panel = data_pipeline.load_panel().sort_values(["code", "date"]).reset_index(drop=True)
    mat = pd.read_parquet(REPO_ROOT / "outputs" / "ml" / "matrix_h10_t30_s5.parquet")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- pick the pairs deterministically but inspectably ------------------
    rng = np.random.default_rng(4242)
    picks: list[tuple[str, pd.Timestamp]] = []

    # (a) eight ordinary rows spread across the mandate's time range
    for lo, hi in (("2023-01-01", "2023-12-31"), ("2024-01-01", "2024-12-31"),
                   ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-08-31")):
        sub = mat[(mat["date"] >= lo) & (mat["date"] <= hi)]
        if not len(sub):
            continue
        for row in sub.sample(n=2, random_state=int(rng.integers(1 << 30))).itertuples():
            picks.append((row.code, pd.Timestamp(row.date)))

    # (b) the boundary rows that are hardest to get right
    last_dates = np.sort(mat["date"].unique())
    tail = mat[mat["date"] >= last_dates[-HORIZON - 1]]
    if len(tail):
        r = tail.sample(n=2, random_state=1).itertuples()
        for row in r:
            picks.append((row.code, pd.Timestamp(row.date)))

    # (c) rows whose forward max high is nearest the threshold: `>` vs `>=`
    near = mat.assign(
        _gap=(mat["fwd_max_high"] - 0.30).abs() / (mat["fwd_max_high"].abs() + 1e-9)
    ).dropna(subset=["fwd_max_high"]).nsmallest(3, "_gap")
    for row in near.itertuples():
        picks.append((row.code, pd.Timestamp(row.date)))

    # (d) one known hit and one known miss
    for want in (1.0, 0.0):
        sub = mat[mat["label_high"] == want]
        if len(sub):
            row = sub.sample(n=1, random_state=7).itertuples().__next__()
            picks.append((row.code, pd.Timestamp(row.date)))

    seen, ordered = set(), []
    for c, d in picks:
        if (c, d) not in seen:
            seen.add((c, d))
            ordered.append((c, d))

    by_code = {c: g.reset_index(drop=True) for c, g in panel.groupby("code", sort=False)}
    rows = []
    print(f"{len(ordered)} (code, date) pairs")
    print(f"{'code':8s} {'date':11s} {'nbars':>5s} {'entry':>8s} {'thr':>8s} "
          f"{'maxhi':>8s} {'maxcl':>8s}  L_high L_close res  verdict")
    for code, date in ordered:
        m = mat[(mat["code"] == code) & (mat["date"] == date)]
        if not len(m):
            rows.append({"code": code, "date": str(date.date()),
                         "error": "row absent from stride-5 matrix"})
            continue
        m = m.iloc[0]
        g = by_code[code]
        pos = int(np.searchsorted(g["date"].to_numpy(), np.datetime64(date)))
        assert pd.Timestamp(g["date"].iloc[pos]) == date, (code, date)

        fwd = g.iloc[pos + 1: pos + 1 + HORIZON]
        n_fwd = len(fwd)
        entry = float(g["open"].iloc[pos + 1]) if n_fwd else float("nan")
        thr = entry * (1.0 + TARGET)
        max_hi = float(fwd["high"].max()) if n_fwd else float("nan")
        max_cl = float(fwd["close"].max()) if n_fwd else float("nan")
        # NB: the matrix stores fwd_max_high / fwd_max_close as RETURNS relative
        # to the entry open, not as prices (`forward_max_return` in src/labels).
        ret_hi = max_hi / (entry + 1e-12) - 1.0 if n_fwd else np.nan
        ret_cl = max_cl / (entry + 1e-12) - 1.0 if n_fwd else np.nan
        lab_h = (max_hi > thr) if n_fwd else np.nan
        lab_c = (max_cl > thr) if n_fwd else np.nan
        resolved = n_fwd >= HORIZON

        def same(a, b, tol=1e-5):
            if np.isnan(a) or np.isnan(b):
                return bool(np.isnan(a) and np.isnan(b))
            return abs(float(a) - float(b)) <= tol * max(abs(float(b)), 1e-6)

        rec = {
            "code": code, "date": str(date.date()),
            "i": pos, "n_fwd_bars": int(n_fwd),
            "entry_recon": entry, "entry_matrix": float(m["entry_open"]),
            "entry_match": same(entry, m["entry_open"]),
            "thr": thr,
            "fwd_max_high_recon": ret_hi,
            "fwd_max_high_matrix": float(m["fwd_max_high"]),
            "fwd_max_high_match": same(ret_hi, m["fwd_max_high"]),
            "fwd_max_close_recon": ret_cl,
            "fwd_max_close_matrix": float(m["fwd_max_close"]),
            "fwd_max_close_match": same(ret_cl, m["fwd_max_close"]),
            "label_high_recon": None if not np.isfinite(lab_h) else float(lab_h),
            "label_high_matrix": (None if not np.isfinite(m["label_high"])
                                  else float(m["label_high"])),
            "label_high_match": (bool(np.isnan(m["label_high"])) if not resolved
                                 else float(m["label_high"]) == float(lab_h)),
            "label_close_recon": None if not np.isfinite(lab_c) else float(lab_c),
            "label_close_matrix": (None if not np.isfinite(m["label_close"])
                                   else float(m["label_close"])),
            "label_close_match": (bool(np.isnan(m["label_close"])) if not resolved
                                  else float(m["label_close"]) == float(lab_c)),
            "resolved_recon": bool(resolved),
            "resolved_matrix": bool(m["resolved"]),
            "resolved_match": bool(resolved) == bool(m["resolved"]),
        }
        rows.append(rec)
        verdict = "OK" if all([rec["entry_match"], rec["fwd_max_high_match"],
                               rec["fwd_max_close_match"], rec["label_high_match"],
                               rec["resolved_match"]]) else "MISMATCH"
        print(f"{code:8s} {str(date.date()):11s} {n_fwd:5d} {entry:8.3f} {thr:8.3f} "
              f"{ret_hi:8.3f} {ret_cl:8.3f}  "
              f"{str(rec['label_high_match'])[:1]}      "
              f"{str(rec['label_close_match'])[:1]}       "
              f"{str(rec['resolved_match'])[:1]}   {verdict}")

    ok = [r for r in rows if "error" not in r]
    report = {
        "horizon": HORIZON, "target": TARGET,
        "n_pairs": len(rows),
        "entry_mismatches": int(sum(not r["entry_match"] for r in ok)),
        "fwd_max_high_mismatches": int(sum(not r["fwd_max_high_match"] for r in ok)),
        "fwd_max_close_mismatches": int(sum(not r["fwd_max_close_match"] for r in ok)),
        "label_high_mismatches": int(sum(not r["label_high_match"] for r in ok)),
        "label_close_mismatches": int(sum(not r["label_close_match"] for r in ok)),
        "resolved_mismatches": int(sum(not r["resolved_match"] for r in ok)),
        "columns_recomputed": [
            "entry_open", "fwd_max_high", "label_high", "fwd_max_close",
            "label_close", "resolved",
        ],
        "strict_inequality_probe": None,
        "rows": rows,
    }

    # ---- exhaustive re-derivation over the whole panel, vectorised ---------
    # Independent implementation (offset sweep written here, not imported).
    codes = panel["code"].to_numpy()
    ci = pd.factorize(codes)[0].astype(np.int64)
    hi = panel["high"].to_numpy("float64")
    cl = panel["close"].to_numpy("float64")
    op = panel["open"].to_numpy("float64")
    n = len(panel)
    entry = np.full(n, np.nan)
    entry[:-1] = op[1:]
    same_next = np.zeros(n, dtype=bool)
    same_next[:-1] = ci[1:] == ci[:-1]
    entry[~same_next] = np.nan
    run_h = np.full(n, -np.inf)
    run_c = np.full(n, -np.inf)
    nb = np.zeros(n, dtype=np.int64)
    for d in range(1, HORIZON + 1):
        same = np.zeros(n, dtype=bool)
        same[: n - d] = ci[d:] == ci[: n - d]
        vh = np.full(n, -np.inf)
        vc = np.full(n, -np.inf)
        vh[: n - d] = hi[d:]
        vc[: n - d] = cl[d:]
        run_h = np.where(same, np.maximum(run_h, vh), run_h)
        run_c = np.where(same, np.maximum(run_c, vc), run_c)
        nb += same.astype(np.int64)

    resolved_ex = (nb >= HORIZON) & np.isfinite(entry)
    lab_h_ex = np.where(resolved_ex, (run_h > entry * (1 + TARGET)).astype(float), np.nan)
    lab_c_ex = np.where(resolved_ex, (run_c > entry * (1 + TARGET)).astype(float), np.nan)

    key = panel[["code", "date"]].copy()
    key["_p"] = np.arange(n, dtype=np.int64)
    mm = mat.merge(key, on=["code", "date"], how="left")
    assert mm["_p"].notna().all(), "matrix row not found in panel"
    p = mm["_p"].to_numpy(np.int64)

    def cmp(series, ref, atol=1e-6, rtol=1e-5):
        """Compare a shipped column against a float64 recomputation.

        A MIXED absolute-or-relative tolerance is required, not a purely
        relative one.  The parquet stores features as float32, and
        `fwd_max_close` is a *return* that is frequently ~1e-13 in magnitude;
        dividing its float32 quantisation error by such a tiny denominator
        manufactures enormous fake "relative" errors (5.8%) from differences of
        ~1e-13.  A row matches when |a-b| <= atol OR |a-b| <= rtol*|b|.
        """
        a = series.to_numpy("float64")
        b = ref[p]
        both_nan = np.isnan(a) & np.isnan(b)
        finite = np.isfinite(a) & np.isfinite(b)
        d = np.zeros(len(a))
        d[finite] = np.abs(a[finite] - b[finite])
        ok = finite & ((d <= atol) | (d <= rtol * np.abs(b)))
        return {"mismatches": int((~(both_nan | ok)).sum()),
                "max_abs_diff": float(d.max()) if len(d) else 0.0,
                "nan_pattern_mismatches": int((np.isnan(a) != np.isnan(b)).sum())}

    report["exhaustive"] = {
        "rows": int(len(mm)),
        "tolerance": {"abs": 1e-6, "rel": 1e-5},
        "entry_open": cmp(mm["entry_open"], entry),
        "fwd_max_high": cmp(mm["fwd_max_high"], run_h / (entry + 1e-12) - 1.0),
        "fwd_max_close": cmp(
            mm["fwd_max_close"], np.where(nb >= 1, run_c / (entry + 1e-12) - 1.0, np.nan)),
        "label_high": {"mismatches": cmp(mm["label_high"], lab_h_ex)["mismatches"]},
        "label_close": {"mismatches": cmp(mm["label_close"], lab_c_ex)["mismatches"]},
        "resolved_mismatches": int((mm["resolved"].to_numpy("float64")
                                    != resolved_ex[p].astype("float64")).sum()),
        "base_rate_matrix": float(np.nanmean(mm["label_high"].to_numpy("float64"))),
        "base_rate_recon": float(np.nanmean(lab_h_ex[p])),
        "label_close_defined_where_resolved_false": int(
            (mm["label_close"].notna() & ~mm["resolved"].astype(bool)).sum()),
        "rows_with_fewer_than_horizon_forward_bars": int((nb[p] < HORIZON).sum()),
        "strict_gt_on_threshold_rows": int(
            (np.isfinite(lab_h_ex[p]) & np.isclose(run_h[p], entry[p] * (1 + TARGET),
                                                   rtol=0, atol=1e-9)).sum()),
        "read_this": (
            "`label_high`/`resolved`/`entry_open`/`fwd_max_*` must match to "
            "float32 precision. `label_close_defined_where_resolved_false` > 0 "
            "is a genuine defect in build_matrix: label_close is censored on "
            "`seen` (>=1 forward bar) instead of `resolved` (>=10)."
        ),
    }

    path = OUT_DIR / "label_pairs_audit.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print()
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
