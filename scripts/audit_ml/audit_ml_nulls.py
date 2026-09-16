"""ADVERSARIAL AUDIT 3/4 -- NULL TESTS for the walk-forward harness.

Question this file answers: **can `src/ml/walkforward.py` manufacture precision
out of pure noise?**

A harness reporting 15.98% OOS precision is evidence only if the same harness
reports ~base rate when the labels or features carry no information.  Twelve
variants are pushed through the *unmodified* production code path
(`wf.make_model` -> `wf.evaluate_fold` -> `wf.summarise`, exactly as
`src/ml/search.py` calls it):

  real                  shipped features + shipped label_high (must be 15.98%)
  perm_global_101/2/3   label_high globally shuffled (3 seeds)  <- key null
  perm_within_date_404  label shuffled inside each session -- the null that
                        specifically probes the `cs_*` cross-sectional features
  label_bernoulli_505   i.i.d. Bernoulli labels at the same base rate
  feat_gauss_7/8        every feature replaced by i.i.d. N(0,1)
  feat_permute_9        every feature column independently row-shuffled
  oracle_strong         a deliberately leaking feature (fwd_max_high + noise):
                        POSITIVE CONTROL proving the test has power
  oracle_weak           a mild leak (label_high + N(0,2)): minimum detectable
                        effect calibration
  feat_gauss_auc0       noise features + noise labels: double-null

Instrumentation method
----------------------
`wf.make_model` is wrapped in the worker so that the estimator it returns is a
recording proxy.  `evaluate_fold` then runs completely unmodified and we harvest
the training scores, test scores, labels and dates on the way through.  There is
no second implementation of the harness to drift out of sync: the number
reported here IS the number `wf.evaluate_fold` computed.

Nothing under `src/` or `experts/` is modified.  Output:
`outputs/ml/audit/nulls_audit.json`, `outputs/ml/audit/real_oos_scores.npz`.

Usage
-----
    python scripts/audit_ml/audit_ml_nulls.py --stage bench
    python scripts/audit_ml/audit_ml_nulls.py --stage battery --workers 3
    python scripts/audit_ml/audit_ml_nulls.py --stage auc
    python scripts/audit_ml/audit_ml_nulls.py --stage ceiling
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.ml import walkforward as wf  # noqa: E402

# Captured BEFORE any patch: `wf.evaluate_fold` resolves `make_model` from its
# module globals, so the recording wrapper must call this saved original.
_ORIG_MAKE_MODEL = wf.make_model

OUT_DIR = REPO_ROOT / "outputs" / "ml" / "audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MATRIX = REPO_ROOT / "outputs" / "ml" / "matrix_h10_t30_s5.parquet"
FINAL_HOLDOUT_START = "2026-01-01"
N_FOLDS = 5
HORIZON = 10
EMBARGO = 2
MIN_TRAIN_SESSIONS = 150
TARGET_RATE = 0.02

# Baseline configuration: identical to `fam_hgb_0` in src/ml/search.py, which is
# the published 15.98% / 1,790-signal result.
BASE_CFG = dict(name="null", model="hgb", params={}, feature_groups=[],
                label="label_high", target_rate=TARGET_RATE)

VARIANTS: list[tuple[str, str, int, str]] = [
    ("real", "real", 0, "shipped features + shipped label_high (control)"),
    ("perm_global_101", "perm_global", 101, "global label shuffle"),
    ("perm_global_202", "perm_global", 202, "global label shuffle"),
    ("perm_global_303", "perm_global", 303, "global label shuffle"),
    ("perm_within_date_404", "perm_within_date", 404,
     "label shuffled inside each session (preserves the per-date base rate)"),
    ("label_bernoulli_505", "label_bernoulli", 505,
     "i.i.d. Bernoulli labels at the same global base rate"),
    ("feat_gauss_7", "feat_gauss", 7, "all features ~ N(0,1), real labels"),
    ("feat_gauss_8", "feat_gauss", 8, "all features ~ N(0,1), real labels"),
    ("feat_gauss_auc0", "feat_gauss_auc0", 9,
     "N(0,1) features AND Bernoulli labels (double null)"),
    ("feat_permute_9", "feat_permute", 9,
     "each feature column independently row-permuted, real labels"),
    ("perm_train_only_606", "perm_train_only", 606,
     "labels shuffled in the TRAIN block only; test labels real. Isolates the "
     "fit+threshold path: a real model on real test labels is trained on noise"),
    ("perm_test_only_707", "perm_test_only", 707,
     "test labels shuffled inside each test block; training untouched. Isolates "
     "the EVALUATION path: can evaluate_fold report lift when the test labels "
     "carry no information"),
    ("oracle_strong", "oracle_strong", 11,
     "POSITIVE CONTROL: fwd_max_high + N(0,0.3) added as a feature"),
    ("oracle_weak", "oracle_weak", 12,
     "MDE CALIBRATION: label_high + N(0,2) added as a feature"),
]


# ---------------------------------------------------------------------------
# variant construction -- may return a shallow copy; pandas CoW keeps the
# parent frame untouched.  Verified by the caller on `real`.
# ---------------------------------------------------------------------------
def _apply_variant(frame: pd.DataFrame, kind: str, seed: int) -> pd.DataFrame:
    n = len(frame)
    if kind == "real":
        return frame
    rng = np.random.default_rng(seed)
    if kind in ("perm_global", "perm_within_date", "label_bernoulli",
                "feat_gauss_auc0"):
        out = frame.copy(deep=False)
        v = out["label_high"].to_numpy("float64")   # float32 -> float64 => new array
        if kind == "perm_global":
            ok = np.isfinite(v)
            v[ok] = rng.permutation(v[ok])
        elif kind == "perm_within_date":
            for _, ix in out.groupby("date", sort=False).indices.items():
                ix = np.asarray(ix)
                sub = ix[np.isfinite(v[ix])]
                v[sub] = rng.permutation(v[sub])
        else:
            ok = np.isfinite(v)
            p = float(np.nanmean(v))
            v[ok] = (rng.random(int(ok.sum())) < p).astype("float64")
        out["label_high"] = v
        if kind == "feat_gauss_auc0":
            for col in wf.feature_columns(frame):
                out[col] = rng.standard_normal(n).astype("float32")
        return out
    if kind == "feat_gauss":
        out = frame.copy(deep=False)
        for col in wf.feature_columns(frame):
            out[col] = rng.standard_normal(n).astype("float32")
        return out
    if kind == "feat_permute":
        out = frame.copy(deep=False)
        for col in wf.feature_columns(frame):
            out[col] = rng.permutation(frame[col].to_numpy("float32"))
        return out
    if kind == "oracle_strong":
        out = frame.copy(deep=False)
        out["ORACLE_fwd"] = (
            frame["fwd_max_high"].to_numpy("float64") + rng.normal(0.0, 0.3, n)
        ).astype("float32")
        return out
    if kind == "oracle_weak":
        out = frame.copy(deep=False)
        y = np.nan_to_num(frame["label_high"].to_numpy("float64"), nan=0.0)
        out["ORACLE_leaky"] = (y + rng.normal(0.0, 2.0, n)).astype("float32")
        return out
    if kind in ("perm_train_only", "perm_test_only"):
        return frame          # applied per fold, see _apply_fold_label_null
    raise ValueError(kind)


def _apply_fold_label_null(frame: pd.DataFrame, kind: str, seed: int,
                           fold) -> pd.DataFrame:
    """Fold-scoped label shuffle for the two path-isolating nulls.

    `perm_train_only` corrupts the training labels only, so a model that fits
    train (now noise) and is scored on the *real* test labels must return the
    base rate.  `perm_test_only` leaves training intact and corrupts the test
    labels, so a harness that still reports lift is fabricating it in the
    evaluation path (threshold, masking or averaging).
    """
    sess = fold.train_sessions if kind == "perm_train_only" else fold.test_sessions
    out = frame.copy(deep=False)
    v = out["label_high"].to_numpy("float64")
    mask = out["date"].isin(sess).to_numpy()
    finite = mask & np.isfinite(v)
    rng = np.random.default_rng(seed)
    v[finite] = rng.permutation(v[finite])
    out["label_high"] = v
    return out


# ---------------------------------------------------------------------------
# score recorder -- wraps wf.make_model, leaves evaluate_fold untouched
# ---------------------------------------------------------------------------
class _RecordingModel:
    """Delegates every attribute to the real estimator, records predict_proba."""

    def __init__(self, inner):
        self._inner = inner
        self.calls: list[tuple[np.ndarray, np.ndarray]] = []

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def fit(self, x, y):
        self._inner.fit(x, y)
        return self

    def predict_proba(self, x):
        out = self._inner.predict_proba(x)
        self.calls.append((np.asarray(out[:, 1], dtype="float64"), None))
        return out


_FOLD_STATE: dict = {}


def _patched_make_model(cfg, seed: int = 0):
    assert wf.make_model is _patched_make_model, "patch not installed"
    model = _RecordingModel(_ORIG_MAKE_MODEL(cfg, seed))
    _FOLD_STATE["model"] = model
    return model


_MATRIX: pd.DataFrame | None = None
_FOLDS: list | None = None


def _init_worker(matrix_path: str) -> None:
    global _MATRIX, _FOLDS
    wf.make_model = _patched_make_model          # process-local patch only
    _MATRIX = pd.read_parquet(matrix_path)
    sessions = np.sort(_MATRIX["date"].unique())
    _FOLDS = wf.folds(
        sessions, n_folds=N_FOLDS, horizon=HORIZON, embargo=EMBARGO,
        min_train_sessions=MIN_TRAIN_SESSIONS, final_holdout_start=FINAL_HOLDOUT_START,
    )


def _auc(y: np.ndarray, s: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(roc_auc_score(y, s))


def _frontier_max_precision(y: np.ndarray, s: np.ndarray, min_signals: int) -> dict:
    """Best precision reachable by ANY threshold on this test block.

    The p-hacking ceiling: what a search tuning the threshold on the test block
    could report, against which the harness's train-only threshold is compared.
    """
    order = np.argsort(-s, kind="mergesort")
    ys = y[order]
    tp = np.cumsum(ys)
    cum = np.arange(1, len(ys) + 1)
    out = {"min_signals": int(min_signals), "max_precision": float("nan"),
           "at_signals": 0, "at_share": float("nan")}
    if len(ys) >= min_signals:
        sl = slice(min_signals - 1, len(ys))
        prec = tp[sl] / cum[sl]
        j = int(np.argmax(prec))
        k = min_signals + j
        out.update(max_precision=float(prec[j]), at_signals=int(k),
                   at_share=float(k / len(ys)))
    return out


def _run_variant(job: tuple[str, str, int]) -> dict:
    name, kind, seed = job
    t0 = time.time()
    try:
        assert _MATRIX is not None and _FOLDS is not None
        frame = _apply_variant(_MATRIX, kind, seed)
        cfg = wf.Config(**BASE_CFG)

        official: list[dict] = []
        cap: list[dict] = []
        for fold in _FOLDS:
            fold_frame = frame
            if kind in ("perm_train_only", "perm_test_only"):
                fold_frame = _apply_fold_label_null(frame, kind, seed, fold)
            train = fold_frame[fold_frame["date"].isin(fold.train_sessions)]
            test = fold_frame[fold_frame["date"].isin(fold.test_sessions)]
            _FOLD_STATE.clear()
            res = wf.evaluate_fold(train, test, cfg, 0)
            official.append(res)
            rec = _FOLD_STATE.get("model")
            if rec is None or "error" in res or len(rec.calls) < 2:
                continue
            s_tr = rec.calls[0][0]
            s_te = rec.calls[1][0]
            tr = train[train["label_high"].notna()
                       & train["resolved"].fillna(0).astype(bool)]
            te = test[test["label_high"].notna()]
            thr = wf.pick_threshold(s_tr, tr["label_high"].to_numpy("float64"),
                                    cfg.target_rate)
            pred_te = s_te >= thr
            cap.append({
                "fold": fold.name,
                "s_te": s_te.astype("float32"),
                "y_te": te["label_high"].to_numpy("float64"),
                "d_te": te["date"].to_numpy(),
                "code_te": te["code"].to_numpy(),
                "threshold": float(thr),
                "monotone": bool(np.all(np.diff(np.sort(s_te)) >= -1e-12)),
                "harness_precision": res["oos_precision"],
                "audit_precision": float(te["label_high"].to_numpy("float64")[pred_te].mean())
                if pred_te.any() else float("nan"),
                "harness_signals": int(res["oos_signals"]),
                "audit_signals": int(pred_te.sum()),
            })

        summary = wf.summarise(official)
        summary["config"] = name
        summary["variant"] = kind
        summary["seed"] = int(seed)
        summary["seconds"] = round(time.time() - t0, 1)
        # Per-fold detail, so every fold can be checked against its OWN base rate
        # instead of only against the pooled figure.  This matters because
        # `summarise` reports oos_precision signal-weighted but oos_base_rate as
        # an unweighted mean of folds -- the two are not directly comparable
        # when folds have very different base rates (here 2.7% .. 8.0%).
        summary["per_fold_detail"] = [
            {"fold": r.get("config"), "n_train": r.get("n_train"),
             "n_test": r.get("n_test"), "signals": r.get("oos_signals"),
             "precision": r.get("oos_precision"),
             "base_rate": r.get("oos_base_rate"),
             "lift": (r.get("oos_precision") / r.get("oos_base_rate")
                      if r.get("oos_base_rate") else None),
             "distinct_stocks": r.get("oos_distinct_stocks"),
             "distinct_dates": r.get("oos_distinct_dates"),
             "threshold": r.get("threshold")}
            for r in official if "error" not in r
        ]

        if cap:
            s_all = np.concatenate([c["s_te"].astype("float64") for c in cap])
            y_all = np.concatenate([c["y_te"] for c in cap])
            d_all = np.concatenate([c["d_te"] for c in cap])
            k_all = np.concatenate([c["code_te"] for c in cap])
            summary["pooled_auc"] = _auc(y_all, s_all)
            summary["pooled_rows"] = int(len(y_all))
            summary["pooled_positives"] = int(y_all.sum())
            summary["pooled_base_rate"] = float(y_all.mean())
            summary["harness_vs_audit_precision_max_abs_diff"] = float(
                np.nanmax([abs(c["harness_precision"] - c["audit_precision"])
                           for c in cap]))
            summary["harness_vs_audit_signals_max_abs_diff"] = int(
                max(abs(c["harness_signals"] - c["audit_signals"]) for c in cap))
            summary["scores_monotone"] = bool(all(c["monotone"] for c in cap))
            summary["test_oracle_frontier"] = [
                _frontier_max_precision(y_all, s_all, k) for k in (100, 500, 2000)
            ]
            if kind == "real":
                np.savez_compressed(
                    OUT_DIR / "real_oos_scores.npz",
                    scores=s_all.astype("float32"), labels=y_all,
                    dates=d_all.astype("datetime64[D]").astype("int64"),
                    codes=k_all,
                    fold_thresholds=np.array([c["threshold"] for c in cap]))
        return summary
    except Exception:  # noqa: BLE001
        return {"config": name, "variant": kind, "seed": int(seed),
                "error": traceback.format_exc(limit=4)}


# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------
def stage_bench(args) -> None:
    frame = pd.read_parquet(MATRIX)
    sessions = np.sort(frame["date"].unique())
    fold_list = wf.folds(sessions, n_folds=N_FOLDS, horizon=HORIZON, embargo=EMBARGO,
                         min_train_sessions=MIN_TRAIN_SESSIONS,
                         final_holdout_start=FINAL_HOLDOUT_START)
    cfg = wf.Config(**BASE_CFG)
    total = 0.0
    for fold in fold_list:
        train = frame[frame["date"].isin(fold.train_sessions)]
        test = frame[frame["date"].isin(fold.test_sessions)]
        t0 = time.time()
        res = wf.evaluate_fold(train, test, cfg, 0)
        dt = time.time() - t0
        total += dt
        print(json.dumps({"fold": fold.name, "seconds": round(dt, 1),
                          "oos_precision": res.get("oos_precision"),
                          "oos_signals": res.get("oos_signals"),
                          "insample_precision": res.get("insample_precision"),
                          "n_train": res.get("n_train"),
                          "n_test": res.get("n_test")}, indent=None))
    print(f"\nreal config, 4 folds: {total:.1f}s serial")
    print(f"projected battery (3 workers, {len(VARIANTS)} variants): "
          f"{len(VARIANTS) * total / 3 / 60:.1f} min")


def stage_battery(args) -> None:
    jobs = [v for v in VARIANTS if not args.only or v[0] in set(args.only.split(","))]
    print(f"battery: {len(jobs)} variants, {args.workers} workers", flush=True)
    t0 = time.time()
    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_worker,
                             initargs=(str(MATRIX),)) as pool:
        futures = {pool.submit(_run_variant, (n, k, s)): n for n, k, s, _ in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            res = fut.result()
            results.append(res)
            if "error" in res:
                print(f"[{i}/{len(jobs)}] {res['config']:22s} ERROR "
                      f"{res['error'][-500:]}", flush=True)
            else:
                print(f"[{i}/{len(jobs)}] {res['config']:22s} "
                      f"OOS {res['oos_precision']*100:6.2f}% "
                      f"({res['oos_signals']:>6d} sig) base "
                      f"{res['oos_base_rate']*100:5.2f}% "
                      f"lift {res['oos_lift']:5.2f}x "
                      f"AUC {res.get('pooled_auc', float('nan')):.4f} "
                      f"{res['seconds']:6.0f}s", flush=True)

    order = {n: i for i, (n, *_r) in enumerate(VARIANTS)}
    results.sort(key=lambda r: order.get(r["config"], 99))
    payload = {
        "matrix": str(MATRIX.relative_to(REPO_ROOT)),
        "folds": N_FOLDS, "horizon": HORIZON, "embargo": EMBARGO,
        "min_train_sessions": MIN_TRAIN_SESSIONS,
        "final_holdout_start": FINAL_HOLDOUT_START,
        "baseline_cfg": BASE_CFG,
        "battery_seconds": round(time.time() - t0, 1),
        "instrumentation": (
            "wf.make_model patched in-process to a recording proxy; "
            "wf.evaluate_fold and wf.summarise executed unmodified."
        ),
        "variants": {n: {"kind": k, "seed": s, "description": d}
                     for n, k, s, d in VARIANTS},
        "results": results,
    }
    path = OUT_DIR / "nulls_audit.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {path}  ({time.time()-t0:.0f}s)", flush=True)


def stage_auc(args) -> None:
    """Single-feature AUC scan against the real label, plus its own null."""
    print("loading matrix ...", flush=True)
    frame = wf.load_matrix()
    cols = wf.feature_columns(frame)
    y = frame["label_high"].to_numpy("float64")
    finite_y = np.isfinite(y)
    print(f"{len(cols)} features, {int(finite_y.sum())} rows with a label", flush=True)

    dates = frame["date"]
    rows = []
    for i, col in enumerate(cols):
        v = frame[col].to_numpy("float64")
        ok = finite_y & np.isfinite(v)
        auc = _auc(y[ok], v[ok])
        # Within-session percentile rank: removes the market/date component and
        # isolates whether the feature selects *stocks* rather than *days*.
        r = frame.groupby("date", sort=False)[col].rank(pct=True).to_numpy("float64")
        ok2 = finite_y & np.isfinite(r)
        rows.append({"feature": col, "auc": auc,
                     "auc_within_date_rank": _auc(y[ok2], r[ok2]),
                     "finite_share": float(ok.mean())})
        del v, r
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(cols)}", flush=True)
    df = pd.DataFrame(rows).sort_values("auc", ascending=False)
    df.to_csv(OUT_DIR / "feature_auc_scan.csv", index=False)

    # Empirical null: with the label permuted, what is the best |AUC| any of
    # these features can reach by chance?  This is the significance threshold
    # that a "suspicious" AUC must clear.
    null_max, null_all = [], []
    for seed in (11, 22, 33):
        rng = np.random.default_rng(seed)
        yp = y.copy()
        yp[finite_y] = rng.permutation(yp[finite_y])
        mx, mx_name = 0.0, ""
        for col in cols:
            v = frame[col].to_numpy("float64")
            ok = np.isfinite(v) & finite_y
            a = _auc(yp[ok], v[ok])
            if np.isfinite(a):
                null_all.append(a)
                a = abs(a - 0.5) + 0.5
            else:
                a = 0.0
            if a > mx:
                mx, mx_name = a, col
        null_max.append({"seed": seed, "max_abs_auc_dev": float(mx),
                         "feature": mx_name})
        print(f"  null scan seed {seed}: max |AUC-0.5| {mx:.4f} ({mx_name})",
              flush=True)

    na = np.array(null_all, dtype="float64")
    payload = {
        "n_features": len(cols),
        "n_rows": int(len(frame)),
        "base_rate": float(np.nanmean(y)),
        "top25": df.head(25).to_dict("records"),
        "flagged_auc_gt_0.75": df[df["auc"] > 0.75].to_dict("records"),
        "flagged_auc_lt_0.25": df[df["auc"] < 0.25].to_dict("records"),
        "permutation_null": {
            "n_values": int(len(na)),
            "mean": float(na.mean()),
            "sd": float(na.std(ddof=1)),
            "max": float(na.max()),
            "min": float(na.min()),
            "abs_dev_max": float(np.abs(na - 0.5).max()),
            "per_seed_best": null_max,
        },
        "note": (
            "auc = single-feature AUC against label_high over all finite rows. "
            "auc_within_date_rank = AUC of the feature's within-session "
            "percentile rank, which removes the market/date component and "
            "isolates stock selection. The permutation null is the largest "
            "|AUC-0.5| reachable by the best of these features when the label is "
            "pure noise -- the threshold against which 'suspicious' is judged."
        ),
    }
    (OUT_DIR / "feature_auc_scan.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(df.head(15).to_string(index=False))
    print(f"\nwrote {OUT_DIR/'feature_auc_scan.csv'}")


def stage_ceiling(args) -> None:
    """What OOS precision is reachable by chance at a 2% publication rate?"""
    from scipy import stats

    r = json.loads((OUT_DIR / "nulls_audit.json").read_text(encoding="utf-8"))
    null_kinds = {"perm_global", "perm_within_date", "label_bernoulli",
                  "feat_gauss_auc0"}
    perms = [x for x in r["results"]
             if x.get("variant") in null_kinds and "error" not in x]

    real = next(x for x in r["results"] if x["config"] == "real")
    frame = wf.load_matrix()
    sessions = np.sort(frame["date"].unique())
    fold_list = wf.folds(sessions, n_folds=N_FOLDS, horizon=HORIZON, embargo=EMBARGO,
                         min_train_sessions=MIN_TRAIN_SESSIONS,
                         final_holdout_start=FINAL_HOLDOUT_START)
    n_te = 0
    for f in fold_list:
        te = frame[frame["date"].isin(f.test_sessions)]
        n_te += int(te["label_high"].notna().sum())

    def hyper(k: int, N: int, pi: float) -> dict:
        """Precision when publishing k of N rows with no information at all.

        Drawing k rows without replacement from a population with K = pi*N
        positives: SD(precision) = sqrt(pi(1-pi)(N-k)/(k(N-1))).
        """
        sd = math.sqrt(max(pi * (1 - pi) * (N - k) / (k * (N - 1)), 1e-18))
        return {
            "k_signals": int(k), "of_rows": int(N), "base_rate": pi,
            "mean_precision": pi, "sd": sd,
            "p975": pi + 1.96 * sd, "p999": pi + 3.09 * sd,
            "p99_of_max_over_M_independent_tries": {
                str(M): pi + sd * math.sqrt(2 * math.log(M))
                for M in (10, 100, 1000)
            },
        }

    pi_obs = float(real["oos_base_rate"])
    k_obs = int(real["oos_signals"])
    null_p = np.array([x["oos_precision"] for x in perms], dtype="float64")
    null_l = np.array([x["oos_lift"] for x in perms], dtype="float64")
    null_a = np.array([x.get("pooled_auc", np.nan) for x in perms], dtype="float64")

    out = {
        "real_baseline": {
            "oos_precision": real["oos_precision"], "oos_signals": k_obs,
            "oos_base_rate": pi_obs, "oos_lift": real["oos_lift"],
            "insample_precision": real["insample_precision"],
            "per_fold_oos": real["per_fold_oos"],
            "per_fold_signals": real["per_fold_signals"],
            "folds_above_base": real["folds_above_base"],
            "pooled_auc": real.get("pooled_auc"),
        },
        "chance_at_target_2pct_publication": hyper(int(round(0.02 * n_te)), n_te, pi_obs),
        "chance_at_observed_publication": hyper(k_obs, n_te, pi_obs),
        "empirical_null": {
            "variants": [{"config": x["config"],
                          "oos_precision": x.get("oos_precision"),
                          "oos_signals": x.get("oos_signals"),
                          "oos_base_rate": x.get("oos_base_rate"),
                          "oos_lift": x.get("oos_lift"),
                          "pooled_auc": x.get("pooled_auc")} for x in perms],
            "precision_mean": float(np.nanmean(null_p)),
            "precision_min": float(np.nanmin(null_p)),
            "precision_max": float(np.nanmax(null_p)),
            "lift_mean": float(np.nanmean(null_l)),
            "lift_min": float(np.nanmin(null_l)),
            "lift_max": float(np.nanmax(null_l)),
            "auc_mean": float(np.nanmean(null_a)),
            "auc_min": float(np.nanmin(null_a)),
            "auc_max": float(np.nanmax(null_a)),
            "k_nulls": int(len(perms)),
        },
    }
    if len(null_p) > 1:
        sd_p = float(np.std(null_p, ddof=1))
        z = (real["oos_precision"] - float(np.mean(null_p))) / max(sd_p, 1e-12)
        sd_l = float(np.std(null_l, ddof=1))
        out["real_vs_null"] = {
            "null_precision_mean": float(np.mean(null_p)),
            "null_precision_sd": sd_p,
            "z_precision": float(z),
            "lift_mean": float(np.mean(null_l)),
            "lift_sd": sd_l,
            "lift_z": float((real["oos_lift"] - float(np.mean(null_l)))
                            / max(sd_l, 1e-12)),
            "p_one_sided_normal": float(1.0 - stats.norm.cdf(z)),
            "caveat": (
                f"only {len(null_p)} null draws; the normal approximation is "
                "used as an illustration, not as a calibrated p-value."
            ),
        }
    (OUT_DIR / "null_ceiling.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out, indent=2, default=str))
    print(f"\nwrote {OUT_DIR/'null_ceiling.json'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", default="battery",
                    choices=["bench", "battery", "auc", "ceiling"])
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--only", default="", help="comma-separated variant names")
    args = ap.parse_args()
    {"bench": stage_bench, "battery": stage_battery,
     "auc": stage_auc, "ceiling": stage_ceiling}[args.stage](args)


if __name__ == "__main__":
    main()
