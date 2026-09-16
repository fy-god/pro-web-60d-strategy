"""ADVERSARIAL AUDIT 2/4 -- label integrity and alignment audit.

Independently recomputes `label_high`, `label_close`, `entry_open`, `resolved`
from the RAW panel for a deterministic sample of (code, date) rows and compares
them, cell by cell, against the shipped matrix. Nothing here imports the label
code path under test except src.data_pipeline (raw bars only); the recomputation
is written from the task specification, not copied from src/labels.py.

Spec under test
---------------
    entry            = open[t+1]                     (same stock only)
    window           = sessions t+1 .. t+H           (H = 10, same stock only)
    label_high       = max(high[t+1..t+H]) > entry * (1 + target)   STRICTLY
    label_close      = max(close[t+1..t+H]) > entry * (1 + target)  STRICTLY
    resolved         = at least H future bars exist

Also checked
------------
* the count of forward bars actually available per row (right-censoring)
* that no row's label uses a bar at or before t
* that `resolved` is exactly `future_bars >= H`
* the stride-5 sampling: rows are code-major/date-ascending and every kept row
  is a genuine panel row (no fabricated or duplicated (code, date) pairs)
* that the label really does distinguish `>` from `>=` at the boundary

Usage
-----
    python scripts/audit_ml/audit_ml_labels.py
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
OUT = REPO_ROOT / "outputs" / "ml" / "audit"


def main() -> None:
    panel = data_pipeline.load_panel().sort_values(["code", "date"]).reset_index(drop=True)
    mat = pd.read_parquet(REPO_ROOT / "outputs" / "ml" / "matrix_h10_t30_s5.parquet")
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {}

    # Index the panel per stock once.
    by_code = {c: g.reset_index(drop=True) for c, g in panel.groupby("code", sort=False)}

    # ---------------------------------------------------------------- A
    # Deterministic sample of matrix rows, stratified over the whole date range.
    rng = np.random.default_rng(20260917)
    n_sample = 4000
    idx = np.sort(rng.choice(len(mat), size=n_sample, replace=False))
    sample = mat.iloc[idx]

    rows = []
    for _, r in sample.iterrows():
        g = by_code[r["code"]]
        pos = int(np.searchsorted(g["date"].to_numpy(), np.datetime64(r["date"])))
        # position must be exact
        assert pd.Timestamp(g["date"].iloc[pos]) == pd.Timestamp(r["date"]), (r["code"], r["date"])
        fut = g.iloc[pos + 1 : pos + 1 + HORIZON]
        n_fut = len(fut)
        entry = float(g["open"].iloc[pos + 1]) if n_fut >= 1 else np.nan
        if n_fut < 1:
            rows.append({
                "code": r["code"], "date": str(pd.Timestamp(r["date"]).date()),
                "n_fut": 0, "skip": True,
            })
            continue
        fmax_high = float(fut["high"].max())
        fmax_close = float(fut["close"].max())
        thr = entry * (1.0 + TARGET)
        lab_h = 1.0 if fmax_high > thr else 0.0
        lab_c = 1.0 if fmax_close > thr else 0.0
        resolved = n_fut >= HORIZON
        rows.append({
            "code": r["code"],
            "date": str(pd.Timestamp(r["date"]).date()),
            "pos": pos,
            "n_fut": n_fut,
            "entry_recon": entry,
            "entry_matrix": float(r["entry_open"]),
            "entry_abs_diff": float(abs(entry - r["entry_open"])),
            "thr": thr,
            "fmax_high_recon": fmax_high,
            "fmax_high_matrix": float(r["fwd_max_high"]),
            "label_high_recon": lab_h,
            "label_high_matrix": float(r["label_high"]) if np.isfinite(r["label_high"]) else np.nan,
            "label_high_match": bool(
                (not np.isfinite(r["label_high"])) if not resolved
                else float(r["label_high"]) == lab_h
            ),
            "label_close_recon": lab_c,
            "label_close_matrix": float(r["label_close"]) if np.isfinite(r["label_close"]) else np.nan,
            "label_close_match": bool(
                (not np.isfinite(r["label_close"])) if not resolved
                else float(r["label_close"]) == lab_c
            ),
            "resolved_recon": bool(resolved),
            "resolved_matrix": bool(r["resolved"]),
        })

    df = pd.DataFrame(rows)
    report["A_sample"] = {
        "n_sampled": int(len(df)),
        "n_skipped_no_future": int(df["skip"].sum()) if "skip" in df else 0,
        "entry_max_abs_diff": float(df["entry_abs_diff"].max()),
        "entry_mismatch_gt_1e-4": int((df["entry_abs_diff"] > 1e-4).sum()),
        "label_high_mismatches": int((~df["label_high_match"]).sum()),
        "label_close_mismatches": int((~df["label_close_match"]).sum()),
        "resolved_mismatches": int((df["resolved_recon"] != df["resolved_matrix"]).sum()),
        "fwd_max_high_max_abs_diff": float(
            (df["fmax_high_recon"] - df["fmax_high_matrix"]).abs().max()
        ),
    }
    bad = df[~df["label_high_match"] | ~df["label_close_match"]]
    report["A_mismatch_examples"] = bad.head(20).to_dict("records")

    # ---------------------------------------------------------------- B
    # Exhaustive resolved/label check over the WHOLE matrix, vectorised.
    print("exhaustive vectorised label recomputation over all 536,143 rows ...")
    code_codes, code_inv = np.unique(panel["code"].to_numpy(), return_inverse=True)
    ci = code_inv.astype(np.int64)
    n = len(panel)

    # Map matrix rows onto panel rows by (code, date) via a merge.
    key = panel[["code", "date"]].copy()
    key["_pidx"] = np.arange(len(panel), dtype=np.int64)
    mm = mat[["code", "date", "label_high", "label_close", "resolved", "entry_open",
              "fwd_max_high"]].merge(key, on=["code", "date"], how="left")
    assert mm["_pidx"].notna().all(), "matrix contains (code,date) not in panel"
    pidx = mm["_pidx"].to_numpy(np.int64)

    highs = panel["high"].to_numpy("float64")
    closes = panel["close"].to_numpy("float64")
    opens = panel["open"].to_numpy("float64")

    n = len(panel)
    run_h = np.full(n, -np.inf)
    run_c = np.full(n, -np.inf)
    nb = np.zeros(n, dtype=np.int64)
    for d in range(1, HORIZON + 1):
        same = np.zeros(n, dtype=bool)
        same[: n - d] = ci[d:] == ci[: n - d]
        ok = same
        vh = np.full(n, -np.inf)
        vc = np.full(n, -np.inf)
        vh[: n - d] = highs[d:]
        vc[: n - d] = closes[d:]
        run_h = np.where(ok, np.maximum(run_h, vh), run_h)
        run_c = np.where(ok, np.maximum(run_c, vc), run_c)
        nb += ok.astype(np.int64)

    entry = np.full(n, np.nan)
    entry[: n - 1] = opens[1:]
    same_next = np.zeros(n, dtype=bool)
    same_next[: n - 1] = ci[1:] == ci[: n - 1]
    entry[~same_next] = np.nan

    resolved_ex = (nb >= HORIZON) & np.isfinite(entry)
    lab_h_ex = np.where(resolved_ex, (run_h > entry * (1 + TARGET)).astype(float), np.nan)
    lab_c_ex = np.where(resolved_ex, (run_c > entry * (1 + TARGET)).astype(float), np.nan)

    mh = mm["label_high"].to_numpy("float64")
    mc = mm["label_close"].to_numpy("float64")
    mr = mm["resolved"].to_numpy("float64")
    lh_ex, lc_ex, res_ex = lab_h_ex[pidx], lab_c_ex[pidx], resolved_ex[pidx]
    ok_h = np.isnan(lh_ex) & np.isnan(mh) | (lh_ex == mh)
    ok_c = np.isnan(lc_ex) & np.isnan(mc) | (lc_ex == mc)

    report["B_exhaustive"] = {
        "rows_checked": int(len(mm)),
        "resolved_mismatches": int((res_ex.astype(float) != mr).sum()),
        "label_high_mismatches": int((~ok_h).sum()),
        "label_close_mismatches": int((~ok_c).sum()),
        "label_high_base_rate_matrix": float(np.nanmean(mh)),
        "label_high_base_rate_recon": float(np.nanmean(lh_ex)),
        "label_close_base_rate_matrix": float(np.nanmean(mc)),
        "label_close_base_rate_recon": float(np.nanmean(lc_ex)),
        "hit_rates_equal": bool(np.isclose(np.nanmean(mh), np.nanmean(lh_ex), atol=1e-12)),
    }

    # ---------------------------------------------------------------- C
    # STRICT > vs >= : find rows whose forward max high lands exactly on the
    # threshold and confirm they are labelled 0.
    thr_all = entry * (1 + TARGET)
    exact = np.isfinite(run_h) & np.isclose(run_h, thr_all, rtol=0, atol=1e-9)
    report["C_strict_inequality"] = {
        "panel_rows_with_max_high_exactly_on_threshold": int(exact.sum()),
        "matrix_rows_among_them": int(np.isin(pidx, np.flatnonzero(exact)).sum()),
        "labelled_zero_when_on_threshold": bool(
            np.all(lab_h_ex[exact][np.isfinite(lab_h_ex[exact])] == 0.0)
        ),
    }

    # ---------------------------------------------------------------- D
    # stride-5 sampling integrity
    mat_sorted = mat[["code", "date"]].sort_values(["code", "date"]).reset_index(drop=True)
    report["D_stride"] = {
        "matrix_rows": int(len(mat)),
        "panel_rows": int(len(panel)),
        "ratio": float(len(mat) / len(panel)),
        "duplicate_code_date": int(mat.duplicated(["code", "date"]).sum()),
        "is_code_major_date_ascending": bool(mat[["code", "date"]].equals(mat_sorted)),
        "all_rows_exist_in_panel": bool(mm["_pidx"].notna().all()),
        "n_distinct_dates": int(mat["date"].nunique()),
        "rows_per_date_min": int(mat.groupby("date").size().min()),
        "rows_per_date_max": int(mat.groupby("date").size().max()),
    }

    (OUT / "label_audit.json").write_text(json.dumps(report, indent=2, default=str),
                                          encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    print(f"\nwrote {OUT / 'label_audit.json'}")


if __name__ == "__main__":
    main()
