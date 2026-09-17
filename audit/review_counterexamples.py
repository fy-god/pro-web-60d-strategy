"""Executable counterexamples U07-U12 from docs/reviews/2026-09-17_ML_update_review.md.

Self-contained: every expression is copied from THIS repository, and no other
project's source is reproduced. The private low-zone label counterexamples
(U01-U06, U13-U14) are deliberately not included here; that report says which
repository holds them.

These are artificial software/arithmetic checks. They establish logic defects,
not market results: no panel is loaded, no model is fitted, no hit rate is
claimed. Run:

    python audit/review_counterexamples.py

Writes audit/review_counterexamples.json next to this file.
"""
from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
checks: list[dict] = []


def add(cid: str, name: str, source: str, observed: dict, note: str) -> None:
    checks.append({"id": cid, "check": name, "source": source,
                   "observed": observed, "note": note})


# ---------------------------------------------------------------- U07 / U12
def frontier(y: np.ndarray, scores: np.ndarray) -> np.ndarray:
    """Exact prefix-precision expression from src/ml/precision_ceiling.py."""
    order = np.argsort(-scores, kind="stable")
    y_sorted = y[order]
    k = np.arange(1, len(y_sorted) + 1)
    tp = np.cumsum(y_sorted)[k - 1]
    return tp / k


# U07: the frontier depends on the sort order, so it bounds ONE ranking only.
y = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
old_scores = np.arange(10.0)                       # positives ranked last
new_scores = np.r_[10.0, 9.0, np.arange(8.0)]      # positives ranked first
old_max = float(frontier(y, old_scores)[1:].max())
new_max = float(frontier(y, new_scores)[1:].max())
assert new_max > old_max
add("U07", "a fixed-score frontier is not a bound on other rankings",
    "src/ml/precision_ceiling.py::frontier (argsort -> cumsum -> /k)",
    {"old_ranking_max_precision_min2": old_max,
     "new_ranking_max_precision_min2": new_max,
     "identical_labels": True},
    "Same 10 labels, different score order: 20% vs 100%. The frontier "
    "constrains the ranking it was computed from, not every model.")

# U12: a prefix taken inside a run of tied scores is not reachable by any
# non-empty scalar threshold, because a threshold selects the whole tie.
tied = np.ones(10) * 0.5
prefix_at2 = float(frontier(y, tied)[1])            # k = 2 -> 100%
nonempty_threshold = float(y[tied >= 0.5].mean())   # threshold selects all 10
assert prefix_at2 == 1.0 and nonempty_threshold == 0.2
add("U12", "a prefix inside a score tie is not achievable by a scalar threshold",
    "src/ml/precision_ceiling.py::frontier vs. threshold selection",
    {"prefix_precision_at_k2": prefix_at2,
     "nonempty_threshold_precision": nonempty_threshold},
    "Top-K reporting and threshold reporting are different units; ties must "
    "have an explicit rule.")


# --------------------------------------------------------------------- U08
# src/ml/final_holdout.py splits on HOLDOUT_START = "2026-01-01" and trains on
# every row with date < cutoff, without checking when the 10-session label ends.
HOLDOUT_START = "2026-01-01"
sessions = np.arange("2025-12-15", "2026-01-15", dtype="datetime64[D]")
sessions = sessions[np.is_busday(sessions)]          # business-day calendar
frame_rows = []
for i, day in enumerate(sessions):
    end = sessions[i + 10] if i + 10 < len(sessions) else np.datetime64("NaT")
    frame_rows.append((day, end))
cutoff = np.datetime64(HOLDOUT_START)
train = [(d, e) for d, e in frame_rows if d < cutoff]
violations = [(d, e) for d, e in train if not np.isnat(e) and e >= cutoff]
assert violations, "expected label windows crossing the holdout boundary"
add("U08", "date-only holdout split admits training rows whose label ends later",
    "src/ml/final_holdout.py (frame['date'] < HOLDOUT_START) with the "
    "10-session label horizon",
    {"train_rows": len(train),
     "rows_crossing_boundary": len(violations),
     "first_crossing_signal_date": str(violations[0][0])},
    "Constructed calendar, not the real panel. It shows the filter is "
    "label-blind; the real affected-row count must come from the panel.")


# --------------------------------------------------------------------- U09
# src/ml/build_matrix.py applies out.iloc[::stride] AFTER all stocks are
# concatenated, so one stock's sampling depends on every other stock.
def strided_dates(rows: list[tuple[str, int]], stride: int = 5) -> list[int]:
    """out.iloc[::stride], applied to the concatenated frame."""
    return [d for c, d in rows[::stride] if c == "A"]


dates = list(range(10))
before = strided_dates([("A", d) for d in dates])
after = strided_dates([("0", -1)] + [("A", d) for d in dates])
assert before != after
add("U09", "a global stride shifts one stock's samples when another is added",
    "src/ml/build_matrix.py (out.iloc[::stride] after concatenation)",
    {"stock_A_dates_before": before, "stock_A_dates_after": after},
    "Stock A's own bars are unchanged; its sampled dates are not. Any "
    "stride>1 matrix is therefore not reproducible under a panel change.")


# --------------------------------------------------------------------- U10
# src/tradeability.py: open_at_limit = gap >= (limit - LIMIT_TOLERANCE),
# with LIMIT_MAIN = 0.10 and LIMIT_TOLERANCE = 0.005.
LIMIT_MAIN, LIMIT_TOLERANCE = 0.10, 0.005
gap = 0.096
classified = bool(gap >= (LIMIT_MAIN - LIMIT_TOLERANCE))
assert classified
add("U10", "the 0.5pp tolerance classifies a below-limit gap as open-at-limit",
    "src/tradeability.py (gap >= limit - LIMIT_TOLERANCE)",
    {"gap": gap, "configured_limit": LIMIT_MAIN,
     "tolerance": LIMIT_TOLERANCE, "classified_open_at_limit": classified,
     "actual_fillability_still_unknown": True},
    "A 9.6% gap is treated like a 10% limit gap. This is a tolerance "
    "property of the code, not a verdict on any real stock's fill.")


# --------------------------------------------------------------------- U11
# src/ml/build_matrix.py stores features as float32. Rounding the entry price
# through float32 can turn a false exact-boundary comparison into a true one.
entry, multiple, close = 9.99, 4.0, 39.96
rounded = float(np.float32(entry))
wrong = bool(close / (rounded + 1e-12) - 1.0 > (multiple - 1.0))
correct = bool(close > multiple * entry)
assert wrong and not correct
add("U11", "float32 entry can flip an exact-target comparison",
    "src/ml/build_matrix.py (.astype('float32')) applied to a price used in "
    "an exact-boundary test",
    {"entry": entry, "float32_entry": rounded, "close": close,
     "strict_4x_target_met": correct,
     "expression_after_float32_rounding": wrong},
    "39.96 is exactly 4x9.99, so the strict test is False. Rounding the entry "
    "to float32 makes the same expression read True. Widening back to float64 "
    "cannot restore the discarded precision.")


payload = {
    "kind": "artificial_software_and_arithmetic_counterexamples",
    "market_training_runs": 0,
    "scope": "U07-U12 only; U01-U06 and U13-U14 are label counterexamples "
             "belonging to another repository and are not copied here",
    "python": sys.version,
    "numpy": np.__version__,
    "platform": platform.platform(),
    "source": "docs/reviews/2026-09-17_ML_update_review.md section 13",
    "checks": checks,
    "passed": len(checks),
    "total": 6,
}
out = HERE / "review_counterexamples.json"
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
               encoding="utf-8")

for c in checks:
    print(f"{c['id']} {c['check']}")
    print(f"    {c['observed']}")
print(f"{len(checks)}/6 counterexamples reproduced; market training = 0")
print(f"wrote {out.relative_to(HERE.parent.parent)}")
