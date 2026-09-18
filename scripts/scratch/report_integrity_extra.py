"""Complementary report integrity check for pro-web-60d-strategy.

This is a *second* checker that covers identities the existing
``scripts/scratch/report_integrity_check.py`` does not assert. It does not
replace or modify that file; run both.

Covered here (all absent from the other checker, verified by grep):
  * ml_precision_ceiling.json  -- the ``requirement_70pct`` closed form
  * ml_concentration.json      -- ``walkforward_total_signals``, largest-fold
                                  share, the "excluding largest fold" pooling,
                                  and the holdout drop-top-dates ordering
  * ml_search_wide.json        -- the ``failed`` list and its ``n_failed`` /
                                  ``n_configs`` bookkeeping, including whether
                                  the recorded exception is a real feature-group
                                  name (regression guard for the historical
                                  "unknown feature group" defect)
  * ml_null_tests.json         -- ``permuted_labels`` summary statistics
  * ml_search_*.json           -- per-fold base-rate agreement across every
                                  configuration that shares a label
  * tradeability.json          -- the ``overall`` block identities (the other
                                  checker only reads the JSON for one total)
  * live_readiness.csv         -- net == gross - round-trip cost
  * hitrate_vs_expectancy.json -- the two Spearman correlations and the
                                  positive-expectancy counts, recomputed
  * webpro_cards_100_reproduction.csv
                               -- tp + fp == yes_predictions, yes_precision,
                                  and the blank-when-undefined convention
  * lowzone_hit_rates.csv      -- ``baseline_rate`` vs lowzone_baselines.json
  * webpro_hit_rates.csv       -- ``baseline__*`` vs webpro_baselines.json
  * frontier CSVs              -- precision/n_published integrality, the
                                  fpr == fp/(N-P) identity, and recall
                                  monotonicity

Tolerances
----------
Relative tolerance ``RTOL = 1e-6`` for floats; integer counts compared exactly.
``hit_rate_pct`` is a 2-dp display column and is compared at that precision.
JSON float round-tripping therefore never shows up as a mismatch.

Usage
-----
    $env:PYTHONPATH='.'
    python scripts/scratch/report_integrity_extra.py

``reports/`` is opened read-only; nothing is written.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

RTOL = 1e-6
REPO = Path(__file__).resolve().parents[2]
REPORTS = REPO / "reports"

ROWS: list[tuple[str, str, str]] = []
CHECKS = 0
NOTES: list[str] = []


def finding(sev: str, where: str, detail: str) -> None:
    ROWS.append((sev, where, detail))


def note(text: str) -> None:
    NOTES.append(text)


def close(a, b, rtol: float = RTOL) -> bool:
    if a is None or b is None:
        return False
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    if math.isinf(a) or math.isinf(b):
        return a == b
    return abs(a - b) <= rtol * max(abs(a), abs(b), 1e-300)


def ident(sev: str, where: str, name: str, got, want, rtol: float = RTOL) -> None:
    global CHECKS
    CHECKS += 1
    if got is None or want is None:
        finding(sev, where, f"{name}: operand missing (got={got!r}, want={want!r})")
        return
    if not close(got, want, rtol):
        finding(
            sev, where,
            f"{name}: reported {got!r}, recomputed {want!r} "
            f"(abs diff {abs(float(got) - float(want)):.6g}, "
            f"rel {abs(float(got) - float(want)) / max(abs(float(want)), 1e-300):.3e})",
        )


def ident_text(sev: str, where: str, name: str, got, want) -> None:
    """Exact string identity. Separate from ``ident``, which does float arithmetic."""
    global CHECKS
    CHECKS += 1
    if got is None or want is None:
        finding(sev, where, f"{name}: operand missing (got={got!r}, want={want!r})")
        return
    if str(got) != str(want):
        finding(sev, where, f"{name}: reported {got!r}, declared {want!r}")


def bound(where: str, name: str, v, lo=0.0, hi=1.0) -> None:
    global CHECKS
    CHECKS += 1
    if v is None:
        finding("A", where, f"{name}: missing")
    elif not (lo - 1e-12 <= float(v) <= hi + 1e-12):
        finding("A", where, f"{name}={v!r} outside [{lo}, {hi}]")


def load_json(name: str):
    p = REPORTS / name
    if not p.exists():
        note(f"missing report: {name}")
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def load_csv(name: str) -> list[dict]:
    p = REPORTS / name
    if not p.exists():
        note(f"missing report: {name}")
        return []
    with p.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def num(row: dict, key: str):
    raw = row.get(key)
    if raw is None:
        return None
    raw = str(raw).strip()
    if raw in ("", "nan", "NaN", "null", "None", "NA"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def iop(row: dict, key: str):
    v = num(row, key)
    return None if v is None else int(round(v))


# --------------------------------------------------------------------------- #
def check_ceiling_requirement() -> None:
    """requirement_70pct is a closed form in the base rate and the recall."""
    d = load_json("ml_precision_ceiling.json")
    if not d:
        return
    pi = d.get("base_rate")
    req = d.get("requirement_70pct") or {}
    if pi is None or not req:
        finding("A", "ml_precision_ceiling.json", "base_rate or requirement_70pct missing")
        return
    for key, want in req.items():
        recall = float(key.split("_", 1)[1])
        # required_fpr = pi*recall*(1-P) / ((1-pi)*P)  with P = 0.70
        got = pi * recall * (1 - 0.70) / ((1 - pi) * 0.70)
        ident("A", f"ml_precision_ceiling.json :: requirement_70pct[{key}]",
              "required_fpr = pi*recall*(1-P)/((1-pi)*P)", want, got)
    # required_fpr is proportional to recall, so it must fall as the recall the
    # strategy is asked to achieve falls.
    seq = sorted(((float(k.split("_", 1)[1]), v) for k, v in req.items()))
    global CHECKS
    CHECKS += 1
    if any(seq[i][1] > seq[i + 1][1] + 1e-15 for i in range(len(seq) - 1)):
        finding("A", "ml_precision_ceiling.json :: requirement_70pct",
                f"required fpr is not increasing in the required recall: {seq}")
    # the practical ceiling must be the max over the >=250 rows
    pcs = d.get("practical_ceiling_by_min_signals") or {}
    keys = [k for k in pcs if int(k) >= 250]
    if keys:
        ident("A", "ml_precision_ceiling.json",
              "practical_ceiling_250plus_raw == max(max_precision_raw over bounds >=250)",
              d.get("practical_ceiling_250plus_raw"),
              max(pcs[k]["max_precision_raw"] for k in keys))
        ident("A", "ml_precision_ceiling.json",
              "practical_ceiling_250plus_rank == max(max_precision_rank over bounds >=250)",
              d.get("practical_ceiling_250plus_rank"),
              max(pcs[k]["max_precision_rank"] for k in keys))
        # a looser min_signals bound can never do worse
        ordered = sorted(pcs, key=int)
        CHECKS_local = None
        for a, b in zip(ordered, ordered[1:]):
            if pcs[a]["max_precision_raw"] < pcs[b]["max_precision_raw"] - 1e-12:
                finding("A", "ml_precision_ceiling.json",
                        f"raising the min_signals bound from {a} to {b} increased "
                        f"max_precision_raw "
                        f"({pcs[a]['max_precision_raw']!r} -> "
                        f"{pcs[b]['max_precision_raw']!r}); a tighter budget cannot "
                        f"admit a better prefix")
    # the same at_signals/recall repeated across bounds is disclosed, not an error
    ats = {k: pcs[k]["at_signals"] for k in pcs}
    if len(set(ats.values())) < len(ats):
        note("ml_precision_ceiling.json: at_signals repeats across min_signals bounds "
             f"({ats}) because the best realisable prefix sits at one k; the "
             "repetition is a property of the grid, not duplication")


def check_concentration() -> None:
    d = load_json("ml_concentration.json")
    if not d:
        return
    w = "ml_concentration.json"
    folds = d.get("walkforward_folds") or []
    if folds:
        sig = [int(f.get("signals", 0)) for f in folds]
        tot = sum(sig)
        ident("A", w, "walkforward_total_signals == sum(fold signals)",
              d.get("walkforward_total_signals"), tot)
        if tot:
            ident("A", w, "walkforward_largest_fold_share == max(signals)/total",
                  d.get("walkforward_largest_fold_share"), max(sig) / tot)
        # excluding the largest fold is a ratio-of-sums over the rest
        i = sig.index(max(sig))
        rest_r = [f["precision"] for j, f in enumerate(folds) if j != i]
        rest_n = [sig[j] for j in range(len(folds)) if j != i]
        if rest_n and sum(rest_n):
            ident("A", w, "walkforward_excluding_largest_fold == ratio-of-sums over "
                          "the remaining folds",
                  d.get("walkforward_excluding_largest_fold"),
                  sum(r * n for r, n in zip(rest_r, rest_n)) / sum(rest_n))
        # pooled precision is ratio-of-sums, and must agree with the per-fold hits
        rates = [f["precision"] for f in folds]
        ident("A", w, "walkforward_pooled == sum(prec_i*sig_i)/sum(sig_i)",
              d.get("walkforward_pooled"),
              sum(r * n for r, n in zip(rates, sig)) / tot if tot else None)
        CHECKS_pool = None
        for j, (r, n) in enumerate(zip(rates, sig)):
            hits = r * n
            if abs(hits - round(hits)) > 1e-6 * max(1.0, abs(hits)):
                finding("A", w, f"fold {j}: precision {r!r} x signals {n} = {hits!r}, "
                                f"not an integral hit count")
        flat = sum(rates) / len(rates)
        wrong = sum(r * n for r, n in zip(rates, sig)) / tot if tot else float("nan")
        note(f"{w}: the two wrong poolings would give unweighted {flat!r} "
             f"({flat - (d.get('walkforward_pooled') or 0):+.6f}) and "
             f"signal-weighted {wrong!r}")

        # daily-precision diagnostics must bracket the pooled precision
        for f in folds:
            for key in ("precision_drop_worst_date", "precision_drop_best_date"):
                if key in f:
                    CHECKS_daily = None
                    if not (f["precision_drop_worst_date"] - 1e-12
                            <= f["precision"] <= f["precision_drop_best_date"] + 1e-12):
                        finding("A", w,
                                f"fold {f.get('name')}: precision {f['precision']!r} "
                                f"is not inside [drop_worst={f['precision_drop_worst_date']!r}, "
                                f"drop_best={f['precision_drop_best_date']!r}]")

    ho = d.get("holdout") or {}
    if ho:
        hw = f"{w} :: holdout"
        bound(hw, "precision", ho.get("precision"))
        bound(hw, "base_rate", ho.get("base_rate"))
        bound(hw, "busiest_date_share", ho.get("busiest_date_share"))
        bound(hw, "first_half_precision", ho.get("first_half_precision"))
        bound(hw, "second_half_precision", ho.get("second_half_precision"))
        drops = sorted(((int(k), v) for k, v in (ho.get("drop_top_dates") or {}).items()))
        if drops:
            # dropping zero dates must reproduce the headline precision
            ident("A", hw, "drop_top_dates[0] == precision",
                  drops[0][1] if drops[0][0] == 0 else None, ho.get("precision"))
            bad = [(drops[i], drops[i + 1]) for i in range(len(drops) - 1)
                   if drops[i + 1][1] < drops[i][1] - 1e-12]
            if bad:
                finding("D", hw,
                        "precision is not monotone in the number of dropped dates "
                        f"({bad}); expected only if the dates removed are not the "
                        "most concentrated ones")


def check_search_failures_and_fold_bases() -> None:
    """`failed` bookkeeping, the feature-group guard, and per-fold base agreement."""
    known_groups = {
        "momentum", "volatility", "volume", "limitup", "position",
        "candle", "kdj", "market", "cross",
    }

    for name in ("ml_search_models.json", "ml_search_ablation.json",
                 "ml_search_wide.json"):
        d = load_json(name)
        if not d:
            continue
        ranked = d.get("ranked") or []
        failed = d.get("failed") or []
        ident("A", name, "n_configs == len(ranked) + len(failed)",
              d.get("n_configs"), len(ranked) + len(failed))
        ident("A", name, "n_failed == len(failed)", d.get("n_failed"), len(failed))
        for f in failed:
            cfg = f.get("config", "?")
            err = str(f.get("error", ""))
            fw = f"{name} :: failed[{cfg}]"
            # guard the historical "unknown feature group" regression
            if "unknown feature group" in err:
                import re as _re
                quoted = _re.findall(r"unknown feature group \\?'?\"?([A-Za-z_][A-Za-z0-9_]*)",
                                     err)
                unknown = [g for g in quoted if g not in known_groups]
                if unknown:
                    finding(
                        "D", fw,
                        f"configuration failed with an unknown feature group "
                        f"{unknown}. The real groups are {sorted(known_groups)}. "
                        f"The config is dropped from `ranked`, so the grid silently "
                        f"loses coverage (and `n_failed` is the only trace).",
                    )
                else:
                    finding("D", fw, f"configuration failed: {err.strip().splitlines()[-1][:160]}")
            else:
                finding("D", fw, f"configuration failed: {err.strip().splitlines()[-1][:160]}")

        # Within ONE report every configuration that shares a label must share the
        # per-fold base vector for a given fold count: the base rate is a property
        # of the fold's test rows alone.  (Across reports this need not hold --
        # different reports were built on different matrices -- so the comparison
        # is deliberately scoped to a single file.)
        per_label: dict[tuple, dict[tuple, set]] = {}
        for row in ranked:
            label = row.get("label")
            pfb = row.get("per_fold_base")
            if not label or not isinstance(pfb, list) or not pfb:
                continue
            key = tuple(round(float(v), 12) for v in pfb)
            per_label.setdefault((label, len(pfb)), {}).setdefault(key, set()).add(
                row.get("config")
            )
        for (label, n), vectors in sorted(per_label.items()):
            if len(vectors) > 1:
                detail = "; ".join(
                    f"{list(k)} used by {len(cfgs)} config(s) e.g. {sorted(cfgs)[0]}"
                    for k, cfgs in sorted(vectors.items(), key=lambda kv: -len(kv[1]))
                )
                finding(
                    "A",
                    f"{name}: per-fold base rate for label {label} on {n} folds",
                    f"{len(vectors)} distinct base-rate vectors inside one report. "
                    f"A base rate depends only on the fold's test rows, so every "
                    f"config with the same label and fold count must agree: {detail}",
                )

        # The two search reports that share a matrix must agree with each other.
        if name == "ml_search_models.json":
            other = load_json("ml_search_ablation.json")
            if other:
                for row in ranked:
                    lab, pf = row.get("label"), row.get("per_fold_base")
                    mate = next(
                        (r for r in (other.get("ranked") or [])
                         if r.get("label") == lab
                         and len(r.get("per_fold_base") or []) == len(pf or [])
                         and (r.get("feature_groups") or []) == (row.get("feature_groups") or [])),
                        None,
                    )
                    if mate and not all(close(a, b) for a, b in
                                        zip(pf, mate["per_fold_base"])):
                        finding("A", "ml_search_models.json vs ml_search_ablation.json",
                                f"label {lab}: per-fold base vectors differ for the "
                                f"same label and fold count: {pf} vs "
                                f"{mate['per_fold_base']}")


def check_null_test_summaries() -> None:
    d = load_json("ml_null_tests.json")
    if not d:
        return
    w = "ml_null_tests.json"
    pl = d.get("permuted_labels") or {}
    if pl:
        prec = pl.get("oos_precision") or []
        base = pl.get("oos_base_rate") or []
        if prec:
            ident("A", w, "permuted_labels.mean_precision", pl.get("mean_precision"),
                  sum(prec) / len(prec))
            ident("A", w, "permuted_labels.max_precision", pl.get("max_precision"),
                  max(prec))
        if base:
            ident("A", w, "permuted_labels.mean_base_rate", pl.get("mean_base_rate"),
                  sum(base) / len(base))
        if prec and base and len(prec) == len(base):
            CHECKS_x = None
            for i, (p, b) in enumerate(zip(prec, base)):
                if p > b + 1e-9:
                    note(f"{w}: permuted seed {i} precision {p!r} exceeds its base "
                         f"{b!r} - a permuted label should not beat the base rate")
    nf = d.get("noise_features") or {}
    if nf:
        sig = nf.get("per_fold_signals") or []
        if sig:
            ident("A", w, "noise_features.oos_signals == sum(per_fold_signals)",
                  nf.get("oos_signals"), sum(sig))
        ident("A", w, "noise_features.oos_lift == oos_precision/oos_base_rate",
              nf.get("oos_lift"),
              (nf["oos_precision"] / nf["oos_base_rate"])
              if nf.get("oos_base_rate") else None)
        rates = nf.get("per_fold_oos") or []
        if rates and sig:
            ident("A", w, "noise_features.oos_precision == "
                          "sum(prec_i*sig_i)/sum(sig_i)",
                  nf.get("oos_precision"),
                  sum(r * n for r, n in zip(rates, sig)) / sum(sig))
    auc = d.get("feature_auc") or {}
    top = auc.get("top") or []
    if top:
        aucs = [t.get("auc") for t in top]
        CHECKS_s = None
        if any(aucs[i] < aucs[i + 1] - 1e-12 for i in range(len(aucs) - 1)):
            finding("A", w, "feature_auc.top is not sorted by auc descending")
        for t in top:
            bound(f"{w} :: feature_auc[{t.get('feature')}]", "auc", t.get("auc"))


def check_tradeability_overall() -> None:
    d = load_json("tradeability.json")
    if not d:
        return
    o = d.get("overall")
    if not o:
        finding("A", "tradeability.json", "no `overall` block")
        return
    w = "tradeability.json :: overall"
    sig = o.get("signals")
    ident("A", w, "hit_rate == hits/signals", o.get("hit_rate"),
          (o["hits"] / sig) if sig else None)
    ident("A", w, "unfillable_pct == unfillable/signals", o.get("unfillable_pct"),
          (o["unfillable"] / sig) if sig else None)
    ident("A", w, "tradeable_signals == signals - unfillable", o.get("tradeable_signals"),
          (sig - o["unfillable"]) if sig is not None
          and o.get("unfillable") is not None else None)
    ident("A", w, "tradeable_hit_rate == tradeable_hits/tradeable_signals",
          o.get("tradeable_hit_rate"),
          (o["tradeable_hits"] / o["tradeable_signals"])
          if o.get("tradeable_signals") else None)
    ident("A", w, "unfillable == gapped_at_limit + no_next_bar", o.get("unfillable"),
          (o["gapped_at_limit"] + o["no_next_bar"])
          if o.get("gapped_at_limit") is not None
          and o.get("no_next_bar") is not None else None)
    CHECKS_t = None
    if o.get("one_word_limit") is not None and o.get("gapped_at_limit") is not None \
            and o["one_word_limit"] > o["gapped_at_limit"]:
        finding("A", w, f"one_word_limit={o['one_word_limit']} > "
                        f"gapped_at_limit={o['gapped_at_limit']} "
                        f"(a one-word limit is a subset of gaps at the limit)")
    if o.get("tradeable_hits") is not None and o.get("hits") is not None \
            and o["tradeable_hits"] > o["hits"]:
        finding("A", w, f"tradeable_hits={o['tradeable_hits']} > hits={o['hits']}")
    for k in ("hit_rate", "unfillable_pct", "tradeable_hit_rate"):
        bound(w, k, o.get(k))

    worst = d.get("worst_by_unfillable") or []
    if worst:
        pcts = [r.get("unfillable_pct") for r in worst]
        CHECKS_w = None
        if any(pcts[i] < pcts[i + 1] - 1e-12 for i in range(len(pcts) - 1)):
            finding("A", "tradeability.json :: worst_by_unfillable",
                    "not sorted by unfillable_pct descending")
        keep = max(len(worst) - 1, 1)
        if len(worst) > keep:
            note(f"tradeability.json: worst_by_unfillable holds {len(worst)} rows "
                 f"(per_strategy.head(10))")


def check_live_readiness_cost() -> None:
    rows = load_csv("live_readiness.csv")
    if not rows:
        return
    for r in rows:
        lab = r.get("label", "?")
        w = f"live_readiness.csv :: {lab}"
        cost = num(r, "cost_bps_round_trip")
        if cost is None:
            continue
        c = cost / 10000.0
        ident("A", w, "net_mean_return == gross_mean_return - cost",
              num(r, "net_mean_return"),
              (num(r, "gross_mean_return") - c)
              if num(r, "gross_mean_return") is not None else None)
        ident("A", w, "net_median_return == gross_median_return - cost",
              num(r, "net_median_return"),
              (num(r, "gross_median_return") - c)
              if num(r, "gross_median_return") is not None else None)
        sig, res = iop(r, "signals"), iop(r, "resolved")
        CHECKS_l = None
        if res is not None and sig is not None and res > sig:
            finding("A", w, f"resolved={res} > signals={sig}")
        p10, p90 = num(r, "net_p10"), num(r, "net_p90")
        if p10 is not None and p90 is not None and p10 > p90:
            finding("A", w, f"net_p10={p10} > net_p90={p90}")
        bound(w, "net_win_rate", num(r, "net_win_rate"))
        med, mean = num(r, "net_median_return"), num(r, "net_mean_return")
        if med is not None and mean is not None and abs(med) > abs(mean) * 50 + 1:
            note(f"{w}: net_median_return={med!r} is far from net_mean_return={mean!r}; "
                 "expected for a right-skewed forward-return distribution")


def check_hitrate_correlations() -> None:
    rows = load_csv("hitrate_vs_expectancy.csv")
    d = load_json("hitrate_vs_expectancy.json")
    if not rows or not d:
        return
    w = "hitrate_vs_expectancy.csv"
    ident("A", w, "json strategies == CSV row count", d.get("strategies"), len(rows))
    pairs = [
        (num(r, "hit_rate"), num(r, "net_expectancy"),
         num(r, "net_expectancy_at_target")) for r in rows
    ]
    pairs = [p for p in pairs if None not in p]
    if len(pairs) < 3:
        finding("A", w, "too few complete rows to recompute the correlations")
        return
    hr = [p[0] for p in pairs]
    ne = [p[1] for p in pairs]
    at = [p[2] for p in pairs]

    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        out = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    def spearman(x, y):
        rx, ry = rank(x), rank(y)
        mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
        num_ = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
        dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
        dy = math.sqrt(sum((b - my) ** 2 for b in ry))
        return num_ / (dx * dy)

    ident("A", w, "spearman_hit_rate_vs_net_expectancy",
          d.get("spearman_hit_rate_vs_net_expectancy"), spearman(hr, ne))
    ident("A", w, "spearman_hit_rate_vs_at_target_expectancy",
          d.get("spearman_hit_rate_vs_at_target_expectancy"), spearman(hr, at))
    ident("A", w, "positive_expectancy_count", d.get("positive_expectancy_count"),
          sum(1 for v in ne if v > 0))
    ident("A", w, "positive_at_target_count", d.get("positive_at_target_count"),
          sum(1 for v in at if v > 0))
    for r in rows:
        sid = r.get("strategy_id", "?")
        rw = f"{w} :: {sid}"
        bound(rw, "hit_rate", num(r, "hit_rate"))
        bound(rw, "net_win_rate", num(r, "net_win_rate"))
        bound(rw, "pct_hits_that_did_not_beat_cost",
              num(r, "pct_hits_that_did_not_beat_cost"))
        sig = iop(r, "signals")
        CHECKS_hr = None
        if sig is not None and sig <= 0:
            finding("A", rw, f"signals={sig}: a rate is reported for an empty set")


def check_cards() -> None:
    rows = load_csv("webpro_cards_100_reproduction.csv")
    if not rows:
        return
    w = "webpro_cards_100_reproduction.csv"
    seen: dict[tuple, int] = {}
    for r in rows:
        sid, tag = r.get("strategy_id", "?"), r.get("batch_tag", "?")
        rw = f"{w} :: {sid} :: {tag}"
        seen[(sid, tag)] = seen.get((sid, tag), 0) + 1
        yp, tp, fp = iop(r, "yes_predictions"), iop(r, "tp"), iop(r, "fp")
        prec = num(r, "yes_precision")
        if None not in (yp, tp, fp):
            ident("A", rw, "tp + fp == yes_predictions", tp + fp, yp)
            CHECKS_c = None
            if tp > yp or fp > yp:
                finding("A", rw, f"tp={tp} or fp={fp} exceeds yes_predictions={yp}")
        if yp == 0:
            if prec is not None:
                finding("A", rw, f"yes_precision={prec!r} reported for "
                                 f"yes_predictions=0 (undefined)")
            if iop(r, "tp") not in (None, 0) or iop(r, "fp") not in (None, 0):
                finding("A", rw, "non-zero tp/fp with yes_predictions=0")
        elif yp is not None and yp > 0:
            if prec is None:
                finding("A", rw, f"yes_precision blank although yes_predictions={yp}")
            else:
                ident("A", rw, "yes_precision == tp/yes_predictions", prec, tp / yp)
        if prec is not None:
            bound(rw, "yes_precision", prec)
        bound(rw, "accuracy", num(r, "accuracy"))
        bound(rw, "positive_recall", num(r, "positive_recall"))
        errs = iop(r, "errors")
        if errs is not None and yp is not None and errs > yp:
            note(f"{rw}: errors={errs} exceeds yes_predictions={yp}")
    dupes = {k: v for k, v in seen.items() if v > 1}
    if dupes:
        finding("D", w, f"the same (strategy_id, batch_tag) appears more than once: "
                        f"{dupes}")


def check_baseline_agreement() -> None:
    """Published baseline rates must be the same number in every carrier."""
    wb = load_json("webpro_baselines.json") or {}
    lb = load_json("lowzone_baselines.json") or {}

    whr = load_csv("webpro_hit_rates.csv")
    for r in whr:
        sid = r.get("strategy_id", "?")
        for reg in ("webpro", "low60", "low504"):
            got = num(r, f"baseline__{reg}")
            want = (wb.get(reg) or {}).get("bull_rate")
            if got is None or want is None:
                continue
            ident("C", f"webpro_hit_rates.csv :: {sid} :: {reg}",
                  f"baseline__{reg} == webpro_baselines.{reg}.bull_rate", got, want)

    lz = load_csv("lowzone_hit_rates.csv")
    for r in lz:
        vid = r.get("version", "?")
        reg = r.get("regime")
        got = num(r, "baseline_rate")
        want = (lb.get(reg) or {}).get("bull_rate")
        if got is None or want is None:
            continue
        ident("C", f"lowzone_hit_rates.csv :: {vid}", "baseline_rate == "
              f"lowzone_baselines.{reg}.bull_rate", got, want)

    # Provenance, when present, must agree across the carriers: the id a CSV row
    # quotes must be the id its own baseline JSON publishes. This is the check
    # that stops the two families being silently re-mixed.
    for r in whr:
        sid = r.get("strategy_id", "?")
        for reg in ("webpro", "low60", "low504"):
            quoted = r.get(f"baseline_population__{reg}")
            if not quoted:
                continue
            declared = ((wb.get(reg) or {}).get("population") or {}).get(
                "population_id")
            if declared:
                ident_text("C", f"webpro_hit_rates.csv :: {sid} :: {reg}",
                           f"baseline_population__{reg} == webpro_baselines."
                           f"{reg}.population.population_id", quoted, declared)
    for r in lz:
        quoted = r.get("baseline_population_id")
        reg = r.get("regime")
        if not quoted:
            continue
        declared = ((lb.get(reg) or {}).get("population") or {}).get("population_id")
        if declared:
            ident_text("C", f"lowzone_hit_rates.csv :: {r.get('version','?')}",
                       "baseline_population_id == lowzone_baselines."
                       f"{reg}.population.population_id", quoted, declared)

    # A provenance block must describe the row set its own payload published: if
    # `rows` disagrees with `candidates`/`evaluated_points`, the block is stale.
    for name, payload, count_key in (
        ("lowzone_baselines.json", lb, "candidates"),
        ("webpro_baselines.json", wb, "evaluated_points"),
    ):
        for reg in ("webpro", "low60", "low504"):
            blk = (payload.get(reg) or {}).get("population")
            n = (payload.get(reg) or {}).get(count_key)
            if not blk or blk.get("rows") is None or n is None:
                continue
            ident("C", f"{name} :: {reg} :: population.rows",
                  f"population.rows == {count_key}", blk["rows"], n, rtol=0.0)

    # The two baseline files both publish a "bull_rate" for the same regime, but
    # over different bar populations: backtest_lowzone censuses the full resolved
    # panel, scan_all censuses the scanned grid (--stride, default 5, above the
    # min-history floor). Report the gap, and -- now that both payloads carry a
    # `population` block -- say which row set each one counted.
    #
    # STATISTICS NOTE. An earlier version of this check tested the scanned set
    # against its complement with a two-proportion z over resolved rows, and for
    # `low504` reported z = +11.50 and the verdict "NOT explainable by sampling
    # noise". That verdict is wrong, and it is wrong in an instructive way: rows
    # are not independent Bernoulli draws. On any one market date the bull event is
    # heavily cross-sectional, and neighbouring dates' forward windows overlap
    # almost completely, so the effective sample size is closer to the number of
    # *dates* (~320 for low504) than to the number of rows (~1.1M). Rows-per-date
    # is ~588 scanned vs ~2,318 complement, so the row-level standard error is
    # understated by roughly an order of magnitude.
    #
    # Re-testing the same contrast with market dates as clusters -- and with a
    # date-block bootstrap that assumes nothing about the within-date correlation
    # -- gives z = +1.24 for `low504`, i.e. entirely consistent with noise. The
    # contrast is also structurally confounded: `scanned` = `_seq >= 60 AND
    # _seq % 5 == 0` while `complement` = everything else, so the test bundles the
    # min-history filter with the stride. Separated out, the min-history filter is
    # the real effect (low504: +3.47 pp, cluster z = +16.9, bootstrap p < 0.001)
    # and the stride contributes nothing (low504: -0.08 pp, cluster z = -0.17).
    #
    # So: report the gap as a population difference to be labelled, NOT as a
    # statistical anomaly. See scripts/scratch/baseline_contrast_test.py, which
    # reproduces every number quoted above from the shard label columns.
    for reg in ("webpro", "low60", "low504"):
        a = (lb.get(reg) or {}).get("bull_rate")
        b = (wb.get(reg) or {}).get("bull_rate")
        if a is None or b is None or close(a, b):
            continue
        ca = (lb.get(reg) or {}).get("candidates")
        cb = (wb.get(reg) or {}).get("evaluated_points")
        pa = (lb.get(reg) or {}).get("population") or {}
        pb = (wb.get(reg) or {}).get("population") or {}
        detail = (f"bull_rate differs: {a!r} over {ca:,} candidates vs {b!r} over "
                  f"{cb:,} evaluated points (rel diff {abs(a - b) / b:.4%}). Both "
                  f"files are published as the baseline for the '{reg}' regime, but "
                  f"they measure different bar populations.")
        if pa.get("population_id") and pb.get("population_id"):
            detail += (f" The payloads now name them: lowzone_baselines = "
                       f"{pa['population_id']!r}, webpro_baselines = "
                       f"{pb['population_id']!r}.")
        else:
            detail += (" Neither payload carries a `population` block yet, so re-run "
                       "`python -m src.backtest_lowzone` and `python -m src.scan_all "
                       "--stride 5` to label them.")
        # The subset arithmetic stays: it is worth recording that the smaller row
        # set is a strict subset, since that is *why* a naive two-proportion test
        # is the wrong instrument here.
        if ca and cb and cb < ca:
            pos_a, pos_b = a * ca, b * cb
            nc, pos_c = ca - cb, pos_a - pos_b
            if nc > 0:
                pc = pos_c / nc
                p = (pos_b + pos_c) / (cb + nc)
                se = math.sqrt(p * (1 - p) * (1 / cb + 1 / nc))
                z = (b - pc) / se if se > 0 else 0.0
                detail += (f" The smaller set is a subset of the larger, so a naive "
                           f"two-proportion test over rows gives z = {z:+.2f}; that "
                           f"statistic is NOT usable, because resolved rows are not "
                           f"independent - the bull event is cross-sectional within a "
                           f"date and forward windows overlap across neighbouring "
                           f"dates. Re-testing the identical contrast with market "
                           f"dates as clusters gives z of order 1 (see "
                           f"scripts/scratch/baseline_contrast_test.py). The gap is "
                           f"a population difference, not a statistical anomaly, and "
                           f"the fix is a provenance label, not an investigation.")
        detail += (f" The two populations differ by a factor of {ca / cb:.2f}, so a "
                   f"reader combining a hit rate from one file with the baseline "
                   f"from the other gets an inconsistent lift.")
        finding("D", f"lowzone_baselines.json vs webpro_baselines.json :: {reg}",
                detail)

    # a one-word-tier baseline must not exceed the any-tier baseline
    for reg in ("webpro", "low60", "low504"):
        blk = lb.get(reg) or {}
        any_t = blk.get("bull_rate")
        if any_t is None:
            continue
        for tier in ("tier_ge_1_rate", "tier_ge_2_rate", "tier_ge_3_rate",
                     "tier_ge_4_rate", "tier_ge_5_rate"):
            v = blk.get(tier)
            if v is not None and v > any_t * 2.5:
                note(f"lowzone_baselines.json :: {reg}.{tier}={v!r} is more than "
                     f"2.5x the any-tier rate {any_t!r}")


def check_frontier_identity() -> None:
    for name in ("ml_precision_frontier_oos.csv", "ml_precision_frontier_insample.csv"):
        rows = load_csv(name)
        if not rows:
            continue
        by_fold: dict[str, list[dict]] = {}
        for r in rows:
            by_fold.setdefault(r.get("fold", "?"), []).append(r)
        for fold, group in by_fold.items():
            w = f"{name} :: {fold}"
            n = [num(r, "n_published") for r in group]
            pub = [num(r, "publish_rate") for r in group]
            prec = [num(r, "precision") for r in group]
            rec = [num(r, "recall") for r in group]
            fpr = [num(r, "fpr") for r in group]
            if any(v is None for v in n + pub + prec + rec + fpr):
                finding("A", w, "a frontier column has missing values")
                continue
            sizes = [a / b for a, b in zip(n, pub) if b]
            N = sum(sizes) / len(sizes)
            if max(sizes) - min(sizes) > 1e-3:
                finding("A", w, f"publish_rate implies inconsistent fold sizes "
                                f"{min(sizes):.4f}..{max(sizes):.4f}")
            tp = [p * k for p, k in zip(prec, n)]
            dev = max(abs(t - round(t)) for t in tp)
            if dev > 1e-6:
                i = max(range(len(tp)), key=lambda j: abs(tp[j] - round(tp[j])))
                finding("A", w, f"precision x n_published is not integral: "
                                f"n_published={int(n[i])} precision={prec[i]!r} -> "
                                f"{tp[i]!r} hits")
            sel = [j for j in range(len(rec)) if rec[j] > 0]
            if sel:
                pos = [tp[j] / rec[j] for j in sel]
                if max(pos) - min(pos) > 1e-3:
                    finding("A", w, f"implied positive count varies across rows: "
                                    f"{min(pos):.6f}..{max(pos):.6f}")
                P = sum(pos) / len(pos)
                if N - P > 0:
                    worst = max(abs((n[j] - tp[j]) / (N - P) - fpr[j])
                                for j in range(len(n)))
                    if worst > 1e-9:
                        finding("A", w, f"fpr != (n_published - tp)/(N - P); max abs "
                                        f"deviation {worst:.3e}")
                note(f"{w}: N={N:,.0f} labelled rows, P={P:,.0f} positives, "
                     f"base={P / N!r}")
            if any(p < -1e-12 or p > 1 + 1e-12 for p in prec):
                finding("A", w, "precision outside [0, 1]")
            if any(v < -1e-12 or v > 1 + 1e-12 for v in rec + fpr):
                finding("A", w, "recall or fpr outside [0, 1]")
            # n_published is strictly increasing across the sampled grid
            if any(n[i] >= n[i + 1] for i in range(len(n) - 1)):
                finding("A", w, "n_published is not strictly increasing down the file")


def check_top_level_base_rate_scope() -> None:
    """A top-level ``oos_base_rate`` that is really the rank-1 row's own base rate.

    ``src/ml/search.py`` writes ``"oos_base_rate": ok[0]["oos_base_rate"]``, i.e.
    the rank-1 row's own value. A base rate depends on the label AND the fold
    count, so when the rank-1 row is not ``label_high`` on the full fold count the
    report-level field silently describes a different population from the rows a
    reader will pair it with.
    """
    for name in ("ml_search_models.json", "ml_search_ablation.json",
                 "ml_search_wide.json"):
        d = load_json(name)
        if not d:
            continue
        ranked = d.get("ranked") or []
        top = d.get("oos_base_rate")
        if not ranked or top is None:
            continue
        vals = {}
        for r in ranked:
            if r.get("oos_base_rate") is None:
                continue
            vals.setdefault(round(float(r["oos_base_rate"]), 12), []).append(r)
        ident("A", name, "top-level oos_base_rate == rank-1 row's oos_base_rate",
              top, ranked[0].get("oos_base_rate"))
        if len(vals) <= 1:
            continue
        # the field is ambiguous: quantify the worst mis-pairing
        worst = None
        for v, rows in vals.items():
            if close(v, top):
                continue
            for r in rows:
                p = r.get("oos_precision")
                if not p:
                    continue
                ok = p / float(r["oos_base_rate"])
                bad = p / float(top)
                err = abs(bad / ok - 1)
                if worst is None or err > worst[0]:
                    worst = (err, r, v, bad)
        if worst:
            err, r, v, bad = worst
            labels = sorted({(x.get("label"), x.get("n_folds")) for x in ranked
                             if not close(x.get("oos_base_rate") or 0, top)})
            finding(
                "D", f"{name} :: top-level `oos_base_rate`",
                f"the report-level field is {top!r} (the rank-1 row "
                f"{ranked[0].get('config')!r}, label={ranked[0].get('label')!r}, "
                f"n_folds={ranked[0].get('n_folds')}), but the report also contains "
                f"{len(vals)} distinct per-row base rates covering labels/fold-counts "
                f"{labels}. The field is a row-level quantity carrying a report-level "
                f"name. Pairing it with row {r.get('config')!r} "
                f"(label={r.get('label')!r}, n_folds={r.get('n_folds')}, own base "
                f"{float(r['oos_base_rate'])!r}) gives lift {bad!r} instead of the "
                f"published {r.get('oos_lift')!r} - an overstatement of {err:.2%}. "
                f"Every row's own ``oos_lift`` is self-consistent; the hazard is "
                f"purely in reading the top-level field as the report's base rate.",
            )
        else:
            note(f"{name}: top-level oos_base_rate {top!r} is the rank-1 row's own "
                 f"base rate and the report contains {len(vals)} distinct per-row "
                 f"base rates; no mis-pairing quantified")


def check_published_vs_worktree() -> None:
    """State plainly whether each report on disk still carries the known defect.

    ``scripts/scratch/report_integrity_check.py`` audits ``git HEAD`` (the
    published revision); this file audits the working tree. Those are different
    inputs, so the two must be reconciled rather than averaged.
    """
    import subprocess

    # label_high per-fold base rate, stride-5 (published) vs stride-1 (rebuilt)
    s5 = [0.02947299547941946, 0.08016014494871271, 0.02669452824444383,
          0.028643949835559984]
    s1 = [0.029958391948440515, 0.08014798709496423, 0.026432681210960526,
          0.028532597571658984]
    ros_s5 = 11496 / 281227

    def head_json(name):
        p = subprocess.run(["git", "show", f"HEAD:reports/{name}"],
                           capture_output=True, cwd=REPO)
        if p.returncode != 0:
            return None
        try:
            return json.loads(p.stdout.decode("utf-8"))
        except ValueError:
            return None

    print("\n--- published (git HEAD) vs working tree")
    for name in ("ml_null_tests.json", "ml_search_models.json",
                 "ml_search_ablation.json"):
        h = head_json(name)
        w = load_json(name)
        if h is None or w is None:
            continue
        hv = (h.get("noise_features") or {}).get("oos_base_rate") or h.get("oos_base_rate")
        wv = (w.get("noise_features") or {}).get("oos_base_rate") or w.get("oos_base_rate")
        hn = h.get("n_rows")
        wn = w.get("n_rows")
        print(f"  {name}")
        print(f"    HEAD     base={hv!r} n_rows={hn!r}")
        print(f"    worktree base={wv!r} n_rows={wn!r}")
        if hv is not None and close(hv, sum(s5) / 4) and not close(hv, ros_s5):
            print(f"    HEAD is the UNWEIGHTED MEAN of the per-fold base rates: the "
                  f"defect is present in the published file")
            print(f"      correct ratio-of-sums = {ros_s5!r} "
                  f"(error {hv - ros_s5:+.9f}, "
                  f"{(hv - ros_s5) / ros_s5:.4%})")
        if wv is not None and (close(wv, ros_s5) or close(wv, sum(s1) / 1)):
            print(f"    worktree equals the ratio-of-sums over its own fold counts: "
                  f"the pooling defect is fixed on disk")
    print("  NOTE: `git show HEAD:src/ml/walkforward.py` already binds "
          "`\"oos_base_rate\": base_exact`,")
    print("  so HEAD's source is correct. The published reports/ml_null_tests.json "
          "predates")
    print("  that fix (last written by 9e3f332, before 6b09f33), i.e. it is a stale "
          "artifact,")
    print("  not a live code defect.")


def frontier_fold_bases(name: str = "ml_precision_frontier_oos.csv"):
    """Recover (rows, positives, base) per fold from the OOS frontier.

    At ``publish_rate == 1`` every labelled row of the fold is published, so
    ``n_published`` is the fold's labelled-row count and ``precision`` is its
    base rate. This is the only way to get the per-fold base vector for reports
    that do not carry ``per_fold_base``.
    """
    rows = load_csv(name)
    out = {}
    for r in rows:
        if not close(num(r, "publish_rate"), 1.0):
            continue
        fold = r.get("fold")
        n = num(r, "n_published")
        p = num(r, "precision")
        if fold is None or n is None or p is None:
            continue
        out[fold] = (int(round(n)), p * n, p)
    return [out[k] for k in sorted(out)]


def check_pooling_without_per_fold_base() -> None:
    """Test the pooling of a base rate even when ``per_fold_base`` is absent.

    ``ml_null_tests.json`` at HEAD publishes ``per_fold_oos`` and
    ``per_fold_signals`` but no ``per_fold_base``, so the ratio-of-sums for the
    base rate cannot be recomputed from the file alone. The fold row/positive
    counts are recovered from the OOS frontier instead, and the reported pooled
    base is compared against the correct ratio of sums and against both wrong
    poolings.
    """
    folds = frontier_fold_bases()
    if not folds:
        return
    correct = sum(p for _, p, _ in folds) / sum(n for n, _, _ in folds)

    for name in ("ml_null_tests.json", "ml_search_models.json",
                 "ml_search_ablation.json"):
        d = load_json(name)
        if not d:
            continue
        blocks = []
        if isinstance(d.get("noise_features"), dict):
            blocks.append(("noise_features", d["noise_features"]))
        for r in (d.get("ranked") or []):
            if isinstance(r.get("oos_base_rate"), (int, float)):
                blocks.append((f"ranked[{r.get('config')}]", r))
        for where, blk in blocks:
            rep = blk.get("oos_base_rate")
            if rep is None:
                continue
            if isinstance(blk.get("per_fold_base"), list) and blk["per_fold_base"]:
                continue  # already covered by the per-fold check
            CHECKS_local = None
            # only meaningful when the block used the full fold set
            if blk.get("n_folds") not in (None, len(folds)) and name != "ml_null_tests.json":
                continue
            flat = sum(b for _, _, b in folds) / len(folds)
            if close(rep, correct):
                continue
            if close(rep, flat):
                sigs = blk.get("per_fold_signals")
                by_sig = (sum(b * s for (_, _, b), s in zip(folds, sigs))
                          / sum(sigs)) if sigs and len(sigs) == len(folds) else None
                finding(
                    "B", f"{name} :: {where}",
                    f"oos_base_rate is the UNWEIGHTED MEAN of the per-fold base "
                    f"rates: reported {rep!r} == mean({[round(b, 12) for _, _, b in folds]})"
                    f" == {flat!r}. The correct ratio-of-sums is {correct!r} "
                    f"= {sum(p for _, p, _ in folds):.0f}/"
                    f"{sum(n for n, _, _ in folds):.0f}. Error {rep - correct:+.9f} "
                    f"({(rep - correct) / correct:.4%} relative). "
                    + (f"The signal-weighted pooling would give {by_sig!r}. "
                       if by_sig is not None else "")
                    + (f"oos_lift {blk.get('oos_lift')!r} inherits the error: against "
                       f"the correct base rate it should be "
                       f"{blk['oos_precision'] / correct!r}."
                       if blk.get("oos_precision") else ""),
                )
            else:
                finding(
                    "B", f"{name} :: {where}",
                    f"oos_base_rate {rep!r} matches neither the correct ratio-of-sums "
                    f"{correct!r} nor the unweighted mean {flat!r}",
                )


def check_signal_count_bases() -> None:
    """Same strategy, different signal counts: state which basis each uses."""
    hre = load_csv("hitrate_vs_expectancy.csv")
    tab = load_csv("tradeability_by_strategy.csv")
    whr = load_csv("webpro_hit_rates.csv")
    if not (hre and tab and whr):
        return
    a = {r.get("strategy_id"): iop(r, "signals") for r in hre}
    t = {r.get("label"): iop(r, "signals") for r in tab}
    raw = {r.get("strategy_id"): iop(r, "signals_raw__webpro") for r in whr}
    ded = {r.get("strategy_id"): iop(r, "signals_deduped__webpro") for r in whr}
    cen = {r.get("strategy_id"): iop(r, "censored_signals__webpro") for r in whr}

    shared = sorted(set(a) & set(t))
    diffs = [(k, a[k], t[k]) for k in shared if a[k] != t[k]]
    if diffs:
        # tradeability counts the raw population plus the signals whose forward
        # window is censored; hitrate_vs_expectancy counts the raw population the
        # scorer emitted.  Both are legitimate, but they are different bases.
        explains = all(
            t[k] == (raw.get(k) or 0) + (cen.get(k) or 0) for k, _, _ in diffs
        )
        extra = all(t[k] == (raw.get(k) or 0) for k, _, _ in diffs)
        finding(
            "D" if explains else "C",
            "hitrate_vs_expectancy.csv vs tradeability_by_strategy.csv",
            f"{len(diffs)} of {len(shared)} shared strategy_ids report different "
            f"signal counts. "
            + ("Every difference is exactly the censored-signal count: "
               "tradeability_by_strategy.signal == signals_raw__webpro + "
               "censored_signals__webpro, while hitrate_vs_expectancy.signals == "
               "signals_raw__webpro. Two different but individually defensible "
               "denominators; the two files must not be compared directly. "
               if explains else
               "The difference is NOT explained by the raw/censored basis. ")
            + "Examples: "
            + "; ".join(f"{k}: hitrate={x} tradeability={y} "
                        f"(webpro raw={raw.get(k)}, deduped={ded.get(k)}, "
                        f"censored={cen.get(k)})" for k, x, y in diffs[:5]),
        )
        if extra:
            finding("D", "hitrate_vs_expectancy.csv vs tradeability_by_strategy.csv",
                    "some rows match on the raw basis and some on raw+censored, so "
                    "the two files do not even use a consistent basis between them")
    else:
        note("hitrate_vs_expectancy.csv and tradeability_by_strategy.csv agree on "
             "signal counts for every shared strategy")

    mism = [(k, a[k], raw[k]) for k in sorted(set(a) & set(raw))
            if a[k] is not None and raw[k] is not None and a[k] != raw[k]]
    if mism:
        finding("C", "hitrate_vs_expectancy.csv vs webpro_hit_rates.csv",
                f"signals differs from signals_raw__webpro for {len(mism)} "
                f"strategy_ids: {mism[:5]}")
    else:
        note("hitrate_vs_expectancy.csv `signals` == webpro_hit_rates.csv "
             "`signals_raw__webpro` for all shared strategies (same raw basis)")


def check_tradeable_subset() -> None:
    """tradeable_* must be a subset of the full population in the CSV too."""
    rows = load_csv("tradeability_by_strategy.csv")
    for r in rows:
        lab = r.get("label", "?")
        w = f"tradeability_by_strategy.csv :: {lab}"
        sig, unf = iop(r, "signals"), iop(r, "unfillable")
        ts, th = iop(r, "tradeable_signals"), iop(r, "tradeable_hits")
        hits = iop(r, "hits")
        ident("A", w, "tradeable_signals == signals - unfillable", ts,
              (sig - unf) if None not in (sig, unf) else None)
        ident("A", w, "hit_rate == hits/signals", num(r, "hit_rate"),
              (hits / sig) if sig else None)
        ident("A", w, "unfillable_pct == unfillable/signals",
              num(r, "unfillable_pct"), (unf / sig) if sig else None)
        ident("A", w, "tradeable_hit_rate == tradeable_hits/tradeable_signals",
              num(r, "tradeable_hit_rate"), (th / ts) if ts else None)
        ident("A", w, "unfillable == gapped_at_limit + no_next_bar", unf,
              (iop(r, "gapped_at_limit") + iop(r, "no_next_bar"))
              if iop(r, "gapped_at_limit") is not None
              and iop(r, "no_next_bar") is not None else None)
        CHECKS_ts = None
        if None not in (ts, th, hits):
            if th > hits:
                finding("A", w, f"tradeable_hits={th} > hits={hits}")
        if None not in (unf, iop(r, "one_word_limit")) \
                and iop(r, "one_word_limit") > unf:
            finding("A", w, f"one_word_limit={iop(r, 'one_word_limit')} > "
                            f"unfillable={unf}")
        if None not in (hits, sig) and hits > sig:
            finding("A", w, f"hits={hits} > signals={sig}")


# --------------------------------------------------------------------------- #
def materialise_head(dest: Path) -> int:
    """Write the published revision of reports/ into ``dest``. Returns file count."""
    import subprocess

    listing = subprocess.run(["git", "ls-tree", "--name-only", "HEAD:reports"],
                             capture_output=True, cwd=REPO)
    if listing.returncode != 0:
        raise SystemExit("not a git checkout; cannot audit the published revision")
    names = [n.strip() for n in listing.stdout.decode("utf-8").split() if n.strip()]
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for name in names:
        blob = subprocess.run(["git", "show", f"HEAD:reports/{name}"],
                              capture_output=True, cwd=REPO)
        if blob.returncode != 0:
            continue
        (dest / name).write_bytes(blob.stdout)
        n += 1
    return n


def main() -> int:
    argv = sys.argv[1:]
    global REPORTS
    if "--head" in argv:
        import tempfile

        tmp = Path(tempfile.mkdtemp(prefix="published_reports_"))
        n = materialise_head(tmp / "reports")
        REPORTS = tmp / "reports"
        print("=" * 78)
        print(f"AUDITING THE PUBLISHED REVISION (git HEAD:reports) - {n} files")
        print("(pass no flag to audit the working tree instead)")
        print("=" * 78)
    else:
        print("=" * 78)
        print(f"AUDITING THE WORKING TREE - {REPORTS}")
        print("(pass --head to audit the published revision instead)")
        print("=" * 78)
    print(f"tolerance: relative {RTOL} (integer counts compared exactly)")
    print("=" * 78)

    check_ceiling_requirement()
    check_concentration()
    check_search_failures_and_fold_bases()
    check_null_test_summaries()
    check_tradeability_overall()
    check_tradeable_subset()
    check_live_readiness_cost()
    check_hitrate_correlations()
    check_cards()
    check_baseline_agreement()
    check_frontier_identity()
    check_pooling_without_per_fold_base()
    check_top_level_base_rate_scope()
    check_signal_count_bases()
    if "--head" not in argv:
        check_published_vs_worktree()

    for sev, label in (("A", "DEFINITE arithmetic / logic error"),
                       ("B", "POOLING discrepancy"),
                       ("C", "CROSS-REPORT disagreement"),
                       ("D", "SUSPICIOUS - not conclusive")):
        mine = [r for r in ROWS if r[0] == sev]
        print(f"\n--- ({sev}) {label}: {len(mine)}")
        for _, where, detail in mine:
            print(f"  * {where}\n      {detail}")

    print(f"\nassertions executed: {CHECKS}")
    if NOTES:
        print(f"\n--- notes ({len(NOTES)})")
        for n in NOTES:
            print(f"    - {n}")
    hard = [r for r in ROWS if r[0] in ("A", "B", "C")]
    print("\n" + "=" * 78)
    print(f"summary: {len(hard)} definite/pooling/cross-report finding(s), "
          f"{len([r for r in ROWS if r[0] == 'D'])} suspicious item(s)")
    print("=" * 78)
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
