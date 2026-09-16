"""Institutional-style multi-horizon relative-strength proxy."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import close_location, returns, slope


STRATEGY_ID = "relative_strength_rank"
DISPLAY_NAME = "Relative Strength Rank"
THESIS = (
    "A short swing candidate should show strength across multiple horizons, not "
    "only a one-day spike; persistent positive returns and a firm close receive "
    "credit while extreme extension is penalized."
)
THRESHOLD = 0.72
FORMULA = (
    "score = 0.30*five_day_strength + 0.25*twenty_day_strength + "
    "0.20*forty_day_strength + 0.15*trend_alignment + 0.10*close_strength; "
    "predict 1 iff score >= 0.72."
)
FACTOR_DEFINITIONS = {
    "five_day_strength": "Five-session close return scaled from 0% to 12%.",
    "twenty_day_strength": "Twenty-session close return scaled from 0% to 25%.",
    "forty_day_strength": "Forty-session close return scaled from 0% to 50%.",
    "trend_alignment": "Average of positive 20- and 40-session close slopes, scaled to typical short-swing strength.",
    "close_strength": "Latest close location inside its range.",
}
SOURCE = "Multi-horizon momentum / relative strength"
SOURCE_REFERENCE = "MSCI/Barra momentum factor family; Qlib Alpha158 cross-sectional research"
BATCH_TAG = "01a00acc-695f-7792-b239-b4a4c09e5d3c"


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    five = _clip(returns(card.bars, 5) / 0.12)
    twenty = _clip(returns(card.bars, 20) / 0.25)
    forty = _clip(returns(card.bars, 40) / 0.50)
    slopes = tuple(slope(tuple(bar.close for bar in card.bars), window) for window in (20, 40))
    trend_alignment = _clip(sum(slopes) / 2.0 / 0.15)
    close_strength = close_location(card.bars[-1])
    components = {
        "five_day_strength": five,
        "twenty_day_strength": twenty,
        "forty_day_strength": forty,
        "trend_alignment": trend_alignment,
        "close_strength": close_strength,
    }
    score = 0.30 * five + 0.25 * twenty + 0.20 * forty + 0.15 * trend_alignment + 0.10 * close_strength
    rationale = (
        f"Visible 5/20/40-session returns=({returns(card.bars, 5):.4f}, "
        f"{returns(card.bars, 20):.4f}, {returns(card.bars, 40):.4f}), slopes="
        f"{slopes!r}, close location={close_strength:.4f}; score={score:.4f}."
    )
    return ExpertDecision(STRATEGY_ID, card.sample_id, int(score >= THRESHOLD), score, THRESHOLD, components, rationale)

