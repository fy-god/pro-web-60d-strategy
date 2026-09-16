"""Strict, outcome-free input and output contracts for expert strategies."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
import math
from numbers import Integral
from typing import Any


_SAFE_FIELDS = frozenset(
    {
        "index",
        "sample_id",
        "code",
        "name",
        "observation_date",
        "horizon_sessions",
        "target_gain",
        "bars",
        "indicators",
    }
)
_UNSAFE_FIELDS = frozenset(
    {
        "outcome",
        "label",
        "answers",
        "future",
        "future_bars",
        "actual",
        "future_max_return",
        "future_min_return",
        "target",
    }
)
_BAR_FIELDS = frozenset(
    {"date", "open", "high", "low", "close", "volume", "amount", "turnover"}
)
_INDICATOR_FIELDS = frozenset(
    {"kdj_k", "kdj_d", "kdj_j", "turnover", "volume_ratio"}
)


def _text(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _finite(value: Any, *, name: str, nonnegative: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be finite")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(number) or (nonnegative and number < 0.0):
        raise ValueError(f"{name} must be finite")
    return number


def _strict_binary(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) not in (0, 1):
        raise ValueError(f"{name} must be 0 or 1")
    return int(value)


@dataclass(frozen=True, slots=True)
class VisibleBar:
    """One visible active-session OHLCV row."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    turnover: float

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any], *, index: int) -> "VisibleBar":
        if not isinstance(raw, Mapping):
            raise ValueError(f"bar {index} must be an object")
        unknown = set(raw) - _BAR_FIELDS
        missing = _BAR_FIELDS - set(raw)
        if unknown:
            raise ValueError(f"bar {index} has unknown field(s): {sorted(unknown)}")
        if missing:
            raise ValueError(f"bar {index} is missing field(s): {sorted(missing)}")
        raw_date = _text(raw["date"], name=f"bar {index} date")
        try:
            parsed_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise ValueError(f"bar {index} date must be ISO date") from exc
        if parsed_date.isoformat() != raw_date:
            raise ValueError(f"bar {index} date must be ISO date")
        values = {
            field: _finite(raw[field], name=f"bar {index} {field}", nonnegative=field in {"volume", "amount", "turnover"})
            for field in ("open", "high", "low", "close")
        }
        if min(values["open"], values["close"]) < values["low"]:
            raise ValueError(f"bar {index} low is above open or close")
        if max(values["open"], values["close"]) > values["high"]:
            raise ValueError(f"bar {index} high is below open or close")
        return cls(
            date=raw_date,
            open=values["open"],
            high=values["high"],
            low=values["low"],
            close=values["close"],
            volume=_finite(raw["volume"], name=f"bar {index} volume", nonnegative=True),
            amount=_finite(raw["amount"], name=f"bar {index} amount", nonnegative=True),
            turnover=_finite(raw["turnover"], name=f"bar {index} turnover", nonnegative=True),
        )


@dataclass(frozen=True, slots=True)
class ExpertCard:
    """A validated 60-session card with no outcome-derived values."""

    sample_id: str
    code: str
    name: str
    observation_date: str
    bars: tuple[VisibleBar, ...]
    indicators: Mapping[str, tuple[float, ...]]
    horizon_sessions: int = 10
    target_gain: float = 0.30
    index: int | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ExpertCard":
        if not isinstance(raw, Mapping):
            raise ValueError("card must be an object")
        unsafe = set(raw) & _UNSAFE_FIELDS
        if unsafe:
            raise ValueError(f"unsafe field(s): {sorted(unsafe)}")
        unknown = set(raw) - _SAFE_FIELDS
        if unknown:
            raise ValueError(f"unknown field(s): {sorted(unknown)}")
        required = {"sample_id", "code", "name", "observation_date", "bars", "indicators"}
        missing = required - set(raw)
        if missing:
            raise ValueError(f"card is missing field(s): {sorted(missing)}")

        sample_id = _text(raw["sample_id"], name="sample_id")
        code = _text(raw["code"], name="code")
        if len(code) != 6 or not code.isdigit():
            raise ValueError("code must be a six-digit stock code")
        name = _text(raw["name"], name="name")
        observation_date = _text(raw["observation_date"], name="observation_date")
        try:
            observation = date.fromisoformat(observation_date)
        except ValueError as exc:
            raise ValueError("observation_date must be ISO date") from exc
        if observation.isoformat() != observation_date:
            raise ValueError("observation_date must be ISO date")

        raw_bars = raw["bars"]
        if not isinstance(raw_bars, Sequence) or isinstance(raw_bars, (str, bytes)):
            raise ValueError("bars must be a sequence")
        if len(raw_bars) != 60:
            raise ValueError("bars must contain exactly 60 visible sessions")
        bars = tuple(VisibleBar.from_mapping(item, index=index) for index, item in enumerate(raw_bars))
        parsed_dates = tuple(date.fromisoformat(item.date) for item in bars)
        if any(left >= right for left, right in zip(parsed_dates, parsed_dates[1:])):
            raise ValueError("bar dates must be strictly increasing")
        if bars[-1].date != observation_date:
            raise ValueError("last visible bar must match observation_date")

        raw_indicators = raw["indicators"]
        if not isinstance(raw_indicators, Mapping):
            raise ValueError("indicators must be an object")
        unknown_indicators = set(raw_indicators) - _INDICATOR_FIELDS
        missing_indicators = _INDICATOR_FIELDS - set(raw_indicators)
        if unknown_indicators:
            raise ValueError(f"indicators have unknown field(s): {sorted(unknown_indicators)}")
        if missing_indicators:
            raise ValueError(f"indicators are missing field(s): {sorted(missing_indicators)}")
        indicators: dict[str, tuple[float, ...]] = {}
        for field in sorted(_INDICATOR_FIELDS):
            values = raw_indicators[field]
            if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or len(values) != 60:
                raise ValueError(f"indicator {field} must contain exactly 60 values")
            indicators[field] = tuple(
                _finite(value, name=f"indicator {field}") for value in values
            )

        horizon = raw.get("horizon_sessions", 10)
        if isinstance(horizon, bool) or not isinstance(horizon, Integral) or int(horizon) <= 0:
            raise ValueError("horizon_sessions must be a positive integer")
        target_gain = _finite(raw.get("target_gain", 0.30), name="target_gain", nonnegative=True)
        index = raw.get("index")
        if index is not None and (isinstance(index, bool) or not isinstance(index, Integral) or int(index) < 0):
            raise ValueError("index must be a non-negative integer")
        return cls(
            sample_id=sample_id,
            code=code,
            name=name,
            observation_date=observation_date,
            bars=bars,
            indicators=indicators,
            horizon_sessions=int(horizon),
            target_gain=target_gain,
            index=None if index is None else int(index),
        )

    def indicator(self, name: str, offset: int = -1) -> float:
        values = self.indicator_series(name)
        try:
            return values[offset]
        except IndexError as exc:
            raise ValueError(f"indicator offset is outside {name!r}") from exc

    def indicator_series(self, name: str) -> tuple[float, ...]:
        try:
            return self.indicators[name]
        except KeyError as exc:
            raise ValueError(f"unknown indicator: {name}") from exc


@dataclass(frozen=True, slots=True)
class ExpertDecision:
    """One deterministic binary decision and its explainable factors."""

    strategy_id: str
    sample_id: str
    prediction: int
    score: float
    threshold: float
    components: Mapping[str, float]
    rationale: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy_id", _text(self.strategy_id, name="strategy_id"))
        object.__setattr__(self, "sample_id", _text(self.sample_id, name="sample_id"))
        object.__setattr__(self, "prediction", _strict_binary(self.prediction, name="prediction"))
        object.__setattr__(self, "score", _finite(self.score, name="score"))
        object.__setattr__(self, "threshold", _finite(self.threshold, name="threshold"))
        if not isinstance(self.components, Mapping) or not self.components:
            raise ValueError("components must be a non-empty mapping")
        components = {
            _text(key, name="component name"): _finite(value, name=f"component {key}")
            for key, value in self.components.items()
        }
        object.__setattr__(self, "components", components)
        object.__setattr__(self, "rationale", _text(self.rationale, name="rationale"))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "sample_id": self.sample_id,
            "prediction": self.prediction,
            "score": self.score,
            "threshold": self.threshold,
            "components": dict(self.components),
            "rationale": self.rationale,
        }


__all__ = ["ExpertCard", "ExpertDecision", "VisibleBar"]
