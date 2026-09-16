"""Small causal feature primitives shared by the ten strategy modules."""

from __future__ import annotations

from collections.abc import Sequence
import math

from .contracts import ExpertCard, VisibleBar

EPS = 1e-12


def _window(values: Sequence[float], window: int, *, name: str) -> tuple[float, ...]:
    if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
        raise ValueError(f"{name} window must be positive")
    if len(values) < window:
        raise ValueError(f"{name} window requires {window} values")
    result = tuple(float(value) for value in values[-window:])
    if not all(math.isfinite(value) for value in result):
        raise ValueError(f"{name} values must be finite")
    return result


def _closes(bars: Sequence[VisibleBar]) -> tuple[float, ...]:
    if not bars:
        raise ValueError("bars must not be empty")
    return tuple(float(bar.close) for bar in bars)


def returns(bars: Sequence[VisibleBar], periods: int) -> float:
    if isinstance(periods, bool) or not isinstance(periods, int) or periods <= 0:
        raise ValueError("periods must be positive")
    closes = _closes(bars)
    if len(closes) <= periods:
        raise ValueError("periods exceeds visible bars")
    return closes[-1] / (closes[-1 - periods] + EPS) - 1.0


def rolling_mean(values: Sequence[float], window: int) -> float:
    tail = _window(values, window, name="rolling mean")
    return sum(tail) / len(tail)


def rolling_std(values: Sequence[float], window: int) -> float:
    tail = _window(values, window, name="rolling std")
    mean = sum(tail) / len(tail)
    return math.sqrt(sum((value - mean) ** 2 for value in tail) / len(tail))


def slope(values: Sequence[float], window: int) -> float:
    tail = _window(values, window, name="slope")
    return (tail[-1] - tail[0]) / (abs(tail[0]) + EPS)


def close_location(bar: VisibleBar) -> float:
    span = bar.high - bar.low
    if span <= EPS:
        return 0.5
    return min(1.0, max(0.0, (bar.close - bar.low) / span))


def upper_wick_ratio(bar: VisibleBar) -> float:
    body_top = max(bar.open, bar.close)
    return max(0.0, bar.high - body_top) / (abs(bar.open) + EPS)


def lower_wick_ratio(bar: VisibleBar) -> float:
    body_bottom = min(bar.open, bar.close)
    return max(0.0, body_bottom - bar.low) / (abs(bar.open) + EPS)


def volume_ratio(bars: Sequence[VisibleBar], short: int = 5, long: int = 20) -> float:
    if short <= 0 or long <= short:
        raise ValueError("volume ratio requires 0 < short < long")
    if len(bars) < long + 1:
        raise ValueError("volume ratio requires a prior long window")
    current = sum(bar.volume for bar in bars[-short:]) / short
    baseline = sum(bar.volume for bar in bars[-long - 1 : -short]) / (long + 1 - short)
    return current / (baseline + EPS)


def average_true_range(bars: Sequence[VisibleBar], window: int = 14) -> float:
    if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
        raise ValueError("average true range window must be positive")
    if len(bars) <= window:
        raise ValueError("average true range requires a prior bar")
    tail = bars[-window - 1 :]
    ranges = []
    for previous, bar in zip(tail[:-1], tail[1:], strict=True):
        ranges.append(
            max(
                bar.high - bar.low,
                abs(bar.high - previous.close),
                abs(bar.low - previous.close),
            )
        )
    return sum(ranges) / len(ranges)


def relative_strength_index(bars: Sequence[VisibleBar], window: int = 14) -> float:
    if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
        raise ValueError("relative strength index window must be positive")
    if len(bars) <= window:
        raise ValueError("relative strength index requires a prior bar")
    closes = tuple(bar.close for bar in bars[-window - 1 :])
    gains = []
    losses = []
    for previous, current in zip(closes[:-1], closes[1:], strict=True):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    average_gain = sum(gains) / window
    average_loss = sum(losses) / window
    if average_loss <= EPS:
        return 100.0 if average_gain > EPS else 50.0
    relative = average_gain / average_loss
    return 100.0 - 100.0 / (1.0 + relative)


def obv_slope(bars: Sequence[VisibleBar], window: int = 20) -> float:
    if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
        raise ValueError("obv slope window must be positive")
    if len(bars) <= window:
        raise ValueError("obv slope requires a prior bar")
    obv = [0.0]
    for previous, bar in zip(bars[:-1], bars[1:], strict=True):
        if bar.close > previous.close:
            obv.append(obv[-1] + bar.volume)
        elif bar.close < previous.close:
            obv.append(obv[-1] - bar.volume)
        else:
            obv.append(obv[-1])
    tail = tuple(obv[-window:])
    scale = sum(bar.volume for bar in bars[-window:]) / window + EPS
    return (tail[-1] - tail[0]) / scale


def turnover_mean(bars: Sequence[VisibleBar], window: int = 5) -> float:
    return rolling_mean(tuple(bar.turnover for bar in bars), window)


def kdj_turn(card: ExpertCard) -> float:
    return card.indicator("kdj_k") - card.indicator("kdj_d")


def kdj_cross_change(card: ExpertCard, window: int = 3) -> float:
    differences = tuple(
        k - d
        for k, d in zip(
            card.indicator_series("kdj_k"), card.indicator_series("kdj_d"), strict=True
        )
    )
    tail = _window(differences, window, name="kdj cross")
    return tail[-1] - tail[0]


def range_pct(bars: Sequence[VisibleBar], window: int = 20) -> float:
    tail = _window(tuple(bar.close for bar in bars), window, name="range")
    return (max(tail) - min(tail)) / (abs(min(tail)) + EPS)


def position_in_window(bars: Sequence[VisibleBar], window: int = 20) -> float:
    tail = _window(tuple(bar.close for bar in bars), window, name="position")
    low, high = min(tail), max(tail)
    return (tail[-1] - low) / (high - low + EPS)


def drawdown_from_high(bars: Sequence[VisibleBar], window: int = 20) -> float:
    tail = _window(tuple(bar.close for bar in bars), window, name="drawdown")
    return tail[-1] / (max(tail) + EPS) - 1.0


def distance_from_prior_high(bars: Sequence[VisibleBar], window: int = 20) -> float:
    if len(bars) <= window:
        raise ValueError("prior high requires one bar before the window")
    prior = tuple(bar.close for bar in bars[-window - 1 : -1])
    return bars[-1].close / (max(prior) + EPS) - 1.0


def recent_return_series(bars: Sequence[VisibleBar], window: int = 5) -> tuple[float, ...]:
    closes = _window(tuple(bar.close for bar in bars), window + 1, name="return series")
    return tuple(closes[index] / (closes[index - 1] + EPS) - 1.0 for index in range(1, len(closes)))


def positive_volume_share(bars: Sequence[VisibleBar], window: int = 10) -> float:
    if len(bars) <= window:
        raise ValueError("positive volume share requires a prior bar")
    tail = bars[-window:]
    positive = sum(
        bar.volume
        for previous, bar in zip(bars[-window - 1 : -1], tail, strict=True)
        if bar.close > previous.close
    )
    total = sum(bar.volume for bar in tail)
    return positive / (total + EPS)


def high_low_span(bar: VisibleBar) -> float:
    return (bar.high - bar.low) / (abs(bar.open) + EPS)


__all__ = [
    "EPS",
    "average_true_range",
    "close_location",
    "distance_from_prior_high",
    "drawdown_from_high",
    "high_low_span",
    "kdj_cross_change",
    "kdj_turn",
    "lower_wick_ratio",
    "position_in_window",
    "obv_slope",
    "positive_volume_share",
    "range_pct",
    "recent_return_series",
    "returns",
    "rolling_mean",
    "rolling_std",
    "relative_strength_index",
    "slope",
    "turnover_mean",
    "upper_wick_ratio",
    "volume_ratio",
]
