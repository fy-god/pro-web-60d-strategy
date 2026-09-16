"""Visible-bar oversold rebound specialist."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import (
    close_location as _close_location,
    drawdown_from_high as _drawdown_from_high,
    kdj_cross_change as _kdj_cross_change,
    kdj_turn as _kdj_turn,
    lower_wick_ratio as _lower_wick_ratio,
    position_in_window as _position_in_window,
    returns as _returns,
    volume_ratio as _volume_ratio,
)


STRATEGY_ID: str = "oversold_rebound"
DISPLAY_NAME: str = "Oversold Rebound"
THESIS: str = (
    "A rebound from a deeply sold-off, low-range position is more credible when selling "
    "pressure fades, KDJ turns from oversold, downside rejection appears, and the close recovers."
)
THRESHOLD: float = 0.82
FORMULA: str = (
    "score = 0.18*deep_drawdown + 0.14*low_range_percentile + "
    "0.16*selling_exhaustion + 0.20*kdj_oversold_turn + "
    "0.12*lower_wick + 0.20*reversal_close; "
    "predict 1 iff score >= 0.82."
)
FACTOR_DEFINITIONS: dict[str, str] = {
    "deep_drawdown": (
        "clip(-drawdown_from_high(bars[:-1],20)/0.15,0,1), where a 15% or larger "
        "drawdown into the pre-reversal close receives full credit."
    ),
    "low_range_percentile": (
        "clip(1-position_in_window(bars[:-1],20),0,1), so a pre-reversal close at "
        "the bottom of its recent visible range receives full credit."
    ),
    "selling_exhaustion": (
        "0.55*clip(-returns(bars[:-1],4)/0.05,0,1) + "
        "0.45*clip((1.10-volume_ratio(bars[:-1],5,20))/0.70,0,1), "
        "combining a final selloff with fading volume."
    ),
    "kdj_oversold_turn": (
        "0.40*clip((30-min(kdj_k[-5:]))/20,0,1) + "
        "0.35*clip(kdj_cross_change(card,5)/15,0,1) + "
        "0.25*clip(kdj_turn(card)/5,0,1)."
    ),
    "lower_wick": (
        "clip(lower_wick_ratio(last_bar)/0.06,0,1), with a lower wick at least "
        "6% of the current open receiving full credit."
    ),
    "reversal_close": (
        "0.55*close_location(last_bar) + 0.45*clip(returns(bars,3)/0.06,0,1), "
        "combining close placement with a short visible rebound."
    ),
}


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    pre_reversal = card.bars[:-1]
    current = card.bars[-1]

    deep_drawdown = _clip(-_drawdown_from_high(pre_reversal, window=20) / 0.15)
    low_range_percentile = _clip(
        1.0 - _position_in_window(pre_reversal, window=20)
    )

    selling_pressure = _clip(-_returns(pre_reversal, periods=4) / 0.05)
    volume_fade = _clip(
        (1.10 - _volume_ratio(pre_reversal, short=5, long=20)) / 0.70
    )
    selling_exhaustion = 0.55 * selling_pressure + 0.45 * volume_fade

    recent_kdj_k = card.indicator_series("kdj_k")[-5:]
    oversold_level = _clip((30.0 - min(recent_kdj_k)) / 20.0)
    upward_cross = _clip(_kdj_cross_change(card, window=5) / 15.0)
    current_turn = _clip(_kdj_turn(card) / 5.0)
    kdj_oversold_turn = (
        0.40 * oversold_level + 0.35 * upward_cross + 0.25 * current_turn
    )

    lower_wick = _clip(_lower_wick_ratio(current) / 0.06)
    reversal_close = 0.55 * _close_location(current) + 0.45 * _clip(
        _returns(card.bars, periods=3) / 0.06
    )

    components = {
        "deep_drawdown": deep_drawdown,
        "low_range_percentile": low_range_percentile,
        "selling_exhaustion": selling_exhaustion,
        "kdj_oversold_turn": kdj_oversold_turn,
        "lower_wick": lower_wick,
        "reversal_close": reversal_close,
    }
    score = (
        0.18 * deep_drawdown
        + 0.14 * low_range_percentile
        + 0.16 * selling_exhaustion
        + 0.20 * kdj_oversold_turn
        + 0.12 * lower_wick
        + 0.20 * reversal_close
    )
    rationale = (
        f"Visible factors: deep drawdown={deep_drawdown:.3f}, "
        f"low range percentile={low_range_percentile:.3f}, "
        f"selling exhaustion={selling_exhaustion:.3f}, "
        f"KDJ oversold turn={kdj_oversold_turn:.3f}, "
        f"lower wick={lower_wick:.3f}, reversal close={reversal_close:.3f}; "
        f"weighted score={score:.3f} against threshold={THRESHOLD:.2f}."
    )
    return ExpertDecision(
        strategy_id=STRATEGY_ID,
        sample_id=card.sample_id,
        prediction=int(score >= THRESHOLD),
        score=score,
        threshold=THRESHOLD,
        components=components,
        rationale=rationale,
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
