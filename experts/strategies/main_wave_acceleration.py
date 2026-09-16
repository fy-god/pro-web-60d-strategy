"""Causal main-wave acceleration strategy using only visible session bars."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import recent_return_series, returns, slope


STRATEGY_ID: str = "main_wave_acceleration"
DISPLAY_NAME: str = "Main Wave Acceleration"
THESIS: str = (
    "A main wave is more credible when returns align across horizons, visible "
    "trend slopes stay positive, highs and lows rise, acceleration is recent, "
    "and the move is not already overextended."
)
THRESHOLD: float = 0.85
FORMULA: str = (
    "score = 0.25*aligned_multi_horizon_returns + 0.20*positive_slopes + "
    "0.20*higher_highs_lows + 0.20*recent_acceleration + "
    "0.15*overextension_penalty; predict 1 iff score >= 0.85."
)
FACTOR_DEFINITIONS: dict[str, str] = {
    "aligned_multi_horizon_returns": (
        "1.0 when the visible 5-, 10-, and 20-session close returns are at least "
        "3%, 5%, and 10%, respectively; otherwise 0.0."
    ),
    "positive_slopes": (
        "1.0 when visible close slopes over the last 10, 20, and 40 sessions are "
        "all positive; otherwise 0.0."
    ),
    "higher_highs_lows": (
        "1.0 when the latest visible 10-session block has both a higher maximum "
        "high and a higher minimum low than the preceding 10-session block; "
        "otherwise 0.0."
    ),
    "recent_acceleration": (
        "1.0 when the mean of the last three visible close-to-close returns is "
        "greater than the mean of the first three returns in the latest 10-return "
        "window and the latest return is positive; otherwise 0.0."
    ),
    "overextension_penalty": (
        "Full credit while the visible 20-session return is at most 20%; above "
        "20%, credit declines linearly to zero at 40% and is clipped to [0, 1]."
    ),
}


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    closes = tuple(bar.close for bar in card.bars)

    horizon_returns = tuple(
        returns(card.bars, periods=period)
        for period in (5, 10, 20)
    )
    aligned_multi_horizon_returns = float(
        all(
            value >= minimum
            for value, minimum in zip(
                horizon_returns,
                (0.03, 0.05, 0.10),
                strict=True,
            )
        )
    )

    slope_values = tuple(
        slope(closes, window=window)
        for window in (10, 20, 40)
    )
    positive_slopes = float(all(value > 0.0 for value in slope_values))

    prior_block = card.bars[-20:-10]
    recent_block = card.bars[-10:]
    higher_highs_lows = float(
        max(bar.high for bar in recent_block)
        > max(bar.high for bar in prior_block)
        and min(bar.low for bar in recent_block)
        > min(bar.low for bar in prior_block)
    )

    recent_returns = recent_return_series(card.bars, window=10)
    recent_acceleration = float(
        sum(recent_returns[-3:]) / 3.0
        > sum(recent_returns[:3]) / 3.0
        and recent_returns[-1] > 0.0
    )

    extension = returns(card.bars, periods=20)
    overextension_penalty = (
        1.0
        if extension <= 0.20
        else _clip((0.40 - extension) / 0.20)
    )

    components = {
        "aligned_multi_horizon_returns": aligned_multi_horizon_returns,
        "positive_slopes": positive_slopes,
        "higher_highs_lows": higher_highs_lows,
        "recent_acceleration": recent_acceleration,
        "overextension_penalty": overextension_penalty,
    }
    score = (
        0.25 * aligned_multi_horizon_returns
        + 0.20 * positive_slopes
        + 0.20 * higher_highs_lows
        + 0.20 * recent_acceleration
        + 0.15 * overextension_penalty
    )
    rationale = (
        f"Visible 5/10/20-session returns={horizon_returns!r}; "
        f"10/20/40-session slopes={slope_values!r}; higher highs/lows="
        f"{higher_highs_lows:.0f}; recent acceleration={recent_acceleration:.0f}; "
        f"20-session extension={extension:.4f}; weighted score={score:.4f} "
        f"against threshold={THRESHOLD:.2f}."
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
