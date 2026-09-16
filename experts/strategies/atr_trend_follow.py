"""ATR-normalized trend-following setup."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import average_true_range, close_location, distance_from_prior_high, slope


STRATEGY_ID = "atr_trend_follow"
DISPLAY_NAME = "ATR Trend Follow"
THESIS = (
    "Trend continuation is more actionable when the price is above its recent "
    "channel, the slope is positive, the move closes firmly, and volatility is "
    "large enough to move but not so large that a fixed stop is meaningless."
)
THRESHOLD = 0.72
FORMULA = (
    "score = 0.30*channel_position + 0.25*trend_slope + 0.20*atr_regime "
    "+ 0.15*close_strength + 0.10*stop_room; predict 1 iff score >= 0.72."
)
FACTOR_DEFINITIONS = {
    "channel_position": "Latest close distance above the prior 20-session high, scaled around the breakout boundary.",
    "trend_slope": "20-session close slope, scaled to full credit at 15%.",
    "atr_regime": "Full credit for ATR14/close between 2% and 8%; fades outside a 1%-12% range.",
    "close_strength": "Latest close location inside its high-low range.",
    "stop_room": "Credit for at least 1.5 ATR of room between the latest close and the recent 10-session low.",
}
SOURCE = "ATR-normalized trend following"
SOURCE_REFERENCE = "CTA volatility sizing and stop logic; VeighNa backtest workflow"
BATCH_TAG = "01a00acc-695f-7792-b239-b4a4c09e5d3c"


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    latest = card.bars[-1]
    atr = average_true_range(card.bars, 14)
    atr_pct = atr / (latest.close + 1e-12)
    channel_position = _clip((distance_from_prior_high(card.bars, 20) + 0.02) / 0.05)
    trend_slope = _clip(slope(tuple(bar.close for bar in card.bars), 20) / 0.15)
    atr_regime = _clip((atr_pct - 0.01) / 0.01) if atr_pct < 0.02 else _clip((0.12 - atr_pct) / 0.04)
    close_strength = close_location(latest)
    recent_low = min(bar.low for bar in card.bars[-10:])
    stop_room = _clip((latest.close - recent_low) / (1.5 * atr + 1e-12))
    components = {
        "channel_position": channel_position,
        "trend_slope": trend_slope,
        "atr_regime": atr_regime,
        "close_strength": close_strength,
        "stop_room": stop_room,
    }
    score = 0.30 * channel_position + 0.25 * trend_slope + 0.20 * atr_regime + 0.15 * close_strength + 0.10 * stop_room
    rationale = (
        f"Visible breakout distance={distance_from_prior_high(card.bars, 20):.4f}, "
        f"20-session slope={slope(tuple(bar.close for bar in card.bars), 20):.4f}, "
        f"ATR14/close={atr_pct:.4f}, stop room={stop_room:.4f}; score={score:.4f}."
    )
    return ExpertDecision(STRATEGY_ID, card.sample_id, int(score >= THRESHOLD), score, THRESHOLD, components, rationale)

