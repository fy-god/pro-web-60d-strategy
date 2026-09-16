"""Blind prediction sealing, central scoring, and immutable bundle loading."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import hashlib
import json
import math
from pathlib import Path
import tempfile
from typing import Any

from .contracts import ExpertCard, ExpertDecision
from .registry import StrategyDefinition, all_strategies


EVALUATION_SCHEMA = "ly.kline_expert_evaluation.v2"
EXPECTED_CARD_COUNT = 100
EXPECTED_POSITIVE_COUNT = 50


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(_canonical_bytes(value))
            handle.write(b"\n")
            handle.flush()
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _binary(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or value not in (0, 1):
        raise ValueError(f"{name} must be binary 0 or 1")
    return int(value)


def _load_cards(session_dir: Path) -> tuple[str, tuple[ExpertCard, ...], str]:
    path = session_dir / "cards.json"
    document = _read_json(path, "cards.json")
    session_id = document.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise ValueError("cards.json session_id is missing")
    raw_cards = document.get("cards")
    if not isinstance(raw_cards, list) or len(raw_cards) != EXPECTED_CARD_COUNT:
        raise ValueError("cards.json must contain exactly 100 cards")
    cards = tuple(ExpertCard.from_mapping(item) for item in raw_cards)
    sample_ids = [card.sample_id for card in cards]
    if len(set(sample_ids)) != len(sample_ids):
        raise ValueError("cards.json contains duplicate sample IDs")
    if any(card.index is not None and card.index != index for index, card in enumerate(cards)):
        raise ValueError("cards.json card indexes are not in order")
    return session_id, cards, _sha256_file(path)


def _load_outcomes(path: Path) -> dict[str, Any]:
    return _read_json(path, "outcomes.json")


def _validate_outcomes(
    document: Mapping[str, Any], *, session_id: str, sample_ids: Sequence[str]
) -> list[dict[str, Any]]:
    if document.get("session_id") != session_id:
        raise ValueError("outcomes.json session_id does not match cards.json")
    raw_outcomes = document.get("outcomes")
    if not isinstance(raw_outcomes, list) or len(raw_outcomes) != len(sample_ids):
        raise ValueError("outcomes.json does not cover every card")
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_outcomes):
        if not isinstance(raw, Mapping):
            raise ValueError("outcome must be an object")
        if "sample_id" in raw and raw.get("sample_id") != sample_ids[index]:
            raise ValueError("outcomes.json sample IDs are missing, reordered, or unknown")
        result.append({"sample_id": sample_ids[index], "label": _binary(raw.get("label"), name="label")})
    if sum(item["label"] for item in result) != EXPECTED_POSITIVE_COUNT:
        raise ValueError("evaluation session must contain exactly 50 positive outcomes")
    return result


def score_predictions(predicted: Sequence[Any], actual: Sequence[Any]) -> dict[str, int | float]:
    if len(predicted) != len(actual):
        raise ValueError("predicted and actual must have equal lengths")
    predictions = [_binary(value, name="prediction") for value in predicted]
    labels = [_binary(value, name="label") for value in actual]
    total = len(labels)
    tp = sum(prediction == label == 1 for prediction, label in zip(predictions, labels, strict=True))
    tn = sum(prediction == label == 0 for prediction, label in zip(predictions, labels, strict=True))
    fp = sum(prediction == 1 and label == 0 for prediction, label in zip(predictions, labels, strict=True))
    fn = sum(prediction == 0 and label == 1 for prediction, label in zip(predictions, labels, strict=True))
    correct = tp + tn
    predicted_yes = tp + fp
    positives = tp + fn
    accuracy = correct / total if total else 0.0
    if total:
        z = 1.959963984540054
        denominator = 1.0 + z * z / total
        centre = (accuracy + z * z / (2.0 * total)) / denominator
        margin = z * math.sqrt(
            accuracy * (1.0 - accuracy) / total + z * z / (4.0 * total * total)
        ) / denominator
        wilson_low = max(0.0, centre - margin)
        wilson_high = min(1.0, centre + margin)
    else:
        wilson_low = wilson_high = 0.0
    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "positive_recall": tp / positives if positives else 0.0,
        "yes_precision": tp / predicted_yes if predicted_yes else 0.0,
        "predicted_yes_count": predicted_yes,
        "predicted_yes_rate": predicted_yes / total if total else 0.0,
        "accuracy_wilson_low": wilson_low,
        "accuracy_wilson_high": wilson_high,
    }


def _validate_prediction_rows(
    rows: Sequence[Any], *, strategy_id: str, sample_ids: Sequence[str]
) -> list[dict[str, Any]]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ValueError(f"{strategy_id} predictions must be a sequence")
    if len(rows) != len(sample_ids):
        raise ValueError(f"{strategy_id} predictions do not cover every card")
    validated: list[dict[str, Any]] = []
    for index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise ValueError(f"{strategy_id} prediction must be an object")
        if raw.get("strategy_id") != strategy_id:
            raise ValueError(f"{strategy_id} prediction has the wrong strategy ID")
        if raw.get("sample_id") != sample_ids[index]:
            raise ValueError(f"{strategy_id} predictions are missing, reordered, or duplicated")
        decision = ExpertDecision(
            strategy_id,
            sample_ids[index],
            raw.get("prediction"),
            raw.get("score"),
            raw.get("threshold"),
            raw.get("components"),
            raw.get("rationale"),
        )
        validated.append(decision.to_mapping())
    return validated


def score_sealed_predictions(
    predictions: Mapping[str, Sequence[Any]], outcomes: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if not isinstance(predictions, Mapping) or not predictions:
        raise ValueError("sealed predictions must be a non-empty mapping")
    if not isinstance(outcomes, Sequence) or not outcomes:
        raise ValueError("outcomes must be a non-empty sequence")
    sample_ids = []
    labels = []
    for outcome in outcomes:
        if not isinstance(outcome, Mapping):
            raise ValueError("outcome must be an object")
        sample_id = outcome.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id or sample_id in sample_ids:
            raise ValueError("outcomes contain invalid or duplicate sample IDs")
        sample_ids.append(sample_id)
        labels.append(_binary(outcome.get("label"), name="label"))

    validated_by_strategy: dict[str, list[dict[str, Any]]] = {}
    scores: dict[str, dict[str, int | float]] = {}
    for strategy_id, rows in predictions.items():
        if not isinstance(strategy_id, str) or not strategy_id:
            raise ValueError("strategy ID must be a non-empty string")
        validated = _validate_prediction_rows(rows, strategy_id=strategy_id, sample_ids=sample_ids)
        validated_by_strategy[strategy_id] = validated
        scores[strategy_id] = score_predictions(
            [row["prediction"] for row in validated], labels
        )

    pairwise: dict[str, float] = {}
    strategy_ids = list(validated_by_strategy)
    for left_index, left in enumerate(strategy_ids):
        left_predictions = [row["prediction"] for row in validated_by_strategy[left]]
        for right in strategy_ids[left_index + 1 :]:
            right_predictions = [row["prediction"] for row in validated_by_strategy[right]]
            key = f"{left}__{right}"
            pairwise[key] = sum(
                left_value != right_value
                for left_value, right_value in zip(left_predictions, right_predictions, strict=True)
            ) / len(sample_ids)

    card_results = []
    for index, sample_id in enumerate(sample_ids):
        card_results.append(
            {
                "sample_id": sample_id,
                "label": labels[index],
                "experts": {
                    strategy_id: validated_by_strategy[strategy_id][index]
                    for strategy_id in strategy_ids
                },
            }
        )
    return {"scores": scores, "pairwise_disagreement": pairwise, "card_results": card_results}


def _strategy_spec(strategy: StrategyDefinition) -> dict[str, Any]:
    return {
        "strategy_id": strategy.strategy_id,
        "display_name": strategy.display_name,
        "thesis": strategy.thesis,
        "threshold": strategy.threshold,
        "formula": strategy.formula,
        "factor_definitions": dict(strategy.factor_definitions),
        "source": getattr(strategy, "source", "Initial internal rule"),
        "source_reference": getattr(strategy, "source_reference", "Project initial strategy"),
        "batch_tag": getattr(strategy, "batch_tag", "custom"),
        "selection_metric": getattr(strategy, "selection_metric", "accuracy"),
    }


def evaluate_session(
    session_dir: str | Path,
    output_dir: str | Path,
    *,
    strategies: Sequence[StrategyDefinition] | None = None,
    outcomes_reader: Callable[[Path], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate and hash every prediction before opening the outcome file."""

    session_root = Path(session_dir).resolve()
    output_root = Path(output_dir).resolve()
    session_id, cards, cards_sha256 = _load_cards(session_root)
    strategy_list = tuple(strategies) if strategies is not None else all_strategies()
    if not strategy_list:
        raise ValueError("at least one strategy is required")
    strategy_ids = [strategy.strategy_id for strategy in strategy_list]
    if len(set(strategy_ids)) != len(strategy_ids):
        raise ValueError("strategy IDs must be unique")
    output_root.mkdir(parents=True, exist_ok=True)
    sealed_root = output_root / "sealed_predictions"
    predictions: dict[str, list[dict[str, Any]]] = {}
    prediction_hashes: dict[str, str] = {}

    for strategy in strategy_list:
        rows: list[dict[str, Any]] = []
        for card in cards:
            decision = strategy.predict(card)
            if not isinstance(decision, ExpertDecision):
                raise ValueError(f"{strategy.strategy_id} did not return ExpertDecision")
            if decision.strategy_id != strategy.strategy_id or decision.sample_id != card.sample_id:
                raise ValueError(f"{strategy.strategy_id} returned mismatched identity")
            rows.append(decision.to_mapping())
        document = {
            "schema": EVALUATION_SCHEMA,
            "session_id": session_id,
            "card_sha256": cards_sha256,
            "strategy_id": strategy.strategy_id,
            "predictions": rows,
        }
        path = sealed_root / f"{strategy.strategy_id}.json"
        _write_json_atomic(path, document)
        predictions[strategy.strategy_id] = rows
        prediction_hashes[strategy.strategy_id] = _sha256_file(path)

    reader = outcomes_reader or _load_outcomes
    outcomes_path = session_root / "outcomes.json"
    outcomes_document = reader(outcomes_path)
    if not isinstance(outcomes_document, Mapping):
        raise ValueError("outcomes reader must return an object")
    validated_outcomes = _validate_outcomes(
        outcomes_document,
        session_id=session_id,
        sample_ids=[card.sample_id for card in cards],
    )
    scored = score_sealed_predictions(predictions, validated_outcomes)

    specs_document = {
        "schema": EVALUATION_SCHEMA,
        "session_id": session_id,
        "strategies": [_strategy_spec(strategy) for strategy in strategy_list],
    }
    scores_document = {
        "schema": EVALUATION_SCHEMA,
        "session_id": session_id,
        "card_sha256": cards_sha256,
        "sample_count": len(cards),
        "positive_count": sum(item["label"] for item in validated_outcomes),
        "scores": scored["scores"],
        "pairwise_disagreement": scored["pairwise_disagreement"],
    }
    card_results_document = {
        "schema": EVALUATION_SCHEMA,
        "session_id": session_id,
        "card_sha256": cards_sha256,
        "card_results": scored["card_results"],
    }
    _write_json_atomic(output_root / "strategy_specs.json", specs_document)
    _write_json_atomic(output_root / "scores.json", scores_document)
    _write_json_atomic(output_root / "card_results.json", card_results_document)
    artifact_hashes = {
        "strategy_specs.json": _sha256_file(output_root / "strategy_specs.json"),
        "scores.json": _sha256_file(output_root / "scores.json"),
        "card_results.json": _sha256_file(output_root / "card_results.json"),
        **{
            f"sealed_predictions/{strategy_id}.json": hash_value
            for strategy_id, hash_value in prediction_hashes.items()
        },
    }
    manifest = {
        "schema": EVALUATION_SCHEMA,
        "session_id": session_id,
        "cards_sha256": cards_sha256,
        "outcomes_sha256": _sha256_file(outcomes_path),
        "prediction_hashes": prediction_hashes,
        "artifact_sha256": artifact_hashes,
        "strategy_ids": strategy_ids,
        "sample_count": len(cards),
        "positive_count": sum(item["label"] for item in validated_outcomes),
    }
    _write_json_atomic(output_root / "evaluation_manifest.json", manifest)
    return {
        "manifest": manifest,
        "scores": scored["scores"],
        "pairwise_disagreement": scored["pairwise_disagreement"],
        "card_results": scored["card_results"],
    }


def load_evaluation_bundle(
    output_dir: str | Path,
    *,
    expected_session_id: str | None = None,
    expected_cards_sha256: str | None = None,
    expected_outcomes_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate a bundle for server use and return its read-only documents."""

    root = Path(output_dir).resolve()
    manifest = _read_json(root / "evaluation_manifest.json", "evaluation manifest")
    if manifest.get("schema") != EVALUATION_SCHEMA:
        raise ValueError("evaluation schema is unsupported")
    session_id = manifest.get("session_id")
    if expected_session_id is not None and session_id != expected_session_id:
        raise ValueError("evaluation session_id does not match active session")
    if expected_cards_sha256 is not None and manifest.get("cards_sha256") != expected_cards_sha256:
        raise ValueError("evaluation cards hash does not match active session")
    if expected_outcomes_sha256 is not None and manifest.get("outcomes_sha256") != expected_outcomes_sha256:
        raise ValueError("evaluation outcomes hash does not match active session")
    artifact_hashes = manifest.get("artifact_sha256")
    if not isinstance(artifact_hashes, Mapping):
        raise ValueError("evaluation artifact hashes are missing")
    for relative, expected_hash in artifact_hashes.items():
        path = root / str(relative)
        if not path.is_file() or _sha256_file(path) != expected_hash:
            raise ValueError(f"evaluation artifact hash mismatch: {relative}")
    scores = _read_json(root / "scores.json", "scores.json")
    specs = _read_json(root / "strategy_specs.json", "strategy_specs.json")
    card_results = _read_json(root / "card_results.json", "card_results.json")
    if scores.get("session_id") != session_id or specs.get("session_id") != session_id or card_results.get("session_id") != session_id:
        raise ValueError("evaluation artifact session IDs do not agree")
    if not isinstance(scores.get("scores"), Mapping) or not isinstance(specs.get("strategies"), list):
        raise ValueError("evaluation aggregate artifacts are malformed")
    rows = card_results.get("card_results")
    if not isinstance(rows, list) or len(rows) != EXPECTED_CARD_COUNT:
        raise ValueError("evaluation card results must contain exactly 100 rows")
    return {"manifest": manifest, "scores": scores, "strategy_specs": specs, "card_results": card_results}


__all__ = [
    "EVALUATION_SCHEMA",
    "EXPECTED_CARD_COUNT",
    "evaluate_session",
    "load_evaluation_bundle",
    "score_predictions",
    "score_sealed_predictions",
]
