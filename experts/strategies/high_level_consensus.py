"""Causal high-level consensus strategy using only visible session data."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import (
    close_location,
    distance_from_prior_high,
    high_low_span,
    kdj_cross_change,
    kdj_turn,
    returns,
    upper_wick_ratio,
    volume_ratio,
)


STRATEGY_ID: str = "high_level_consensus"
DISPLAY_NAME: str = "High-Level Consensus"
THESIS: str = (
    "A high-level consensus setup combines a sustained preceding trend with a "
    "controlled short disagreement, renewed visible strength, and strict "
    "filters against failed breakouts."
)
THRESHOLD: float = 0.80
FORMULA: str = (
    "score = 0.25*preceding_trend + 0.25*controlled_short_disagreement "
    "+ 0.25*renewed_strength + 0.25*strict_failure_risk_filters; "
    "predict 1 iff score >= 0.80."
)
FACTOR_DEFINITIONS: dict[str, str] = {
    "preceding_trend": (
        "1.0 when the 20-session and 40-session returns of the visible bars "
        "before the latest bar are at least 8% and 12%, respectively; otherwise 0.0."
    ),
    "controlled_short_disagreement": (
        "1.0 when the preceding five-session return stays between -8% and 5%, "
        "the latest visible K-D turn is at least -8 points, and the three-session "
        "K-D cross change is nonnegative; otherwise 0.0."
    ),
    "renewed_strength": (
        "1.0 when the latest three-session visible return is at least 4%, the "
        "latest close is at least 75% up its visible bar range, and the visible "
        "five-to-prior volume ratio is at least 1.25; otherwise 0.0."
    ),
    "strict_failure_risk_filters": (
        "1.0 when the latest visible close is at least 2% above the prior "
        "20-session high, its upper wick is at most 10% of the open, and its "
        "high-low span is at most 8% of the open; otherwise 0.0."
    ),
}


def predict(card: ExpertCard) -> ExpertDecision:
    preceding_bars = card.bars[:-1]
    preceding_trend = float(
        returns(preceding_bars, periods=20) >= 0.08
        and returns(preceding_bars, periods=40) >= 0.12
    )

    preceding_short_return = returns(preceding_bars, periods=5)
    controlled_short_disagreement = float(
        -0.08 <= preceding_short_return <= 0.05
        and kdj_turn(card) >= -8.0
        and kdj_cross_change(card, window=3) >= 0.0
    )

    latest_bar = card.bars[-1]
    renewed_strength = float(
        returns(card.bars, periods=3) >= 0.04
        and close_location(latest_bar) >= 0.75
        and volume_ratio(card.bars, short=5, long=20) >= 1.25
    )

    strict_failure_risk_filters = float(
        distance_from_prior_high(card.bars, window=20) >= 0.02
        and upper_wick_ratio(latest_bar) <= 0.10
        and high_low_span(latest_bar) <= 0.08
    )

    components = {
        "preceding_trend": preceding_trend,
        "controlled_short_disagreement": controlled_short_disagreement,
        "renewed_strength": renewed_strength,
        "strict_failure_risk_filters": strict_failure_risk_filters,
    }
    score = sum(0.25 * value for value in components.values())
    rationale = (
        "Visible inputs only: preceding trend "
        f"{preceding_trend:.1f}, controlled short disagreement "
        f"{controlled_short_disagreement:.1f}, renewed strength "
        f"{renewed_strength:.1f}, strict failure-risk filters "
        f"{strict_failure_risk_filters:.1f}; weighted score {score:.2f} "
        f"against threshold {THRESHOLD:.2f}."
    )
    return ExpertDecision(
        strategy_id=STRATEGY_ID,
        sample_id=card.sample_id,
        prediction=int(score >= THRESHOLD),
        score=score,
        threshold=THRESHOLD,
        components=components,
        rationale=rationale,
    )


__all__ = [
    "STRATEGY_ID",
    "DISPLAY_NAME",
    "THESIS",
    "THRESHOLD",
    "FORMULA",
    "FACTOR_DEFINITIONS",
    "predict",
]
