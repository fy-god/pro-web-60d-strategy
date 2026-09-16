"""Causal rising-structure, washout, and renewal strategy."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import (
    EPS,
    close_location,
    kdj_cross_change,
    kdj_turn,
    returns,
    slope,
    volume_ratio,
)


STRATEGY_ID: str = "washout_complete"
DISPLAY_NAME: str = "Washout Complete"
THESIS: str = (
    "A visible rising structure followed by a low-volume pullback that holds prior "
    "support, turns upward in KDJ, and finishes with renewed close strength."
)
THRESHOLD: float = 0.82
FORMULA: str = (
    "0.24*rising_structure + 0.20*shrinking_volume_pullback + "
    "0.20*support_hold + 0.16*kdj_turn + 0.20*renewed_close_strength"
)
FACTOR_DEFINITIONS: dict[str, str] = {
    "rising_structure": (
        "0.50*clip((returns(bars,35)+0.04)/0.20,0,1) + "
        "0.50*clip((slope(closes,35)+0.02)/0.16,0,1)"
    ),
    "shrinking_volume_pullback": (
        "0.55*clip(-returns(bars[:-5],4)/0.06,0,1) + "
        "0.45*clip((1.10-volume_ratio(bars[:-5],5,20))/0.60,0,1)"
    ),
    "support_hold": (
        "clip(((min(low[-15:-5])-min(close[-35:-15]))/"
        "(abs(min(close[-35:-15]))+EPS))/0.05,0,1)"
    ),
    "kdj_turn": (
        "0.50*clip((kdj_turn(card)+4.0)/18.0,0,1) + "
        "0.50*clip(kdj_cross_change(card,5)/20.0,0,1)"
    ),
    "renewed_close_strength": (
        "0.55*close_location(last_bar) + "
        "0.45*clip((returns(bars,3)+0.01)/0.07,0,1)"
    ),
}


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    bars = card.bars
    closes = tuple(bar.close for bar in bars)

    rising_structure = 0.5 * _clip((returns(bars, 35) + 0.04) / 0.20) + 0.5 * _clip(
        (slope(closes, 35) + 0.02) / 0.16
    )

    pullback_bars = bars[:-5]
    pullback_return = returns(pullback_bars, 4)
    pullback_volume_ratio = volume_ratio(pullback_bars, short=5, long=20)
    shrinking_volume_pullback = 0.55 * _clip(-pullback_return / 0.06) + 0.45 * _clip(
        (1.10 - pullback_volume_ratio) / 0.60
    )

    prior_base_support = min(bar.close for bar in bars[-35:-15])
    pullback_floor = min(bar.low for bar in bars[-15:-5])
    support_gap = (pullback_floor - prior_base_support) / (
        abs(prior_base_support) + EPS
    )
    support_hold = _clip(support_gap / 0.05)

    kdj_turn_component = 0.5 * _clip((kdj_turn(card) + 4.0) / 18.0) + 0.5 * _clip(
        kdj_cross_change(card, 5) / 20.0
    )

    renewed_close_strength = 0.55 * close_location(bars[-1]) + 0.45 * _clip(
        (returns(bars, 3) + 0.01) / 0.07
    )

    components = {
        "rising_structure": rising_structure,
        "shrinking_volume_pullback": shrinking_volume_pullback,
        "support_hold": support_hold,
        "kdj_turn": kdj_turn_component,
        "renewed_close_strength": renewed_close_strength,
    }
    score = (
        0.24 * components["rising_structure"]
        + 0.20 * components["shrinking_volume_pullback"]
        + 0.20 * components["support_hold"]
        + 0.16 * components["kdj_turn"]
        + 0.20 * components["renewed_close_strength"]
    )
    prediction = int(score >= THRESHOLD)
    rationale = (
        f"Visible rising structure={rising_structure:.3f}, "
        f"shrinking-volume pullback={shrinking_volume_pullback:.3f}, "
        f"support hold={support_hold:.3f}, KDJ turn={kdj_turn_component:.3f}, "
        f"renewed close strength={renewed_close_strength:.3f}; "
        f"weighted score={score:.3f} against threshold={THRESHOLD:.2f}."
    )
    return ExpertDecision(
        STRATEGY_ID,
        card.sample_id,
        prediction,
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
