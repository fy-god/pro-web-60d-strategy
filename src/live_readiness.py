"""Live-readiness assessment: could any of this be traded, and could it be traded intraday?

Answers four concrete questions with measured numbers rather than opinion.

1. **Signal latency.** When is a signal knowable, and when can it be acted on?
   Every strategy reads a 60-bar *daily* card and its last visible bar is the
   signal bar, so the decision requires that bar's **close**. Earliest possible
   fill is therefore the next session's open — a minimum of one overnight gap
   with no ability to act intraday on the signal day itself.

2. **Holding period.** The target contract fixes a minimum holding horizon.

3. **Expectancy.** The hit rates elsewhere in this repo use the forward *maximum*
   high, which is an idealised exit. This module instead measures the realised
   close-to-close return over each horizon, which is what a mechanical holder
   would actually get, and reports it net of a cost assumption.

4. **Intraday feasibility.** Whether the strategy logic can even be evaluated
   from intraday data, and what intraday data exists locally.

Usage
-----
    python -m src.live_readiness
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

# Round-trip cost assumption for A-shares, in basis points of turnover value:
# commission ~2.5bp each side, stamp duty 5bp on the sell side (as of 2023-08),
# plus transfer fee ~0.1bp. Slippage is excluded and would only make this worse.
COST_BPS_ROUND_TRIP = 2.5 + 2.5 + 5.0 + 0.2

MINUTE_DATA = Path(
    r"D:\xm\a_share_intraday_lab\analysis\two_week_top100_20260817_20260828"
    r"\minute_bars_used_two_week.parquet"
)


def realised_return(panel: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Close at the horizon's end vs. the next session's open, per (code, date).

    Alignment must match ``labels.forward_outcomes`` exactly, which sweeps
    ``d = 1..horizon`` so its window spans bars 1..horizon ahead of the signal
    bar. The entry is bar 1's open; the exit is therefore bar ``horizon``'s
    close — **not** ``horizon + 1``. Getting this wrong by one session
    misstates every expectancy below.
    """
    frame = panel.sort_values(["code", "date"]).copy()
    grouped = frame.groupby("code", sort=False)
    frame["entry_open"] = grouped["open"].shift(-1)
    frame["exit_close"] = grouped["close"].shift(-horizon)
    frame["return_h"] = frame["exit_close"] / frame["entry_open"] - 1.0
    return frame[["code", "date", "entry_open", "exit_close", "return_h"]]


def assess(signals: pd.DataFrame, panel: pd.DataFrame, horizon: int,
           label: str) -> dict:
    """Expectancy and tradeability for one strategy family under one horizon."""
    returns = realised_return(panel, horizon)
    merged = signals.merge(returns, on=["code", "date"], how="left")
    live = merged[merged["return_h"].notna()]

    if live.empty:
        return {"label": label, "signals": len(signals), "resolved": 0}

    r = live["return_h"].to_numpy("float64")
    cost = COST_BPS_ROUND_TRIP / 10_000.0
    net = r - cost

    return {
        "label": label,
        "horizon_sessions": horizon,
        "signals": int(len(signals)),
        "resolved": int(len(live)),
        "gross_mean_return": float(r.mean()),
        "gross_median_return": float(np.median(r)),
        "net_mean_return": float(net.mean()),
        "net_median_return": float(np.median(net)),
        "net_win_rate": float((net > 0).mean()),
        "net_p10": float(np.percentile(net, 10)),
        "net_p90": float(np.percentile(net, 90)),
        "cost_bps_round_trip": COST_BPS_ROUND_TRIP,
    }


def intraday_feasibility() -> dict:
    """What intraday data exists, and whether the strategy logic can use it."""
    info = {
        "daily_strategy_logic": (
            "Every strategy consumes a 60-bar DAILY card built by src.runner.make_card, "
            "and the signal bar is the last visible bar. The decision therefore needs "
            "that bar's daily CLOSE. A mid-session evaluation would substitute the "
            "current price for the close, which changes the rule and is NOT what was "
            "backtested."
        ),
        "earliest_actionable_moment": (
            "The next session's open, at the earliest. The original project's own "
            "next-day-close strategy documentation states the signal is confirmed at "
            "the close of one-minute candles and the fill window is the NEXT minute — "
            "a one-minute strategy, not this one."
        ),
        "min_holding": "10 sessions (Web Pro +30% contract)",
        "t_plus_rule": "A-shares are T+1: shares bought today cannot be sold today.",
        "minute_data_available": None,
    }
    if MINUTE_DATA.exists():
        m = pd.read_parquet(MINUTE_DATA, columns=["symbol", "datetime"])
        info["minute_data_available"] = {
            "path": str(MINUTE_DATA),
            "rows": int(len(m)),
            "symbols": int(m["symbol"].nunique()),
            "start": str(m["datetime"].min()),
            "end": str(m["datetime"].max()),
            "trading_days": int(m["datetime"].dt.date.nunique()),
            "verdict": (
                "Two weeks of one-minute bars for ~100 stocks. This cannot train, "
                "validate, or even sanity-check a 60-DAILY-bar strategy, and it is "
                "far too short to measure a 10-session outcome."
            ),
        }
    else:
        info["minute_data_available"] = "not found"
    return info


def main() -> None:
    panel = data_pipeline.load_panel()[
        ["code", "date", "open", "high", "low", "close", "volume"]
    ]

    webpro = pd.read_csv(
        OUT_DIR / "webpro_signals.csv",
        dtype={"code": "string"},
        usecols=["code", "date", "strategy_id", "label_bull__webpro"],
        parse_dates=["date"],
    )
    webpro["code"] = webpro["code"].str.zfill(6)

    results = []
    # Web Pro's own contract, plus a shorter and a longer holding period so the
    # sensitivity of expectancy to the exit rule is visible.
    for horizon in (10, 20, 60):
        block = assess(webpro, panel, horizon, f"ALL Web Pro signals, hold {horizon}")
        results.append(block)

    # Per-strategy expectancy at the contract horizon, for every strategy.
    for sid, group in webpro.groupby("strategy_id", sort=False):
        results.append(assess(group, panel, 10, sid))

    frame = pd.DataFrame(results)
    frame.to_csv(REPORT_DIR / "live_readiness.csv", index=False)

    print("=== realised return, net of costs (close-to-close over the horizon) ===")
    show = frame.head(3).copy()
    for c in ("gross_mean_return", "gross_median_return", "net_mean_return",
              "net_median_return", "net_win_rate", "net_p10", "net_p90"):
        show[c] = (show[c].astype(float) * 100).round(2)
    print(show[["label", "resolved", "gross_mean_return", "net_mean_return",
                "net_median_return", "net_win_rate", "net_p10", "net_p90"]].to_string(index=False))

    print("\n=== per-strategy expectancy, hold 10, net of costs ===")
    per = frame.iloc[3:].copy()
    per["net_mean_return"] = per["net_mean_return"].astype(float) * 100
    per["net_median_return"] = per["net_median_return"].astype(float) * 100
    per["net_win_rate"] = per["net_win_rate"].astype(float) * 100
    per = per.sort_values("net_mean_return", ascending=False)
    out = per[["label", "resolved", "net_mean_return", "net_median_return", "net_win_rate"]].copy()
    for c in ("net_mean_return", "net_median_return", "net_win_rate"):
        out[c] = out[c].round(2)
    print(out.to_string(index=False))

    info = intraday_feasibility()
    print("\n=== intraday feasibility ===")
    print(json.dumps(info, indent=2, ensure_ascii=False))

    (REPORT_DIR / "live_readiness.json").write_text(
        json.dumps({"expectancy": results, "intraday": info}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nwrote {REPORT_DIR / 'live_readiness.csv'}")


if __name__ == "__main__":
    main()
