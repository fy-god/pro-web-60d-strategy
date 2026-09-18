"""Quantify the `_seq >= 60` filter: warm-up artefact, or calendar exclusion?

``scan_all.population_baselines`` keeps ``_seq >= 60``; ``backtest_lowzone.main``
keeps every row. On this panel the predicate removes every observation dated
before ~2023-04-04, because 2,853 of 3,193 codes are present on the first session
(2023-01-03) and their 60th bar is 2023-04-04.

For ``low504`` the observation date fixes the forward window's endpoint
(504 sessions later), so which *period* an observation sits in decides whether the
2024 rally is inside its window. This script separates the two candidate
mechanisms directly:

  * calendar exclusion — the filter drops the excluded date window entirely;
  * maturity — a stock's first 60 bars behave differently at the same date.

and standardises the min-history block onto the early block's month mix.

Usage
-----
    $env:PYTHONPATH='.'
    python scripts/scratch/baseline_minhistory_calendar_test.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
SHARD_DIR = REPO / "data" / "shards"
OUT = REPO / "outputs" / "baseline_minhistory_calendar_test.json"

REGIMES = ("webpro", "low60", "low504")
MIN_HISTORY = 60
STRIDE = 5
CUT = pd.Timestamp("2023-04-04")   # the date `_seq >= 60` starts for panel-start codes


def load() -> pd.DataFrame:
    manifest = json.loads((SHARD_DIR / "manifest.json").read_text(encoding="utf-8"))
    cols = ["code", "date"] + [
        f"{c}__{r}" for r in REGIMES for c in ("label_bull", "label_resolved")
    ]
    parts = []
    for entry in manifest["shards"]:
        frame = pd.read_parquet(entry["path"], columns=cols)
        frame = frame.sort_values(["code", "date"], kind="mergesort")
        frame["_seq"] = frame.groupby("code", sort=False).cumcount()
        parts.append(frame)
    out = pd.concat(parts, ignore_index=True)
    out["ym"] = out["date"].dt.to_period("M").astype(str)
    out["pre_cut"] = out["date"] < CUT
    return out


def rate(sub: pd.DataFrame, regime: str) -> tuple[int, int, float]:
    live = sub[sub[f"label_resolved__{regime}"]]
    n = int(len(live))
    if not n:
        return 0, 0, float("nan")
    hits = int(live[f"label_bull__{regime}"].fillna(0).sum())
    return n, hits, hits / n


def prop_z(hits_a: int, n_a: int, hits_b: int, n_b: int) -> float:
    if not n_a or not n_b:
        return float("nan")
    p_a, p_b = hits_a / n_a, hits_b / n_b
    p = (hits_a + hits_b) / (n_a + n_b)
    se = math.sqrt(p * (1 - p) * (1 / n_a + 1 / n_b))
    return (p_a - p_b) / se if se > 0 else float("nan")


def main() -> None:
    frame = load()
    report: dict = {"cut_date": CUT.strftime("%Y-%m-%d"), "regimes": {}}
    lines: list[str] = [
        f"panel {len(frame):,} rows; _seq >= {MIN_HISTORY} begins at {CUT:%Y-%m-%d} "
        f"for the {int(frame[frame['date'] == frame['date'].min()]['code'].nunique())} "
        f"codes present on the first session",
        "",
    ]

    for regime in REGIMES:
        resolved = frame[frame[f"label_resolved__{regime}"]].copy()
        early = resolved[resolved["_seq"] < MIN_HISTORY]
        minh = resolved[resolved["_seq"] >= MIN_HISTORY]

        # Split the early block at the calendar cut so the excluded window is
        # separated from the early-block rows that survive it.
        e_pre = early[early["pre_cut"]]
        e_post = early[~early["pre_cut"]]

        n_ep, h_ep, r_ep = rate(e_pre, regime)
        n_eo, h_eo, r_eo = rate(e_post, regime)
        n_m, h_m, r_m = rate(minh, regime)
        n_a, h_a, r_a = rate(resolved, regime)

        # If the early block's surviving (post-cut) rows match the min-history
        # block, then `_seq >= 60` is a pure calendar exclusion, not maturity.
        z_post = prop_z(h_eo, n_eo, h_m, n_m)

        # Standardise the min-history block onto the early block's month mix,
        # over months both blocks occupy.
        g_m = minh.groupby("ym", sort=True)
        n_by_m = g_m.size()
        h_by_m = g_m[f"label_bull__{regime}"].sum()
        r_by_m = (h_by_m / n_by_m)
        g_e = early.groupby("ym", sort=True)
        n_e_by_m = g_e.size()
        common = n_by_m.index.intersection(n_e_by_m.index)
        if len(common):
            w_e = n_e_by_m[common] / n_e_by_m[common].sum()
            std_m_at_e = float((r_by_m[common] * w_e).sum())
            actual_e_common = float(
                (early[early["ym"].isin(common)]
                 .groupby("ym")[f"label_bull__{regime}"].sum()
                 / early[early["ym"].isin(common)].groupby("ym").size()
                 ).reindex(common).fillna(0.0).mul(w_e).sum()
            )
        else:
            std_m_at_e, actual_e_common = float("nan"), float("nan")

        # Rate the min-history block achieves if the excluded window's own
        # observations are simply put back in (i.e. what the full census does).
        report["regimes"][regime] = {
            "full_census": {"n": n_a, "hits": h_a, "rate": r_a},
            "early_block": {"n": int(len(early)), "hits": int(early[f"label_bull__{regime}"].fillna(0).sum()), "rate": rate(early, regime)[2]},
            "early_pre_cut": {"n": n_ep, "hits": h_ep, "rate": r_ep},
            "early_post_cut": {"n": n_eo, "hits": h_eo, "rate": r_eo},
            "min_history": {"n": n_m, "hits": h_m, "rate": r_m},
            "excluded_window_share_of_early": n_ep / max(len(early), 1),
            "z_early_post_cut_vs_min_history": z_post,
            "min_history_standardised_to_early_month_mix": std_m_at_e,
            "early_actual_over_common_months": actual_e_common,
        }

        lines += [
            f"=== {regime}",
            f"  full census                n={n_a:>9,} rate={r_a*100:8.4f}%",
            f"  early block (seq<60)       n={int(len(early)):>9,} "
            f"rate={rate(early, regime)[2]*100:8.4f}%",
            f"    .. of which pre-cut      n={n_ep:>9,} rate={r_ep*100:8.4f}% "
            f"({n_ep/max(len(early),1)*100:.1f}% of the early block)",
            f"    .. of which post-cut     n={n_eo:>9,} rate={r_eo*100:8.4f}%",
            f"  min-history block          n={n_m:>9,} rate={r_m*100:8.4f}%",
            f"  z(early post-cut vs min-history) = {z_post:+.2f}   "
            f"<- if |z| small, the filter is a CALENDAR exclusion, not maturity",
            f"  min-history reweighted to the early month mix: {std_m_at_e*100:8.4f}% "
            f"(early actual on those months {actual_e_common*100:8.4f}%)",
            "",
        ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n".join(lines))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
