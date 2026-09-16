"""Short-term RSI-style mean reversion after a controlled selloff."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import (
    close_location,
    drawdown_from_high,
    kdj_cross_change,
    lower_wick_ratio,
    relative_strength_index,
    volume_ratio,
)


STRATEGY_ID = "rsi_mean_reversion"
DISPLAY_NAME = "RSI Mean Reversion"
THESIS = (
    "A short-term rebound is more credible after an oversold move when price is "
    "far below its recent high, downside rejection appears, KDJ turns upward, "
    "and selling volume is not accelerating into panic."
)
THRESHOLD = 0.68
FORMULA = (
    "score = 0.30*rsi_oversold + 0.25*drawdown + 0.20*rejection + "
    "0.15*kdj_turn + 0.10*nonpanic_volume; predict 1 iff score >= 0.68."
)
FACTOR_DEFINITIONS = {
    "rsi_oversold": "14-session RSI score: full credit at RSI 25 or below, zero at RSI 45 or above.",
    "drawdown": "Drawdown from the visible 20-session high, full credit at -20% or worse.",
    "rejection": "Combination of latest lower-wick ratio and close location, rewarding downside rejection.",
    "kdj_turn": "Three-session upward change in K-D spread, scaled at 8 points.",
    "nonpanic_volume": "Full credit when visible volume ratio is at or below 1.5; fades to zero at 3.0.",
}
SOURCE = "RSI short-term mean reversion"
SOURCE_REFERENCE = "Short-term reversal/liquidity research and common GitHub technical strategy family"
BATCH_TAG = "01a00acc-695f-7792-b239-b4a4c09e5d3c"


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    rsi = relative_strength_index(card.bars, 14)
    rsi_oversold = _clip((45.0 - rsi) / 20.0)
    drawdown = _clip(-drawdown_from_high(card.bars, 20) / 0.20)
    rejection = _clip(0.65 * lower_wick_ratio(card.bars[-1]) / 0.08 + 0.35 * close_location(card.bars[-1]))
    kdj_turn = _clip(kdj_cross_change(card, window=3) / 8.0)
    expansion = volume_ratio(card.bars, short=5, long=20)
    nonpanic_volume = _clip((3.0 - expansion) / 1.5)
    components = {
        "rsi_oversold": rsi_oversold,
        "drawdown": drawdown,
        "rejection": rejection,
        "kdj_turn": kdj_turn,
        "nonpanic_volume": nonpanic_volume,
    }
    score = 0.30 * rsi_oversold + 0.25 * drawdown + 0.20 * rejection + 0.15 * kdj_turn + 0.10 * nonpanic_volume
    rationale = (
        f"Visible RSI14={rsi:.2f}, 20-session drawdown={drawdown_from_high(card.bars, 20):.4f}, "
        f"lower-wick={lower_wick_ratio(card.bars[-1]):.4f}, K-D turn={kdj_cross_change(card, 3):.4f}, "
        f"volume ratio={expansion:.4f}; score={score:.4f}."
    )
    return ExpertDecision(STRATEGY_ID, card.sample_id, int(score >= THRESHOLD), score, THRESHOLD, components, rationale)
