"""Census of the two bar populations both published "base rates" are measured on.

Why this exists
---------------
``reports/lowzone_baselines.json`` and ``reports/webpro_baselines.json`` both
publish a field called ``bull_rate`` for the same three regimes, and the two
numbers disagree (webpro 3.0893% vs 3.0348%, low60 0.0725% vs 0.0752%, low504
4.2099% vs 4.6956%). The disagreement is not a bug in either writer: they
deliberately census different row sets.

  * ``src.backtest_lowzone.main`` reads the **full panel** through
    ``load_layers()`` and censuses every resolved row:  ``candidates``.
  * ``src.scan_all.population_baselines`` censuses the **scanned population**,
    i.e. the rows ``runner.build_scan_targets(stride=5, min_history=60)`` would
    hand to the strategies: ``_seq >= 60 and _seq % 5 == 0``.
    Field name there: ``evaluated_points``.

This script reconstructs both populations *exactly* from the shard label
columns (no panel, no feature columns, no labels recomputed), asserts that the
reconstruction reproduces both published files to the last digit, and then
decomposes the gap so the mechanism is measurable rather than asserted:

  1. full census             = every resolved row of the panel
  2. scanned census          = resolved & _seq >= 60 & _seq % 5 == 0
  3. early census            = resolved & _seq < 60        (min-history tail)
  4. min-history census      = resolved & _seq >= 60       (all residues)
  5. residue table           = min-history census split by _seq % 5
  6. mix standardisation     = is the residue gap composition or within-stratum?

The nested test is subset-vs-complement (the scanned set is a subset of the
full set, so a two-proportion z between them would be invalid): both arms for
the regime's bull label, with the pooled-variance standard error.

Usage
-----
    $env:PYTHONPATH='.'
    python scripts/scratch/baseline_population_census.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
SHARD_DIR = REPO / "data" / "shards"
REPORTS = REPO / "reports"
OUT = REPO / "outputs" / "baseline_population_census.json"

REGIMES = ("webpro", "low60", "low504")
MIN_HISTORY = 60   # == runner.VISIBLE_BARS == scan_all.MIN_HISTORY
STRIDE = 5         # == scan_all --stride default
HORIZONS = {"webpro": 10, "low60": 60, "low504": 504}


def _z_subset(n_sub: int, hits_sub: int, n_rest: int, hits_rest: int) -> tuple[float, float]:
    """Subset-vs-complement z for a nested sample. Returns (z, complement rate)."""
    if not n_sub or not n_rest:
        return float("nan"), float("nan")
    p_sub = hits_sub / n_sub
    p_rest = hits_rest / n_rest
    pooled = (hits_sub + hits_rest) / (n_sub + n_rest)
    se = math.sqrt(pooled * (1.0 - pooled) * (1.0 / n_sub + 1.0 / n_rest))
    return ((p_sub - p_rest) / se if se > 0 else float("nan")), p_rest


def load_census_frame() -> pd.DataFrame:
    """Read only the shard label columns needed, with the scan's own ``_seq``."""
    manifest = json.loads((SHARD_DIR / "manifest.json").read_text(encoding="utf-8"))
    cols = ["code", "date"] + [
        f"{c}__{r}" for r in REGIMES for c in ("label_bull", "label_resolved")
    ]
    parts = []
    for entry in manifest["shards"]:
        frame = pd.read_parquet(entry["path"], columns=cols)
        # The shard is written (code, date)-sorted; cumcount inside a code is
        # then exactly the `_seq` build_scan_targets assigns.
        frame = frame.sort_values(["code", "date"], kind="mergesort")
        frame["_seq"] = frame.groupby("code", sort=False).cumcount()
        parts.append(frame)
    out = pd.concat(parts, ignore_index=True)
    out["ym"] = out["date"].dt.to_period("M").astype(str)
    # Bars still ahead of this bar inside its own stock: reproduces
    # labels.forward_outcomes' future_bars, which is what `resolved` encodes.
    n_bars = out.groupby("code", sort=False)["_seq"].transform("max") + 1
    out["bars_left"] = n_bars - 1 - out["_seq"]
    return out


def _census(sub: pd.DataFrame, label: str, resolved: str) -> dict:
    live = sub[sub[resolved]]
    n = int(len(live))
    hits = int(live[label].fillna(0).sum()) if n else 0
    return {
        "n": n,
        "hits": hits,
        "rate": (hits / n) if n else float("nan"),
        "date_min": (live["date"].min().strftime("%Y-%m-%d") if n else None),
        "date_max": (live["date"].max().strftime("%Y-%m-%d") if n else None),
        "seq_min": (int(live["_seq"].min()) if n else None),
        "seq_max": (int(live["_seq"].max()) if n else None),
    }


def main() -> None:
    frame = load_census_frame()
    print(f"census frame: {len(frame):,} rows, {frame['code'].nunique()} codes", flush=True)

    lz = json.loads((REPORTS / "lowzone_baselines.json").read_text(encoding="utf-8"))
    wp = json.loads((REPORTS / "webpro_baselines.json").read_text(encoding="utf-8"))

    report: dict = {"frame_rows": int(len(frame)), "regimes": {}}
    verdict: list[str] = []

    for regime in REGIMES:
        label, resolved = f"label_bull__{regime}", f"label_resolved__{regime}"
        full = frame
        scanned = frame[(frame["_seq"] >= MIN_HISTORY) & (frame["_seq"] % STRIDE == 0)]
        early = frame[frame["_seq"] < MIN_HISTORY]
        minhist = frame[frame["_seq"] >= MIN_HISTORY]

        c_full = _census(full, label, resolved)
        c_scan = _census(scanned, label, resolved)
        c_early = _census(early, label, resolved)
        c_minh = _census(minhist, label, resolved)

        # Complement of the scanned set inside the full set.
        n_rest = c_full["n"] - c_scan["n"]
        hits_rest = c_full["hits"] - c_scan["hits"]
        z_full, rate_rest = _z_subset(c_scan["n"], c_scan["hits"], n_rest, hits_rest)

        # Residue effect isolated inside the min-history population.
        z_residue, rate_other_res = _z_subset(
            c_scan["n"], c_scan["hits"], c_minh["n"] - c_scan["n"], c_minh["hits"] - c_scan["hits"]
        )

        # min_history effect isolated among residue-0 rows only.
        res0 = frame[frame["_seq"] % STRIDE == 0]
        c_res0 = _census(res0, label, resolved)
        c_res0_early = _census(res0[res0["_seq"] < MIN_HISTORY], label, resolved)
        c_res0_late = _census(res0[res0["_seq"] >= MIN_HISTORY], label, resolved)
        z_mh, rate_res0_rest = _z_subset(
            c_res0_late["n"], c_res0_late["hits"],
            c_res0_early["n"], c_res0_early["hits"],
        )

        residue = {}
        for r in range(STRIDE):
            block = minhist[minhist["_seq"] % STRIDE == r]
            residue[str(r)] = _census(block, label, resolved)

        # Direct standardisation: residue-0 rate reweighted to the rest-of-
        # min-history calendar mix, and vice versa. If the two standardised
        # rates are still apart, the gap is within-stratum (a real selection
        # effect of the residue); if they collapse together, it was calendar mix.
        def _strata(sub: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
            live = sub[sub[resolved]]
            g = live.groupby("ym", sort=False)
            n = g.size()
            h = g[label].sum()
            return n, h, h / n

        n_a, h_a, r_a = _strata(minhist[minhist["_seq"] % STRIDE == 0])
        n_b, h_b, r_b = _strata(minhist[minhist["_seq"] % STRIDE != 0])
        common = n_a.index.intersection(n_b.index)
        w_a, w_b = n_a[common] / n_a[common].sum(), n_b[common] / n_b[common].sum()
        std_a = float((r_a[common] * w_b).sum())   # residue-0 rates, complement's mix
        std_b = float((r_b[common] * w_a).sum())   # complement rates, residue-0's mix

        report["regimes"][regime] = {
            "horizon": HORIZONS[regime],
            "full_census": c_full,
            "scanned_census": c_scan,
            "complement_of_scanned": {"n": n_rest, "hits": hits_rest, "rate": rate_rest},
            "early_seq_lt_60": c_early,
            "min_history_seq_ge_60": c_minh,
            "residue_0_all_seq": c_res0,
            "residue_0_early": c_res0_early,
            "residue_0_min_history": c_res0_late,
            "residue_table_min_history": residue,
            "z_scanned_vs_complement": z_full,
            "z_residue0_vs_other_residues_in_min_history": z_residue,
            "z_min_history_vs_early_within_residue0": z_mh,
            "standardised_residue0_at_complement_mix": std_a,
            "standardised_complement_at_residue0_mix": std_b,
            "published_lowzone": {
                "candidates": lz.get(regime, {}).get("candidates"),
                "bull_rate": lz.get(regime, {}).get("bull_rate"),
            },
            "published_webpro": {
                "evaluated_points": wp.get(regime, {}).get("evaluated_points"),
                "bull_rate": wp.get(regime, {}).get("bull_rate"),
            },
        }

        ok_full = (
            c_full["n"] == lz[regime]["candidates"]
            and abs(c_full["rate"] - lz[regime]["bull_rate"]) < 1e-12
        )
        ok_scan = (
            c_scan["n"] == wp[regime]["evaluated_points"]
            and abs(c_scan["rate"] - wp[regime]["bull_rate"]) < 1e-12
        )
        verdict.append(
            f"{regime:7s} full {c_full['n']:>9,} @ {c_full['rate']:.10f} "
            f"{'== lowzone_baselines OK' if ok_full else '!= lowzone_baselines MISMATCH'}"
        )
        verdict.append(
            f"{regime:7s} scan {c_scan['n']:>9,} @ {c_scan['rate']:.10f} "
            f"{'== webpro_baselines OK' if ok_scan else '!= webpro_baselines MISMATCH'}"
        )
        verdict.append(
            f"{regime:7s} complement {n_rest:>9,} @ {rate_rest:.10f} | "
            f"z(scanned vs complement) = {z_full:+.2f}"
        )
        verdict.append(
            f"{regime:7s} seq<60 {c_early['n']:>9,} @ {c_early['rate']:.10f} | "
            f"seq>=60 {c_minh['n']:>9,} @ {c_minh['rate']:.10f} | "
            f"z(min-history vs early, residue 0 only) = {z_mh:+.2f}"
        )
        verdict.append(
            f"{regime:7s} residue 0 {c_scan['n']:>9,} @ {c_scan['rate']:.10f} vs "
            f"residues 1-4 {c_minh['n'] - c_scan['n']:>9,} @ {rate_other_res:.10f} | "
            f"z = {z_residue:+.2f}"
        )
        rates = {k: v["rate"] for k, v in residue.items()}
        verdict.append(
            f"{regime:7s} residues 0-4 within seq>=60: "
            + "  ".join(f"{k}:{v*100:.4f}%" for k, v in rates.items())
        )
        verdict.append(
            f"{regime:7s} standardised: residue0@complement-mix {std_a*100:.4f}% "
            f"vs complement@residue0-mix {std_b*100:.4f}%"
        )
        verdict.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n".join(verdict))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
