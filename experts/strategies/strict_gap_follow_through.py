"""High-precision, lower-coverage gap-continuation selector."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision

from ._strict_selector import thresholded_decision
from .gap_follow_through import FACTOR_DEFINITIONS as _BASE_FACTORS
from .gap_follow_through import predict as _base_predict


STRATEGY_ID = "strict_gap_follow_through"
BASE_STRATEGY_ID = "gap_follow_through"
DISPLAY_NAME = "Strict Gap Follow Through"
THESIS = (
    "Require a stronger gap-follow-through score before saying yes. The selector "
    "trades recall for positive precision and should be read with its coverage."
)
THRESHOLD = 0.75
FORMULA = "reuse gap_follow_through score; predict 1 iff score >= 0.75."
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
