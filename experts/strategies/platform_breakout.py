"""Causal platform breakout strategy using only visible session bars."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import (
    distance_from_prior_high,
    range_pct,
    returns,
    volume_ratio,
)


STRATEGY_ID: str = "platform_breakout"
DISPLAY_NAME: str = "Platform Breakout"
THESIS: str = (
    "A breakout from a tight visible platform is stronger when price clears both "
    "the prior 20- and 40-session highs, volume expands, and the prior advance "
    "has not already become extended."
)
THRESHOLD: float = 0.80
FORMULA: str = (
    "score = 0.25*volatility_squeeze + 0.25*breakout_20_40 + "
    "0.25*volume_ratio_expansion + 0.25*limited_prior_extension; "
    "predict 1 when score >= 0.80."
)
FACTOR_DEFINITIONS: dict[str, str] = {
    "volatility_squeeze": (
        "1.0 when the 20-session close range immediately before the visible "
        "breakout is at most 70% of the preceding 20-session close range; "
        "otherwise 0.0."
    ),
    "breakout_20_40": (
        "1.0 when the visible close is at least 1% above both its prior "
        "20-session and prior 40-session close highs; otherwise 0.0."
    ),
    "volume_ratio_expansion": (
        "The visible five-session volume ratio against its preceding visible "
        "baseline, with one point at a 2.0x ratio and clipping to [0, 1]."
    ),
    "limited_prior_extension": (
        "The pre-breakout 20-session return mapped to [0, 1], with full credit "
        "at or below 0% extension and zero credit at 30% extension."
    ),
}


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    pre_breakout = card.bars[:-1]

    recent_platform_range = range_pct(pre_breakout, window=20)
    prior_platform_range = range_pct(pre_breakout[:-20], window=20)
    volatility_squeeze = (
        1.0
        if recent_platform_range <= 0.70 * prior_platform_range
        else 0.0
    )

    breakout_20_distance = distance_from_prior_high(card.bars, window=20)
    breakout_40_distance = distance_from_prior_high(card.bars, window=40)
    breakout_20_40 = (
        1.0
        if breakout_20_distance >= 0.01 and breakout_40_distance >= 0.01
        else 0.0
    )

    expansion_ratio = volume_ratio(card.bars, short=5, long=20)
    volume_ratio_expansion = _clip((expansion_ratio - 1.0) / 1.0)

    prior_extension = returns(pre_breakout, periods=20)
    limited_prior_extension = _clip((0.30 - prior_extension) / 0.30)

    components = {
        "volatility_squeeze": volatility_squeeze,
        "breakout_20_40": breakout_20_40,
        "volume_ratio_expansion": volume_ratio_expansion,
        "limited_prior_extension": limited_prior_extension,
    }
    score = sum(0.25 * value for value in components.values())
    rationale = (
        f"Visible platform range={recent_platform_range:.4f} versus prior "
        f"range={prior_platform_range:.4f}; prior-20 distance="
        f"{breakout_20_distance:.4f}, prior-40 distance="
        f"{breakout_40_distance:.4f}; volume ratio={expansion_ratio:.4f}; "
        f"pre-breakout 20-session extension={prior_extension:.4f}; "
        f"weighted score={score:.4f} against threshold={THRESHOLD:.2f}."
    )
    return ExpertDecision(
        STRATEGY_ID,
        card.sample_id,
        int(score >= THRESHOLD),
        score,
        THRESHOLD,
        components,
        rationale,
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
