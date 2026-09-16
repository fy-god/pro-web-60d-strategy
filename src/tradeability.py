"""Tradeability audit: can these signals actually be bought at the stated entry?

Every hit rate in this repository assumes the entry is the **next session's
open**. That assumption fails in a specific and quantifiable way on A-shares:
a stock that limits up at the open cannot be bought there, because there are no
sellers. The original project's entry test (``next_day_volume > 0 and
next_day_open > 0``) accepts such bars as valid entries, which biases every
reported precision upward.

This module measures the size of that bias on the actual emitted signals:

* how many signals have a next open at or near the 10% mainboard limit,
* how many are "one-word" limit boards (open == high == low == close, limit up),
  which are unfillable in practice,
* and the hit rate before vs. after excluding unfillable entries.

Mainboard limits are 10% (5% for ST names, 20% for STAR/ChiNext 688/300 codes).
The panel's universe is mainboard, so 10% is the reference, with the 20% boards
handled separately since their codes are identifiable.

Usage
-----
    python -m src.tradeability
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

# A-share daily price limits by board.
LIMIT_MAIN = 0.10      # 000/001/002/600/601/603/605
LIMIT_STAR = 0.20      # 300 (ChiNext) and 688 (STAR)
LIMIT_ST = 0.05        # ST/*ST names

# Rounding tolerance: a limit-up open is empirically within a few ticks of the
# exact limit because the exchange rounds to 0.01 CNY.
LIMIT_TOLERANCE = 0.005


def limit_for(code: str) -> float:
    """Price limit for a six-digit code. ST status is unknown, so 10% is used."""
    if code.startswith(("300", "688", "301")):
        return LIMIT_STAR
    return LIMIT_MAIN


def audit(signals: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """Attach next-session tradeability flags to each signal."""
    # Next-session bar per stock.
    nxt = panel.sort_values(["code", "date"]).copy()
    nxt["next_open"] = nxt.groupby("code", sort=False)["open"].shift(-1)
    nxt["next_high"] = nxt.groupby("code", sort=False)["high"].shift(-1)
    nxt["next_low"] = nxt.groupby("code", sort=False)["low"].shift(-1)
    nxt["next_close"] = nxt.groupby("code", sort=False)["close"].shift(-1)
    nxt["next_volume"] = nxt.groupby("code", sort=False)["volume"].shift(-1)
    key = nxt[["code", "date", "close", "next_open", "next_high", "next_low",
               "next_close", "next_volume"]]

    out = signals.merge(key, on=["code", "date"], how="left")
    limit = out["code"].map(limit_for).to_numpy("float64")

    prev_close = out["close"].to_numpy("float64")
    next_open = out["next_open"].to_numpy("float64")
    gap = next_open / (prev_close + 1e-12) - 1.0

    out["gap_pct"] = gap
    # Gapped at or above the limit: there were no sellers at the open.
    out["open_at_limit"] = gap >= (limit - LIMIT_TOLERANCE)
    # A one-word board: the whole next session is pinned at the limit.
    out["one_word_limit"] = (
        out["open_at_limit"]
        & (np.abs(out["next_high"] - out["next_open"]) < 1e-9)
        & (np.abs(out["next_low"] - out["next_open"]) < 1e-9)
    )
    # No next bar at all (suspended, delisted, or panel end): also unbuyable.
    out["no_next_bar"] = out["next_open"].isna() | (out["next_volume"].fillna(0) <= 0)
    out["unfillable"] = out["open_at_limit"] | out["no_next_bar"]
    return out


def summarise(frame: pd.DataFrame, label: str) -> dict:
    """Hit rate before and after removing unfillable entries."""
    n = len(frame)
    if n == 0:
        return {"label": label, "signals": 0}
    hits = int(frame["label_bull"].fillna(0).sum())
    blocked = int(frame["unfillable"].sum())
    tradeable = frame[~frame["unfillable"]]
    t_hits = int(tradeable["label_bull"].fillna(0).sum())
    return {
        "label": label,
        "signals": n,
        "hits": hits,
        "hit_rate": hits / n,
        "unfillable": blocked,
        "unfillable_pct": blocked / n,
        "one_word_limit": int(frame["one_word_limit"].sum()),
        "gapped_at_limit": int(frame["open_at_limit"].sum()),
        "no_next_bar": int(frame["no_next_bar"].sum()),
        "tradeable_signals": len(tradeable),
        "tradeable_hits": t_hits,
        "tradeable_hit_rate": (t_hits / len(tradeable)) if len(tradeable) else float("nan"),
    }


def main() -> None:
    panel = data_pipeline.load_panel()[["code", "date", "open", "high", "low", "close", "volume"]]

    webpro = pd.read_csv(
        OUT_DIR / "webpro_signals.csv",
        dtype={"code": "string"},
        usecols=["code", "date", "strategy_id", "label_bull__webpro"],
        parse_dates=["date"],
    )
    webpro["code"] = webpro["code"].str.zfill(6)
    webpro = webpro.rename(columns={"label_bull__webpro": "label_bull"})

    audited = audit(webpro, panel)
    per_strategy = pd.DataFrame(
        [summarise(g, sid) for sid, g in audited.groupby("strategy_id", sort=False)]
    ).sort_values("unfillable_pct", ascending=False)
    per_strategy.to_csv(REPORT_DIR / "tradeability_by_strategy.csv", index=False)

    overall = summarise(audited, "ALL Web Pro signals")
    print("=== fillability of every emitted Web Pro signal ===")
    for k, v in overall.items():
        if isinstance(v, float):
            print(f"  {k:24s} {v:.4f}")
        else:
            print(f"  {k:24s} {v}")

    print("\n=== worst strategies by unfillable share ===")
    show = per_strategy[["label", "signals", "hit_rate", "unfillable_pct",
                         "one_word_limit", "tradeable_hit_rate"]].head(10)
    show = show.assign(hit_rate=(show["hit_rate"] * 100).round(2),
                       unfillable_pct=(show["unfillable_pct"] * 100).round(2),
                       tradeable_hit_rate=(show["tradeable_hit_rate"] * 100).round(2))
    print(show.to_string(index=False))

    summary = {
        "overall": overall,
        "worst_by_unfillable": per_strategy.head(10).to_dict("records"),
        "notes": (
            "Entries are the next session's open. A stock that gaps to its price "
            "limit at the open has no sellers, so the stated entry is not "
            "available. No next bar (suspension/delisting) is likewise unbuyable. "
            "ST status is unknown, so ST names are treated as 10% boards; their "
            "true 5% limit means the unfillable count here is an underestimate."
        ),
    }
    (REPORT_DIR / "tradeability.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nwrote {REPORT_DIR / 'tradeability_by_strategy.csv'}")


if __name__ == "__main__":
    main()
