"""Fixed roster and validated public interface for expert strategies."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import importlib
import math
from typing import Any

from .contracts import ExpertCard, ExpertDecision


STRATEGY_IDS = (
    "leader_momentum",
    "first_board_breakout",
    "reversal_engulf",
    "washout_complete",
    "accumulation_base",
    "platform_breakout",
    "main_wave_acceleration",
    "oversold_rebound",
    "turnover_weak_to_strong",
    "high_level_consensus",
    "donchian_turtle",
    "bollinger_squeeze",
    "rsi_mean_reversion",
    "gap_follow_through",
    "pullback_retest",
    "obv_volume_price",
    "turnover_regime_switch",
    "relative_strength_rank",
    "atr_trend_follow",
    "limit_up_retest",
    "strict_washout_complete",
    "strict_gap_follow_through",
    "strict_platform_breakout",
    "strict_relative_strength",
    "strict_obv_volume_price",
    "strict_gap_follow_through_v2",
    "strict_turnover_weak_to_strong_v2",
    "strict_washout_complete_v2",
    "strict_oversold_rebound_v2",
    "strict_accumulation_base_v2",
    "strict_relative_strength_v2",
    "strict_leader_momentum_v2",
    "strict_platform_breakout_v2",
    "strict_obv_volume_price_v2",
    "strict_first_board_breakout_v2",
    "strict_bollinger_release_v2",
)


def _text(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class StrategyDefinition:
    """Immutable metadata and checked prediction entry point for one strategy."""

    strategy_id: str
    display_name: str
    thesis: str
    threshold: float
    formula: str
    factor_definitions: Mapping[str, str]
    _predictor: Callable[[ExpertCard], ExpertDecision]
    source: str = "Initial internal rule"
    source_reference: str = "Project initial strategy"
    batch_tag: str = "initial-10"
    selection_metric: str = "accuracy"

    def predict(self, card: ExpertCard) -> ExpertDecision:
        if not isinstance(card, ExpertCard):
            raise TypeError("strategy.predict requires an ExpertCard")
        decision = self._predictor(card)
        if not isinstance(decision, ExpertDecision):
            raise TypeError(f"{self.strategy_id} returned a non-ExpertDecision")
        if decision.strategy_id != self.strategy_id:
            raise ValueError(f"{self.strategy_id} returned the wrong strategy_id")
        if decision.sample_id != card.sample_id:
            raise ValueError(f"{self.strategy_id} returned the wrong sample_id")
        return decision


def _load(module_name: str, expected_id: str) -> StrategyDefinition:
    module = importlib.import_module(f"experts.strategies.{module_name}")
    values = {
        "strategy_id": getattr(module, "STRATEGY_ID", None),
        "display_name": getattr(module, "DISPLAY_NAME", None),
        "thesis": getattr(module, "THESIS", None),
        "threshold": getattr(module, "THRESHOLD", None),
        "formula": getattr(module, "FORMULA", None),
        "factor_definitions": getattr(module, "FACTOR_DEFINITIONS", None),
        "predict": getattr(module, "predict", None),
        "source": getattr(module, "SOURCE", "Initial internal rule"),
        "source_reference": getattr(module, "SOURCE_REFERENCE", "Project initial strategy"),
        "batch_tag": getattr(module, "BATCH_TAG", "initial-10"),
        "selection_metric": getattr(module, "SELECTION_METRIC", "accuracy"),
    }
    if values["strategy_id"] != expected_id:
        raise ValueError(f"strategy module {module_name} has an unexpected strategy_id")
    for field in (
        "strategy_id",
        "display_name",
        "thesis",
        "formula",
        "source",
        "source_reference",
        "batch_tag",
        "selection_metric",
    ):
        _text(values[field], name=field)
    try:
        threshold = float(values["threshold"])
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{expected_id} threshold must be finite") from exc
    if not math.isfinite(threshold):
        raise ValueError(f"{expected_id} threshold must be finite")
    factors = values["factor_definitions"]
    if not isinstance(factors, Mapping) or not factors:
        raise ValueError(f"{expected_id} factor_definitions must be non-empty")
    factor_copy = {
        _text(key, name="factor name"): _text(value, name="factor definition")
        for key, value in factors.items()
    }
    if not callable(values["predict"]):
        raise ValueError(f"{expected_id} must expose predict(card)")
    return StrategyDefinition(
        strategy_id=expected_id,
        display_name=str(values["display_name"]).strip(),
        thesis=str(values["thesis"]).strip(),
        threshold=threshold,
        formula=str(values["formula"]).strip(),
        factor_definitions=factor_copy,
        _predictor=values["predict"],
        source=str(values["source"]).strip(),
        source_reference=str(values["source_reference"]).strip(),
        batch_tag=str(values["batch_tag"]).strip(),
        selection_metric=str(values["selection_metric"]).strip(),
    )


def all_strategies() -> tuple[StrategyDefinition, ...]:
    return tuple(_load(strategy_id, strategy_id) for strategy_id in STRATEGY_IDS)


def list_strategy_ids() -> list[str]:
    return list(STRATEGY_IDS)


def get_strategy(strategy_id: str) -> StrategyDefinition:
    if strategy_id not in STRATEGY_IDS:
        raise KeyError(f"unknown strategy: {strategy_id}")
    return _load(strategy_id, strategy_id)


__all__ = ["STRATEGY_IDS", "StrategyDefinition", "all_strategies", "get_strategy", "list_strategy_ids"]
