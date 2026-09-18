"""Is `_seq >= 60` a maturity filter or a calendar filter, and is z=+11.50 real?

Three questions, all answered from the shard label columns alone.

Q1. ``runner.build_scan_targets`` keeps ``_seq >= min_history``, where ``_seq`` is
    a per-stock bar index. On a panel that starts 2023-01-03 with 2,853 of 3,193
    codes present on the first session, that predicate may *also* be a calendar
    cut. The test replaces it with a pure date predicate and measures how far the
    two row sets differ.

Q2. Decompose the gap between the two published populations into its two causes:
    the ``min_history`` filter and the ``stride`` sampling.

Q3. ``report_integrity_extra.check_baseline_agreement`` tests the scanned set
    against its complement with a two-proportion z that treats rows as
    independent. Rows are not independent: on any one market date the bull event
    is heavily cross-sectional, and forward windows of neighbouring dates overlap
    almost entirely. Q3 reports two corrected statistics alongside the row-level
    one:

      * cluster-robust  — same estimand (the marginal rate difference), standard
        error summed over market dates instead of over rows;
      * date-equal-weight — each market date contributes one rate, so dates count
        once regardless of how many rows they carry.

Usage
-----
    $env:PYTHONPATH='.'
    python scripts/scratch/baseline_effective_sample.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
SHARD_DIR = REPO / "data" / "shards"
OUT = REPO / "outputs" / "baseline_effective_sample.json"

REGIMES = ("webpro", "low60", "low504")
MIN_HISTORY = 60
STRIDE = 5
CUT = pd.Timestamp("2023-04-04")


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
    return pd.concat(parts, ignore_index=True)


def census(sub: pd.DataFrame, regime: str) -> dict:
    live = sub[sub[f"label_resolved__{regime}"]]
    n = int(len(live))
    if not n:
        return {"n": 0, "hits": 0, "rate": float("nan")}
    hits = int(live[f"label_bull__{regime}"].fillna(0).sum())
    return {"n": n, "hits": hits, "rate": hits / n}


def row_z(a: dict, b: dict) -> float:
    """The published test: rows treated as independent Bernoulli draws."""
    if not a["n"] or not b["n"]:
        return float("nan")
    p = (a["hits"] + b["hits"]) / (a["n"] + b["n"])
    se = math.sqrt(p * (1 - p) * (1 / a["n"] + 1 / b["n"]))
    return (a["rate"] - b["rate"]) / se if se > 0 else float("nan")


def _arm(frame: pd.DataFrame, regime: str) -> tuple[float, float, int]:
    """(rate, cluster-robust variance of the rate, n) with clusters = dates."""
    label, resolved = f"label_bull__{regime}", f"label_resolved__{regime}"
    live = frame[frame[resolved]]
    if live.empty:
        return float("nan"), float("nan"), 0
    g = live.groupby("date", sort=True)
    n_d = g.size().to_numpy("float64")
    h_d = g[label].sum().to_numpy("float64")
    n = float(n_d.sum())
    p = float(h_d.sum()) / n
    resid = h_d - p * n_d                      # date-level influence contributions
    return p, float((resid ** 2).sum()) / (n ** 2), int(n)


def cluster_z(a: pd.DataFrame, b: pd.DataFrame, regime: str) -> float:
    """Same estimand as row_z, standard error summed over dates not rows."""
    p_a, v_a, n_a = _arm(a, regime)
    p_b, v_b, n_b = _arm(b, regime)
    if not n_a or not n_b:
        return float("nan")
    se = math.sqrt(v_a + v_b)
    return (p_a - p_b) / se if se > 0 else float("nan")


def date_equal_weight_z(a: pd.DataFrame, b: pd.DataFrame, regime: str) -> dict:
    """Each market date contributes one rate; dates present in both arms only."""
    label, resolved = f"label_bull__{regime}", f"label_resolved__{regime}"

    def per_date(frame: pd.DataFrame) -> pd.DataFrame:
        live = frame[frame[resolved]]
        if live.empty:
            return pd.DataFrame(columns=["date", "n", "rate"])
        g = live.groupby("date", sort=True)
        out = pd.DataFrame({"n": g.size(), "hits": g[label].sum()})
        out["rate"] = out["hits"] / out["n"]
        return out.reset_index()

    da, db = per_date(a), per_date(b)
    if da.empty or db.empty:
        return {"z": float("nan"), "dates": 0}
    common = da["date"].isin(set(db["date"])) & db["date"].isin(set(da["date"]))
    # Align on the shared calendar so the comparison is like-for-like.
    shared = sorted(set(da["date"]) & set(db["date"]))
    da = da[da["date"].isin(shared)]
    db = db[db["date"].isin(shared)]
    del common
    ma, mb = float(da["rate"].mean()), float(db["rate"].mean())
    va = float(da["rate"].var(ddof=1)) / len(da)
    vb = float(db["rate"].var(ddof=1)) / len(db)
    se = math.sqrt(va + vb)
    return {
        "z": (ma - mb) / se if se > 0 else float("nan"),
        "rate_a": ma, "rate_b": mb, "dates": len(shared), "se": se,
    }


def contrast(name: str, a: pd.DataFrame, b: pd.DataFrame, regime: str) -> dict:
    ca, cb = census(a, regime), census(b, regime)
    dz = date_equal_weight_z(a, b, regime)
    rz = row_z(ca, cb)
    cz = cluster_z(a, b, regime)
    return {
        "name": name,
        "a": ca, "b": cb,
        "z_row_level": rz,
        "z_cluster_robust": cz,
        "z_date_equal_weight": dz["z"],
        "shared_dates": dz.get("dates"),
        "rate_a_date_equal_weight": dz.get("rate_a"),
        "rate_b_date_equal_weight": dz.get("rate_b"),
        "row_z_inflation_vs_cluster": abs(rz / cz) if cz and cz == cz else None,
    }


def main() -> None:
    frame = load()
    report: dict = {"cut_date": CUT.strftime("%Y-%m-%d"), "regimes": {}}
    lines = [f"panel {len(frame):,} rows, {frame['code'].nunique()} codes", ""]

    for regime in REGIMES:
        resolved = frame[frame[f"label_resolved__{regime}"]].copy()
        by_seq = resolved[resolved["_seq"] >= MIN_HISTORY]
        by_date = resolved[resolved["date"] >= CUT]
        early = resolved[resolved["_seq"] < MIN_HISTORY]
        scanned = by_seq[by_seq["_seq"] % STRIDE == 0]
        not_scanned = by_seq[by_seq["_seq"] % STRIDE != 0]

        c_full = census(resolved, regime)
        c_seq = census(by_seq, regime)
        c_date = census(by_date, regime)
        # Rows the seq predicate keeps but the date predicate does not.
        seq_only = census(by_seq[by_seq["date"] < CUT], regime)
        date_only = census(resolved[(resolved["_seq"] < MIN_HISTORY)
                                    & (resolved["date"] >= CUT)], regime)

        published = contrast("scanned vs its complement (the published test)",
                             scanned, resolved.drop(scanned.index), regime)
        stride_only = contrast("scanned vs non-scanned, both _seq >= 60 (stride alone)",
                               scanned, not_scanned, regime)
        calendar_only = contrast("_seq >= 60 vs _seq < 60 (min_history alone)",
                                 by_seq, early, regime)

        report["regimes"][regime] = {
            "full_census": c_full,
            "seq_ge_60": c_seq,
            "date_ge_cut": c_date,
            "seq_keeps_but_date_excludes": seq_only,
            "date_keeps_but_seq_excludes": date_only,
            "seq_predicate_is_subset_of_date_predicate": seq_only["n"] == 0,
            "contrasts": {c["name"]: c for c in (published, stride_only, calendar_only)},
        }

        lines += [
            f"=== {regime}",
            f"  full census                       n={c_full['n']:>9,} rate={c_full['rate']*100:8.4f}%",
            f"  _seq >= {MIN_HISTORY}                     n={c_seq['n']:>9,} rate={c_seq['rate']*100:8.4f}%",
            f"  date >= {CUT:%Y-%m-%d}              n={c_date['n']:>9,} rate={c_date['rate']*100:8.4f}%",
            f"  _seq>=60 but date<cut            n={seq_only['n']:>9,}  "
            f"<- 0 proves min_history implies the calendar cut",
            f"  date>=cut but _seq<60            n={date_only['n']:>9,} rate={date_only['rate']*100:8.4f}% "
            f"(late listings' first 60 bars)",
            "",
        ]
        for c in (published, stride_only, calendar_only):
            lines += [
                f"  -- {c['name']}",
                f"     rates {c['a']['rate']*100:8.4f}% (n={c['a']['n']:,}) vs "
                f"{c['b']['rate']*100:8.4f}% (n={c['b']['n']:,})  "
                f"diff {(c['a']['rate']-c['b']['rate'])*100:+.4f} pp",
                f"     z row-level        {c['z_row_level']:+8.2f}",
                f"     z cluster-robust   {c['z_cluster_robust']:+8.2f}   "
                f"(same estimand, SE over dates)",
                f"     z date-equal-weight{c['z_date_equal_weight']:+8.2f}   "
                f"({c['shared_dates']} shared dates)",
                f"     row z inflates by  "
                f"{c['row_z_inflation_vs_cluster']:.1f}x"
                if c["row_z_inflation_vs_cluster"] else "     row z inflates by  n/a",
                "",
            ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n".join(lines))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
