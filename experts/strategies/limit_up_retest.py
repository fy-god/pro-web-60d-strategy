"""A-share limit-like event and continuation/retest strategy from daily bars."""

from __future__ import annotations

from experts.contracts import ExpertCard, ExpertDecision
from experts.features import close_location, recent_return_series, upper_wick_ratio, volume_ratio


STRATEGY_ID = "limit_up_retest"
DISPLAY_NAME = "Limit-Up Retest"
THESIS = (
    "An A-share limit-like move is more useful as a short-term signal when it is "
    "followed by a hold or renewed strength, rather than a failed spike; the "
    "daily-bar proxy requires a near-limit return and controlled rejection."
)
THRESHOLD = 0.70
FORMULA = (
    "score = 0.30*limit_event + 0.25*post_event_hold + 0.20*follow_through "
    "+ 0.15*volume_support + 0.10*close_quality; predict 1 iff score >= 0.70."
)
FACTOR_DEFINITIONS = {
    "limit_event": "Count of visible close-to-close returns at or above 8.5% in the latest 20 sessions, capped at two events.",
    "post_event_hold": "Latest close relative to the close at the latest near-limit event; full credit when it holds 98% or more.",
    "follow_through": "Positive near-limit or positive continuation return in the latest five visible sessions.",
    "volume_support": "Visible five-session volume ratio, scaled from 1.0 to 2.0.",
    "close_quality": "Close location and inverse upper-wick rejection score.",
}
SOURCE = "A-share limit-up continuation/retest"
SOURCE_REFERENCE = "A-share short-line board/reversal pattern family; daily-bar proxy without intraday order data"
BATCH_TAG = "01a00acc-695f-7792-b239-b4a4c09e5d3c"


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def predict(card: ExpertCard) -> ExpertDecision:
    returns = recent_return_series(card.bars, window=20)
    event_indices = [index for index, value in enumerate(returns) if value >= 0.085]
    recent_events = event_indices[-2:]
    limit_event = _clip(len(recent_events) / 2.0)
    if event_indices:
        event_bar_index = len(card.bars) - 20 + event_indices[-1]
        event_close = card.bars[event_bar_index].close
        post_event_hold = _clip((card.bars[-1].close / (event_close + 1e-12) - 0.98) / 0.12)
    else:
        post_event_hold = 0.0
    follow_through = _clip(max(returns[-5:]) / 0.08)
    expansion = volume_ratio(card.bars, short=5, long=20)
    volume_support = _clip((expansion - 1.0) / 1.0)
    latest = card.bars[-1]
    close_quality = 0.65 * close_location(latest) + 0.35 * _clip(1.0 - upper_wick_ratio(latest) / 0.12)
    components = {
        "limit_event": limit_event,
        "post_event_hold": post_event_hold,
        "follow_through": follow_through,
        "volume_support": volume_support,
        "close_quality": close_quality,
    }
    score = 0.30 * limit_event + 0.25 * post_event_hold + 0.20 * follow_through + 0.15 * volume_support + 0.10 * close_quality
    rationale = (
        f"Visible near-limit events in 20 sessions={len(event_indices)}, latest event "
        f"hold={post_event_hold:.4f}, five-session follow-through={follow_through:.4f}, "
        f"volume ratio={expansion:.4f}, close quality={close_quality:.4f}; score={score:.4f}."
    )
    return ExpertDecision(STRATEGY_ID, card.sample_id, int(score >= THRESHOLD), score, THRESHOLD, components, rationale)
