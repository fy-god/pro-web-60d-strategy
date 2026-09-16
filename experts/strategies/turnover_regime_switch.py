"""Turnover-conditioned short-term momentum versus reversal strategy."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import EPS, kdj_cross_change, returns, turnover_mean


STRATEGY_ID = "turnover_regime_switch"
DISPLAY_NAME = "Turnover Regime Switch"
THESIS = (
    "Short-horizon continuation and reversal need different liquidity regimes: "
    "high turnover can validate news-like momentum, while low turnover makes a "
    "sharp short-term selloff more likely to mean-revert."
)
THRESHOLD = 0.62
FORMULA = (
    "score = 0.35*high_turnover_momentum + 0.30*low_turnover_reversal "
    "+ 0.20*kdj_recovery + 0.15*regime_clarity; predict 1 iff score >= 0.62."
)
FACTOR_DEFINITIONS = {
    "high_turnover_momentum": "Minimum of turnover expansion and positive five-session return strength.",
    "low_turnover_reversal": "Minimum of negative three-session shock strength and inverse turnover expansion.",
    "kdj_recovery": "Three-session upward change in K-D spread, scaled at 8 points.",
    "regime_clarity": "Distance of the turnover ratio from the ambiguous middle regime, clipped to [0,1].",
}
SOURCE = "Turnover-conditioned momentum/reversal"
SOURCE_REFERENCE = "Chiang, Kirby and Nie short-term momentum/reversal research"
BATCH_TAG = "01a00acc-695f-7792-b239-b4a4c09e5d3c"


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    short_turnover = turnover_mean(card.bars, 5)
    prior_turnover = turnover_mean(card.bars[:-5], 20)
    ratio = short_turnover / (prior_turnover + EPS)
    turnover_expansion = _clip((ratio - 1.0) / 1.0)
    momentum = _clip(returns(card.bars, 5) / 0.10)
    high_turnover_momentum = min(turnover_expansion, momentum)
    shock = _clip(-returns(card.bars, 3) / 0.08)
    low_turnover = _clip((1.5 - ratio) / 1.0)
    low_turnover_reversal = min(shock, low_turnover)
    kdj_recovery = _clip(kdj_cross_change(card, 3) / 8.0)
    regime_clarity = _clip(abs(ratio - 1.0) / 0.75)
    components = {
        "high_turnover_momentum": high_turnover_momentum,
        "low_turnover_reversal": low_turnover_reversal,
        "kdj_recovery": kdj_recovery,
        "regime_clarity": regime_clarity,
    }
    score = 0.35 * high_turnover_momentum + 0.30 * low_turnover_reversal + 0.20 * kdj_recovery + 0.15 * regime_clarity
    rationale = (
        f"Visible turnover ratio={ratio:.4f}, five-session return={returns(card.bars, 5):.4f}, "
        f"three-session shock={returns(card.bars, 3):.4f}, K-D change="
        f"{kdj_cross_change(card, 3):.4f}; score={score:.4f}."
    )
    return ExpertDecision(STRATEGY_ID, card.sample_id, int(score >= THRESHOLD), score, THRESHOLD, components, rationale)

