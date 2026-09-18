"""Measure exactly how the three published CSVs count signals.

The README's "two files count differently" note was written against the OLD
tradeability denominator (emitted). After the fix, tradeability divides by the
RESOLVED count, so the relation between the files changed and the note must be
re-derived rather than hand-edited. This measures:

  hitrate_vs_expectancy.signals        (H)
  webpro_hit_rates.signals_raw__webpro (W_raw)  + censored_signals__webpro (W_cen)
  tradeability.signals                (T_res)   and .signals_raw (T_raw) + .censored

and reports which equalities actually hold, plus the atr_trend_follow case used as
the README's worked example.
"""
from __future__ import annotations

import pandas as pd

H = {r["strategy_id"]: r for r in pd.read_csv("reports/hitrate_vs_expectancy.csv")
     .to_dict("records")}
W = {r["strategy_id"]: r for r in pd.read_csv("reports/webpro_hit_rates.csv")
     .to_dict("records")}
T = {r["label"]: r for r in pd.read_csv("reports/tradeability_by_strategy.csv")
     .to_dict("records")}

shared = sorted(set(H) & set(W) & set(T))
print(f"shared strategies: {len(shared)}  (H={len(H)} W={len(W)} T={len(T)})")
print()

eq = {"H == W_raw": 0, "H == T_res": 0, "H == T_raw": 0,
      "W_raw + W_cen == T_raw": 0, "W_raw == T_res": 0, "W_cen == T_cen": 0,
      "T_raw - T_cen == T_res": 0}
first_diff_H_T = None
for s in shared:
    h = int(H[s]["signals"])
    wr = int(W[s]["signals_raw__webpro"])
    wc = int(W[s]["censored_signals__webpro"])
    tr = int(T[s]["signals_raw"])
    tc = int(T[s]["censored"])
    t = int(T[s]["signals"])
    if h == wr:
        eq["H == W_raw"] += 1
    if h == t:
        eq["H == T_res"] += 1
    else:
        if first_diff_H_T is None:
            first_diff_H_T = (s, h, t)
    if h == tr:
        eq["H == T_raw"] += 1
    if wr + wc == tr:
        eq["W_raw + W_cen == T_raw"] += 1
    if wr == t:
        eq["W_raw == T_res"] += 1
    if wc == tc:
        eq["W_cen == T_cen"] += 1
    if tr - tc == t:
        eq["T_raw - T_cen == T_res"] += 1

n = len(shared)
for k, v in eq.items():
    print(f"  {k:<24} {v:>3}/{n}  {'ALL' if v == n else ''}")
if first_diff_H_T:
    print(f"  first H != T_res: {first_diff_H_T}")

print("\n=== the worked example: atr_trend_follow ===")
s = "atr_trend_follow"
print(f"  hitrate_vs_expectancy.signals        H      = {int(H[s]['signals']):>7,}")
print(f"  webpro_hit_rates.signals_raw__webpro W_raw  = {int(W[s]['signals_raw__webpro']):>7,}")
print(f"  webpro_hit_rates.censored_signals    W_cen  = {int(W[s]['censored_signals__webpro']):>7,}")
print(f"  tradeability.signals_raw             T_raw  = {int(T[s]['signals_raw']):>7,}")
print(f"  tradeability.censored                T_cen  = {int(T[s]['censored']):>7,}")
print(f"  tradeability.signals (resolved)      T_res  = {int(T[s]['signals']):>7,}")
print(f"  unfillable = {int(T[s]['unfillable'])}  "
      f"share = {T[s]['unfillable_pct']*100:.2f}% of resolved")

print("\n=== so what is the correct statement? ===")
h_eq_t = eq["H == T_res"] == n
print(f"  hitrate_vs_expectancy.signals == tradeability.signals "
      f"for {eq['H == T_res']}/{n} strategies")
print(f"  webpro_hit_rates' `signals_raw__webpro` == tradeability's RESOLVED count "
      f"for {eq['W_raw == T_res']}/{n}")
if eq["W_raw + W_cen == T_raw"] == n:
    print("  webpro_hit_rates' raw+censored == tradeability's EMITTED count for all")
print()
if h_eq_t:
    print("  => the two files now MATCH on the signal count; the old note's")
    print("     'the second count is larger' is obsolete and must be rewritten.")
else:
    print("  => they still differ; document the measured relation.")
