"""Measure each strict_* variant against its base on the published evaluation.

A lower `strict_*` THRESHOLD is only meaningful if it changes the emitted set. The
claim in these modules' THESIS lines is "A higher cutoff keeps only ... the
strongest", i.e. a subset. This measures, from the shipped webpro_hit_rates.csv,
whether each strict variant actually emits FEWER signals than its base and whether
its precision is higher -- the two observable consequences of the claim.
"""
from __future__ import annotations

import importlib
import pathlib
import re

import pandas as pd

STRAT = pathlib.Path("experts/strategies")
W = {r["strategy_id"]: r for r in pd.read_csv("reports/webpro_hit_rates.csv")
     .to_dict("records")}

PAIRS = [
    ("accumulation_base", "strict_accumulation_base_v2"),
    ("bollinger_squeeze", "strict_bollinger_release_v2"),
    ("first_board_breakout", "strict_first_board_breakout_v2"),
    ("gap_follow_through", "strict_gap_follow_through"),
    ("gap_follow_through", "strict_gap_follow_through_v2"),
    ("leader_momentum", "strict_leader_momentum_v2"),
    ("obv_volume_price", "strict_obv_volume_price"),
    ("obv_volume_price", "strict_obv_volume_price_v2"),
    ("oversold_rebound", "strict_oversold_rebound_v2"),
    ("platform_breakout", "strict_platform_breakout"),
    ("platform_breakout", "strict_platform_breakout_v2"),
    ("relative_strength_rank", "strict_relative_strength"),
    ("relative_strength_rank", "strict_relative_strength_v2"),
    ("turnover_weak_to_strong", "strict_turnover_weak_to_strong_v2"),
    ("washout_complete", "strict_washout_complete"),
    ("washout_complete", "strict_washout_complete_v2"),
]


def base_t_of(name: str) -> float | None:
    m = importlib.import_module(f"experts.strategies.{name}")
    return getattr(m, "THRESHOLD", None)


def claims_higher(name: str) -> bool:
    src = (STRAT / f"{name}.py").read_text(encoding="utf-8")
    m = importlib.import_module(f"experts.strategies.{name}")
    blob = str(getattr(m, "THESIS", "")) + " " + str(getattr(m, "FORMULA", ""))
    return bool(re.search(r"higher cutoff|stronger .* score|stricter", blob, re.I))


print(f"{'strict variant':<34}{'T':>9}{'base T':>9}{'dir':>7}"
      f"{'base sig':>10}{'strict sig':>11}{'ratio':>8}"
      f"{'base P':>8}{'strict P':>9}{'claim':>7}")
print("-" * 122)
rows = []
missing = []
for base, strict in PAIRS:
    bt, st = base_t_of(base), base_t_of(strict)
    if bt is None or st is None or base not in W or strict not in W:
        missing.append((base, strict, base in W, strict in W))
        continue
    bs = int(W[base]["signals_deduped__webpro"])
    ss = int(W[strict]["signals_deduped__webpro"])
    bp = float(W[base]["bull_precision_deduped__webpro"]) * 100
    sp = float(W[strict]["bull_precision_deduped__webpro"]) * 100
    ratio = ss / bs if bs else float("inf")
    d = "LOOSER" if st < bt else ("tighter" if st > bt else "equal")
    claim = "HIGHER" if claims_higher(strict) else "-"
    rows.append({"base": base, "strict": strict, "T": st, "base_T": bt,
                 "dir": d, "base_sig": bs, "strict_sig": ss,
                 "base_P": bp, "strict_P": sp, "claims": claim})
    print(f"{strict:<34}{st:>9.4f}{bt:>9.4f}{d:>7}{bs:>10,}{ss:>11,}"
          f"{ratio:>7.2f}x{bp:>7.2f}%{sp:>8.2f}%{claim:>7}")

print("-" * 122)
if missing:
    print("not comparable (no signals emitted, so no row):")
    for base, strict, b, s in missing:
        print(f"    {strict:<32} base `{base}` in CSV: {b}")
    print("    -- `accumulation_base` emitted zero signals over the whole "
          "evaluated universe, which the README documents; a selector whose base "
          "never fires cannot be looser than it in practice.")
print("\n  figures are the published de-duplicated counts "
      "(`signals_deduped__webpro`) and bull precision.")

looser = [r for r in rows if r["dir"] == "LOOSER"]
print(f"\n=== the LOOSER variants: does the lower threshold actually admit more? ===")
more, less = [], []
for r in looser:
    (more if r["strict_sig"] > r["base_sig"] else less).append(r)
print(f"  emit MORE signals than base : {len(more)}")
for r in more:
    print(f"    {r['strict']:<32} {r['base_sig']:>7,} -> {r['strict_sig']:>7,}  "
          f"P {r['base_P']:.2f}% -> {r['strict_P']:.2f}%")
print(f"  emit FEWER signals than base: {len(less)}")
for r in less:
    print(f"    {r['strict']:<32} {r['base_sig']:>7,} -> {r['strict_sig']:>7,}  "
          f"P {r['base_P']:.2f}% -> {r['strict_P']:.2f}%")

print(f"\n=== the claim: 'a higher cutoff keeps only the strongest' ===")
both = [r for r in rows if r["claims"] == "HIGHER"]
viol = [r for r in both if r["dir"] == "LOOSER"]
print(f"  variants whose text claims a HIGHER cutoff : {len(both)}")
print(f"  ...that actually use a LOWER threshold     : {len(viol)}")
for r in viol:
    print(f"    {r['strict']:<32} T={r['T']:.4f} vs base {r['base_T']:.4f}")
print(f"\n  variants with an equal-or-higher threshold : "
      f"{len(rows) - len(looser)}/{len(rows)}")

import io, json
io.open("scripts/scratch/_strict_vs_base.json", "w", encoding="utf-8").write(
    json.dumps(rows, indent=2))
print("\nwrote scripts/scratch/_strict_vs_base.json")
