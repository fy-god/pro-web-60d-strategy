"""Fixed-cutoff leader_momentum variant, fitted on the 100-card development scan, not a stricter selector: emits 4.52x leader_momentum's signals at -3.14pp precision."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.strategies._strict_selector import thresholded_decision
from experts.strategies.leader_momentum import (
    FACTOR_DEFINITIONS as _BASE_FACTORS,
    predict as _base_predict,
)


STRATEGY_ID = "strict_leader_momentum_v2"
DISPLAY_NAME = "Strict Leader Momentum v2 [Development]"
THESIS = (
    "A fixed cutoff fitted on the 100-card development scan, not a stricter selector: it "
    "sits BELOW the threshold of the base strategy leader_momentum, so it emits a SUPERSET "
    "of that strategy rather than a subset."
)
THRESHOLD = 0.788535
BASE_STRATEGY_ID = "leader_momentum"
FORMULA = "Reuse leader_momentum score; predict 1 iff score >= 0.788535; development-only."
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
