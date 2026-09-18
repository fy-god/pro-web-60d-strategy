"""Development-only high-precision OBV volume-price selector."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.strategies._strict_selector import thresholded_decision
from experts.strategies.obv_volume_price import (
    FACTOR_DEFINITIONS as _BASE_FACTORS,
    predict as _base_predict,
)


STRATEGY_ID = "strict_obv_volume_price_v2"
DISPLAY_NAME = "Strict OBV Volume-Price v2 [Development]"
THESIS = "A higher cutoff keeps only volume-price structures with the strongest visible accumulation confirmation."
THRESHOLD = 0.969655
BASE_STRATEGY_ID = "obv_volume_price"
FORMULA = "Reuse obv_volume_price score; predict 1 iff score >= 0.969655; development-only."
FACTOR_DEFINITIONS = dict(_BASE_FACTORS)
SOURCE = "Handoff development selector"
SOURCE_REFERENCE = "100-card exploratory precision scan; development-only"
BATCH_TAG = "strict-precision-v2-development-2026-08-18"
SELECTION_METRIC = "positive_precision"


def predict(card: ExpertCard) -> ExpertDecision:
    return thresholded_decision(
        card,
        strategy_id=STRATEGY_ID,
        threshold=THRESHOLD,
        base_predict=_base_predict,
    )


__all__ = [
    "STRATEGY_ID",
    "DISPLAY_NAME",
    "THESIS",
    "THRESHOLD",
    "BASE_STRATEGY_ID",
    "FORMULA",
    "FACTOR_DEFINITIONS",
    "SOURCE",
    "SOURCE_REFERENCE",
    "BATCH_TAG",
    "SELECTION_METRIC",
    "predict",
]
