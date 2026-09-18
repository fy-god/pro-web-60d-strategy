"""Fixed-cutoff accumulation_base variant, fitted on the 100-card development scan, not a stricter selector: THRESHOLD sits below accumulation_base's, so it emits a superset."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.strategies._strict_selector import thresholded_decision
from experts.strategies.accumulation_base import (
    FACTOR_DEFINITIONS as _BASE_FACTORS,
    predict as _base_predict,
)


STRATEGY_ID = "strict_accumulation_base_v2"
DISPLAY_NAME = "Strict Accumulation Base v2 [Development]"
THESIS = (
    "A fixed cutoff fitted on the 100-card development scan, not a stricter selector: it "
    "sits BELOW the threshold of the base strategy accumulation_base, so it emits a SUPERSET "
    "of that strategy rather than a subset."
)
THRESHOLD = 0.462083
BASE_STRATEGY_ID = "accumulation_base"
FORMULA = "Reuse accumulation_base score; predict 1 iff score >= 0.462083; development-only."
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
