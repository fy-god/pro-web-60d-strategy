"""High-precision, lower-coverage multi-horizon strength selector."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision

from ._strict_selector import thresholded_decision
from .relative_strength_rank import FACTOR_DEFINITIONS as _BASE_FACTORS
from .relative_strength_rank import predict as _base_predict


STRATEGY_ID = "strict_relative_strength"
BASE_STRATEGY_ID = "relative_strength_rank"
DISPLAY_NAME = "Strict Relative Strength"
THESIS = (
    "Select only the strongest multi-horizon relative-strength scores. This favors "
    "precision over recall and is not a calibrated probability."
)
THRESHOLD = 0.96
FORMULA = "reuse relative_strength_rank score; predict 1 iff score >= 0.96."
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
