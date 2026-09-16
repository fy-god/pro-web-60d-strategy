"""Render the final result tables from the backtest reports into markdown.

Kept as a script (rather than hand-written into the README) so the published
numbers are always regenerated from the measured CSVs and can never drift from
the data.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "reports"
OUT = REPO / "RESULTS.md"


def webpro_table() -> str:
    path = REPORTS / "webpro_hit_rates.csv"
    if not path.exists():
        return "_Web Pro results not available._\n"
    frame = pd.read_csv(path).sort_values("lift__webpro", ascending=False)
    lines = [
        "| # | Strategy | Signals | Hits | **Hit rate** | Base rate | Lift | Wilson 95% low | Stocks | Dates |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for i, r in enumerate(frame.itertuples(), 1):
        lines.append(
            f"| {i} | `{r.strategy_id}` | {r.signals_deduped__webpro} "
            f"| {r.bull_hits_deduped__webpro} "
            f"| **{r.bull_precision_deduped__webpro*100:.2f}%** "
            f"| {r.baseline__webpro*100:.3f}% | {r.lift__webpro:.2f}x "
            f"| {r.bull_wilson_low__webpro*100:.2f}% "
            f"| {r.distinct_stocks__webpro} | {r.distinct_dates__webpro} |"
        )
    return "\n".join(lines) + "\n"


def lowzone_table() -> str:
    path = REPORTS / "lowzone_hit_rates.csv"
    if not path.exists():
        return "_Low-zone results not available._\n"
    frame = pd.read_csv(path)
    frame = frame[frame["signals_deduped"] > 0]
    lines = [
        "| Version | Regime | Signals | Hits | **Hit rate** | Base rate | Lift | Wilson 95% low | Stocks | Protocol |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in frame.sort_values(["regime", "version"]).itertuples():
        proto = ("per-year in-sample fit (NOT cross-year)"
                 if bool(r.in_sample) else "walk-forward, prior-year threshold")
        lines.append(
            f"| **{r.version}** | {r.regime} | {r.signals_deduped} | {r.bull_hits} "
            f"| **{r.bull_precision*100:.2f}%** | {r.baseline_rate*100:.3f}% "
            f"| {r.lift_vs_baseline:.2f}x | {r.wilson_low*100:.2f}% "
            f"| {r.distinct_stocks} | {proto} |"
        )
    return "\n".join(lines) + "\n"


def baselines() -> str:
    path = REPORTS / "webpro_baselines.json"
    if not path.exists():
        return ""
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    lines = [
        "| Regime | Contract | Evaluated points | Natural bull rate | Natural joint rate |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    labels = {
        "webpro": "10 sessions, **+30%**",
        "low60": "60 sessions, **4x** (i.e. +300%)",
        "low504": "504 sessions, **4x**",
    }
    for regime, d in data.items():
        lines.append(
            f"| `{regime}` | {labels.get(regime, regime)} | {d['evaluated_points']:,} "
            f"| {d['bull_rate']*100:.4f}% | {d['joint_rate']*100:.4f}% |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    sections = [
        "# Measured Results\n",
        "Every number below is regenerated from the backtest output CSVs by "
        "`python -m src.render_results`, so it cannot drift from the data.\n",
        "## Natural base rates (the population each strategy is scored against)\n",
        baselines(),
        "\n## Web Pro family — 36 strategies, full universe\n",
        "Horizon 10 sessions, target +30%, entry at the next session's open, "
        "signals de-duplicated at a 60-session cooldown. **Lift** is the hit rate "
        "divided by the natural base rate of 3.035%: a lift of 1.0 means the "
        "strategy is indistinguishable from picking at random.\n",
        webpro_table(),
        "\n## 60-Day Low-Zone family — V00–V08\n",
        "Scored under both contracts. V07/V08 use a per-year threshold chosen on "
        "the evaluation year itself and are flagged as in-sample fits, which is "
        "what the source project's own record does.\n",
        lowzone_table(),
    ]
    OUT.write_text("\n".join(sections), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
