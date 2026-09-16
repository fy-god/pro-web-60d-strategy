"""Does a high hit rate actually mean a profitable strategy?

The rest of this repository reports **hit rate**: the share of signals whose
forward *maximum high* reaches +30% within 10 sessions. That number says nothing
about what happens on the other ~81% of signals, and nothing about the path taken
to get there. A strategy can reach a 19% hit rate while losing money, if its
misses fall harder than its hits rise, or if the entry is systematically poor.

This module tests that directly. For every strategy it computes:

* **hit rate** — the reported headline (forward max high > +30%),
* **expectancy** — the mean realised close-to-close return over the same
  horizon, the thing a holder actually earns,
* **conditional returns** — mean return *given* the label was a hit vs given it
  was a miss, which exposes lottery-like strategies,
* **the rank relationship** between the two, so the inversion is measured rather
  than asserted.

A "hit" is also an idealised exit: it assumes the holder sells exactly at the
+30% touch. `realised_at_target` below additionally reports the best case where
every hit is sold at target and every miss is held to the horizon close, which is
still an upper bound but a much tighter one than the hit rate implies.

Usage
-----
    python -m src.hitrate_vs_expectancy
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src import data_pipeline

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports"
OUT_DIR = REPO_ROOT / "outputs"

HORIZON = 10
TARGET = 0.30
COST_BPS_ROUND_TRIP = 10.2  # commission 2x2.5bp + stamp 5bp + transfer 0.2bp


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman rank correlation, computed directly to avoid a scipy dependency."""
    a_rank = pd.Series(a).rank().to_numpy("float64").copy()
    b_rank = pd.Series(b).rank().to_numpy("float64").copy()
    a_rank -= a_rank.mean()
    b_rank -= b_rank.mean()
    denom = np.sqrt((a_rank**2).sum() * (b_rank**2).sum())
    return float((a_rank * b_rank).sum() / denom) if denom else float("nan")


def main() -> None:
    panel = data_pipeline.load_panel()[
        ["code", "date", "open", "high", "low", "close"]
    ].sort_values(["code", "date"])
    grouped = panel.groupby("code", sort=False)
    panel["entry_open"] = grouped["open"].shift(-1)
    panel["exit_close"] = grouped["close"].shift(-HORIZON)
    # Realised close-to-close return over the same window the label uses.
    panel["realised"] = panel["exit_close"] / panel["entry_open"] - 1.0

    signals = pd.read_csv(
        OUT_DIR / "webpro_signals.csv",
        dtype={"code": "string"},
        usecols=["code", "date", "strategy_id", "label_bull__webpro"],
        parse_dates=["date"],
    )
    signals["code"] = signals["code"].str.zfill(6)
    merged = signals.merge(
        panel[["code", "date", "realised", "entry_open"]], on=["code", "date"], how="left"
    )
    merged = merged[merged["realised"].notna()]

    cost = COST_BPS_ROUND_TRIP / 10_000.0
    rows = []
    for sid, group in merged.groupby("strategy_id", sort=False):
        realised = group["realised"].to_numpy("float64")
        hit = group["label_bull__webpro"].to_numpy("float64") == 1.0
        n = len(realised)
        if n == 0:
            continue
        net = realised - cost
        # Idealised: sell every hit exactly at target, hold misses to the close.
        at_target = np.where(hit, TARGET - cost, realised - cost)
        rows.append({
            "strategy_id": sid,
            "signals": n,
            "hit_rate": float(hit.mean()),
            "net_expectancy": float(net.mean()),
            "net_median": float(np.median(net)),
            "net_win_rate": float((net > 0).mean()),
            "net_expectancy_at_target": float(at_target.mean()),
            "mean_return_if_hit": float(realised[hit].mean()) if hit.any() else np.nan,
            "mean_return_if_miss": float(realised[~hit].mean()) if (~hit).any() else np.nan,
            "pct_hits_that_did_not_beat_cost": float(
                (realised[hit] <= cost).mean()
            ) if hit.any() else np.nan,
        })

    frame = pd.DataFrame(rows).sort_values("hit_rate", ascending=False)
    frame.to_csv(REPORT_DIR / "hitrate_vs_expectancy.csv", index=False)

    rho = spearman(frame["hit_rate"].to_numpy(), frame["net_expectancy"].to_numpy())
    rho_at = spearman(
        frame["hit_rate"].to_numpy(), frame["net_expectancy_at_target"].to_numpy()
    )

    print("=== strategies ranked by reported HIT RATE ===")
    show = frame.copy()
    for c in ("hit_rate", "net_expectancy", "net_median", "net_win_rate",
              "net_expectancy_at_target", "mean_return_if_hit", "mean_return_if_miss"):
        show[c] = (show[c].astype(float) * 100).round(2)
    print(show[["strategy_id", "signals", "hit_rate", "net_expectancy",
                "net_expectancy_at_target", "mean_return_if_hit",
                "mean_return_if_miss", "net_win_rate"]].to_string(index=False))

    print(f"\nSpearman rank correlation, hit rate vs net expectancy: {rho:+.3f}")
    print(f"Spearman rank correlation, hit rate vs AT-TARGET expectancy: {rho_at:+.3f}")
    print(f"strategies with positive net expectancy: "
          f"{int((frame['net_expectancy'] > 0).sum())} / {len(frame)}")
    print(f"strategies with positive AT-TARGET expectancy: "
          f"{int((frame['net_expectancy_at_target'] > 0).sum())} / {len(frame)}")

    top = frame.nlargest(5, "hit_rate")
    print("\n--- the five highest hit rates, and what they actually earn ---")
    for r in top.itertuples():
        print(f"  {r.strategy_id:32s} hit {r.hit_rate*100:5.2f}%  "
              f"net {r.net_expectancy*100:+6.2f}%  "
              f"at-target {r.net_expectancy_at_target*100:+6.2f}%  "
              f"if-hit {r.mean_return_if_hit*100:+6.2f}%  "
              f"if-miss {r.mean_return_if_miss*100:+6.2f}%")

    (REPORT_DIR / "hitrate_vs_expectancy.json").write_text(
        json.dumps({
            "spearman_hit_rate_vs_net_expectancy": rho,
            "spearman_hit_rate_vs_at_target_expectancy": rho_at,
            "positive_expectancy_count": int((frame["net_expectancy"] > 0).sum()),
            "positive_at_target_count": int((frame["net_expectancy_at_target"] > 0).sum()),
            "strategies": len(frame),
            "note": (
                "Hit rate is the share of signals whose forward MAXIMUM HIGH reaches "
                "+30% within 10 sessions. Net expectancy is the mean realised "
                "next-open-to-horizon-close return less 10.2bp round-trip cost. "
                "A negative rank correlation means the reported hit-rate ranking "
                "orders strategies in the opposite order to what they earn."
            ),
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nwrote {REPORT_DIR / 'hitrate_vs_expectancy.csv'}")


if __name__ == "__main__":
    main()
