"""Causal low-position accumulation-base strategy."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import (
    EPS,
    close_location,
    positive_volume_share,
    range_pct,
    rolling_mean,
    rolling_std,
)


STRATEGY_ID: str = "accumulation_base"
DISPLAY_NAME: str = "Accumulation Base"
THESIS: str = (
    "A low-volatility base is more credible when its visible range compresses, "
    "up-day volume outweighs down-day volume, turnover stays stable, and "
    "close locations improve."
)
THRESHOLD: float = 0.90
FORMULA: str = (
    "score = 0.25*range_compression + "
    "0.25*positive_negative_volume_asymmetry + "
    "0.25*stable_turnover + 0.25*improving_close_location; "
    "predict 1 when score >= 0.90."
)
FACTOR_DEFINITIONS: dict[str, str] = {
    "range_compression": (
        "clip((prior 20-session close range - recent 10-session close range) / "
        "(0.50 * prior range + EPS), 0, 1), using range_pct on visible bars."
    ),
    "positive_negative_volume_asymmetry": (
        "clip((positive_volume_share(card.bars, window=10) - 0.50) / 0.25, "
        "0, 1); 75% or more of recent volume on rising closes receives full credit."
    ),
    "stable_turnover": (
        "clip((0.20 - recent 10-session turnover coefficient of variation) / "
        "0.20, 0, 1), where coefficient of variation is rolling standard "
        "deviation divided by rolling mean."
    ),
    "improving_close_location": (
        "0.70 * clip((mean close location in the recent five sessions - mean "
        "close location in the preceding five sessions) / 0.25, 0, 1) + "
        "0.30 * latest visible close location."
    ),
}


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    recent_range = range_pct(card.bars, window=10)
    prior_range = range_pct(card.bars[:-10], window=20)
    range_compression = _clip(
        (prior_range - recent_range) / (0.50 * prior_range + EPS)
    )

    positive_volume_share_score = positive_volume_share(card.bars, window=10)
    positive_negative_volume_asymmetry = _clip(
        (positive_volume_share_score - 0.50) / 0.25
    )

    turnover_values = tuple(bar.turnover for bar in card.bars)
    recent_turnover_mean = rolling_mean(turnover_values, window=10)
    recent_turnover_cv = rolling_std(turnover_values, window=10) / (
        recent_turnover_mean + EPS
    )
    stable_turnover = _clip((0.20 - recent_turnover_cv) / 0.20)

    close_locations = tuple(close_location(bar) for bar in card.bars)
    prior_close_location = rolling_mean(close_locations[-10:-5], window=5)
    recent_close_location = rolling_mean(close_locations[-5:], window=5)
    close_location_improvement = _clip(
        (recent_close_location - prior_close_location) / 0.25
    )
    improving_close_location = (
        0.70 * close_location_improvement + 0.30 * close_locations[-1]
    )

    components = {
        "range_compression": range_compression,
        "positive_negative_volume_asymmetry": positive_negative_volume_asymmetry,
        "stable_turnover": stable_turnover,
        "improving_close_location": improving_close_location,
    }
    score = sum(0.25 * value for value in components.values())
    rationale = (
        f"Visible range compression={range_compression:.3f}, "
        f"positive/negative volume asymmetry={positive_negative_volume_asymmetry:.3f}, "
        f"stable turnover={stable_turnover:.3f}, "
        f"improving close location={improving_close_location:.3f}; "
        f"weighted score={score:.3f} against threshold={THRESHOLD:.2f}."
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
