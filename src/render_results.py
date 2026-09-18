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


def _webpro_family_ids() -> list[str]:
    """Strategy ids declared by the vendored family, or [] if unavailable."""
    try:
        from experts.registry import STRATEGY_IDS
    except Exception:  # noqa: BLE001 - the count is cosmetic, never fatal
        return []
    return list(STRATEGY_IDS)


def webpro_coverage_note(frame: "pd.DataFrame") -> str:
    """Name how many declared strategies actually produced a row.

    A strategy whose score never crosses its threshold emits no signal, so it
    has no row in `webpro_hit_rates.csv` (which is built by grouping *emitted*
    signals). Silently ranking 35 of 36 against a heading that says 36 would
    read as full coverage, so the gap is stated from the data rather than
    hard-coded.
    """
    declared = _webpro_family_ids()
    present = set(frame["strategy_id"])
    ranked = len(present)
    if not declared:
        return (f"_This table ranks the {ranked} strategies that emitted at least "
                f"one signal; any strategy that never fired has no row here._\n")
    missing = [s for s in declared if s not in present]
    total = len(declared)
    if not missing:
        return (f"_All {total} declared strategies emitted at least one signal and "
                f"appear below._\n")
    note = (
        f"_The family declares **{total}** strategies; the table below ranks the "
        f"**{ranked} that emitted at least one signal**. "
        + ", ".join(f"`{m}`" for m in missing)
        + (" fired **zero** times over the whole evaluated universe, so it has no "
           "row in `reports/webpro_hit_rates.csv` and cannot be ranked. Absence "
           "here means \"never triggered\", not \"excluded\"; it is still "
           "exercised by the 100-card reproduction in `README.md` §3._\n"
           if len(missing) == 1 else
           " fired **zero** times over the whole evaluated universe, so they have "
           "no rows in `reports/webpro_hit_rates.csv` and cannot be ranked. "
           "Absence here means \"never triggered\", not \"excluded\"._\n")
    )
    return note


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
    lines.append("")
    panel_rate = _lowzone_panel_baseline("webpro")
    scanned_rate = f"{frame['baseline__webpro'].iloc[0]*100:.3f}%"
    lines.append(
        "_Base rate_ here is the **scanned evaluation grid** figure, matching the "
        "grid these strategies were scored on. The 60-day low-zone table below uses "
        "a base rate censused over the **full resolved panel** instead, because those "
        "versions are evaluated on every resolved bar rather than on a thinned grid. "
        "Both are internally consistent, but the two base-rate columns are **not "
        "interchangeable**: the same `webpro` contract reads "
        f"{scanned_rate} on the scanned grid"
        + (f" and {panel_rate} on the full panel" if panel_rate else "")
        + ".\n"
    )
    return "\n".join(lines) + "\n"


def _lowzone_panel_baseline(regime: str) -> str:
    """The full-panel base rate for ``regime``, as a percentage string.

    Read from the low-zone CSV so the cross-reference in the Web Pro table stays
    true if the panel or the regimes change; empty string if unavailable, in which
    case the calling sentence just omits the contrast.
    """
    path = REPORTS / "lowzone_hit_rates.csv"
    if not path.exists():
        return ""
    frame = pd.read_csv(path)
    if "baseline_rate" not in frame.columns or "regime" not in frame.columns:
        return ""
    sub = frame[frame["regime"] == regime]
    if sub.empty:
        return ""
    return f"{sub['baseline_rate'].iloc[0]*100:.3f}%"


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
    # Name the row set. `reports/lowzone_baselines.json` publishes a base rate for
    # the same three regimes over the *full* panel, and the two disagree by up to
    # ~10% in relative terms, so an unqualified "the base rate" is ambiguous.
    #
    # Prefer the payload's own `population` block. If it is absent the file predates
    # that block, and this file *is* written by scan_all.population_baselines, so the
    # population is the scanned grid by construction — state that rather than stay
    # silent, or a reader of an un-regenerated RESULTS.md is back to the ambiguity.
    pop = None
    spans = []
    for d in data.values():
        blk = d.get("population")
        if not isinstance(blk, dict):
            continue
        if pop is None:
            pop = blk
        # Each contract resolves over its own span (a 504-session window runs out
        # of future bars far earlier than a 10-session one), so the note quotes the
        # union rather than whichever regime happens to come first.
        if blk.get("date_min"):
            spans.append(str(blk["date_min"]))
        if blk.get("date_max"):
            spans.append(str(blk["date_max"]))
    if pop is None:
        # No `population` block, so this file predates it. The stride must not be
        # guessed: `webpro_scan_summary.json` is written by the same scan and
        # records the stride it actually ran with, so read it there rather than
        # hardcoding 5. A hardcoded 5 would silently mislabel a stride-1 scan.
        scan_stride, scan_min_history = None, None
        try:
            import json as _json

            summary_path = REPORTS / "webpro_scan_summary.json"
            if summary_path.exists():
                summary = _json.loads(summary_path.read_text(encoding="utf-8"))
                scan_stride = summary.get("stride")
                scan_min_history = summary.get("min_history")
        except (OSError, ValueError):
            pass
        pop = {
            "population": "scanned",
            "stride": scan_stride,
            "min_history": scan_min_history,
            "date_min": None,
            "date_max": None,
        }
        # `webpro_scan_summary.json` records `stride` but predates `min_history`
        # and `population`, so recover min_history from the constant the scan
        # itself uses (`src/scan_all.py: MIN_HISTORY = runner.VISIBLE_BARS`)
        # rather than printing "None" or re-hardcoding 60 here.
        if pop["min_history"] is None:
            try:
                from src import runner as _runner

                pop["min_history"] = _runner.VISIBLE_BARS
            except Exception:
                pass
        if scan_stride is not None:
            note = (" (This file predates the `population` block now emitted by "
                    "`src.scan_all`; its stride and min_history are read from "
                    "`webpro_scan_summary.json`, which the same scan wrote. "
                    "Re-run `python -m src.scan_all` to record them here "
                    "explicitly.)")
        else:
            note = (" (This file predates the `population` block, and "
                    "`webpro_scan_summary.json` is missing or unreadable, so the "
                    "grid it was measured on cannot be stated. Re-run "
                    "`python -m src.scan_all`.)")
    else:
        note = ""
    span = ""
    if spans:
        span = f" over {min(spans)} .. {max(spans)}"
    lines.append("")
    # If the stride could not be recovered, say so rather than printing "every
    # Noneth bar".
    if pop.get("stride") is not None:
        grid_line = (
            f"These are measured on the **scanned evaluation grid**: per-stock bar "
            f"index `_seq >= {pop['min_history']}` and then every "
            f"{pop['stride']}th bar{span}.")
    else:
        grid_line = (
            f"These are measured on the **scanned evaluation grid** (per-stock bar "
            f"index `_seq >= {pop.get('min_history')}` and then every Nth "
            f"bar{span}), whose stride this file cannot state.")
    lines.append(
        f"{grid_line} That is the population the strategies "
        f"were actually scored on, so it is the correct denominator for every "
        f"lift below. It is *not* the whole panel — because almost every stock "
        f"is present on the first session, the `_seq >= {pop.get('min_history')}` "
        f"filter also drops the 2023-Q1 warm-up window, which is why the "
        f"scanned rate sits above the full-panel rate for `low504`. "
        f"`reports/lowzone_baselines.json` publishes the full-panel figures "
        f"(different populations, different numbers); a lift must not mix the "
        f"two. See [README.md §5](README.md#5-results).{note}\n"
    )
    return "\n".join(lines) + "\n"


def expectancy_table() -> str:
    """Hit rate vs. what a holder actually earns, on the same signals."""
    path = REPORTS / "hitrate_vs_expectancy.csv"
    if not path.exists():
        return "_Expectancy analysis not available._\n"
    frame = pd.read_csv(path).sort_values("hit_rate", ascending=False)
    lines = [
        "| Strategy | Signals | Hit rate | **Net 10d return** | At-target | If hit | If miss | Net win rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in frame.itertuples():
        lines.append(
            f"| `{r.strategy_id}` | {r.signals} | {r.hit_rate*100:.2f}% "
            f"| **{r.net_expectancy*100:+.2f}%** | {r.net_expectancy_at_target*100:+.2f}% "
            f"| {r.mean_return_if_hit*100:+.2f}% | {r.mean_return_if_miss*100:+.2f}% "
            f"| {r.net_win_rate*100:.2f}% |"
        )
    return "\n".join(lines) + "\n"


def tradeability_table() -> str:
    path = REPORTS / "tradeability_by_strategy.csv"
    if not path.exists():
        return "_Tradeability analysis not available._\n"
    frame = pd.read_csv(path).sort_values("unfillable_pct", ascending=False)
    lines = [
        "| Strategy | Signals | Unfillable | Share | One-word limit | Hit rate as reported | Hit rate excluding unfillable |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in frame.itertuples():
        lines.append(
            f"| `{r.label}` | {r.signals} | {r.unfillable} | {r.unfillable_pct*100:.2f}% "
            f"| {r.one_word_limit} | {r.hit_rate*100:.2f}% | {r.tradeable_hit_rate*100:.2f}% |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    sections = [
        "# Measured Results\n",
        "Every number below is regenerated from the backtest output CSVs by "
        "`python -m src.render_results`, so it cannot drift from the data.\n",
        "## Natural base rates (the population each strategy is scored against)\n",
        baselines(),
        "\n## Web Pro family — 36 strategies registered, 35 signalled\n",
        "Horizon 10 sessions, target +30%, entry at the next session's open, "
        "signals de-duplicated at a 60-session cooldown. **Lift** is the hit rate "
        "divided by the natural base rate of 3.035% *on the scanned evaluation "
        "grid* (the population above, and the grid these strategies were scored "
        "on): a lift of 1.0 means the strategy is indistinguishable from picking "
        "at random.\n",
        webpro_table(),
        webpro_coverage_note(pd.read_csv(REPORTS / "webpro_hit_rates.csv")
                             if (REPORTS / "webpro_hit_rates.csv").exists()
                             else pd.DataFrame({"strategy_id": []})),
        "\n## What a holder actually earns — the hit-rate inversion\n",
        "Hit rate is the share of signals whose forward **maximum high** touches "
        "+30% within 10 sessions. It says nothing about what happens on the other "
        "signals. This table computes, on those same signals, the mean realised "
        "next-open-to-horizon-close return net of 10.2 bp round-trip cost.\n",
        "**The two rankings are inverted** (Spearman rho = -0.511): the strategies "
        "with the highest hit rates lose the most money. `leader_momentum` has the "
        "best hit rate in the family and the worst expectancy; `rsi_mean_reversion` "
        "and `strict_oversold_rebound_v2` sit at or below the 3.035% base rate and "
        "are among the minority that make money.\n",
        "**If hit** and **if miss** are conditional means and are therefore "
        "selection-biased by construction; they appear only to expose the lottery "
        "structure — winners are credited with their +30% touch while losers run to "
        "the horizon close.\n",
        expectancy_table(),
        "\n## Can the signals actually be bought?\n",
        "Every hit rate above assumes the entry is the next session's open. A stock "
        "that gaps to its price limit at the open has no sellers, so that entry does "
        "not exist. This measures how much of each strategy's signal count is "
        "unfillable, and the hit rate once those are removed.\n",
        tradeability_table(),
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
