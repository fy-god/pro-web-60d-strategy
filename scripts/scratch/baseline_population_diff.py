"""Decompose the min_history vs stride effect on the published base rates.

``src.scan_all.population_baselines`` filters ``_seq >= 60 and _seq % 5 == 0``;
``src.backtest_lowzone.main`` filters nothing. ``_seq`` is a per-stock bar index,
but this panel begins on 2023-01-03 with almost every code present from the first
session, so ``_seq >= 60`` is *also* a calendar filter that drops every
observation dated before roughly 2023-04-04. For the 504-session regime the
observation date fixes the forward window's endpoint, so that is a substantive
population difference, not a warm-up artefact.

This script measures, per regime: the observation-month composition of the
early (``_seq < 60``) and min-history (``_seq >= 60``) blocks, the rate by
observation year, and the counterfactual base rates with each filter applied
alone and together.

Usage
-----
    $env:PYTHONPATH='.'
    python scripts/scratch/baseline_population_diff.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
SHARD_DIR = REPO / "data" / "shards"
OUT = REPO / "outputs" / "baseline_population_diff.json"

REGIMES = ("webpro", "low60", "low504")
MIN_HISTORY = 60
STRIDE = 5


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
    out["year"] = out["date"].dt.year
    out["ym"] = out["date"].dt.to_period("M").astype(str)
    return out


def rate(sub: pd.DataFrame, regime: str) -> tuple[int, int, float]:
    live = sub[sub[f"label_resolved__{regime}"]]
    n = int(len(live))
    if not n:
        return 0, 0, float("nan")
    hits = int(live[f"label_bull__{regime}"].fillna(0).sum())
    return n, hits, hits / n


def main() -> None:
    frame = load()
    report: dict = {
        "frame_rows": int(len(frame)),
        "codes": int(frame["code"].nunique()),
        "date_min": frame["date"].min().strftime("%Y-%m-%d"),
        "date_max": frame["date"].max().strftime("%Y-%m-%d"),
        "codes_present_on_first_date": int(
            frame[frame["date"] == frame["date"].min()]["code"].nunique()
        ),
        # How many codes have at least MIN_HISTORY bars: if that is ~all of them,
        # the filter cannot be a listing-age warm-up.
        "codes_with_ge_60_bars": int(
            (frame.groupby("code", sort=False).size() >= MIN_HISTORY).sum()
        ),
        "regimes": {},
    }
    lines: list[str] = [
        f"panel {len(frame):,} rows, {frame['code'].nunique()} codes, "
        f"{report['date_min']} .. {report['date_max']}",
        f"codes present on the first session: "
        f"{report['codes_present_on_first_date']} / {frame['code'].nunique()}",
        f"codes with >= {MIN_HISTORY} bars: {report['codes_with_ge_60_bars']}",
        "",
    ]

    for regime in REGIMES:
        resolved = frame[frame[f"label_resolved__{regime}"]]
        early = resolved[resolved["_seq"] < MIN_HISTORY]
        minh = resolved[resolved["_seq"] >= MIN_HISTORY]

        # Calendar span of each block, and how much of each falls in 2023Q1.
        span = {
            "early": {
                "n": int(len(early)),
                "date_min": early["date"].min().strftime("%Y-%m-%d"),
                "date_max": early["date"].max().strftime("%Y-%m-%d"),
                "share_before_2023_04_04": float(
                    (early["date"] < pd.Timestamp("2023-04-04")).mean()
                ) if len(early) else None,
            },
            "min_history": {
                "n": int(len(minh)),
                "date_min": minh["date"].min().strftime("%Y-%m-%d"),
                "date_max": minh["date"].max().strftime("%Y-%m-%d"),
                "share_before_2023_04_04": float(
                    (minh["date"] < pd.Timestamp("2023-04-04")).mean()
                ) if len(minh) else None,
            },
        }

        by_year = {}
        for year, block in resolved.groupby("year", sort=True):
            n, hits, r = rate(block, regime)
            e = block[block["_seq"] < MIN_HISTORY]
            m = block[block["_seq"] >= MIN_HISTORY]
            by_year[str(int(year))] = {
                "n": n, "hits": hits, "rate": r,
                "n_early": int(len(e[e[f"label_resolved__{regime}"]])) if len(e) else 0,
                "n_min_history": int(len(m[m[f"label_resolved__{regime}"]])) if len(m) else 0,
            }

        # Counterfactual populations: each filter alone, both, neither.
        variants = {
            "neither_filter (lowzone_baselines)": resolved,
            "min_history_only": resolved[resolved["_seq"] >= MIN_HISTORY],
            "stride_only": resolved[resolved["_seq"] % STRIDE == 0],
            "min_history_and_stride (webpro_baselines)": resolved[
                (resolved["_seq"] >= MIN_HISTORY) & (resolved["_seq"] % STRIDE == 0)
            ],
        }
        variant_rates = {}
        for name, sub in variants.items():
            n, hits, r = rate(sub, regime)
            variant_rates[name] = {"n": n, "hits": hits, "rate": r}

        # Effects, holding the other filter fixed.
        base = variant_rates["neither_filter (lowzone_baselines)"]["rate"]
        mh_only = variant_rates["min_history_only"]["rate"]
        st_only = variant_rates["stride_only"]["rate"]
        both = variant_rates["min_history_and_stride (webpro_baselines)"]["rate"]

        report["regimes"][regime] = {
            "span": span,
            "by_year": by_year,
            "variants": variant_rates,
            "effect_min_history_alone_pp": (mh_only - base) * 100,
            "effect_stride_alone_pp": (st_only - base) * 100,
            "effect_stride_within_min_history_pp": (both - mh_only) * 100,
            "effect_total_pp": (both - base) * 100,
        }

        lines += [
            f"=== {regime}",
            f"  early  (seq<60) : n={span['early']['n']:>9,} "
            f"{span['early']['date_min']} .. {span['early']['date_max']} "
            f"({span['early']['share_before_2023_04_04']*100:.1f}% before 2023-04-04)",
            f"  minhist(seq>=60): n={span['min_history']['n']:>9,} "
            f"{span['min_history']['date_min']} .. {span['min_history']['date_max']} "
            f"({span['min_history']['share_before_2023_04_04']*100:.1f}% before 2023-04-04)",
            f"  by observation year:",
        ]
        for year, d in by_year.items():
            lines.append(
                f"    {year}: n={d['n']:>9,} rate={d['rate']*100:8.4f}%  "
                f"(early {d['n_early']:>7,} / minhist {d['n_min_history']:>9,})"
            )
        lines += [
            f"  counterfactual populations:",
        ]
        for name, d in variant_rates.items():
            lines.append(f"    {name:42s} n={d['n']:>9,} rate={d['rate']*100:8.4f}%")
        lines += [
            f"  effect of min_history alone        : "
            f"{report['regimes'][regime]['effect_min_history_alone_pp']:+.4f} pp",
            f"  effect of stride alone             : "
            f"{report['regimes'][regime]['effect_stride_alone_pp']:+.4f} pp",
            f"  effect of stride within min_history: "
            f"{report['regimes'][regime]['effect_stride_within_min_history_pp']:+.4f} pp",
            f"  total (webpro - lowzone)           : "
            f"{report['regimes'][regime]['effect_total_pp']:+.4f} pp",
            "",
        ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n".join(lines))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
