"""The definitive test of the two published base rates.

``report_integrity_extra.check_baseline_agreement`` reports z = +11.50 for
``low504`` and calls the gap "NOT explainable by sampling noise". That verdict
rests on a two-proportion z that treats every resolved row as an independent
Bernoulli trial. This script re-tests the same contrast three ways that respect
the panel's actual dependence structure, and then isolates *which* filter is
responsible for the gap.

The contrast the audit tests is

    scanned   = rows with _seq >= 60 AND _seq % 5 == 0
    complement = every other resolved row

so it bundles two different filters together. They are separated here.

Three variance estimators for the same estimand (p_scanned - p_complement):

  row      — independent rows (what the audit uses)
  cluster  — clusters are market dates; a date's influence enters both arms, so
             the contrast variance is v_a + v_b - 2*cov_ab, not v_a + v_b
  bootstrap— block bootstrap resampling whole market dates, which makes no
             parametric assumption about the within-date correlation

Plus an assumption-light test: the scan picks residue class 0 of 5. If the
residue class carries no information, the five classes are exchangeable, so
residue 0's rank among the five is a distribution-free check on the selection.

Usage
-----
    $env:PYTHONPATH='.'
    python scripts/scratch/baseline_contrast_test.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
SHARD_DIR = REPO / "data" / "shards"
OUT = REPO / "outputs" / "baseline_contrast_test.json"

REGIMES = ("webpro", "low60", "low504")
MIN_HISTORY = 60
STRIDE = 5
CUT = pd.Timestamp("2023-04-04")
N_BOOT = 4000
SEED = 20260918


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


def by_date(frame: pd.DataFrame, regime: str) -> pd.DataFrame:
    """Collapse a row set to one (n, hits) pair per market date."""
    label, resolved = f"label_bull__{regime}", f"label_resolved__{regime}"
    live = frame[frame[resolved]]
    if live.empty:
        return pd.DataFrame(columns=["date", "n", "hits"])
    g = live.groupby("date", sort=True)
    out = pd.DataFrame({"n": g.size().astype("float64"),
                        "hits": g[label].sum().astype("float64")})
    return out.reset_index()


def _variance_terms(da: pd.DataFrame, db: pd.DataFrame,
                    p_a: float, p_b: float) -> tuple[float, float, float]:
    """v_a, v_b, cov for p_a = sum(hits_a)/sum(n_a) with dates as clusters."""
    n_a, n_b = da["n"].sum(), db["n"].sum()
    ra = (da["hits"] - p_a * da["n"]).to_numpy() / n_a
    rb = (db["hits"] - p_b * db["n"]).to_numpy() / n_b
    ia = dict(zip(da["date"], ra))
    ib = dict(zip(db["date"], rb))
    shared = sorted(set(ia) & set(ib))
    v_a = float((ra ** 2).sum())
    v_b = float((rb ** 2).sum())
    cov = float(sum(ia[d] * ib[d] for d in shared))
    return v_a, v_b, cov


def date_block_bootstrap(da: pd.DataFrame, db: pd.DataFrame, rng: np.random.Generator,
                         n_boot: int = N_BOOT) -> dict:
    """Resample whole market dates and recompute the contrast.

    Dates are drawn once per replicate and applied to both arms, which preserves
    both the within-date correlation and the across-arm correlation.
    """
    all_dates = sorted(set(da["date"]) | set(db["date"]))
    idx = {d: i for i, d in enumerate(all_dates)}
    n_all = len(all_dates)

    def stack(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        n = np.zeros(n_all)
        h = np.zeros(n_all)
        pos = df["date"].map(idx).to_numpy()
        np.add.at(n, pos, df["n"].to_numpy())
        np.add.at(h, pos, df["hits"].to_numpy())
        return n, h

    n_a, h_a = stack(da)
    n_b, h_b = stack(db)
    diffs = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, n_all, n_all)
        sa, sb = n_a[pick].sum(), n_b[pick].sum()
        if sa <= 0 or sb <= 0:
            diffs[b] = np.nan
            continue
        diffs[b] = h_a[pick].sum() / sa - h_b[pick].sum() / sb
    diffs = diffs[np.isfinite(diffs)]
    return {
        "n_boot": int(len(diffs)),
        "sd": float(diffs.std(ddof=1)),
        "p_two_sided": float(2 * min((diffs <= 0).mean(), (diffs >= 0).mean())),
        "ci95": [float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))],
    }


def contrast(name: str, a: pd.DataFrame, b: pd.DataFrame, regime: str,
             rng: np.random.Generator) -> dict:
    da, db = by_date(a, regime), by_date(b, regime)
    if da.empty or db.empty:
        return {"name": name, "skipped": True}
    n_a, n_b = float(da["n"].sum()), float(db["n"].sum())
    p_a, p_b = float(da["hits"].sum()) / n_a, float(db["hits"].sum()) / n_b
    diff = p_a - p_b

    # row-level (the audit's estimator)
    p_pool = (da["hits"].sum() + db["hits"].sum()) / (n_a + n_b)
    se_row = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))

    v_a, v_b, cov = _variance_terms(da, db, p_a, p_b)
    se_cluster = math.sqrt(max(v_a + v_b - 2 * cov, 0.0))
    boot = date_block_bootstrap(da, db, rng)

    return {
        "name": name,
        "n_a": int(n_a), "n_b": int(n_b),
        "rate_a": p_a, "rate_b": p_b, "diff_pp": 100 * diff,
        "dates_a": int(len(da)), "dates_b": int(len(db)),
        "z_row": diff / se_row if se_row > 0 else float("nan"),
        "z_cluster": diff / se_cluster if se_cluster > 0 else float("nan"),
        "se_row": se_row, "se_cluster": se_cluster,
        "cov_vs_va_plus_vb": 2 * cov / (v_a + v_b) if (v_a + v_b) else float("nan"),
        "bootstrap": boot,
        "z_bootstrap": diff / boot["sd"] if boot["sd"] > 0 else float("nan"),
    }


def main() -> None:
    frame = load()
    rng = np.random.default_rng(SEED)
    report: dict = {"seed": SEED, "n_boot": N_BOOT, "regimes": {}}
    lines: list[str] = []

    for regime in REGIMES:
        resolved = frame[frame[f"label_resolved__{regime}"]].copy()
        minhist = resolved[resolved["_seq"] >= MIN_HISTORY]
        early = resolved[resolved["_seq"] < MIN_HISTORY]
        scanned = minhist[minhist["_seq"] % STRIDE == 0]
        complement = resolved.drop(scanned.index)
        not_scanned = minhist[minhist["_seq"] % STRIDE != 0]

        c_pub = contrast("scanned vs complement (the published test)",
                         scanned, complement, regime, rng)
        c_stride = contrast("stride alone, within _seq >= 60", scanned, not_scanned,
                            regime, rng)
        c_mh = contrast("min_history alone, all residues", minhist, early, regime, rng)

        # Residual-class exchangeability: every residue is a legal scan grid.
        res_rows = []
        for r in range(STRIDE):
            sub = minhist[minhist["_seq"] % STRIDE == r]
            live = sub[sub[f"label_resolved__{regime}"]]
            n = int(len(live))
            hits = int(live[f"label_bull__{regime}"].fillna(0).sum())
            res_rows.append({"residue": r, "n": n, "hits": hits,
                             "rate": hits / n if n else float("nan")})
        rates = np.array([r["rate"] for r in res_rows])
        report["regimes"][regime] = {
            "residues": res_rows,
            "residue_min": float(rates.min()), "residue_max": float(rates.max()),
            "residue_0_rate": res_rows[0]["rate"],
            "residue_0_rank_ascending": int((rates < res_rows[0]["rate"]).sum()) + 1,
            "residue_spread_pp": 100 * float(rates.max() - rates.min()),
            "published_contrast": c_pub,
            "stride_only_contrast": c_stride,
            "min_history_only_contrast": c_mh,
            # Structural invariant: min_history implies the calendar cut.
            "rows_seq_ge_60_and_date_lt_cut": int(
                (minhist["date"] < CUT).sum()),
        }

        lines += [
            f"=== {regime}",
            f"  residue classes within _seq >= 60 (the 5 legal scan grids):",
            "    " + "  ".join(f"r{r['residue']}={r['rate']*100:7.4f}% (n={r['n']:,})"
                              for r in res_rows),
            f"    spread {100*(rates.max()-rates.min()):.4f} pp; residue 0 (the one the "
            f"scan uses) ranks {int((rates < res_rows[0]['rate']).sum())+1} of 5 ascending",
            f"  min_history implies the calendar cut: rows with _seq >= 60 and "
            f"date < {CUT:%Y-%m-%d} = {int((minhist['date'] < CUT).sum())}",
            "",
        ]
        for c in (c_pub, c_stride, c_mh):
            if c.get("skipped"):
                continue
            lines += [
                f"  -- {c['name']}",
                f"     {c['rate_a']*100:8.4f}% (n={c['n_a']:,}, {c['dates_a']} dates) vs "
                f"{c['rate_b']*100:8.4f}% (n={c['n_b']:,}, {c['dates_b']} dates)",
                f"     diff {c['diff_pp']:+.4f} pp",
                f"     z row-level    {c['z_row']:+8.2f}   (audit's estimator)",
                f"     z cluster      {c['z_cluster']:+8.2f}   "
                f"(SE {c['se_cluster']:.3e} vs row SE {c['se_row']:.3e})",
                f"     z bootstrap    {c['z_bootstrap']:+8.2f}   "
                f"95% CI [{c['bootstrap']['ci95'][0]*100:+.4f}, "
                f"{c['bootstrap']['ci95'][1]*100:+.4f}] pp, "
                f"p={c['bootstrap']['p_two_sided']:.3f}",
                "",
            ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n".join(lines))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
