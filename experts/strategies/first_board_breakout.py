"""Causal first-board breakout strategy using only the visible card tail."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import (
    close_location,
    distance_from_prior_high,
    recent_return_series,
    volume_ratio,
)


STRATEGY_ID: str = "first_board_breakout"
DISPLAY_NAME: str = "First Board Breakout"
THESIS: str = (
    "A fresh close above the prior 20-session high is stronger when recent "
    "limit-like acceleration is absent, the breakout closes firmly, and "
    "volume expands without becoming climactic."
)
THRESHOLD: float = 0.90
FORMULA: str = (
    "score = 0.30*no_recent_near_limit + 0.30*fresh_prior_20_high + "
    "0.20*close_strength + 0.20*controlled_volume_expansion; "
    "predict 1 when score >= 0.90."
)
FACTOR_DEFINITIONS: dict[str, str] = {
    "no_recent_near_limit": (
        "1.0 when the maximum five-session return from "
        "recent_return_series(card.bars, window=5) is below 0.09; otherwise 0.0."
    ),
    "fresh_prior_20_high": (
        "1.0 when the visible close is at least 1% above its prior 20-session "
        "close high and the preceding visible close was not above its own prior "
        "20-session close high; otherwise 0.0."
    ),
    "close_strength": "The visible last-bar close_location(card.bars[-1]) in [0, 1].",
    "controlled_volume_expansion": (
        "1.0 when volume_ratio(card.bars, short=5, long=20) is between 1.2 and "
        "2.5 inclusive; otherwise 0.0."
    ),
}


def predict(card: ExpertCard) -> ExpertDecision:
    recent_returns = recent_return_series(card.bars, window=5)
    maximum_recent_return = max(recent_returns)
    no_recent_near_limit = 1.0 if maximum_recent_return < 0.09 else 0.0

    breakout_distance = distance_from_prior_high(card.bars, window=20)
    previous_breakout_distance = distance_from_prior_high(card.bars[:-1], window=20)
    fresh_prior_20_high = (
        1.0
        if breakout_distance >= 0.01 and previous_breakout_distance <= 0.0
        else 0.0
    )

    close_strength = close_location(card.bars[-1])
    expansion_ratio = volume_ratio(card.bars, short=5, long=20)
    controlled_volume_expansion = (
        1.0 if 1.2 <= expansion_ratio <= 2.5 else 0.0
    )

    components = {
        "no_recent_near_limit": no_recent_near_limit,
        "fresh_prior_20_high": fresh_prior_20_high,
        "close_strength": close_strength,
        "controlled_volume_expansion": controlled_volume_expansion,
    }
    score = (
        0.30 * no_recent_near_limit
        + 0.30 * fresh_prior_20_high
        + 0.20 * close_strength
        + 0.20 * controlled_volume_expansion
    )
    rationale = (
        f"Visible five-session maximum return {maximum_recent_return:.4f}; "
        f"current prior-20 high distance {breakout_distance:.4f} and previous "
        f"distance {previous_breakout_distance:.4f}; last-bar close location "
        f"{close_strength:.4f}; five-to-prior volume ratio {expansion_ratio:.4f}."
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
