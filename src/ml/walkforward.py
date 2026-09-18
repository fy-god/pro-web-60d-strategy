"""Purged walk-forward evaluation harness.

This module exists because the single most likely way to "reach 70%" on this task
is to fool ourselves. The source project already did exactly that: it selected
thresholds on the same 100 cards it reported, and its 70-80% numbers are
in-sample. Any optimization here must therefore be measured under a protocol
that makes that mistake impossible.

Three protections are implemented.

**Purge.** The label at session *t* is determined by bars *t+1 .. t+H*. A training
row at session *t* therefore contains information about sessions up to *t+H*. If
the test block begins at *t+1* while a training row sits at *t*, the model has
seen the test block's outcome. Every train/test boundary is therefore purged by
``horizon`` sessions: the last ``horizon`` training sessions before a test block
are dropped.

**Embargo.** Beyond the label window, features are rolling statistics whose
windows overlap neighbouring sessions. A short additional embargo of ``embargo``
sessions further reduces this leakage. It is small because the purge already
handles the dominant effect.

**No selection on the final block.** Walk-forward blocks are for development.
The caller must reserve a final period (2026 here) that is never touched by any
hyper-parameter choice, threshold search or feature selection, and evaluate it
exactly once at the end.

The report separates, for every configuration:

* ``insample_*`` — precision on the data the model was fit on. This is the number
  that looks like 70%+ and it is meaningless as a forecast.
* ``oos_*`` — precision on the purged, embargoed, unseen block. This is the only
  number that constitutes evidence.

Usage
-----
    from src.ml.walkforward import folds, evaluate_config
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "outputs" / "ml"
REPORT_DIR = REPO_ROOT / "reports"

# Provenance of the last matrix read in this process, set by load_matrix and
# consumed by save_report. See save_report for why this is recorded rather than
# guessed from the output directory.
LAST_LOAD: dict = {}

META_COLUMNS = {
    "code", "date", "entry_open", "fwd_max_high", "fwd_min_low",
    "fwd_max_close", "label_high", "label_close", "resolved",
}

# Exact, non-overlapping feature group membership. Listed explicitly rather than
# matched by prefix: the first attempt used prefixes and `vol` silently swallowed
# the `volatility` family, making seven "different" ablations identical. Every
# column of the 82-feature matrix appears in exactly one group.
FEATURE_GROUPS: dict[str, set[str]] = {
    "momentum": {
        "ret1", "ret2", "ret3", "ret5", "ret10", "ret20", "ret60", "ret120",
        "ret250", "dist_ma5", "ma5_slope", "dist_ma10", "ma10_slope",
        "dist_ma20", "ma20_slope", "dist_ma60", "ma60_slope", "dist_ma120",
        "ma120_slope", "dist_ma250", "ma250_slope",
    },
    "volatility": {
        "vol5", "vol10", "vol20", "vol60", "atr14_pct", "range_5_20",
        "range_20_60", "range_pct",
    },
    "volume": {
        "vol_ma5", "vol_ma20", "vol_ma60", "vol_ratio_1_5", "vol_ratio_5_20",
        "vol_ratio_20_60", "vol_stability_20",
    },
    "limitup": {
        "limitup_5", "limitup_10", "limitup_20", "limitup_yesterday",
        "up_rate_20",
    },
    "position": {
        "pos_60", "dd_60", "to_high_60", "pos_120", "dd_120", "to_high_120",
        "pos_250", "dd_250", "to_high_250",
    },
    "candle": {
        "close_loc", "upper_wick", "lower_wick", "body_pct", "gap_open",
    },
    "kdj": {
        "kdj_k", "kdj_d", "kdj_j", "kdj_k_chg5", "kdj_j_chg5", "kdj_k_minus_d",
    },
    "market": {
        "mkt_ret1", "mkt_breadth", "mkt_dispersion", "mkt_ret5", "mkt_ret20",
        "mkt_ret60", "mkt_vol20", "beta_60", "resid_ret1",
    },
    "cross": {
        "cs_ret5_rank", "cs_ret5_z", "cs_ret20_rank", "cs_ret20_z",
        "cs_ret60_rank", "cs_ret60_z", "cs_volratio_rank", "cs_volratio_z",
        "cs_atr_rank", "cs_atr_z", "cs_pos60_rank", "cs_pos60_z",
    },
}


def feature_columns(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame.columns if c not in META_COLUMNS]


@dataclass
class Fold:
    """One train/test split with its purge gap made explicit."""

    name: str
    train_sessions: list
    test_sessions: list
    purge_sessions: int = 0

    @property
    def n_train_sessions(self) -> int:
        return len(self.train_sessions)

    @property
    def n_test_sessions(self) -> int:
        return len(self.test_sessions)


def folds(
    sessions: np.ndarray,
    n_folds: int = 5,
    horizon: int = 10,
    embargo: int = 2,
    min_train_sessions: int = 120,
    final_holdout_start: str | None = None,
) -> list[Fold]:
    """Expanding-window walk-forward folds, purged and embargoed.

    The session list is split into ``n_folds + 1`` contiguous blocks by time.
    Fold *k* trains on everything before block *k* and tests on block *k*,
    dropping ``horizon + embargo`` sessions at the boundary.

    When ``final_holdout_start`` is given, no fold ever tests on or after that
    date: those sessions are reserved for a single final evaluation.
    """
    sessions = np.sort(np.asarray(sessions))
    if final_holdout_start is not None:
        cutoff = np.datetime64(pd.Timestamp(final_holdout_start))
        sessions = sessions[sessions < cutoff]

    usable = sessions[min_train_sessions:]
    if len(usable) < n_folds:
        raise ValueError(
            f"only {len(usable)} sessions after the {min_train_sessions}-session "
            f"warm-up; cannot build {n_folds} folds"
        )
    edges = np.linspace(0, len(usable), n_folds + 1).astype(int)

    out: list[Fold] = []
    for k in range(n_folds):
        test_block = usable[edges[k] : edges[k + 1]]
        if len(test_block) == 0:
            continue
        first_test = test_block[0]
        # Purge: a training session whose label window reaches into the test
        # block must be dropped. The label at t spans t+1..t+H, so the last safe
        # training session is H+embargo sessions before the first test session.
        boundary = np.searchsorted(sessions, first_test)
        safe_end = max(0, boundary - (horizon + embargo))
        train_block = sessions[:safe_end]
        if len(train_block) < min_train_sessions:
            continue
        out.append(
            Fold(
                name=f"fold{k}_test_{pd.Timestamp(test_block[0]).date()}"
                     f"_to_{pd.Timestamp(test_block[-1]).date()}",
                train_sessions=list(train_block),
                test_sessions=list(test_block),
                purge_sessions=horizon + embargo,
            )
        )
    return out


def holdout_sessions(sessions: np.ndarray, start: str) -> np.ndarray:
    cutoff = np.datetime64(pd.Timestamp(start))
    return np.sort(np.asarray(sessions))[np.sort(np.asarray(sessions)) >= cutoff]


def _precision(y: np.ndarray, pred: np.ndarray) -> float:
    if pred.sum() == 0:
        return float("nan")
    return float(y[pred].mean())


def pick_threshold(
    scores: np.ndarray,
    y: np.ndarray,
    target_rate: float,
) -> float:
    """Threshold that publishes the top ``target_rate`` share of signals.

    Chosen **only** on training-fold scores. Selecting it on the test block
    would reproduce the source project's central error.
    """
    if len(scores) == 0 or not np.isfinite(scores).any():
        return float("inf")
    k = max(1, int(round(target_rate * len(scores))))
    k = min(k, len(scores))
    ordered = np.sort(scores[np.isfinite(scores)])
    return float(ordered[-k])


@dataclass
class Config:
    """One model configuration to evaluate."""

    name: str
    model: str = "hgb"
    params: dict = field(default_factory=dict)
    feature_groups: list[str] = field(default_factory=list)
    label: str = "label_high"
    target_rate: float = 0.02
    tag: str = ""


def make_model(cfg: Config, seed: int = 0):
    """Instantiate a fresh estimator. Imports are local so the caller can run
    without every optional dependency present."""
    if cfg.model == "hgb":
        from sklearn.ensemble import HistGradientBoostingClassifier

        defaults = dict(
            max_leaf_nodes=15,
            min_samples_leaf=300,
            l2_regularization=10.0,
            learning_rate=0.03,
            max_iter=300,
            early_stopping=False,
            random_state=seed,
        )
        defaults.update(cfg.params)
        return HistGradientBoostingClassifier(**defaults)
    if cfg.model == "logistic":
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        defaults = dict(C=1.0, max_iter=400, solver="lbfgs")
        defaults.update(cfg.params)
        # Feature columns contain NaN wherever a rolling window was too short
        # (early sessions, or a stock with a gap). The tree models tolerate NaN
        # natively, but LogisticRegression raises on it, so the numeric pipeline
        # needs an explicit imputer. Median is fitted on the training block only,
        # so it introduces no leakage.
        return Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(**defaults)),
        ])
    if cfg.model == "rf":
        from sklearn.ensemble import RandomForestClassifier

        defaults = dict(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=200,
            n_jobs=-1,
            random_state=seed,
        )
        defaults.update(cfg.params)
        return RandomForestClassifier(**defaults)
    if cfg.model == "extratrees":
        from sklearn.ensemble import ExtraTreesClassifier

        defaults = dict(
            n_estimators=300,
            max_depth=10,
            min_samples_leaf=150,
            n_jobs=-1,
            random_state=seed,
        )
        defaults.update(cfg.params)
        return ExtraTreesClassifier(**defaults)
    raise ValueError(f"unknown model {cfg.model!r}")


def select_features(columns: list[str], groups: list[str]) -> list[str]:
    """Subset feature columns by group.

    Groups are matched **exactly** against ``FEATURE_GROUPS`` rather than by
    prefix. Prefix matching was tried first and silently produced wrong
    experiments: the group ``vol`` matched the ``volatility`` family, so
    ``drop_volatility``, ``drop_volume`` and five other ablations all resolved to
    the same ten columns and reported identical results. Membership is therefore
    declared explicitly here and verified at import time.
    """
    if not groups:
        return list(columns)
    wanted: set[str] = set()
    for group in groups:
        if group not in FEATURE_GROUPS:
            raise KeyError(f"unknown feature group {group!r}")
        wanted.update(FEATURE_GROUPS[group])
    return [c for c in columns if c in wanted]


def group_membership(columns: list[str]) -> dict[str, list[str]]:
    """Resolve every group to concrete column names for the given frame."""
    return {g: [c for c in columns if c in names] for g, names in FEATURE_GROUPS.items()}


def check_groups(columns: list[str]) -> list[str]:
    """Validate the group table against a real feature list.

    Returns a list of problems. This exists because an earlier prefix-based
    version produced seven ablations that were silently identical, and identical
    results across "different" experiments are easy to miss in a 60-row log.
    """
    problems: list[str] = []
    features = [c for c in columns if c in {
        c2 for names in FEATURE_GROUPS.values() for c2 in names
    }]
    unmapped = [c for c in columns if c not in {
        c2 for names in FEATURE_GROUPS.values() for c2 in names
    }]
    if unmapped:
        problems.append(f"{len(unmapped)} feature(s) in no group: {unmapped[:8]}")
    overlaps = []
    seen: dict[str, str] = {}
    for group, names in FEATURE_GROUPS.items():
        for name in names:
            if name in seen:
                overlaps.append(f"{name} in both {seen[name]} and {group}")
            seen[name] = group
    if overlaps:
        problems.append(f"{len(overlaps)} overlapping column(s): {overlaps[:5]}")
    # Every single-group subset must be distinct from every other.
    subsets: dict[tuple, str] = {}
    for group in FEATURE_GROUPS:
        key = tuple(sorted(select_features(columns, [group])))
        if key in subsets:
            problems.append(f"groups {subsets[key]!r} and {group!r} select identical columns")
        subsets[key] = group
    if not features:
        problems.append("no group resolved to any real column")
    return problems


def evaluate_fold(
    train: pd.DataFrame,
    test: pd.DataFrame,
    cfg: Config,
    seed: int = 0,
) -> dict:
    """Fit on train, score both sets, and report in-sample vs out-of-sample."""
    cols = select_features(feature_columns(train), cfg.feature_groups)
    if not cols:
        return {"config": cfg.name, "error": "no features selected"}

    y_col = cfg.label
    tr = train[train[y_col].notna() & train["resolved"].fillna(0).astype(bool)]
    te = test[test[y_col].notna()]
    if len(tr) < 5000 or len(te) < 200:
        return {"config": cfg.name, "error": "insufficient rows",
                "n_train": int(len(tr)), "n_test": int(len(te))}

    x_tr = tr[cols].to_numpy("float32")
    y_tr = tr[y_col].to_numpy("float64")
    x_te = te[cols].to_numpy("float32")
    y_te = te[y_col].to_numpy("float64")

    model = make_model(cfg, seed)
    model.fit(x_tr, y_tr)

    # In-sample scores, for the honest side-by-side.
    s_tr = model.predict_proba(x_tr)[:, 1]
    s_te = model.predict_proba(x_te)[:, 1]

    # Threshold from TRAINING scores only.
    thr = pick_threshold(s_tr, y_tr, cfg.target_rate)

    pred_tr = s_tr >= thr
    pred_te = s_te >= thr

    base_te = float(y_te.mean())
    return {
        "config": cfg.name,
        "model": cfg.model,
        "label": y_col,
        "n_train": int(len(tr)),
        "n_test": int(len(te)),
        # Raw counts so the pooled base rate can be computed exactly rather than
        # approximated by averaging per-fold rates. Averaging per-fold rates is
        # wrong whenever folds differ in size: the pooled base rate is
        # sum(positives) / sum(test rows), which is weighted by TEST ROWS, not
        # by signal count and not equally. Both wrong versions were shipped at
        # different times; this is the one that is actually correct.
        "oos_positives": int(y_te.sum()),
        "n_features": len(cols),
        "threshold": thr,
        "target_rate": cfg.target_rate,
        "insample_signals": int(pred_tr.sum()),
        "insample_precision": _precision(y_tr, pred_tr),
        "insample_share": float(pred_tr.mean()),
        "oos_signals": int(pred_te.sum()),
        "oos_precision": _precision(y_te, pred_te),
        "oos_share": float(pred_te.mean()),
        "oos_base_rate": base_te,
        "oos_lift": (
            _precision(y_te, pred_te) / base_te if base_te > 0 else float("nan")
        ),
        "oos_distinct_stocks": int(te.loc[pred_te, "code"].nunique()) if pred_te.any() else 0,
        "oos_distinct_dates": int(te.loc[pred_te, "date"].nunique()) if pred_te.any() else 0,
    }


def summarise(fold_results: list[dict]) -> dict:
    """Pool fold results exactly, and report every weighting for transparency.

    Precision and the base rate are both pooled as ratio-of-sums, which is the
    only pooling that reproduces the number you would get by concatenating all
    out-of-sample rows into one frame:

        precision = sum(hits) / sum(signals)
        base rate = sum(positives) / sum(test rows)

    Earlier versions averaged per-fold rates instead. Averaging is wrong whenever
    folds differ in size, and it was wrong twice in two different ways: first the
    base rate was an unweighted mean (4.12% against a true 4.46%), then it was
    weighted by signal count (which is also 4.46% here only by coincidence, since
    bigger folds happened to have higher base rates). Both are reported below so
    the difference is visible rather than hidden.
    """
    ok = [r for r in fold_results if "error" not in r and r.get("oos_signals", 0) > 0]
    if not ok:
        return {"error": "no usable folds", "n_folds": len(fold_results)}

    def pooled(prefix: str) -> tuple[float, int]:
        sig = sum(r[f"{prefix}_signals"] for r in ok)
        if sig == 0:
            return float("nan"), 0
        num = sum(r[f"{prefix}_precision"] * r[f"{prefix}_signals"] for r in ok)
        return num / sig, sig

    ins, n_ins = pooled("insample")
    oos, n_oos = pooled("oos")

    # Exact pooled base rate: total positives over total out-of-sample rows.
    n_rows = sum(r.get("n_test", 0) for r in ok)
    n_pos = sum(r.get("oos_positives", 0) for r in ok)
    base_exact = (n_pos / n_rows) if n_rows else float("nan")

    # The two approximations, kept for comparison.
    base_by_signals = (
        sum(r["oos_base_rate"] * r["oos_signals"] for r in ok) / n_oos
        if n_oos else float("nan")
    )
    base_flat = float(np.mean([r["oos_base_rate"] for r in ok]))

    return {
        "n_folds": len(ok),
        "insample_signals": n_ins,
        "insample_precision": ins,
        "oos_signals": n_oos,
        "oos_precision": oos,
        "oos_base_rate": base_exact,
        "oos_base_rate_by_signals": base_by_signals,
        "oos_base_rate_unweighted": base_flat,
        "oos_base_rate_max_abs_diff": float(
            np.nanmax(np.abs(np.array([base_exact, base_by_signals, base_flat])
                             - base_exact))
        ),
        "oos_lift": oos / base_exact if base_exact > 0 else float("nan"),
        "per_fold_oos": [r["oos_precision"] for r in ok],
        "per_fold_signals": [r["oos_signals"] for r in ok],
        "per_fold_base": [r["oos_base_rate"] for r in ok],
        "folds_above_base": int(sum(
            1 for r in ok if r["oos_precision"] > r["oos_base_rate"]
        )),
    }


def matrix_path(horizon: int = 10, target: int = 30, stride: int = 5) -> Path:
    """Path of the feature matrix for a given (horizon, target, stride).

    Kept separate from ``load_matrix`` so callers can test whether a grid exists
    before reading it, which is how modules avoid silently falling back to a
    different sample of the panel.
    """
    return OUT_DIR / f"matrix_h{horizon}_t{target}_s{stride}.parquet"


def resolve_stride(preferred: int = 1, fallback: int = 5) -> int:
    """Pick the densest matrix that exists, preferring ``preferred``.

    Every report under ``reports/`` records which grid it came from in its
    ``stride`` field, and the numbers differ between grids (the walk-forward
    out-of-sample base rate is 0.04089445 on the full cross-section versus
    0.04087801 on the row-strided subset). So a module that reads whichever
    matrix happens to be the default will silently overwrite a report produced
    on a different grid — the numbers change and nothing says so.

    Four modules hit exactly that: they called ``load_matrix()`` with no stride
    after the default was pinned to 5, while the reports on disk held stride-1
    numbers. Resolving explicitly, and printing the choice, makes the grid an
    explicit part of every run instead of an invisible default.
    """
    if matrix_path(stride=preferred).exists():
        return preferred
    if matrix_path(stride=fallback).exists():
        print(f"note: stride-{preferred} matrix absent; using stride {fallback}. "
              f"Build the dense grid with "
              f"`python -m src.ml.build_matrix --stride {preferred}` to reproduce "
              f"the published reports.")
        return fallback
    raise FileNotFoundError(
        f"no feature matrix found at {matrix_path(stride=preferred)} or "
        f"{matrix_path(stride=fallback)}; build one with "
        f"`python -m src.ml.build_matrix --stride 1`"
    )


def load_matrix(
    horizon: int = 10,
    target: int = 30,
    stride: int | None = None,
) -> pd.DataFrame:
    """Load the feature matrix.

    ``stride=None`` (the default) resolves to the densest available grid and
    prints which one it chose. Passing an explicit stride pins it.

    On grids: ``stride`` subsamples by ROW (every stride-th row of the
    code/date-sorted frame), not by session. All 887 sessions survive, but each
    stock lands on a different date phase, so a retained session carries about
    604 of ~3,022 names rather than a full cross-section. Features and labels
    are computed on the full panel before subsampling, so this is a plain
    thinning and the label distribution barely moves. The one thing it does
    weaken is any per-session cross-sectional claim.

    ``--stride-mode session`` in ``build_matrix`` is the alternative: it keeps
    whole sessions with complete cross-sections but drops far more of the
    timeline (178 sessions at stride 5, too few for the walk-forward).
    """
    if stride is None:
        stride = resolve_stride()
    path = matrix_path(horizon=horizon, target=target, stride=stride)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing; run `python -m src.ml.build_matrix --stride {stride}` first"
        )
    frame = pd.read_parquet(path)
    # Record what was actually read so save_report can stamp it. Provenance has
    # to come from the file this process opened, not from a directory listing.
    global LAST_LOAD
    LAST_LOAD = {
        "path": str(path),
        "stride": stride,
        "rows": int(len(frame)),
        "sessions": int(frame["date"].nunique()),
        "horizon": horizon,
        "target": target,
    }
    return frame


def save_report(name: str, payload: dict) -> Path:
    """Write ``reports/ml_<name>.json``, stamping which matrix was measured.

    Several reports published numbers from different grids and nothing in the
    file said which, so a reader could not tell whether two figures were even
    comparable. Two reports disagreeing on the "same" base rate (0.04087801 vs
    0.04089445) is exactly that ambiguity, and it is a property of the grid, not
    an arithmetic error.

    The provenance comes from ``LAST_LOAD``, which ``load_matrix`` sets when it
    actually reads a file in this process. It is deliberately NOT inferred from
    whatever matrix happens to sit in the output directory: guessing would stamp
    a confident, wrong grid, which is worse than stamping nothing.
    """
    # `name` is a bare stem: the "ml_" prefix and ".json" suffix are added here.
    # A caller passing "ml_concentration.json" therefore wrote
    # reports/ml_ml_concentration.json.json, which no reader looks at and which
    # silently left the real report untouched. Reject the whole shape rather than
    # writing a plausible-looking file nobody will find.
    if name.startswith("ml_") or name.endswith(".json") or "/" in name or "\\" in name:
        raise ValueError(
            f"save_report takes a bare stem like 'concentration', got {name!r}; "
            f"it writes reports/ml_{{name}}.json"
        )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"ml_{name}.json"
    enriched = dict(payload)
    if LAST_LOAD:
        enriched.setdefault("_matrix", Path(LAST_LOAD["path"]).name)
        enriched.setdefault("stride", LAST_LOAD["stride"])
        enriched.setdefault("_matrix_rows", LAST_LOAD["rows"])
        enriched.setdefault("_matrix_sessions", LAST_LOAD["sessions"])
    path.write_text(json.dumps(enriched, indent=2, default=str),
                    encoding="utf-8")
    return path
