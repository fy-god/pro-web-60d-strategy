"""Causal turnover weak-to-strong transition strategy."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import (
    EPS,
    close_location,
    high_low_span,
    returns,
    turnover_mean,
    volume_ratio,
)


STRATEGY_ID: str = "turnover_weak_to_strong"
DISPLAY_NAME: str = "Turnover Weak To Strong"
THESIS: str = (
    "A weak visible stretch is more credible as a transition when the latest "
    "recovery returns with higher turnover, a strong close, a broad bar, and "
    "confirmed volume expansion."
)
THRESHOLD: float = 0.90
FORMULA: str = (
    "score = 0.20*prior_weakness + 0.20*high_turnover_recovery + "
    "0.20*close_location + 0.20*broad_range + "
    "0.20*volume_ratio_confirmation; predict 1 when score >= 0.90."
)
FACTOR_DEFINITIONS: dict[str, str] = {
    "prior_weakness": (
        "clip(-returns(bars[:-5],20)/0.15,0,1), giving full credit when the "
        "visible 20-session pre-recovery return is at or below -15%."
    ),
    "high_turnover_recovery": (
        "The lesser of turnover expansion and recovery strength: turnover "
        "expansion is clip((five-session turnover mean / preceding 20-session "
        "turnover mean - 1.0),0,1), while recovery strength is "
        "clip(returns(bars,5)/0.10,0,1)."
    ),
    "close_location": (
        "close_location(bars[-1]), the latest visible close's position within "
        "its high-low range."
    ),
    "broad_range": (
        "clip(high_low_span(bars[-1])/0.12,0,1), giving full credit when the "
        "latest visible high-low span is at least 12% of its open."
    ),
    "volume_ratio_confirmation": (
        "clip((volume_ratio(bars,5,20)-1.0)/1.0,0,1), giving full credit at "
        "a visible five-session volume ratio of 2.0 or higher."
    ),
}


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    bars = card.bars
    prior_bars = bars[:-5]
    recovery_bars = bars[-5:]

    prior_return = returns(prior_bars, periods=20)
    prior_weakness = _clip(-prior_return / 0.15)

    preceding_turnover = turnover_mean(prior_bars[-20:], window=20)
    recovery_turnover = turnover_mean(recovery_bars, window=5)
    turnover_expansion = _clip(
        (recovery_turnover / (preceding_turnover + EPS) - 1.0)
    )
    recovery_strength = _clip(returns(bars, periods=5) / 0.10)
    high_turnover_recovery = min(turnover_expansion, recovery_strength)

    latest_bar = bars[-1]
    close_location_score = close_location(latest_bar)
    broad_range = _clip(high_low_span(latest_bar) / 0.12)

    expansion_ratio = volume_ratio(bars, short=5, long=20)
    volume_ratio_confirmation = _clip((expansion_ratio - 1.0) / 1.0)

    components = {
        "prior_weakness": prior_weakness,
        "high_turnover_recovery": high_turnover_recovery,
        "close_location": close_location_score,
        "broad_range": broad_range,
        "volume_ratio_confirmation": volume_ratio_confirmation,
    }
    score = sum(0.20 * value for value in components.values())
    rationale = (
        f"Visible pre-recovery 20-session return={prior_return:.4f}; "
        f"turnover expansion={turnover_expansion:.4f}, recovery strength="
        f"{recovery_strength:.4f}; latest close location="
        f"{close_location_score:.4f}, high-low span="
        f"{high_low_span(latest_bar):.4f}; volume ratio={expansion_ratio:.4f}; "
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
