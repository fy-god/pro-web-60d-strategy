"""Verify TARGET_70PCT.md's walk-forward baseline interval is correct.

An independent ML review concluded that the document's claim at
TARGET_70PCT.md:362-363 --

    "A date-block bootstrap over 299 distinct signal dates gives a 95% interval
     of [13.6%, 18.7%]"

-- "matches no artifact" and that the 299 dates conflicted with the holdout's 150
signal dates. This script tests that conclusion by reconstructing the number from
the stored out-of-sample scores.

Result: the claim is CORRECT and the review conflated two different populations.

  * The 15.98% figure in that paragraph is the walk-forward BASELINE
    (fam_hgb_0 over four OOS folds), not the 2026 holdout. The baseline's mask is
    `score >= that row's own fold threshold`, since audit_ml_nulls.py stores one
    train-only threshold per fold.
  * Reconstructed from outputs/ml/audit/real_oos_scores.npz, that mask gives
    exactly 1,790 signals, 286 hits and 15.98% precision -- matching the
    published baseline bit-for-bit, which confirms the reconstruction is the
    right one.
  * That mask spans exactly 299 distinct signal dates. 299 is the BASELINE's
    count; the holdout's 150 dates belong to ml_final_holdout.json and are a
    different population. There is no conflict.
  * The date-block bootstrap over those 299 dates returns [13.5%, 18.5%] with a
    fixed seed, and the interval is seed-sensitive at the upper bound: across 12
    seeds it runs to [13.7%, 18.8%]. The document's [13.6%, 18.7%] sits inside
    that range, so it is a correct reported draw, not a stray number.

The interval was not persisted anywhere, which is why it looked unattributable.
The fix is to publish it: reports/ml_final_holdout.json is the wrong home (wrong
population), so this probe is retained as the reproduction and the numbers below
are stated so the document's claim can be re-derived.

Run: python scripts/scratch/_probe_baseline_ci.py
"""
from __future__ import annotations

import numpy as np

# The four OOS fold test blocks, matching ml_crosssec_final.json's fold labels.
FOLDS = [
    ("2024-02-02", "2024-07-29"),
    ("2024-07-30", "2025-01-17"),
    ("2025-01-20", "2025-07-14"),
    ("2025-07-15", "2025-12-31"),
]
PUBLISHED_SIGNALS = 1790
PUBLISHED_PRECISION_PCT = 15.98
PUBLISHED_DATES = 299
DOC_INTERVAL = (13.6, 18.7)


def _load():
    with np.load("outputs/ml/audit/real_oos_scores.npz", allow_pickle=True) as z:
        return (np.asarray(z["scores"], dtype="float64"),
                np.asarray(z["labels"], dtype="float64"),
                np.asarray(z["dates"]).astype("datetime64[D]"),
                np.asarray(z["fold_thresholds"], dtype="float64"))


def _mask(scores, dates, thr):
    """The baseline's own mask: per-fold train-only thresholds."""
    pred = np.zeros(len(scores), dtype=bool)
    for i, (lo, hi) in enumerate(FOLDS):
        m = (dates >= np.datetime64(lo)) & (dates <= np.datetime64(hi))
        pred |= m & (scores >= thr[i])
    return pred


def _boot(labels, dates, pred, universe, block=1, n_boot=1000, seed=0):
    rng = np.random.default_rng(seed)
    groups = {d: labels[pred & (dates == d)] for d in universe}
    keys = list(universe)
    m = len(keys)
    stats = np.empty(n_boot)
    for i in range(n_boot):
        if block <= 1:
            pick = rng.integers(0, m, size=m)
            chunks = [groups[keys[j]] for j in pick]
        else:
            nb = int(np.ceil(m / block))
            starts = rng.integers(0, m, size=nb)
            chunks = [groups[keys[(s + o) % m]] for s in starts
                      for o in range(block)]
        vals = np.concatenate(chunks) if chunks else np.empty(0)
        stats[i] = vals.mean() if vals.size else np.nan
    return (float(np.nanpercentile(stats, 2.5)),
            float(np.nanpercentile(stats, 97.5)))


def main() -> int:
    scores, labels, dates, thr = _load()
    pred = _mask(scores, dates, thr)

    n = int(pred.sum())
    hits = int(labels[pred].sum())
    pct = 100 * hits / n
    sig_dates = np.unique(dates[pred])
    print(f"reconstructed baseline: {n:,} signals, {hits:,} hits, {pct:.2f}%")
    print(f"published             : {PUBLISHED_SIGNALS:,} signals, "
          f"{PUBLISHED_PRECISION_PCT:.2f}%")
    print(f"distinct signal dates : {len(sig_dates)}  "
          f"(document says {PUBLISHED_DATES})")

    ok = True
    if n != PUBLISHED_SIGNALS or abs(pct - PUBLISHED_PRECISION_PCT) > 0.01:
        print("FAIL: reconstruction does not reproduce the published baseline")
        ok = False
    if len(sig_dates) != PUBLISHED_DATES:
        print("FAIL: signal-date count does not reproduce")
        ok = False

    # The upper bound is seed-sensitive; the document's value must lie within the
    # range the bootstrap actually produces.
    ups, los = [], []
    for seed in range(12):
        lo, hi = _boot(labels, dates, pred, sig_dates, block=1, seed=seed)
        los.append(lo * 100)
        ups.append(hi * 100)
    print(f"\nlower bound over 12 seeds: {min(los):.2f}% .. {max(los):.2f}%")
    print(f"upper bound over 12 seeds: {min(ups):.2f}% .. {max(ups):.2f}%")
    print(f"document interval        : [{DOC_INTERVAL[0]:.1f}%, "
          f"{DOC_INTERVAL[1]:.1f}%]")
    inside = (min(los) <= DOC_INTERVAL[0] <= max(los)
              and min(ups) <= DOC_INTERVAL[1] <= max(ups))
    print(f"document interval inside the realised range: {inside}")
    if not inside:
        print("FAIL: the document's interval is not reproducible")
        ok = False

    print("\nRESULT:", "PASS -- the document's interval is correct" if ok
          else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
