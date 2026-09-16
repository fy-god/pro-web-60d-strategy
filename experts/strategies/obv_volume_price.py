"""OBV-style volume-price confirmation strategy."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import close_location, obv_slope, positive_volume_share, slope, volume_ratio


STRATEGY_ID = "obv_volume_price"
DISPLAY_NAME = "OBV Volume Price"
THESIS = (
    "Price strength is more credible when volume direction confirms it: OBV rises "
    "with price, up-day volume dominates down-day volume, and the latest close "
    "remains firm rather than being a thin price spike."
)
THRESHOLD = 0.70
FORMULA = (
    "score = 0.25*price_slope + 0.30*obv_slope + 0.20*up_volume_share "
    "+ 0.15*volume_confirmation + 0.10*close_strength; predict 1 iff score >= 0.70."
)
FACTOR_DEFINITIONS = {
    "price_slope": "20-session close slope, scaled to full credit at 12%.",
    "obv_slope": "20-session OBV change divided by average recent volume, scaled to [0,1].",
    "up_volume_share": "Share of the latest ten-session volume occurring on up-closing bars.",
    "volume_confirmation": "Visible five-session volume ratio, scaled from 1.0 to 2.0.",
    "close_strength": "Latest close location inside its range.",
}
SOURCE = "OBV volume-price confirmation"
SOURCE_REFERENCE = "Common GitHub volume-analysis strategy family; institutional price-volume confirmation"
BATCH_TAG = "01a00acc-695f-7792-b239-b4a4c09e5d3c"


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    price_slope = _clip(slope(tuple(bar.close for bar in card.bars), 20) / 0.12)
    obv = _clip(obv_slope(card.bars, 20) / 2.0)
    up_volume_share = _clip((positive_volume_share(card.bars, 10) - 0.35) / 0.45)
    expansion = volume_ratio(card.bars, short=5, long=20)
    volume_confirmation = _clip((expansion - 1.0) / 1.0)
    close_strength = close_location(card.bars[-1])
    components = {
        "price_slope": price_slope,
        "obv_slope": obv,
        "up_volume_share": up_volume_share,
        "volume_confirmation": volume_confirmation,
        "close_strength": close_strength,
    }
    score = 0.25 * price_slope + 0.30 * obv + 0.20 * up_volume_share + 0.15 * volume_confirmation + 0.10 * close_strength
    rationale = (
        f"Visible price slope={price_slope:.4f}, OBV normalized slope={obv:.4f}, "
        f"up-volume share={positive_volume_share(card.bars, 10):.4f}, volume ratio="
        f"{expansion:.4f}, close location={close_strength:.4f}; score={score:.4f}."
    )
    return ExpertDecision(STRATEGY_ID, card.sample_id, int(score >= THRESHOLD), score, THRESHOLD, components, rationale)

