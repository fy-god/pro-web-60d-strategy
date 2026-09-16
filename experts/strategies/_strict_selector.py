"""Shared outcome-free wrapper for strict positive-selection variants."""

from __future__ import annotations

from collections.abc import Callable

from experts.contracts import ExpertCard, ExpertDecision


def thresholded_decision(
    card: ExpertCard,
    *,
    strategy_id: str,
    threshold: float,
    base_predict: Callable[[ExpertCard], ExpertDecision],
) -> ExpertDecision:
    """Reuse a causal base score while applying a stricter binary cutoff."""

    base = base_predict(card)
    if base.sample_id != card.sample_id:
        raise ValueError("base strategy returned a mismatched sample_id")
    rationale = (
        f"Strict selector reuses {base.strategy_id} score={base.score:.4f}; "
        f"strict threshold={threshold:.4f}. {base.rationale}"
    )
    return ExpertDecision(
        strategy_id,
        card.sample_id,
        int(base.score >= threshold),
        base.score,
        threshold,
        dict(base.components),
        rationale,
    )


__all__ = ["thresholded_decision"]
