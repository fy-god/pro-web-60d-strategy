from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import (
    close_location,
    recent_return_series,
    turnover_mean,
    volume_ratio,
)


STRATEGY_ID: str = "leader_momentum"
DISPLAY_NAME: str = "Leader Momentum"
THESIS: str = (
    "A leader is strongest when near-limit gains persist, the latest bar closes "
    "near its high, turnover is active, and volume supports the advance."
)
THRESHOLD: float = 0.90
FORMULA: str = (
    "score = 0.30*recent_near_limit_returns + 0.20*close_location "
    "+ 0.20*momentum_persistence + 0.15*turnover + 0.15*volume_support; "
    "recent_near_limit_returns = mean(clip(return / 0.08, 0, 1) for the "
    "last 3 of the last 10 visible close-to-close returns); "
    "momentum_persistence = positive-return share of the last 10 visible "
    "close-to-close returns; turnover = clip(5-session visible turnover mean "
    "/ 4.0, 0, 1); volume_support = clip(visible volume ratio(short=5, "
    "long=20) / 2.0, 0, 1); predict 1 iff score >= 0.90"
)
FACTOR_DEFINITIONS: dict[str, str] = {
    "recent_near_limit_returns": (
        "Mean of the last three visible close-to-close returns, scaled by "
        "0.08 and clipped to [0, 1]."
    ),
    "close_location": (
        "The latest visible bar close's location within its visible high-low "
        "range, clipped to [0, 1]."
    ),
    "momentum_persistence": (
        "The share of positive visible close-to-close returns across the "
        "last ten sessions."
    ),
    "turnover": (
        "The five-session mean of visible bar turnover, scaled by 4.0 and "
        "clipped to [0, 1]."
    ),
    "volume_support": (
        "The visible five-session volume ratio against its prior visible "
        "baseline, scaled by 2.0 and clipped to [0, 1]."
    ),
}


def predict(card: ExpertCard) -> ExpertDecision:
    returns = recent_return_series(card.bars, window=10)
    recent_near_limit_returns = sum(
        min(1.0, max(0.0, value / 0.08))
        for value in returns[-3:]
    ) / 3.0
    close_location_score = close_location(card.bars[-1])
    momentum_persistence = sum(
        1.0 for value in returns if value > 0.0
    ) / len(returns)
    turnover_score = min(
        1.0,
        max(0.0, turnover_mean(card.bars, window=5) / 4.0),
    )
    volume_support = min(
        1.0,
        max(0.0, volume_ratio(card.bars, short=5, long=20) / 2.0),
    )
    components = {
        "recent_near_limit_returns": recent_near_limit_returns,
        "close_location": close_location_score,
        "momentum_persistence": momentum_persistence,
        "turnover": turnover_score,
        "volume_support": volume_support,
    }
    score = (
        0.30 * recent_near_limit_returns
        + 0.20 * close_location_score
        + 0.20 * momentum_persistence
        + 0.15 * turnover_score
        + 0.15 * volume_support
    )
    rationale = (
        "Visible inputs only: recent near-limit returns "
        f"{recent_near_limit_returns:.3f}, close location "
        f"{close_location_score:.3f}, momentum persistence "
        f"{momentum_persistence:.3f}, turnover {turnover_score:.3f}, "
        f"volume support {volume_support:.3f}; weighted score "
        f"{score:.3f} against threshold {THRESHOLD:.2f}."
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
