"""Breakout pullback and support-retest strategy."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import close_location, distance_from_prior_high, volume_ratio


STRATEGY_ID = "pullback_retest"
DISPLAY_NAME = "Pullback Retest"
THESIS = (
    "A breakout continuation is stronger when a prior impulse is followed by a "
    "shallow, lower-volume pullback that remains near the old breakout level and "
    "finishes with a stable close."
)
THRESHOLD = 0.70
FORMULA = (
    "score = 0.25*prior_impulse + 0.25*shallow_pullback + 0.25*level_hold "
    "+ 0.15*volume_dryup + 0.10*close_stability; predict 1 iff score >= 0.70."
)
FACTOR_DEFINITIONS = {
    "prior_impulse": "The preceding ten-session return before the latest five-session pullback, full credit at 12%.",
    "shallow_pullback": "Latest five-session return in [-8%, 2%], with the deepest pullback penalized beyond 8%.",
    "level_hold": "Latest close distance from the prior 20-session high, full credit at -2% or better.",
    "volume_dryup": "Inverse visible five-session volume ratio, rewarding a pullback below the prior baseline.",
    "close_stability": "Latest close location inside its range.",
}
SOURCE = "Breakout pullback and retest"
SOURCE_REFERENCE = "GitHub A-share pullback-repair pattern; CTA support/retest logic"
BATCH_TAG = "01a00acc-695f-7792-b239-b4a4c09e5d3c"


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    closes = tuple(bar.close for bar in card.bars)
    prior_impulse_return = closes[-6] / (closes[-16] + 1e-12) - 1.0
    prior_impulse = _clip(prior_impulse_return / 0.12)
    pullback_return = closes[-1] / (closes[-6] + 1e-12) - 1.0
    shallow_pullback = _clip((0.02 - pullback_return) / 0.10) if pullback_return <= 0.02 else 0.0
    level_distance = distance_from_prior_high(card.bars, 20)
    level_hold = _clip((level_distance + 0.08) / 0.06)
    expansion = volume_ratio(card.bars, short=5, long=20)
    volume_dryup = _clip((1.5 - expansion) / 0.75)
    close_stability = close_location(card.bars[-1])
    components = {
        "prior_impulse": prior_impulse,
        "shallow_pullback": shallow_pullback,
        "level_hold": level_hold,
        "volume_dryup": volume_dryup,
        "close_stability": close_stability,
    }
    score = 0.25 * prior_impulse + 0.25 * shallow_pullback + 0.25 * level_hold + 0.15 * volume_dryup + 0.10 * close_stability
    rationale = (
        f"Visible pre-pullback impulse={prior_impulse_return:.4f}, pullback="
        f"{pullback_return:.4f}, level distance={level_distance:.4f}, volume ratio="
        f"{expansion:.4f}; score={score:.4f}."
    )
    return ExpertDecision(STRATEGY_ID, card.sample_id, int(score >= THRESHOLD), score, THRESHOLD, components, rationale)

