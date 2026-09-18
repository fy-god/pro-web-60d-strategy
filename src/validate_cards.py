"""Reproduce the Web Pro 100-card evaluation from the frozen source bundle.

This is the audit step. The published bundle claims a set of yes-precision
numbers for the 11 development-only ``*_v2`` selectors. We re-run all 36
strategies ourselves against the same 100 real cards and the same sealed
labels, then diff our numbers against the bundle's own ``scores.json``.

A match proves three things at once: the vendored strategy source is
unmodified, our card assembly is correct, and our accounting agrees with the
original. A mismatch is a finding, not something to paper over.

Usage
-----
    python -m src.validate_cards
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

from experts.contracts import ExpertCard, VisibleBar
from experts.registry import STRATEGY_IDS, get_strategy

# The frozen 100-card bundle. `cards.json` and `outcomes.json` are VENDORED under
# data/cards_100/ so this gate runs for anyone who clones the repository; before,
# this was only a hardcoded D:\xm\ path and the project's own correctness gate
# could not be reproduced off this machine. Override with WEBPRO_CARD_BUNDLE if
# you have the full original bundle, which additionally holds expert_evaluation/.
REPO_ROOT_FOR_BUNDLE = Path(__file__).resolve().parents[1]
BUNDLE = Path(
    os.environ.get(
        "WEBPRO_CARD_BUNDLE",
        str(REPO_ROOT_FOR_BUNDLE / "data" / "cards_100"),
    )
)
REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports"

# The published table from the bundle README, used as the diff target.
PUBLISHED = {
    "strict_bollinger_release_v2": (0.8000, 5, 0.53),
    "strict_accumulation_base_v2": (0.7333, 15, 0.57),
    "strict_gap_follow_through_v2": (0.7273, 22, 0.60),
    "strict_leader_momentum_v2": (0.7273, 11, 0.55),
    "strict_platform_breakout_v2": (0.7273, 11, 0.55),
    "strict_relative_strength_v2": (0.7273, 11, 0.55),
    "strict_washout_complete_v2": (0.7222, 18, 0.58),
    "strict_first_board_breakout_v2": (0.7143, 7, 0.53),
    "strict_oversold_rebound_v2": (0.7059, 17, 0.57),
    "strict_obv_volume_price_v2": (0.7000, 10, 0.54),
    "strict_turnover_weak_to_strong_v2": (0.6842, 19, 0.57),
}


def load_cards() -> tuple[list[ExpertCard], list[int]]:
    """Rebuild the 100 ExpertCards and their sealed labels from the bundle."""
    raw = json.loads((BUNDLE / "cards.json").read_text(encoding="utf-8"))
    outcomes = json.loads((BUNDLE / "outcomes.json").read_text(encoding="utf-8"))["outcomes"]

    cards, labels = [], []
    for entry in raw["cards"]:
        bars = tuple(
            VisibleBar(
                date=b["date"], open=float(b["open"]), high=float(b["high"]),
                low=float(b["low"]), close=float(b["close"]), volume=float(b["volume"]),
                amount=float(b["amount"]), turnover=float(b["turnover"]),
            )
            for b in entry["bars"]
        )
        indicators = {
            key: tuple(float(v) for v in series)
            for key, series in entry["indicators"].items()
        }
        cards.append(
            ExpertCard(
                sample_id=entry["sample_id"], code=entry["code"], name=entry["name"],
                observation_date=entry["observation_date"], bars=bars,
                indicators=indicators,
                horizon_sessions=int(entry["horizon_sessions"]),
                target_gain=float(entry["target_gain"]),
            )
        )
        labels.append(int(outcomes[entry["index"]]["label"]))
    return cards, labels


def evaluate(cards: list[ExpertCard], labels: list[int]) -> pd.DataFrame:
    """Run every strategy on every card and score it against the sealed labels."""
    rows = []
    total_positives = sum(labels)
    for sid in STRATEGY_IDS:
        strategy = get_strategy(sid)
        tp = fp = fn = tn = 0
        errors = 0
        for card, label in zip(cards, labels):
            try:
                decision = strategy.predict(card)
                pred = int(decision.prediction)
            except Exception:
                errors += 1
                continue
            if pred == 1 and label == 1:
                tp += 1
            elif pred == 1 and label == 0:
                fp += 1
            elif pred == 0 and label == 1:
                fn += 1
            else:
                tn += 1

        predicted_yes = tp + fp
        rows.append({
            "strategy_id": sid,
            "batch_tag": strategy.batch_tag,
            "threshold": strategy.threshold,
            "yes_predictions": predicted_yes,
            "tp": tp,
            "fp": fp,
            "yes_precision": tp / predicted_yes if predicted_yes else float("nan"),
            "positive_recall": tp / total_positives if total_positives else float("nan"),
            "accuracy": (tp + tn) / len(cards) if cards else float("nan"),
            "errors": errors,
        })
    return pd.DataFrame(rows)


def main() -> None:
    cards, labels = load_cards()
    print(f"cards={len(cards)} positives={sum(labels)} negatives={len(labels)-sum(labels)}")

    frame = evaluate(cards, labels)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(REPORT_DIR / "webpro_cards_100_reproduction.csv", index=False)

    print("\n=== published vs reproduced (the 11 *_v2 selectors) ===")
    print(f"{'strategy':38s} {'pub_prec':>9s} {'our_prec':>9s} {'pub_n':>6s} {'our_n':>6s} {'match':>6s}")
    matches = 0
    for sid, (pub_prec, pub_n, _pub_acc) in PUBLISHED.items():
        row = frame[frame["strategy_id"] == sid].iloc[0]
        prec_match = abs(round(float(row["yes_precision"]), 4) - pub_prec) < 5e-4
        n_match = int(row["yes_predictions"]) == pub_n
        ok = prec_match and n_match
        matches += ok
        print(
            f"{sid:38s} {pub_prec*100:8.2f}% {float(row['yes_precision'])*100:8.2f}% "
            f"{pub_n:6d} {int(row['yes_predictions']):6d} {'OK' if ok else 'DIFF':>6s}"
        )
    print(f"\n{matches}/{len(PUBLISHED)} published selectors reproduced exactly")

    print("\n=== all 36 strategies, ranked by yes-precision ===")
    ranked = frame.sort_values("yes_precision", ascending=False)
    for row in ranked.itertuples():
        prec = f"{row.yes_precision*100:6.2f}%" if pd.notna(row.yes_precision) else "   n/a"
        print(f"{row.strategy_id:38s} n={row.yes_predictions:3d} prec={prec} "
              f"recall={row.positive_recall*100:5.1f}% acc={row.accuracy*100:5.1f}%")


if __name__ == "__main__":
    main()
