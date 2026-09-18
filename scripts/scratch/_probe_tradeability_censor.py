"""Verify the tradeability censoring fix against the published report.

The audit found src/tradeability.py scored censored signals as 0 while keeping them
in the denominator (`hits = label_bull.fillna(0).sum()`, `hit_rate = hits/len`),
contradicting src/labels.py's stated rule that censored rows are excluded from
every denominator.

This probe checks the identity the audit reported -- signals == signals_raw +
censored, and hit_rate == hits/signals_raw for all 35 rows -- and then measures what
the corrected denominator does. It reads the published CSV and the signals file
only; it does not rerun the pipeline.
"""
from __future__ import annotations

import io
import json
import pathlib

import numpy as np
import pandas as pd

REPORT = pathlib.Path("reports/tradeability.json")
SIG = pathlib.Path("outputs/webpro_signals.csv")
CSV = pathlib.Path("reports/tradeability_by_strategy.csv")

print("=== published tradeability.json ===")
pub = json.load(io.open(REPORT, encoding="utf-8"))
ov = pub["overall"]
print(f"  signals {ov['signals']:,}  hits {ov['hits']:,}  "
      f"hit_rate {ov['hit_rate']*100:.3f}%")
print(f"  keys: {sorted(ov.keys())}")

print("\n=== the censoring identity the audit reported ===")
sig = pd.read_csv(SIG, usecols=["strategy_id", "label_bull__webpro",
                                "label_resolved__webpro"],
                  dtype={"strategy_id": "string"})
g = sig.groupby("strategy_id", sort=False)
ledger = pd.DataFrame({
    "signals_raw": g.size(),
    "resolved": g["label_resolved__webpro"].sum(),
}).reset_index()
ledger["censored"] = ledger["signals_raw"] - ledger["resolved"]

by_strat = pd.read_csv(CSV)
byt = {r["label"]: r for r in by_strat.to_dict("records")}
print(f"  {'strategy':<34}{'csv signals':>12}{'raw':>10}{'cens':>8}"
      f"{'hits/raw':>10}{'hits/sig':>10}")

exact_raw, exact_hits, biased = 0, 0, 0
for r in ledger.itertuples():
    row = byt.get(r.strategy_id)
    if row is None:
        continue
    n_csv = int(row["signals"])
    # published hit_rate is hits/signals_raw (censored-inclusive)
    is_raw_basis = abs(float(row["hit_rate"]) - float(row["hits"]) / n_csv) < 1e-12
    exact_raw += (n_csv == r.signals_raw)
    if is_raw_basis:
        biased += 1
    exact_hits += (int(row["hits"]) == int(
        sig[(sig["strategy_id"] == r.strategy_id) & (sig["label_resolved__webpro"])]
        ["label_bull__webpro"].fillna(0).sum()))

print(f"\n  CSV `signals` == emitted raw count on {exact_raw}/{len(ledger)} rows")
print(f"  CSV `hits` == resolved hits on {exact_hits}/{len(ledger)} rows")
print(f"  CSV hit_rate == hits/signals_raw (CENSORED-INCLUSIVE) on "
      f"{biased}/{len(ledger)} rows")

tot_raw = int(ledger["signals_raw"].sum())
tot_res = int(ledger["resolved"].sum())
tot_hits = int(pd.read_csv(CSV)["hits"].sum())
print(f"\n  total emitted {tot_raw:,}  resolved {tot_res:,}  "
      f"censored {tot_raw - tot_res:,}")
print(f"  published basis : {tot_hits:,}/{tot_raw:,} = "
      f"{100*tot_hits/tot_raw:.3f}%")
print(f"  corrected basis : {tot_hits:,}/{tot_res:,} = "
      f"{100*tot_hits/tot_res:.3f}%")

print("\n=== strategies most affected ===")
rows = []
for r in ledger.itertuples():
    row = byt.get(r.strategy_id)
    if row is None:
        continue
    live = sig[(sig["strategy_id"] == r.strategy_id)
               & (sig["label_resolved__webpro"])]
    n_res = len(live)
    hits = int(live["label_bull__webpro"].fillna(0).sum())
    if n_res == 0:
        continue
    rows.append({
        "strategy": r.strategy_id,
        "published_pct": round(float(row["hit_rate"]) * 100, 3),
        "corrected_pct": round(100 * hits / n_res, 3),
        "censored": int(r.censored),
        "delta_pp": round(100 * hits / n_res - float(row["hit_rate"]) * 100, 3),
    })
rows.sort(key=lambda d: -abs(d["delta_pp"]))
for d in rows[:6]:
    print(f"  {d['strategy']:<34} {d['published_pct']:>7.3f}% -> "
          f"{d['corrected_pct']:>7.3f}%  ({d['delta_pp']:+.3f}pp, "
          f"{d['censored']} censored)")

json.dump({"overall": rows and {
    "published_basis": round(100 * tot_hits / tot_raw, 4),
    "corrected_basis": round(100 * tot_hits / tot_res, 4),
    "censored": tot_raw - tot_res}, "per_strategy": rows},
    io.open("scripts/scratch/_tradeability_censor.json", "w", encoding="utf-8"),
    indent=2)

ok = (exact_raw == len(ledger) and exact_hits == len(ledger)
      and biased == len(ledger))
print(f"\nRESULT: {'BUG CONFIRMED' if ok else 'identity mismatch - investigate'} "
      f"-- every published row divides by the censored-inclusive total")
