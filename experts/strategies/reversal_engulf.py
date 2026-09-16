"""Visible-bar bullish reversal engulfing specialist."""

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import (
    EPS as _EPS,
    distance_from_prior_high as _distance_from_prior_high,
    lower_wick_ratio as _lower_wick_ratio,
    returns as _returns,
    volume_ratio as _volume_ratio,
)


STRATEGY_ID = "reversal_engulf"
DISPLAY_NAME = "Reversal Engulf"
THESIS = (
    "A bullish engulfing reversal is stronger when a visible bearish impulse and pullback "
    "are followed by body recovery, a high reclaim, downside rejection, and volume confirmation."
)
THRESHOLD = 0.82
FORMULA = (
    "score = 0.22*prior_impulse + 0.16*pullback + 0.20*body_recovery + "
    "0.17*high_reclaim + 0.10*lower_wick + 0.15*volume_confirmation; "
    "each component is clipped to [0, 1]; predict 1 iff score >= 0.82."
)
FACTOR_DEFINITIONS = {
    "prior_impulse": (
        "The negative four-session return across the last five visible pre-reversal closes, "
        "with an 8% decline receiving full credit."
    ),
    "pullback": (
        "The negative one-session return across the final two visible pre-reversal closes, "
        "with a 4% decline receiving full credit."
    ),
    "body_recovery": (
        "The current visible bullish body divided by the previous visible bearish body, "
        "clipped at full recovery."
    ),
    "high_reclaim": (
        "The current visible close above the highest close in the prior five visible bars, "
        "with a 3% reclaim receiving full credit."
    ),
    "lower_wick": (
        "The current visible lower-wick ratio, with a 3% wick relative to the current open "
        "receiving full credit."
    ),
    "volume_confirmation": (
        "The current five-visible-bar mean volume relative to the preceding sixteen visible "
        "bars, with a 1.5x ratio receiving full credit."
    ),
}


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    visible_before_reversal = card.bars[:-1]
    previous = card.bars[-2]
    current = card.bars[-1]

    prior_impulse = _clip(-_returns(visible_before_reversal, 4) / 0.08)
    pullback = _clip(-_returns(visible_before_reversal, 1) / 0.04)

    previous_bearish_body = max(0.0, previous.open - previous.close)
    current_bullish_body = max(0.0, current.close - current.open)
    body_recovery = _clip(current_bullish_body / (previous_bearish_body + _EPS))

    high_reclaim = _clip(_distance_from_prior_high(card.bars, window=5) / 0.03)
    lower_wick = _clip(_lower_wick_ratio(current) / 0.03)
    volume_confirmation = _clip(
        (_volume_ratio(card.bars, short=5, long=20) - 1.0) / 0.5
    )

    components = {
        "prior_impulse": prior_impulse,
        "pullback": pullback,
        "body_recovery": body_recovery,
        "high_reclaim": high_reclaim,
        "lower_wick": lower_wick,
        "volume_confirmation": volume_confirmation,
    }
    score = (
        0.22 * prior_impulse
        + 0.16 * pullback
        + 0.20 * body_recovery
        + 0.17 * high_reclaim
        + 0.10 * lower_wick
        + 0.15 * volume_confirmation
    )
    rationale = (
        "Visible factors: "
        f"prior impulse={prior_impulse:.3f}, pullback={pullback:.3f}, "
        f"body recovery={body_recovery:.3f}, high reclaim={high_reclaim:.3f}, "
        f"lower wick={lower_wick:.3f}, volume confirmation={volume_confirmation:.3f}; "
        f"weighted score={score:.3f} versus threshold={THRESHOLD:.2f}."
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
