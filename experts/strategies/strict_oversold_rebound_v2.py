"""Fixed-cutoff oversold_rebound variant, fitted on the 100-card development scan, not a stricter selector: emits 102.43x oversold_rebound's signals at -9.01pp precision."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.strategies._strict_selector import thresholded_decision
from experts.strategies.oversold_rebound import (
    FACTOR_DEFINITIONS as _BASE_FACTORS,
    predict as _base_predict,
)


STRATEGY_ID = "strict_oversold_rebound_v2"
DISPLAY_NAME = "Strict Oversold Rebound v2 [Development]"
THESIS = (
    "A fixed cutoff fitted on the 100-card development scan, not a stricter selector: it "
    "sits BELOW the threshold of the base strategy oversold_rebound, so it emits a SUPERSET "
    "of that strategy rather than a subset."
)
THRESHOLD = 0.449606
BASE_STRATEGY_ID = "oversold_rebound"
FORMULA = "Reuse oversold_rebound score; predict 1 iff score >= 0.449606; development-only."
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
