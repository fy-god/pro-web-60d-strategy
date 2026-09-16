"""Daily-bar proxy for an A-share gap and follow-through setup."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import close_location, upper_wick_ratio, volume_ratio


STRATEGY_ID = "gap_follow_through"
DISPLAY_NAME = "Gap Follow Through"
THESIS = (
    "A positive opening gap is more credible as continuation when the day holds "
    "above the prior close, closes near its high, expands volume, and avoids a "
    "large upper rejection wick."
)
THRESHOLD = 0.72
FORMULA = (
    "score = 0.30*gap_quality + 0.25*close_strength + 0.20*volume_confirmation "
    "+ 0.15*range_acceptance + 0.10*rejection_control; predict 1 iff score >= 0.72."
)
FACTOR_DEFINITIONS = {
    "gap_quality": "Latest open divided by prior close: full credit for a 1.5%-6% positive gap, zero for no gap or an excessive gap.",
    "close_strength": "Latest close location inside its high-low range.",
    "volume_confirmation": "Visible five-session volume ratio, scaled from 1.0 to 2.0.",
    "range_acceptance": "Latest close return is positive and the low does not erase the prior close gap reference.",
    "rejection_control": "Inverse upper-wick score, rewarding a close that does not reject the gap.",
}
SOURCE = "A-share gap continuation"
SOURCE_REFERENCE = "GitHub A-share patterns: auction breakout and gentle gap repair"
BATCH_TAG = "01a00acc-695f-7792-b239-b4a4c09e5d3c"


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    previous = card.bars[-2]
    latest = card.bars[-1]
    gap = latest.open / (previous.close + 1e-12) - 1.0
    gap_quality = _clip((gap - 0.005) / 0.055) if gap > 0 else 0.0
    close_strength = close_location(latest)
    expansion = volume_ratio(card.bars, short=5, long=20)
    volume_confirmation = _clip((expansion - 1.0) / 1.0)
    range_acceptance = float(latest.close > previous.close and latest.low >= previous.close * 0.985)
    rejection_control = _clip(1.0 - upper_wick_ratio(latest) / 0.12)
    components = {
        "gap_quality": gap_quality,
        "close_strength": close_strength,
        "volume_confirmation": volume_confirmation,
        "range_acceptance": range_acceptance,
        "rejection_control": rejection_control,
    }
    score = 0.30 * gap_quality + 0.25 * close_strength + 0.20 * volume_confirmation + 0.15 * range_acceptance + 0.10 * rejection_control
    rationale = (
        f"Visible opening gap={gap:.4f}, close location={close_strength:.4f}, "
        f"volume ratio={expansion:.4f}, gap hold={range_acceptance:.0f}, "
        f"upper-wick control={rejection_control:.4f}; score={score:.4f}."
    )
    return ExpertDecision(STRATEGY_ID, card.sample_id, int(score >= THRESHOLD), score, THRESHOLD, components, rationale)

