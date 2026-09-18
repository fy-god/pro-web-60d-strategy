"""Check the README 9.2 figures against the regenerated tradeability CSV.

Section 9.2's table was hand-edited after the denominator fix. Every cell must
match reports/tradeability_by_strategy.csv, and the two prose numbers (family-wide
unfillable and one-word-limit totals) must match the report's overall block.
"""
from __future__ import annotations

import io
import json
import pathlib

import pandas as pd

tb = pd.read_csv("reports/tradeability_by_strategy.csv")
rep = json.load(io.open("reports/tradeability.json", encoding="utf-8"))
ov = rep["overall"]
readme = pathlib.Path("README.md").read_text(encoding="utf-8")

# (label, signals, unfillable, share, one_word, rate, ex_unfillable) as written.
WRITTEN = [
    ("leader_momentum", 616, 98, 15.91, 32, 20.62, 18.34),
    ("strict_gap_follow_through", 3137, 425, 13.55, 167, 14.22, 12.46),
    ("gap_follow_through", 3978, 480, 12.07, 189, 13.00, 11.29),
    ("strict_leader_momentum_v2", 3239, 366, 11.30, 122, 15.96, 14.72),
]

m = {r["label"]: r for r in tb.to_dict("records")}
print(f"{'strategy':<28}{'cell':<16}{'README':>12}{'CSV':>14}  ok")
print("-" * 74)
bad = []
for lab, sig, unf, share, owl, rate, ex in WRITTEN:
    r = m[lab]
    checks = [
        ("signals", sig, int(r["signals"])),
        ("unfillable", unf, int(r["unfillable"])),
        ("share %", share, round(r["unfillable_pct"] * 100, 2)),
        ("one_word_limit", owl, int(r["one_word_limit"])),
        ("hit_rate %", rate, round(r["hit_rate"] * 100, 2)),
        ("excl unfill %", ex, round(r["tradeable_hit_rate"] * 100, 2)),
    ]
    for name, written, actual in checks:
        ok = abs(written - actual) < 5e-3
        if not ok:
            bad.append((lab, name, written, actual))
        print(f"{lab:<28}{name:<16}{written:>12}{actual:>14}  {'OK' if ok else 'MISMATCH'}")

print("-" * 74)
print("=== family-wide prose ===")
pairs = [
    ("resolved signals", 637499, int(ov["signals"])),
    ("emitted signals", 646718, int(ov["signals_raw"])),
    ("censored", 9219, int(ov["censored"])),
    ("unfillable", 10410, int(ov["unfillable"])),
    ("one_word_limit", 4304, int(ov["one_word_limit"])),
]
for name, written, actual in pairs:
    ok = written == actual
    if not ok:
        bad.append(("family", name, written, actual))
    print(f"  {name:<20}{written:>10,}{actual:>10,}  {'OK' if ok else 'MISMATCH'}")
pct = ov["unfillable"] / ov["signals"] * 100
print(f"  unfillable share     README 1.63%   actual {pct:.2f}%  "
      f"{'OK' if abs(pct - 1.63) < 0.005 else 'MISMATCH'}")
if abs(pct - 1.63) >= 0.005:
    bad.append(("family", "share", 1.63, round(pct, 2)))

print("\n=== the two prose strings must be present verbatim ===")
for s in ("**10,410 of 637,499 resolved signals (1.63%) are unfillable**",
          "4,304 are one-word limit boards",
          "38,463 emitted less 663 censored = 37,800 resolved"):
    found = s.replace("\n", " ") in readme.replace("\n", " ")
    print(f"  {'OK ' if found else 'MISSING'} {s[:64]!r}")
    if not found:
        bad.append(("readme", "string", s[:40], None))

print("\n=== the atr_trend_follow example in the two-files note ===")
r = m["atr_trend_follow"]
raw = None
for row in pd.read_csv("reports/webpro_hit_rates.csv").to_dict("records"):
    if row["strategy_id"] == "atr_trend_follow":
        raw = row
print(f"  emitted (tradeability.signals_raw)             : "
      f"{int(r['signals_raw']):,}")
print(f"  webpro_hit_rates.signals_raw__webpro           : "
      f"{int(raw['signals_raw__webpro']):,}")
print(f"  censored (both files)                          : "
      f"{int(r['censored']):,} / {int(raw['censored_signals__webpro']):,}")
print(f"  resolved (tradeability.signals)                : {int(r['signals']):,}")
print(f"  identity 38463 - 663 = 37800 : {38463 - 663 == int(r['signals'])}")
print(f"  and equals webpro_hit_rates.signals_raw : "
      f"{int(r['signals']) == int(raw['signals_raw__webpro'])}")
print(f"  unfillable {int(r['unfillable'])} "
      f"({r['unfillable_pct']*100:.2f}% of resolved)")
for name, written, actual in (("unfillable", 943, int(r["unfillable"])),):
    if written != actual:
        bad.append(("atr", name, written, actual))
print(f"  {'OK' if int(r['unfillable']) == 943 else 'MISMATCH'} unfillable == 943")
if abs(r["unfillable_pct"] * 100 - 2.49) >= 0.005:
    bad.append(("atr", "pct", 2.49, round(r["unfillable_pct"] * 100, 2)))
print(f"  {'OK' if abs(r['unfillable_pct']*100 - 2.49) < 0.005 else 'MISMATCH'} "
      f"share == 2.49%")
if "37,137" in readme:
    bad.append(("readme", "stale 37,137", None, None))
    print("  MISMATCH stale '37,137' still in README")
else:
    print("  OK no stale 37,137 in README")

print(f"\nRESULT: {'ALL FIGURES VERIFIED' if not bad else f'{len(bad)} MISMATCHES'}")
for b in bad[:12]:
    print("   ", b)
