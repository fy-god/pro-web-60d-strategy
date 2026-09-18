"""Verify the in-sample leak in backtest_lowzone's threshold fallback.

src/backtest_lowzone.py:144-147 picks the per-year cutoff from the evaluation
year's OWN scores whenever _prior_year_scores returns None, then stamps
in_sample=False regardless. _prior_year_scores returns None when the only prior
year has no usable fit pool -- which for year=2024 is always, because the panel
starts 2023-01-03 and 2023's own prior pool is empty.

This probe measures the consequence directly on the PUBLISHED signal file, so it
depends on no re-fit:

  1. reproduce each published (version, regime) row from the signals file by
     applying the same dedupe the producer applies -- proves the file is the
     source of the published numbers;
  2. drop eval_year == 2024 and re-dedupe -- the counterfactual on equal footing;
  3. report how much of each published figure 2024 supplies.

Reads only outputs/lowzone_signals.csv (142 MB) with 7 columns.
"""
from __future__ import annotations

import io
import json
import pathlib

import numpy as np
import pandas as pd

CSV = pathlib.Path("outputs/lowzone_signals.csv")
REPORT = pathlib.Path("reports/lowzone_hit_rates.csv")
COOLDOWN = {"webpro": 10, "low60": 60, "low504": 504}
TARGETS = ("V03", "V06", "V07", "V08")


def dedupe(df: pd.DataFrame, cooldown: int) -> pd.DataFrame:
    """Byte-for-byte the producer's rule: session-index walk, first of cluster."""
    if df.empty:
        return df
    out = df.sort_values(["code", "date"]).copy()
    keep = np.zeros(len(out), dtype=bool)
    session_index = {d: i for i, d in enumerate(sorted(out["date"].unique()))}
    positions = out["date"].map(session_index).to_numpy()
    codes = out["code"].to_numpy()
    start = 0
    for i in range(1, len(out) + 1):
        if i == len(out) or codes[i] != codes[start]:
            last = None
            for j in range(start, i):
                if last is None or (positions[j] - last) >= cooldown:
                    keep[j] = True
                    last = positions[j]
            start = i
    return out[keep]


print("loading published signals ...", flush=True)
sig = pd.read_csv(CSV, usecols=["code", "date", "version", "regime",
                                "eval_year", "in_sample", "label_bull"])
print(f"  {len(sig):,} rows, {sig['version'].nunique()} versions, "
      f"regimes {sorted(sig['regime'].unique())}")

published = {}
with io.open(REPORT, encoding="utf-8") as fh:
    import csv
    for row in csv.DictReader(fh):
        published[(row["version"], row["regime"])] = row

print("\n" + "=" * 92)
print(f"{'version/regime':<16}{'published':>22}{'reproduced (all years)':>26}"
      f"{'drop 2024':>22}")
print("=" * 92)
results = []
for (ver, reg), row in sorted(published.items()):
    if ver not in TARGETS:
        continue
    sub = sig[(sig["version"] == ver) & (sig["regime"] == reg)]
    if sub.empty:
        continue
    cd = COOLDOWN[reg]

    d_all = dedupe(sub, cd)
    n_all, h_all = len(d_all), int(d_all["label_bull"].fillna(0).sum())
    r_all = 100 * h_all / n_all if n_all else float("nan")

    no24 = sub[sub["eval_year"] != 2024]
    d_n24 = dedupe(no24, cd)
    n_n24, h_n24 = len(d_n24), int(d_n24["label_bull"].fillna(0).sum())
    r_n24 = 100 * h_n24 / n_n24 if n_n24 else float("nan")

    pub_n = int(row["signals_deduped"])
    pub_r = float(row["hit_rate_pct"])
    pub_ins = row["in_sample"]

    ok = (n_all == pub_n) and abs(r_all - pub_r) < 0.005
    results.append({
        "version": ver, "regime": reg, "in_sample": pub_ins,
        "published_n": pub_n, "published_pct": pub_r,
        "reproduced_n": n_all, "reproduced_pct": round(r_all, 3),
        "reproduces": ok,
        "no2024_n": n_n24, "no2024_pct": round(r_n24, 3),
        "pct_of_signals_from_2024": round(100 * (n_all - n_n24) / n_all, 1)
        if n_all else 0.0,
    })
    print(f"{ver + '/' + reg:<16}"
          f"{f'{pub_n:,} @ {pub_r:.3f}% ({pub_ins})':>22}"
          f"{f'{n_all:,} @ {r_all:.3f}%' + (' OK' if ok else ' MISMATCH'):>26}"
          f"{f'{n_n24:,} @ {r_n24:.3f}%':>22}")

print("=" * 92)

bad = [r for r in results if not r["reproduces"]]
print(f"\nreproduced {len(results) - len(bad)} of {len(results)} published rows "
      f"from the signal file alone")

print("\n--- does in_sample=False hold up? ---")
for r in results:
    if r["in_sample"] == "False" and r["pct_of_signals_from_2024"] > 5:
        print(f"  {r['version']}/{r['regime']}: stamped in_sample=False but "
              f"{r['pct_of_signals_from_2024']}% of its signals come from the "
              f"2024 block whose cutoff was the year's own {99:.0f}th percentile; "
              f"{r['published_pct']:.3f}% -> {r['no2024_pct']:.3f}% without it")

print("\n--- the equal-footing comparison the README draws ---")
by = {(r["version"], r["regime"]): r for r in results}
for reg in ("webpro", "low60"):
    v3, v7, v8 = by.get(("V03", reg)), by.get(("V07", reg)), by.get(("V08", reg))
    if not (v3 and v7 and v8):
        continue
    print(f"  {reg}:")
    print(f"    as published : V03 {v3['published_pct']:.3f}% (in_sample=False) "
          f"vs V07 {v7['published_pct']:.3f}% / V08 {v8['published_pct']:.3f}% "
          f"(in_sample=True)")
    print(f"    no 2024 block: V03 {v3['no2024_pct']:.3f}% "
          f"vs V07 {v7['no2024_pct']:.3f}% / V08 {v8['no2024_pct']:.3f}%")

out = pathlib.Path("scripts/scratch/_lowzone_leak.json")
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"\nwrote {out}")
print("\nRESULT:", "LEAK CONFIRMED" if (
    all(r["reproduces"] for r in results)
    and any(r["in_sample"] == "False" and r["pct_of_signals_from_2024"] > 5
            for r in results)) else "see numbers above")
