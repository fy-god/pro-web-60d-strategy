"""Fixed-cutoff washout_complete variant, fitted on the 100-card development scan, not a stricter selector: emits 2.45x washout_complete's signals at -0.66pp precision."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision

from ._strict_selector import thresholded_decision
from .washout_complete import FACTOR_DEFINITIONS as _BASE_FACTORS
from .washout_complete import predict as _base_predict


STRATEGY_ID = "strict_washout_complete"
BASE_STRATEGY_ID = "washout_complete"
DISPLAY_NAME = "Strict Washout Complete"
THESIS = (
    "A fixed cutoff fitted on the 100-card development scan, not a stricter selector: it "
    "sits BELOW the threshold of the base strategy washout_complete, so it emits a SUPERSET "
    "of that strategy rather than a subset."
)
THRESHOLD = 0.72
FORMULA = "reuse washout_complete score; predict 1 iff score >= 0.72."
FACTOR_DEFINITIONS = dict(_BASE_FACTORS)
SOURCE = "Strict positive-selection filter"
SOURCE_REFERENCE = "Exploratory fixed-quiz threshold; positive precision, not out-of-sample accuracy"
BATCH_TAG = "strict-precision-2026-08-18"
SELECTION_METRIC = "positive_precision"


def predict(card: ExpertCard) -> ExpertDecision:
    return thresholded_decision(
        card,
        strategy_id=STRATEGY_ID,
        threshold=THRESHOLD,
        base_predict=_base_predict,
    )
