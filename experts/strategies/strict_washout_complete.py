"""High-precision, lower-coverage washout-completion selector."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision

from ._strict_selector import thresholded_decision
from .washout_complete import FACTOR_DEFINITIONS as _BASE_FACTORS
from .washout_complete import predict as _base_predict


STRATEGY_ID = "strict_washout_complete"
BASE_STRATEGY_ID = "washout_complete"
DISPLAY_NAME = "Strict Washout Complete"
THESIS = (
    "Select only the upper washout-completion scores. This is a high-precision "
    "selector with deliberately lower coverage, not a claim of broad accuracy."
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
