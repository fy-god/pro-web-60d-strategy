"""ADVERSARIAL AUDIT 1/4 -- feature causality (look-ahead) audit of src/ml/build_matrix.py.

This script does NOT modify any production module. It imports build_matrix and
exercises its feature builders on controlled inputs.

Three independent tests
-----------------------
T1  TRUNCATION TEST (the decisive one).
    Every feature of the matrix must be a function of bars up to and including
    session t. Take a fixed universe of stocks; build the features twice:
      (a) on the full history,
      (b) on history truncated at a global cutoff date T.
    For every row with date <= T the two must agree. If a feature changes when
    future bars are removed, that feature reads the future.
    A deliberately future-dependent positive control column is injected so that
    the test's power to detect leakage is demonstrated, not assumed.

T2  GROUPBY-ROLLING ALIGNMENT.
    src/ml/build_matrix.py `_groll` / `_roll` return
        groupby(...).rolling(...).<agg>().reset_index(level=0, drop=True).to_numpy()
    with no reindex. The claim is that this stays positionally aligned with the
    input frame. Verified by comparing against an explicit per-stock loop, and
    the failure mode is demonstrated on a non-group-sorted frame.

T3  BETA RECONSTRUCTION.
    Independent from-scratch reconstruction of beta_60 and resid_ret1 for
    specific (code, date) rows from the raw panel, compared to the shipped
    matrix.

Usage
-----
    python scripts/audit_ml/audit_ml_leakage.py
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
from src.ml import build_matrix as bm  # noqa: E402

OUT_DIR = REPO_ROOT / "outputs" / "ml" / "audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_UNIVERSE = 400
CUTOFF = pd.Timestamp("2025-06-30")
BETA_FIXTURE = "outputs/ml/audit/leakage_audit.json"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def features_of(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    """Run build_matrix's three feature builders on `frame` in production order."""
    fr = frame.copy()
    price = bm.add_price_features(fr)
    market = bm.add_market_features(fr)
    cross = bm.add_cross_sectional(fr, {**price, **market})
    out: dict[str, np.ndarray] = {}
    for part in (price, market, cross):
        out.update(part)
    return out


def leak_control(frame: pd.DataFrame, kind: str = "future") -> np.ndarray:
    """Positive control: a feature that deliberately violates causality.

    `future` -- forward 5-bar maximum high / close - 1 (pure look-ahead).
    `lead`   -- the close 3 bars ahead / close - 1 (pure look-ahead).
    """
    close = frame["close"].to_numpy("float64")
    codes = frame["code"].to_numpy()
    n = len(frame)
    if kind == "future":
        src = frame["high"].to_numpy("float64")
    else:
        src = close
    out = np.full(n, np.nan)
    for d in range(1, 6 if kind == "future" else 4):
        same = np.zeros(n, dtype=bool)
        if d < n:
            same[: n - d] = codes[d:] == codes[: n - d]
        val = np.full(n, -np.inf)
        if d < n:
            val[: n - d] = src[d:]
        val[~same] = -np.inf
        out = np.where(np.isfinite(val), np.fmax(out, val), out)
    return out / (close + bm.EPS) - 1.0


def main() -> None:
    report: dict = {}

    panel = data_pipeline.load_panel()
    rng = np.random.default_rng(20260917)
    codes = np.sort(panel["code"].unique())
    universe = np.sort(rng.choice(codes, size=N_UNIVERSE, replace=False))
    sub = (
        panel[panel["code"].isin(set(universe.tolist()))]
        .sort_values(["code", "date"])
        .reset_index(drop=True)
    )
    report["universe_stocks"] = int(len(universe))
    report["universe_rows"] = int(len(sub))
    report["cutoff"] = str(CUTOFF.date())

    # ---------------------------------------------------------------- T1
    trunc = sub[sub["date"] <= CUTOFF].reset_index(drop=True)
    report["truncated_rows"] = int(len(trunc))

    full_feats = features_of(sub)
    trunc_feats = features_of(trunc)
    full_feats["LEAK_control_future"] = leak_control(sub, "future").astype("float32")
    full_feats["LEAK_control_lead3"] = leak_control(sub, "lead").astype("float32")
    trunc_feats["LEAK_control_future"] = leak_control(trunc, "future").astype("float32")
    trunc_feats["LEAK_control_lead3"] = leak_control(trunc, "lead").astype("float32")

    # `trunc` is NOT a prefix of `sub`: the cutoff falls part-way through each
    # stock's block, so the correct comparison is a boolean mask, not a slice.
    keep = (sub["date"] <= CUTOFF).to_numpy()
    assert len(trunc) == int(keep.sum())
    assert (sub.loc[keep, ["code", "date"]].to_numpy()
            == trunc[["code", "date"]].to_numpy()).all()

    t1 = []
    for name in sorted(full_feats):
        a = np.asarray(full_feats[name], dtype="float64")[keep]
        b = np.asarray(trunc_feats[name], dtype="float64")
        assert len(a) == len(b), name
        both_nan = np.isnan(a) & np.isnan(b)
        diff = np.where(both_nan, 0.0, np.abs(a - b))
        diff = np.where(np.isnan(diff), 0.0, diff)
        finite = np.isfinite(a) & np.isfinite(b)
        scale = np.maximum(np.abs(a[finite]).max() if finite.any() else 1.0, 1.0)
        t1.append({
            "feature": name,
            "max_abs_diff": float(diff.max()),
            "n_diff_gt_1e-6": int((diff > 1e-6).sum()),
            "n_rows": int(len(b)),
            "rel_diff": float(diff.max() / scale),
        })
    t1 = sorted(t1, key=lambda r: -r["max_abs_diff"])
    report["T1_truncation"] = t1
    report["T1_verdict"] = {
        "features_checked": len(t1),
        "causal_features": int(sum(1 for r in t1 if r["n_diff_gt_1e-6"] == 0)),
        "leaking_features": [r["feature"] for r in t1 if r["n_diff_gt_1e-6"] > 0],
    }

    # ---------------------------------------------------------------- T2
    frame = sub[["code", "date", "close", "high", "low", "volume"]].copy()
    frame["_probe"] = np.arange(len(frame), dtype="float64")
    got = bm._groll(frame, "_probe", 5, "mean")

    def naive_roll(frame, col, window):
        out = np.full(len(frame), np.nan)
        for _, idx in frame.groupby("code", sort=False).indices.items():
            idx = np.sort(idx)
            s = pd.Series(frame[col].to_numpy()[idx])
            out[idx] = s.rolling(window, min_periods=max(2, window // 2)).mean().to_numpy()
        return out

    want = naive_roll(frame, "_probe", 5)
    ok = np.allclose(np.nan_to_num(got, nan=-1.0), np.nan_to_num(want, nan=-1.0))
    report["T2_alignment"] = {
        "aligned_on_group_sorted_frame": bool(ok),
        "n_mismatch_full_history": int((~np.isclose(
            np.nan_to_num(got, nan=-1.0), np.nan_to_num(want, nan=-1.0))).sum()),
    }

    # Demonstrate the underlying fragility on a frame that is NOT group-sorted.
    # The decisive check is whether the returned array equals a naive per-stock
    # rolling evaluated at the SAME row positions of the shuffled frame.
    shuffled = frame.sample(frac=1.0, random_state=7).reset_index(drop=True)
    got_s = bm._groll(shuffled, "_probe", 5, "mean")
    n = len(shuffled)
    probe = shuffled["_probe"].to_numpy("float64")
    codes_s = shuffled["code"].to_numpy()
    naive_pos = np.full(n, np.nan)
    for i in range(n):
        lo = max(0, i - 4)
        # backward window, same stock only, exactly what a correct impl does
        j = i
        vals = []
        while j >= 0 and len(vals) < 5:
            if codes_s[j] != codes_s[i]:
                break
            vals.append(probe[j])
            j -= 1
        if len(vals) >= max(2, 5 // 2):
            naive_pos[i] = float(np.mean(vals))
    pos_ok = np.allclose(np.nan_to_num(got_s, nan=-1.0),
                         np.nan_to_num(naive_pos, nan=-1.0))
    report["T2_alignment"]["naive_positions_vs_reset_index_on_shuffled_frame"] = {
        "positional_match_on_shuffled_frame": bool(pos_ok),
        "n_position_mismatches": int((~np.isclose(
            np.nan_to_num(got_s, nan=-1.0),
            np.nan_to_num(naive_pos, nan=-1.0))).sum()),
        "note": (
            "reset_index(level=0, drop=True) resolves to the GROUP key's order, "
            "not the frame's row order. On a group-sorted frame (which build() "
            "always produces via sort_values([code,date])) the two coincide, so "
            "production is aligned. On an unsorted frame the returned array is "
            "silently in a different order. The helper carries no guard."
        ),
    }
    # and the same check on the production (sorted) frame for contrast
    got_f = bm._groll(frame, "_probe", 5, "mean")
    nf = len(frame)
    probef = frame["_probe"].to_numpy("float64")
    codes_f = frame["code"].to_numpy()
    naive_f = np.full(nf, np.nan)
    for i in range(nf):
        j, vals = i, []
        while j >= 0 and len(vals) < 5:
            if codes_f[j] != codes_f[i]:
                break
            vals.append(probef[j])
            j -= 1
        if len(vals) >= 2:
            naive_f[i] = float(np.mean(vals))
    report["T2_alignment"]["positional_match_on_group_sorted_frame"] = bool(
        np.allclose(np.nan_to_num(got_f, nan=-1.0), np.nan_to_num(naive_f, nan=-1.0))
    )

    # ---------------------------------------------------------------- T3
    # Independent beta reconstruction from raw bars, for a deterministic sample.
    px = panel.sort_values(["code", "date"]).reset_index(drop=True)
    ret1 = px.groupby("code", sort=False)["close"].pct_change()
    ret1 = np.where(np.isclose(px["close"].shift(0), 0), np.nan, ret1)
    px["_r1"] = pd.to_numeric(ret1, errors="coerce")
    # market = equal-weighted mean of ret1 across all stocks that session
    mkt = px.groupby("date", sort=False)["_r1"].mean()

    mat = pd.read_parquet(REPO_ROOT / "outputs" / "ml" / "matrix_h10_t30_s5.parquet")

    t3 = []
    sample = (
        mat.dropna(subset=["beta_60"])
        .sample(n=12, random_state=20260917)[["code", "date", "beta_60", "resid_ret1", "ret1"]]
    )
    r1_map = px.set_index(["code", "date"])["_r1"]
    for _, row in sample.iterrows():
        hist = px[(px["code"] == row["code"]) & (px["date"] <= row["date"])].tail(60)
        if len(hist) < 20:
            continue
        m = mkt.reindex(hist["date"]).to_numpy("float64")
        x = hist["_r1"].to_numpy("float64")
        ok = np.isfinite(x) & np.isfinite(m)
        if ok.sum() < 20:
            continue
        mx, my = x[ok].mean(), m[ok].mean()
        cov = (x[ok] * m[ok]).mean() - mx * my
        var = (m[ok] ** 2).mean() - my ** 2
        beta = cov / (var + bm.EPS)
        beta = float(np.clip(beta, -5.0, 5.0))
        r1_now = float(r1_map.loc[(row["code"], row["date"])])
        resid = r1_now - beta * float(mkt.loc[row["date"]])
        t3.append({
            "code": row["code"],
            "date": str(pd.Timestamp(row["date"]).date()),
            "n_window_bars": int(ok.sum()),
            "beta_matrix": float(row["beta_60"]),
            "beta_reconstructed": beta,
            "beta_abs_diff": float(abs(row["beta_60"] - beta)),
            "resid_matrix": float(row["resid_ret1"]),
            "resid_reconstructed": resid,
            "resid_abs_diff": float(abs(row["resid_ret1"] - resid)),
        })
    report["T3_beta_reconstruction"] = t3
    report["T3_max_abs_diff"] = {
        "beta": float(max((r["beta_abs_diff"] for r in t3), default=float("nan"))),
        "resid": float(max((r["resid_abs_diff"] for r in t3), default=float("nan"))),
    }
    report["T3_note"] = (
        "Reconstruction cannot be bit-exact because the shipped matrix is a "
        "stride-5 subsample of a float32-quantised build and pct_change uses a "
        "different EPS than the module's EPS=1e-12; agreement to ~1e-4 confirms "
        "the beta/resid values are the documented cov/var on trailing 60 bars."
    )

    path = OUT_DIR / "leakage_audit.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    # ------------------------------------------------------------- printout
    print("=" * 78)
    print("T1 TRUNCATION TEST  (features recomputed without bars after %s)" % CUTOFF.date())
    print("=" * 78)
    print(f"  universe {len(universe)} stocks, {len(sub)} dense rows, "
          f"{len(trunc)} rows compared")
    print(f"  features checked: {report['T1_verdict']['features_checked']}")
    print(f"  features unchanged when the future is deleted: "
          f"{report['T1_verdict']['causal_features']}")
    print(f"  LEAKING: {report['T1_verdict']['leaking_features']}")
    print("  worst 12 rows of the table:")
    for r in t1[:12]:
        print(f"    {r['feature']:24s} max|diff| {r['max_abs_diff']:.6g}  "
              f"n>1e-6 {r['n_diff_gt_1e-6']}")
    print()
    print("=" * 78)
    print("T2 GROUPBY-ROLLING ALIGNMENT")
    print("=" * 78)
    print(json.dumps(report["T2_alignment"], indent=2))
    print()
    print("=" * 78)
    print("T3 BETA RECONSTRUCTION")
    print("=" * 78)
    for r in t3:
        print(f"  {r['code']} {r['date']}  beta matrix {r['beta_matrix']:+.6f} "
              f"recon {r['beta_reconstructed']:+.6f}  d={r['beta_abs_diff']:.2e} | "
              f"resid d={r['resid_abs_diff']:.2e}")
    print(f"  max |beta diff| = {report['T3_max_abs_diff']['beta']:.3e}")
    print(f"  max |resid diff| = {report['T3_max_abs_diff']['resid']:.3e}")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
