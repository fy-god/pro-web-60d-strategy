"""Backtest every 60-day low-zone version (V00-V08) on the local panel.

Design decisions that keep this honest
--------------------------------------
* **Purged, year-forward split.** Training uses years strictly before the
  evaluation year. The project's own V08 record is explicit that per-year
  threshold selection is an in-sample fit, so V07/V08 are reported under both
  the in-sample and the year-forward protocol, and labelled accordingly.
* **Both regimes.** Each version is scored under the Web Pro contract
  (10 sessions, +30%) and the low-zone contract (60 sessions, 4x). A version
  can look excellent in one and worthless in the other, and the record shows
  exactly that happening.
* **First-signal policy.** Overlapping candidates on one stock collapse to the
  first signal of the cluster, so a stock that sits in a low zone for a month
  counts once.

Usage
-----
    python -m src.backtest_lowzone --min-tier 1
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from src import data_pipeline, features, labels, lowzone

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs"
REPORT_DIR = REPO_ROOT / "reports"
LAYER_CACHE = REPO_ROOT / "data" / "lowzone_layers.parquet"

MIN_TRAIN_YEARS = 1

# Fraction of candidate bars each model version is allowed to turn into signals.
# A top-decile cutoff keeps the comparison across versions meaningful: every
# model variant emits roughly the same volume of signals, so differing hit rates
# reflect ranking skill rather than differing selectivity.
TARGET_RATE = 0.10


def load_layers() -> pd.DataFrame:
    """Build (and cache) the causal layer + tier table."""
    if LAYER_CACHE.exists():
        return pd.read_parquet(LAYER_CACHE)
    panel = data_pipeline.load_panel()
    layers = lowzone.build_layers(panel)
    LAYER_CACHE.parent.mkdir(parents=True, exist_ok=True)
    layers.to_parquet(LAYER_CACHE, index=False, compression="zstd")
    return layers


def attach_regime_labels(layers: pd.DataFrame) -> pd.DataFrame:
    """Join every evaluation regime's labels onto the layer table."""
    prepared = features.prepare(
        data_pipeline.load_panel()[["code", "date", "open", "high", "low", "close", "volume"]]
    )
    labelled = labels.forward_outcomes_multi(prepared)
    key = ["code", "date"]
    for regime in labels.REGIMES:
        key += [
            f"entry_open__{regime}", f"forward_max_return__{regime}",
            f"forward_min_return__{regime}", f"bars_to_target__{regime}",
            f"label_bull__{regime}", f"label_strict_low__{regime}",
            f"label_joint__{regime}", f"label_resolved__{regime}",
        ]
    merged = layers.merge(labelled[key], on=["code", "date"], how="left")
    return merged


def _impute(train: pd.DataFrame, test: pd.DataFrame, columns: list[str]):
    medians = train[columns].median()
    return (
        train[columns].fillna(medians).to_numpy("float64"),
        test[columns].fillna(medians).to_numpy("float64"),
        medians,
    )


def run_version(
    frame: pd.DataFrame,
    version: lowzone.LowZoneVersion,
    eval_years: tuple[int, ...] = (2024, 2025, 2026),
    regime: str = "webpro",
    allow_insample: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """Evaluate one version under one regime and return its signals and report.

    ``allow_insample`` governs V07/V08: when True their per-year threshold is
    chosen on the evaluation year itself and the result is explicitly flagged
    ``in_sample=True``. When False the threshold comes from prior years only,
    which is the honest cross-year reading.
    """
    label_col = f"label_bull__{regime}"
    resolved_col = f"label_resolved__{regime}"
    horizon = labels.REGIMES[regime][0]

    pool = frame[(frame["recall_tier"] >= version.min_tier) & frame[resolved_col]].copy()
    if pool.empty:
        return pd.DataFrame(), {"version": version.version, "regime": regime, "signals": 0}

    rows = []
    for year in eval_years:
        test = pool[pool["year"] == year]
        if test.empty:
            continue
        train = pool[pool["year"] < year]

        if version.model == "rule":
            test = test.assign(score=1.0)
            in_sample = False
            threshold = 0.0
        else:
            if len(train) < 50 or train[label_col].nunique() < 2:
                continue
            score = _fit_score(train, test, version, regime)
            test = test.assign(score=score)

            # Threshold policy.
            #
            # A fixed 0.5 cutoff is wrong for `gain - alpha*loss`, which is
            # centred near zero: that cutoff emitted 6 signals in four years and
            # made the competitive model look broken when it was only
            # mis-thresholded. Every model variant instead takes a top-quantile
            # cutoff, and *which* data supplies the quantile is the difference
            # between an honest test and an in-sample fit:
            #
            #   per_year_threshold + allow_insample -> quantile of the
            #       evaluation year itself. This is what the project's own
            #       V07/V08 record does, and it is flagged in_sample=True.
            #   otherwise -> quantile of the *prior* years' scores, which never
            #       lets the evaluation year pick its own cutoff.
            if version.per_year_threshold and allow_insample:
                threshold = float(np.quantile(score, 1.0 - TARGET_RATE))
                in_sample = True
            else:
                prior = _prior_year_scores(pool, year, version, regime)
                source = prior if prior is not None and len(prior) >= 50 else score
                threshold = float(np.quantile(source, 1.0 - TARGET_RATE))
                in_sample = False

        selected = test[test["score"] >= threshold].copy()
        selected["eval_year"] = year
        selected["in_sample"] = in_sample if version.model != "rule" else False
        rows.append(selected)

    if not rows:
        return pd.DataFrame(), {"version": version.version, "regime": regime, "signals": 0}

    signals = pd.concat(rows, ignore_index=True)
    if version.first_signal_per_year:
        signals = (
            signals.sort_values(["code", "eval_year", "date"])
            .groupby(["code", "eval_year"], as_index=False)
            .first()
        )

    deduped = labels.dedupe_signals(signals, cooldown=horizon)
    n = len(deduped)
    hits = int(deduped[label_col].fillna(0).sum())
    joint_col = f"label_joint__{regime}"
    joint_hits = int(deduped[joint_col].fillna(0).sum())
    wilson_low, wilson_high = labels._wilson(hits, n)

    auc = float("nan")
    if version.model != "rule" and len(signals) > 10 and signals[label_col].nunique() > 1:
        try:
            auc = float(roc_auc_score(signals[label_col].to_numpy("float64"),
                                      signals["score"].to_numpy("float64")))
        except Exception:
            auc = float("nan")

    report = {
        "version": version.version,
        "display_name": version.display_name,
        "regime": regime,
        "min_tier": version.min_tier,
        "model": version.model,
        "signals_deduped": n,
        "bull_hits": hits,
        "bull_precision": hits / n if n else float("nan"),
        "wilson_low": wilson_low,
        "wilson_high": wilson_high,
        "joint_hits": joint_hits,
        "joint_precision": joint_hits / n if n else float("nan"),
        "distinct_stocks": int(deduped["code"].nunique()) if n else 0,
        "distinct_dates": int(deduped["date"].nunique()) if n else 0,
        "in_sample": bool(signals["in_sample"].any()) if n else False,
        "score_auc_within_signals": auc,
        "candidates_pool": int(len(pool)),
        "hit_rate_pct": round(100 * hits / n, 2) if n else float("nan"),
    }
    return signals, report


def _fit_score(
    train: pd.DataFrame,
    test: pd.DataFrame,
    version: lowzone.LowZoneVersion,
    regime: str,
) -> np.ndarray:
    """Fit the version's model on ``train`` and score ``test``.

    Fitting on strictly earlier years and scoring a later year is what keeps
    this from being the same-year in-sample fit that the project's own V07/V08
    record is explicit about being non-predictive.
    """
    columns = lowzone.FEATURE_COLUMNS
    x_train, x_test, _ = _impute(train, test, columns)

    gain_model = lowzone.make_gain_model()
    gain_model.fit(x_train, train[f"label_bull__{regime}"].to_numpy("float64"))
    gain_score = gain_model.predict_proba(x_test)[:, 1]

    if version.model == "gain":
        return gain_score

    # Competitive model: subtract the loss model's probability.
    y_loss = 1.0 - train[f"label_joint__{regime}"].to_numpy("float64")
    if len(np.unique(y_loss)) < 2:
        return gain_score
    loss_model = lowzone.make_loss_model()
    loss_model.fit(x_train, y_loss)
    loss_score = loss_model.predict_proba(x_test)[:, 1]
    return gain_score - version.alpha * loss_score


def _prior_year_scores(
    pool: pd.DataFrame,
    year: int,
    version: lowzone.LowZoneVersion,
    regime: str,
) -> np.ndarray | None:
    """Scores on years strictly before ``year``, used to pick its threshold.

    Walk-forward threshold selection: the cutoff for ``year`` must not depend on
    ``year``'s own labels, or a per-year quantile silently becomes an in-sample
    fit. Returns None when there is not enough prior data to be meaningful.
    """
    prior = pool[pool["year"] < year]
    if len(prior) < 200:
        return None
    scores = []
    for prior_year in sorted(prior["year"].unique()):
        fit_pool = pool[pool["year"] < prior_year]
        target = pool[pool["year"] == prior_year]
        if len(fit_pool) < 200 or target.empty:
            continue
        if fit_pool[f"label_bull__{regime}"].nunique() < 2:
            continue
        try:
            scores.append(_fit_score(fit_pool, target, version, regime))
        except Exception:
            continue
    if not scores:
        return None
    return np.concatenate(scores)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regimes", default="webpro,low60")
    parser.add_argument("--insample", action="store_true",
                        help="also run the per-year-threshold in-sample protocol")
    args = parser.parse_args()

    t0 = time.time()
    frame = load_layers()
    print(f"layers: {frame.shape} in {time.time()-t0:.1f}s", flush=True)
    tier_counts = frame["recall_tier"].value_counts().sort_index()
    print("tier distribution:\n" + tier_counts.to_string(), flush=True)

    frame = attach_regime_labels(frame)
    print(f"labels joined: {frame.shape} in {time.time()-t0:.1f}s", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Baseline over the FULL resolved panel (no stride, no minimum history).
    #
    # This is NOT the same row set as `reports/webpro_baselines.json`, which
    # scan_all.population_baselines computes over the *scanned* grid only
    # (_seq >= VISIBLE_BARS, then every stride-th bar). Both payloads publish a
    # key called `bull_rate`; they differ by ~1.8% (webpro), ~3.6% (low60) and
    # ~10.3% (low504) in relative terms on this panel. Every payload therefore
    # carries a `population` block so the two cannot be confused. See the
    # "Baseline provenance" note in src/labels.py.
    baselines = {}
    for regime in labels.REGIMES:
        resolved = frame[frame[f"label_resolved__{regime}"]]
        base = float(resolved[f"label_bull__{regime}"].fillna(0).mean())
        baselines[regime] = {
            "candidates": int(len(resolved)),
            "bull_rate": base,
            "population": labels.population_provenance(
                "panel", stride=1, min_history=0, frame=resolved,
            ),
        }
        for tier in range(1, 6):
            sub = resolved[resolved["recall_tier"] >= tier]
            baselines[regime][f"tier_ge_{tier}_rate"] = (
                float(sub[f"label_bull__{regime}"].fillna(0).mean()) if len(sub) else float("nan")
            )
    print("baselines:\n" + json.dumps(baselines, indent=2), flush=True)

    all_reports, all_signals = [], []
    for regime in args.regimes.split(","):
        regime = regime.strip()
        for version in lowzone.VERSIONS:
            signals, report = run_version(frame, version, regime=regime)
            report["baseline_rate"] = baselines[regime]["bull_rate"]
            # Travel with the value: a `baseline_rate` read out of this CSV in
            # isolation must say which row set it censused, because
            # reports/webpro_baselines.json publishes a *different* base rate
            # under the same concept (see the note above).
            report["baseline_population"] = baselines[regime]["population"]["population"]
            report["baseline_population_id"] = baselines[regime]["population"]["population_id"]
            if np.isfinite(report.get("bull_precision", np.nan)) and baselines[regime]["bull_rate"] > 0:
                report["lift_vs_baseline"] = (
                    report["bull_precision"] / baselines[regime]["bull_rate"]
                )
            all_reports.append(report)
            if not signals.empty:
                keep = signals[[
                    "code", "date", "eval_year", "recall_tier", "score",
                    f"forward_max_return__{regime}", f"forward_min_return__{regime}",
                    f"label_bull__{regime}", f"label_joint__{regime}", "in_sample",
                ]].copy()
                keep = keep.rename(columns={
                    f"forward_max_return__{regime}": "forward_max_return",
                    f"forward_min_return__{regime}": "forward_min_return",
                    f"label_bull__{regime}": "label_bull",
                    f"label_joint__{regime}": "label_joint",
                })
                keep["version"] = version.version
                keep["regime"] = regime
                all_signals.append(keep)
            print(f"  {version.version:4s} {regime:7s} n={report.get('signals_deduped',0):5d} "
                  f"hit={report.get('hit_rate_pct', float('nan'))!s:>7} "
                  f"lift={report.get('lift_vs_baseline', float('nan'))!s:>6}", flush=True)

    report_frame = pd.DataFrame(all_reports)
    report_frame.to_csv(REPORT_DIR / "lowzone_hit_rates.csv", index=False)
    if all_signals:
        signals_frame = pd.concat(all_signals, ignore_index=True)
        signals_frame.to_csv(OUT_DIR / "lowzone_signals.csv", index=False)
        print(f"\nsignals written: {len(signals_frame)}")

    (REPORT_DIR / "lowzone_baselines.json").write_text(
        json.dumps(baselines, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("\n=== hit rates ===")
    show = report_frame[["version", "regime", "signals_deduped", "bull_hits",
                         "hit_rate_pct", "baseline_rate", "lift_vs_baseline",
                         "wilson_low", "distinct_stocks", "in_sample"]]
    print(show.to_string(index=False))
    print(f"\ntotal {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
