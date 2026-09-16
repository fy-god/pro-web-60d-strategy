"""High-precision, lower-coverage platform-breakout selector."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision

from ._strict_selector import thresholded_decision
from .platform_breakout import FACTOR_DEFINITIONS as _BASE_FACTORS
from .platform_breakout import predict as _base_predict


STRATEGY_ID = "strict_platform_breakout"
BASE_STRATEGY_ID = "platform_breakout"
DISPLAY_NAME = "Strict Platform Breakout"
THESIS = (
    "Require a strong platform-breakout score before selecting a candidate. It is "
    "intended for selective breakout hunting, with small deliberate coverage."
)
THRESHOLD = 0.65
FORMULA = "reuse platform_breakout score; predict 1 iff score >= 0.65."
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
