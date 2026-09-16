"""High-precision, lower-coverage OBV confirmation selector."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision

from ._strict_selector import thresholded_decision
from .obv_volume_price import FACTOR_DEFINITIONS as _BASE_FACTORS
from .obv_volume_price import predict as _base_predict


STRATEGY_ID = "strict_obv_volume_price"
BASE_STRATEGY_ID = "obv_volume_price"
DISPLAY_NAME = "Strict OBV Volume Price"
THESIS = (
    "Select only the strongest price-volume confirmation scores. The stricter cutoff "
    "reduces false positive selections at the cost of missing many positives."
)
THRESHOLD = 0.97
FORMULA = "reuse obv_volume_price score; predict 1 iff score >= 0.97."
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
