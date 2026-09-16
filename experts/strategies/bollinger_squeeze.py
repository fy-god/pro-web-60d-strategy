"""Bollinger-style volatility squeeze and expansion setup."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import EPS, close_location, rolling_mean, rolling_std, volume_ratio


STRATEGY_ID = "bollinger_squeeze"
DISPLAY_NAME = "Bollinger Squeeze"
THESIS = (
    "A compressed range can precede a short-term expansion when the latest close "
    "reclaims the middle band, volatility starts expanding, and volume confirms "
    "the release without a weak close."
)
THRESHOLD = 0.70
FORMULA = (
    "score = 0.25*squeeze + 0.30*band_release + 0.20*volatility_expansion "
    "+ 0.15*volume_confirmation + 0.10*close_strength; predict 1 iff score >= 0.70."
)
FACTOR_DEFINITIONS = {
    "squeeze": "Full credit when 20-session close standard deviation divided by its mean is at most 6%; fades to zero at 12%.",
    "band_release": "Latest close relative to the 20-session mean and two standard deviations, with full credit above the middle band.",
    "volatility_expansion": "Five-session close volatility divided by the preceding 15-session volatility, scaled from 1.0 to 2.0.",
    "volume_confirmation": "Visible five-session volume ratio, scaled from 1.0 to 2.0.",
    "close_strength": "Latest close location inside its high-low range.",
}
SOURCE = "Bollinger volatility squeeze"
SOURCE_REFERENCE = "Popular technical-system family; Qlib Alpha158 volatility features"
BATCH_TAG = "01a00acc-695f-7792-b239-b4a4c09e5d3c"


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    closes = tuple(bar.close for bar in card.bars)
    mean20 = rolling_mean(closes, 20)
    std20 = rolling_std(closes, 20)
    volatility_pct = std20 / (mean20 + EPS)
    squeeze = _clip((0.12 - volatility_pct) / 0.06)
    band_release = _clip((closes[-1] - mean20) / (2.0 * std20 + EPS) + 0.5)
    prior_std = rolling_std(closes[:-5], 15)
    recent_std = rolling_std(closes, 5)
    volatility_expansion = _clip((recent_std / (prior_std + EPS) - 1.0) / 1.0)
    expansion_ratio = volume_ratio(card.bars, short=5, long=20)
    volume_confirmation = _clip((expansion_ratio - 1.0) / 1.0)
    close_strength = close_location(card.bars[-1])
    components = {
        "squeeze": squeeze,
        "band_release": band_release,
        "volatility_expansion": volatility_expansion,
        "volume_confirmation": volume_confirmation,
        "close_strength": close_strength,
    }
    score = (
        0.25 * squeeze
        + 0.30 * band_release
        + 0.20 * volatility_expansion
        + 0.15 * volume_confirmation
        + 0.10 * close_strength
    )
    rationale = (
        f"Visible 20-session volatility={volatility_pct:.4f}, band release="
        f"{band_release:.4f}, recent/prior volatility={recent_std / (prior_std + EPS):.4f}, "
        f"volume ratio={expansion_ratio:.4f}; score={score:.4f}."
    )
    return ExpertDecision(STRATEGY_ID, card.sample_id, int(score >= THRESHOLD), score, THRESHOLD, components, rationale)

