"""Donchian/Turtle-style trend breakout using visible daily bars only."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import (
    average_true_range,
    close_location,
    distance_from_prior_high,
    slope,
    volume_ratio,
)


STRATEGY_ID = "donchian_turtle"
DISPLAY_NAME = "Donchian Turtle Breakout"
THESIS = (
    "A channel breakout is stronger when price clears the prior high, the trend "
    "is already positive, volume confirms the move, and ATR is tradable rather "
    "than either stagnant or panic-wide."
)
THRESHOLD = 0.72
FORMULA = (
    "score = 0.35*channel_breakout + 0.25*trend_filter + "
    "0.20*volume_confirmation + 0.20*atr_tradeability; predict 1 iff score >= 0.72."
)
FACTOR_DEFINITIONS = {
    "channel_breakout": "Distance of the visible close above the prior 20-session high, scaled to full credit at 3%.",
    "trend_filter": "Positive 20-session close slope, scaled to full credit at 12%.",
    "volume_confirmation": "Visible five-session volume ratio, scaled from 1.0 to 2.0.",
    "atr_tradeability": "Full credit when 14-session ATR is 1.5%-8.0% of price; credit declines outside that band.",
}
SOURCE = "Donchian/Turtle trend following"
SOURCE_REFERENCE = "VeighNa CTA strategy lineage; Qlib factor/backtest workflow"
BATCH_TAG = "01a00acc-695f-7792-b239-b4a4c09e5d3c"


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    breakout_distance = distance_from_prior_high(card.bars, window=20)
    channel_breakout = _clip((breakout_distance + 0.01) / 0.04)
    trend_filter = _clip(slope(tuple(bar.close for bar in card.bars), 20) / 0.12)
    expansion = volume_ratio(card.bars, short=5, long=20)
    volume_confirmation = _clip((expansion - 1.0) / 1.0)
    atr_pct = average_true_range(card.bars, 14) / (card.bars[-1].close + 1e-12)
    atr_tradeability = 1.0 if 0.015 <= atr_pct <= 0.08 else _clip(
        atr_pct / 0.015 if atr_pct < 0.015 else (0.12 - atr_pct) / 0.04
    )
    components = {
        "channel_breakout": channel_breakout,
        "trend_filter": trend_filter,
        "volume_confirmation": volume_confirmation,
        "atr_tradeability": atr_tradeability,
    }
    score = (
        0.35 * channel_breakout
        + 0.25 * trend_filter
        + 0.20 * volume_confirmation
        + 0.20 * atr_tradeability
    )
    rationale = (
        f"Visible prior-20 breakout distance={breakout_distance:.4f}, 20-session "
        f"slope={slope(tuple(bar.close for bar in card.bars), 20):.4f}, volume ratio="
        f"{expansion:.4f}, ATR14/close={atr_pct:.4f}; score={score:.4f}."
    )
    return ExpertDecision(STRATEGY_ID, card.sample_id, int(score >= THRESHOLD), score, THRESHOLD, components, rationale)
