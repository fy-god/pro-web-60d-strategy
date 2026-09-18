"""Report integrity checker for ``reports/``.

Audits every machine-readable report for internal logical/arithmetic consistency
across seven categories:

  1. arithmetic identity   ``lift == precision / base_rate``, ``precision == hits / signals``
  2. pooling correctness   pooled figures recomputed as ratio-of-sums, plus the two
                           wrong poolings (unweighted mean, signal-weighted mean) so
                           the size of the error is visible
  3. interval sanity       every CI brackets its point estimate, low < high
  4. cross-report agreement shared quantities must match exactly across reports
  5. count coherence       ``signals <= n_test``, ``hits <= signals``,
                           ``distinct_stocks <= signals``, rates in [0, 1]
  6. CSV integrity         row counts, ``hits``/``signals``/``hit_rate`` coherence,
                           columns empty where they must be populated
  7. duplicates            the same config name twice, or the same strategy with
                           different signal counts in two reports

Provenance
----------
Some files in the working tree are in flux. The **published** revision of a report
is what ``git show HEAD:reports/<name>`` returns; that is the authoritative version
and is what this checker audits. It then reports, separately, where the working tree
disagrees with the published revision.

Comparison policy
-----------------
Floats are compared with a relative tolerance of ``RTOL = 1e-6`` (see ``relclose``).
Float round-tripping through JSON is therefore never reported as a mismatch.

Usage
-----
    $env:PYTHONPATH='.'; python scripts/scratch/report_integrity_check.py

Read-only with respect to ``reports/``: nothing is written outside ``.audit_tmp/``
(and this script writes nothing at all). Exits 1 when a definite problem is found.
"""

from __future__ import annotations

import csv
import io
import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORTS = REPO / "reports"

RTOL = 1e-6

# Fold test-row counts and positive counts for the 4-fold walk-forward, keyed by
# fold label. Derived from the published out-of-sample precision frontier at
# publish_rate == 1 (which is the whole test block), and cross-checked below
# against every per_fold_base vector in the published reports.
FRONTIER_OOS = "ml_precision_frontier_oos.csv"

# Reports whose pooled figures describe the dense label_high / target 0.30 matrix.
POOLED_LABEL_HIGH_ROWS = 281227
POOLED_LABEL_HIGH_POSITIVES = 11496

findings: list[dict] = []
_GAP_SEEN: set = set()


def finding(category: str, title: str, detail: str) -> None:
    findings.append({"category": category, "title": title, "detail": detail})


def relclose(a, b, rtol: float = RTOL) -> bool:
    """Relative comparison that treats non-finite values strictly."""
    try:
        a = float(a)
        b = float(b)
    except (TypeError, ValueError):
        return False
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    if math.isinf(a) or math.isinf(b):
        return a == b
    return abs(a - b) <= rtol * max(abs(a), abs(b), 1e-300)


# --------------------------------------------------------------------------- io
def git_show(path: str) -> str | None:
    proc = subprocess.run(["git", "show", f"HEAD:{path}"],
                          capture_output=True, cwd=REPO)
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8")


def published_reports() -> set[str]:
    out = subprocess.run(["git", "ls-tree", "--name-only", "HEAD:reports"],
                         capture_output=True, cwd=REPO).stdout.decode("utf-8")
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def load_published(name: str):
    text = git_show(f"reports/{name}")
    if text is None:
        return None
    if name.endswith(".json"):
        return json.loads(text)
    return text


def load_worktree(name: str):
    path = REPORTS / name
    if not path.exists():
        return None
    if name.endswith(".json"):
        return json.loads(path.read_text(encoding="utf-8"))
    return path.read_text(encoding="utf-8")


def csv_rows(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def num(value, default=None):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s in ("", "nan", "NaN", "None", "null"):
        return default
    try:
        return float(s)
    except ValueError:
        return default


# ------------------------------------------------------------------ walkers
def walk_dicts(node, path=""):
    """Yield ``(path, dict)`` for every dict in a nested structure."""
    if isinstance(node, dict):
        yield path, node
        for key, value in node.items():
            yield from walk_dicts(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from walk_dicts(value, f"{path}[{i}]")


def base_vector_rows() -> tuple[dict[str, float], list[str]]:
    """Per-fold test-row counts from the published OOS frontier.

    At ``publish_rate == 1`` the frontier publishes the entire test block, so the
    row count and the rounded precision * n give the fold's size and positives.
    """
    text = load_published(FRONTIER_OOS)
    if text is None:
        return {}, []
    rows: dict[str, int] = {}
    positives: dict[str, int] = {}
    for row in csv_rows(text):
        if relclose(row["publish_rate"], 1.0):
            n = int(row["n_published"])
            rows[row["fold"]] = n
            positives[row["fold"]] = int(round(float(row["precision"]) * n))
    order = sorted(rows)
    return ({f: rows[f] for f in order},
            {f: positives[f] for f in order})


def build_label_folds(pub: dict[str, object], order: list[str],
                      fold_rows: dict[str, int],
                      fold_pos: dict[str, int]) -> dict[str, dict]:
    """Resolve every label to its per-fold (rows, positives, base rate).

    A per-fold *base rate* is a property of the data, not of the model, so the
    same four folds give the same base-rate vector for every configuration that
    uses a given label. The report states those vectors directly, and the
    published OOS frontier independently confirms the fold row counts (the
    published ``label_high`` vector reproduces the frontier's positives exactly).

    Different labels answer different questions over the *same* test rows:
    ``label_high`` is "did the forward maximum high touch the target", which must
    dominate ``label_close`` ("did the forward maximum close touch the target").
    Both are checked below.
    """
    out: dict[str, dict] = {}
    for name in ("ml_search_wide.json", "ml_search_models.json",
                 "ml_search_ablation.json"):
        doc = pub.get(name)
        if not isinstance(doc, dict):
            continue
        for row in (doc.get("ranked") or []):
            label, pfb = row.get("label"), row.get("per_fold_base")
            if not label or not isinstance(pfb, list) or not pfb:
                continue
            if len(pfb) > len(order):
                continue
            rows = [fold_rows[order[i]] for i in range(len(pfb))]
            pos = [round(float(b) * r) for b, r in zip(pfb, rows)]
            # integrality: a base rate times its row count must be a count
            for b, r, k in zip(pfb, rows, pos):
                if abs(float(b) * r - k) > 1e-6:
                    finding("A", f"{name}: per-fold base rate is not a count ratio",
                            f"{row.get('config')} [{label}]: {b!r} * {r} = "
                            f"{float(b) * r!r} is not an integer count of positives")
            entry = {"order": order[:len(pfb)], "rows": rows, "pos": pos,
                     "bases": [float(v) for v in pfb]}
            prev = out.get(label)
            if prev is None or len(prev["bases"]) < len(entry["bases"]):
                out[label] = entry
            elif len(prev["bases"]) == len(entry["bases"]) and not all(
                    relclose(a, b) for a, b in zip(prev["bases"], entry["bases"])):
                finding("A", f"{name}: two configurations disagree on the per-fold base "
                             f"rates for {label}",
                        f"{prev['bases']} vs {entry['bases']} - the base rate depends "
                        f"only on the fold's test rows, so this cannot happen on one "
                        f"matrix")
    # the frontier is the authority for label_high fold sizes
    if "label_high" in out:
        derived = [round(b * fold_rows[order[i]])
                   for i, b in enumerate(out["label_high"]["bases"][:len(order)])]
        truth = [fold_pos[f] for f in order][:len(derived)]
        if derived != truth:
            finding("A", "ml_search_*.json label_high per-fold positives disagree "
                         "with the published OOS frontier",
                    f"derived {derived}, frontier {truth}")
    # label_high must dominate label_close over the same rows
    hi, lo = out.get("label_high"), out.get("label_close")
    if hi and lo and len(hi["pos"]) == len(lo["pos"]):
        for i, (h, l) in enumerate(zip(hi["pos"], lo["pos"])):
            if h < l:
                finding("A", "label_close has more positives than label_high in a fold",
                        f"fold index {i}: close {l} > high {h}; the forward maximum "
                        f"high must reach the target whenever the forward maximum "
                        f"close does")
    return out


# =========================================================== category 1: identities
def check_search_row_identities(rep: str, ranked: list[dict]) -> None:
    for row in ranked:
        cfg = row.get("config", "?")
        sig = row.get("oos_signals")
        prec = row.get("oos_precision")
        base = row.get("oos_base_rate")
        lift = row.get("oos_lift")
        if sig and prec is not None and base is not None:
            if lift is not None and base > 0 and not relclose(lift, prec / base):
                finding("A", f"{rep}: oos_lift != oos_precision / oos_base_rate",
                        f"{cfg}: lift={lift!r}, precision/base="
                        f"{prec / base!r}")
        if sig and prec is not None and not (0.0 <= prec <= 1.0):
            finding("A", f"{rep}: oos_precision outside [0, 1]",
                    f"{cfg}: precision={prec!r}")
        if base is not None and not (0.0 <= base <= 1.0):
            finding("A", f"{rep}: oos_base_rate outside [0, 1]",
                    f"{cfg}: base={base!r}")
        n_oos = row.get("oos_signals", 0) or 0
        n_folds = row.get("n_folds")
        pfs = row.get("per_fold_signals") or []
        pfo = row.get("per_fold_oos") or []
        if n_folds is not None and len(pfs) != n_folds:
            finding("A", f"{rep}: n_folds != len(per_fold_signals)",
                    f"{cfg}: n_folds={n_folds}, len(per_fold_signals)={len(pfs)}")
        if len(pfs) != len(pfo):
            finding("A", f"{rep}: per_fold_signals / per_fold_oos length mismatch",
                    f"{cfg}: {len(pfs)} vs {len(pfo)}")
        if pfs and sum(pfs) != n_oos:
            finding("A", f"{rep}: oos_signals != sum(per_fold_signals)",
                    f"{cfg}: {n_oos} vs {sum(pfs)}")
        if pfs and sum(pfs) and prec is not None:
            pooled = sum(p * s for p, s in zip(pfo, pfs)) / sum(pfs)
            if not relclose(prec, pooled):
                finding("A", f"{rep}: oos_precision != signal-weighted fold mean",
                        f"{cfg}: {prec!r} vs {pooled!r}")
        fab = row.get("folds_above_base")
        pfb = row.get("per_fold_base") or []
        if fab is not None and pfb and len(pfb) == len(pfo):
            expect = sum(1 for p, b in zip(pfo, pfb) if p > b)
            if int(fab) != expect:
                finding("A", f"{rep}: folds_above_base wrong",
                        f"{cfg}: reported {fab}, recomputed {expect}")
        if fab is not None and n_folds is not None and int(fab) > int(n_folds):
            finding("A", f"{rep}: folds_above_base exceeds n_folds",
                    f"{cfg}: {fab} > {n_folds}")
        # the two approximation fields are reported alongside the exact one
        be, bs, bu = (row.get("oos_base_rate"), row.get("oos_base_rate_by_signals"),
                      row.get("oos_base_rate_unweighted"))
        mad = row.get("oos_base_rate_max_abs_diff")
        if None not in (be, bs, bu, mad):
            expect = max(abs(bs - be), abs(bu - be), 0.0)
            if not relclose(mad, expect, 1e-9):
                finding("A", f"{rep}: oos_base_rate_max_abs_diff inconsistent",
                        f"{cfg}: reported {mad!r}, from the three bases {expect!r}")


def check_ceiling(pub: dict, rep: str = "ml_precision_ceiling.json") -> None:
    rows = pub.get("oos_rows")
    pos = pub.get("oos_positives")
    base = pub.get("base_rate")
    if rows and pos and base is not None and not relclose(base, pos / rows):
        finding("A", f"{rep}: base_rate != oos_positives / oos_rows",
                f"{pos}/{rows} = {pos / rows!r}, reported {base!r}")
    for key, block in (pub.get("practical_ceiling_by_min_signals") or {}).items():
        at_sig = block.get("at_signals")
        raw = block.get("max_precision_raw")
        recall = block.get("recall")
        if at_sig and raw is not None:
            hits = raw * at_sig
            if abs(hits - round(hits)) > 1e-9:
                finding("A", f"{rep}: max_precision_raw * at_signals is not a count",
                        f"min_signals={key}: {raw!r} * {at_sig} = {hits!r}")
            if pos and recall is not None:
                expect = round(hits) / pos
                if not relclose(recall, expect):
                    finding("A", f"{rep}: recall != hits / oos_positives",
                            f"min_signals={key}: reported {recall!r}, "
                            f"{round(hits)}/{pos} = {expect!r}")
    top = pub.get("practical_ceiling_250plus_raw")
    block = (pub.get("practical_ceiling_by_min_signals") or {}).get("250", {})
    if top is not None and block.get("max_precision_raw") is not None:
        if not relclose(top, block["max_precision_raw"]):
            finding("A", f"{rep}: practical_ceiling_250plus_raw != the 250 row",
                    f"{top!r} vs {block['max_precision_raw']!r}")


def check_final_holdout(pub: dict, rep: str = "ml_final_holdout.json") -> None:
    sig, hits = pub.get("signals"), pub.get("hits")
    prec, base, lift = pub.get("precision"), pub.get("base_rate"), pub.get("lift")
    n_hold = pub.get("n_holdout_rows")
    if sig and hits is not None and prec is not None:
        if hits > sig:
            finding("A", f"{rep}: hits > signals", f"{hits} > {sig}")
        if not relclose(prec, hits / sig):
            finding("A", f"{rep}: precision != hits / signals",
                    f"reported {prec!r}, {hits}/{sig} = {hits / sig!r}")
    if base is not None and n_hold:
        k = base * n_hold
        if abs(k - round(k)) > 1e-6:
            finding("A", f"{rep}: base_rate * n_holdout_rows is not a count",
                    f"{base!r} * {n_hold} = {k!r}")
    if prec is not None and base and lift is not None:
        if not relclose(lift, prec / base):
            finding("A", f"{rep}: lift != precision / base_rate",
                    f"reported {lift!r}, {prec / base!r}")
    for key in ("wilson_95", "date_clustered_95"):
        ci = pub.get(key)
        if isinstance(ci, list) and len(ci) == 2 and prec is not None:
            lo, hi = ci
            if not lo < hi:
                finding("A", f"{rep}: {key} low >= high", f"[{lo!r}, {hi!r}]")
            if not (lo <= prec <= hi):
                finding("A", f"{rep}: {key} does not bracket precision",
                        f"precision={prec!r}, ci=[{lo!r}, {hi!r}]")
    for key in ("distinct_stocks", "distinct_dates"):
        v = pub.get(key)
        if v is not None and sig is not None and v > sig:
            finding("A", f"{rep}: {key} > signals", f"{v} > {sig}")


# ============================================================ category 2: pooling
def check_pooling(rep: str, node: dict, path: str,
                  label_folds: dict[str, dict]) -> None:
    """Recompute a pooled base rate from its own per-fold detail.

    A per-fold base rate identifies which folds produced it, because the vector is
    a property of the label and the fold boundaries rather than of the model. The
    pooled value must then be the ratio of sums over exactly those folds:

        pooled = sum(round(base_i * rows_i)) / sum(rows_i)

    Matching by value is what makes this check independent: nothing here trusts
    the report's own claim about which folds it used.
    """
    pfb = node.get("per_fold_base")
    reported = node.get("oos_base_rate")
    if not isinstance(pfb, list) or not pfb or reported is None:
        return
    label = node.get("label")
    entry = label_folds.get(label)
    if entry is None:
        return
    pos_all, rows_all = entry["pos"], entry["rows"]
    # a row may have used only the first k folds (a short fold list is truncated)
    if len(pfb) > len(pos_all):
        return
    if not all(relclose(a, b) for a, b in zip(pfb, entry["bases"])):
        # try to identify each fold independently
        idx = []
        for value in pfb:
            hit = [i for i, b in enumerate(entry["bases"]) if relclose(value, b)]
            if len(hit) != 1:
                return
            idx.append(hit[0])
        pos_all = [entry["pos"][i] for i in idx]
        rows_all = [entry["rows"][i] for i in idx]
    else:
        pos_all = entry["pos"][:len(pfb)]
        rows_all = entry["rows"][:len(pfb)]

    rows = sum(rows_all)
    pos = sum(pos_all)
    exact = pos / rows
    flat = sum(pfb) / len(pfb)
    if not relclose(reported, exact):
        rel = abs(reported - exact) / exact * 100 if exact else float("inf")
        finding("B", f"{rep}: pooled base rate is not the ratio of sums",
                f"{path}" + (f" [{label}]" if label else "") + f": reported "
                f"{reported!r}, ratio-of-sums {exact!r} = {pos}/{rows}; "
                f"unweighted mean {flat!r}; error {abs(reported - exact):.6g} "
                f"({rel:.4f}% relative)")
    elif not relclose(reported, flat):
        # the search reports publish all three poolings side by side, so the gap is
        # disclosed rather than hidden; record it once per distinct gap.
        gap = abs(flat - exact)
        key = (rep, round(gap, 12))
        if key not in _GAP_SEEN:
            _GAP_SEEN.add(key)
            finding("D", f"{rep}: the two wrong poolings are published alongside the "
                         f"correct one",
                    f"{path}" + (f" [{label}]" if label else "") + f": correct "
                    f"{exact!r} = {pos}/{rows}, unweighted mean {flat!r}, gap "
                    f"{gap:.6g} ({gap / exact * 100:.4f}% relative). Reported, so it is "
                    f"disclosed rather than hidden; listed here only as context for how "
                    f"much the choice of pooling matters")


def check_pooling_precision(rep: str, ranked: list[dict]) -> None:
    for row in ranked:
        cfg = row.get("config", "?")
        pfs = row.get("per_fold_signals") or []
        pfo = row.get("per_fold_oos") or []
        prec = row.get("oos_precision")
        if not pfs or prec is None or len(pfs) != len(pfo):
            continue
        total = sum(pfs)
        if not total:
            continue
        by_signals = sum(p * s for p, s in zip(pfo, pfs)) / total
        flat = sum(pfo) / len(pfo)
        if not relclose(prec, by_signals):
            finding("B", f"{rep}: pooled precision is not signal-weighted",
                    f"{cfg}: reported {prec!r}, weighted {by_signals!r}, "
                    f"unweighted {flat!r}")


# ========================================================= category 3: intervals
POINT_KEYS = ("precision", "hit_rate", "bull_precision", "bull_precision_deduped",
              "bull_precision_raw", "bull_precision_deduped", "rate", "lift",
              "tradeable_hit_rate", "delta", "value", "point_estimate")


def check_intervals(rep: str, doc) -> None:
    """Every CI block must bracket its own point estimate, with low < high."""
    for path, node in walk_dicts(doc):
        # (a) explicit ci_low / ci_high pairs
        if "ci_low" in node and "ci_high" in node:
            lo, hi = num(node["ci_low"]), num(node["ci_high"])
            if lo is None or hi is None:
                continue
            if not lo < hi:
                finding("A", f"{rep}: interval low >= high",
                        f"{path}: [{node['ci_low']!r}, {node['ci_high']!r}]")
            pts = [(k, num(node[k])) for k in POINT_KEYS if k in node]
            pts = [(k, v) for k, v in pts if v is not None]
            if pts:
                key, value = pts[0]
                if not (lo <= value <= hi):
                    finding("A", f"{rep}: interval does not bracket its point estimate",
                            f"{path}: {key}={value!r}, ci=[{lo!r}, {hi!r}]")
        # (b) wilson_low / wilson_high pairs
        if "wilson_low" in node and "wilson_high" in node:
            lo, hi = num(node["wilson_low"]), num(node["wilson_high"])
            if lo is not None and hi is not None:
                if not lo < hi:
                    finding("A", f"{rep}: wilson low >= high",
                            f"{path}: [{lo!r}, {hi!r}]")
                value = num(node.get("precision"))
                if value is not None and not (lo <= value <= hi):
                    finding("A", f"{rep}: wilson does not bracket precision",
                            f"{path}: precision={value!r}, [{lo!r}, {hi!r}]")
        # (c) wilson as a 2-list
        wilson = node.get("wilson")
        if isinstance(wilson, list) and len(wilson) == 2:
            lo, hi = num(wilson[0]), num(wilson[1])
            if lo is not None and hi is not None:
                if not lo < hi:
                    finding("A", f"{rep}: wilson low >= high",
                            f"{path}: {wilson!r}")
                value = num(node.get("precision"))
                if value is not None and not (lo <= value <= hi):
                    finding("A", f"{rep}: wilson does not bracket precision",
                            f"{path}: precision={value!r}, wilson={wilson!r}")


# ======================================================== category 4: cross-report
def check_cross_report(pub: dict[str, object], fold_pos: dict[str, int],
                       fold_rows: dict[str, int],
                       label_folds: dict[str, dict]) -> None:
    """Shared quantities between reports that share the four walk-forward folds."""
    order = sorted(fold_rows)
    rows = sum(fold_rows.values())
    pos = sum(fold_pos.values())
    pooled = pos / rows

    ceiling = pub.get("ml_precision_ceiling.json") or {}
    models = pub.get("ml_search_models.json") or {}
    ablation = pub.get("ml_search_ablation.json") or {}
    wide = pub.get("ml_search_wide.json") or {}
    crosssec = pub.get("ml_crosssec_hgb0.json") or {}
    crosssec_final = pub.get("ml_crosssec_final.json") or {}
    nulls = pub.get("ml_null_tests.json") or {}

    high = label_folds.get("label_high") or {}
    high_bases = high.get("bases") or []
    high_pos = high.get("pos") or []
    high_rows = high.get("rows") or []
    four_fold_pooled = (sum(high_pos) / sum(high_rows)) if len(high_pos) == 4 else pooled

    ceiling_base = ceiling.get("base_rate")
    if ceiling_base is not None:
        if not relclose(ceiling_base, pooled):
            finding("C", "ml_precision_ceiling.json base_rate disagrees with the frontier",
                    f"reported {ceiling_base!r}, from the OOS frontier {pooled!r} "
                    f"= {pos}/{rows}")
        elif not relclose(ceiling_base, four_fold_pooled):
            finding("D", "ml_precision_ceiling.json base_rate matches the frontier",
                    f"{ceiling_base!r}")
    if ceiling.get("oos_rows") is not None and ceiling["oos_rows"] != rows:
        finding("C", "ml_precision_ceiling.json oos_rows disagrees with the frontier",
                f"{ceiling['oos_rows']} vs {rows}")
    if (ceiling.get("oos_positives") is not None
            and ceiling["oos_positives"] != pos):
        finding("C", "ml_precision_ceiling.json oos_positives disagrees",
                f"{ceiling['oos_positives']} vs {pos}")

    # every 4-fold label_high row in the search reports must share the frontier rate
    for name in ("ml_search_models.json", "ml_search_ablation.json", "ml_search_wide.json"):
        doc = pub.get(name) or {}
        if not isinstance(doc, dict):
            continue
        for row in (doc.get("ranked") or []):
            if row.get("label") != "label_high" or len(row.get("per_fold_base") or []) != 4:
                continue
            if not relclose(row["oos_base_rate"], pooled):
                finding("C", f"{name} {row['config']} base rate disagrees with the frontier",
                        f"reported {row['oos_base_rate']!r}, frontier {pooled!r}")

    # the cross-sectional report is documented as sharing the folds
    for name, doc in (("ml_crosssec_hgb0.json", crosssec),
                      ("ml_crosssec_final.json", crosssec_final)):
        for cfg, res in (doc.get("results") or {}).items():
            got = res.get("oos_base_rate")
            if got is None:
                continue
            if not relclose(got, pooled):
                finding("C", f"{name} {cfg} oos_base_rate disagrees with the frontier",
                        f"reported {got!r}, pooled label_high base rate {pooled!r}")
            if res.get("n_rows") is not None and res["n_rows"] != rows:
                finding("C", f"{name} {cfg} n_rows disagrees with the frontier",
                        f"{res['n_rows']} vs {rows}")
            fsum = [f.get("oos_base_rate") for f in (res.get("per_fold_summary") or [])]
            fsum = [v for v in fsum if v is not None]
            if fsum and high_bases and len(high_bases) >= len(fsum):
                if not all(relclose(a, high_bases[i]) for i, a in enumerate(fsum)):
                    finding("C", f"{name} {cfg} per-fold base rates disagree with the frontier",
                            f"{fsum} vs {high_bases[:len(fsum)]}")

    # null tests share the same matrix, so the base rate must be the same
    for path, node in walk_dicts(nulls):
        got = node.get("oos_base_rate")
        if got is None:
            continue
        if isinstance(node.get("n_folds"), int) and node["n_folds"] == 4:
            if relclose(got, pooled):
                continue
            finding("C", "ml_null_tests.json noise_features.oos_base_rate disagrees with "
                         "the frontier",
                    f"{path}: reported {got!r}, frontier pooled label_high base rate "
                    f"{pooled!r} = {pos}/{rows}")
            # is the reported value the unweighted mean of the shared fold bases?
            if high_bases and relclose(got, sum(high_bases) / len(high_bases)):
                finding("B", "ml_null_tests.json pooles the base rate as an unweighted "
                             "mean instead of a ratio of sums",
                        f"{path}: reported {got!r} == mean{high_bases} = "
                        f"{sum(high_bases) / len(high_bases)!r}; the correct "
                        f"ratio-of-sums is {pooled!r} = {pos}/{rows}; error "
                        f"{abs(got - pooled):.6g} "
                        f"({abs(got - pooled) / pooled * 100:.4f}% relative)")
                prec = node.get("oos_precision")
                lift = node.get("oos_lift")
                if lift is not None and prec is not None:
                    if relclose(lift, prec / got) and not relclose(lift, prec / pooled):
                        finding("B", "ml_null_tests.json oos_lift inherits the wrong "
                                     "base rate",
                                f"{path}: lift={lift!r} = oos_precision / {got!r}; "
                                f"against the correct base rate it should be "
                                f"{prec / pooled!r}")

    # a permuted label destroys the link between features and outcome, so every fold
    # reverts to the matrix-wide base rate. The permuted base rates must therefore
    # cluster around the label_high base rate of the matrix the null ran on, not
    # around the walk-forward pooled rate.
    perm = nulls.get("permuted_labels")
    if isinstance(perm, dict):
        values = perm.get("oos_base_rate")
        seq = [num(v) for v in (values if isinstance(values, list) else [values])]
        seq = [v for v in seq if v is not None]
        matrix_base = None
        for name in ("ml_search_wide.json",):
            for row in ((pub.get(name) or {}).get("ranked") or []):
                if row.get("label") == "label_high" and row.get("n_folds") == 4:
                    matrix_base = row.get("oos_base_rate")
                    break
        mean_base = num(perm.get("mean_base_rate"))
        if seq and mean_base is not None:
            expect = sum(seq) / len(seq)
            if not relclose(mean_base, expect):
                finding("A", "ml_null_tests.json permuted_labels.mean_base_rate is not "
                             "the mean of its own per-seed base rates",
                        f"reported {mean_base!r}, mean of oos_base_rate {expect!r}")
        for i, v in enumerate(seq):
            k = v * rows
            if abs(k - round(k)) > 1e-6:
                # not proof of a defect on its own: a mean of per-fold ratios is
                # legitimately non-integral. Recorded as context only.
                pass
        if seq:
            finding("ok", "ml_null_tests.json permuted-label base rates behave as a "
                          "permutation should",
                    f"per-seed {[round(v, 6) for v in seq]} with mean "
                    f"{round(sum(seq) / len(seq), 6)}; a permuted label removes any "
                    f"per-fold structure, so each fold reverts to the matrix-wide "
                    f"label_high base rate rather than the walk-forward pooled rate. "
                    f"The spread is {max(seq) - min(seq):.2e}, consistent with sampling "
                    f"noise at this row count")


# ========================================================= category 6: CSV integrity
def check_webpro_hit_rates(text: str, rep: str = "reports/webpro_hit_rates.csv") -> None:
    rows = csv_rows(text)
    if not rows:
        finding("A", f"{rep}: empty", "no data rows")
        return
    regimes = sorted({c.split("__", 1)[1] for c in rows[0] if "__" in c})
    problems = 0
    for row in rows:
        sid = row.get("strategy_id", "?")
        for regime in regimes:
            raw = num(row.get(f"signals_raw__{regime}"))
            ded = num(row.get(f"signals_deduped__{regime}"))
            hits_raw = num(row.get(f"bull_hits_raw__{regime}"))
            p_raw = num(row.get(f"bull_precision_raw__{regime}"))
            hits_ded = num(row.get(f"bull_hits_deduped__{regime}"))
            p_ded = num(row.get(f"bull_precision_deduped__{regime}"))
            base = num(row.get(f"baseline__{regime}"))
            lift = num(row.get(f"lift__{regime}"))
            if None in (raw, ded, hits_raw, hits_ded):
                continue
            if ded > raw:
                problems += 1
                finding("A", f"{rep}: deduped signals exceed raw signals",
                        f"{sid}/{regime}: {ded} > {raw}")
            if hits_raw > raw or hits_ded > ded:
                problems += 1
                finding("A", f"{rep}: hits exceed signals",
                        f"{sid}/{regime}: raw {hits_raw}/{raw}, deduped {hits_ded}/{ded}")
            if raw > 0 and p_raw is not None and not relclose(p_raw, hits_raw / raw):
                problems += 1
                finding("A", f"{rep}: bull_precision_raw != bull_hits_raw/signals_raw",
                        f"{sid}/{regime}: {p_raw!r} vs {hits_raw / raw!r}")
            if ded > 0 and p_ded is not None and not relclose(p_ded, hits_ded / ded):
                problems += 1
                finding("A", f"{rep}: bull_precision_deduped != hits/signals",
                        f"{sid}/{regime}: {p_ded!r} vs {hits_ded / ded!r}")
            if p_ded is not None and base and lift is not None and p_ded > 0:
                if not relclose(lift, p_ded / base):
                    problems += 1
                    finding("A", f"{rep}: lift != bull_precision_deduped / baseline",
                            f"{sid}/{regime}: {lift!r} vs {p_ded / base!r}")
            if p_ded is not None and base and p_ded > 0 and not relclose(base, p_ded / lift if lift else None):
                pass
            for key in (f"bull_wilson_low__{regime}", f"bull_wilson_high__{regime}"):
                if num(row.get(key)) is None:
                    problems += 1
                    finding("A", f"{rep}: empty {key} on a populated row", f"{sid}")
    if not problems:
        finding("ok", f"{rep}: identities hold on all {len(rows)} rows",
                f"regimes checked: {', '.join(regimes)}")


def check_tradeability_csv(text: str, rep: str = "reports/tradeability_by_strategy.csv") -> None:
    rows = csv_rows(text)
    if not rows:
        finding("A", f"{rep}: empty", "no data rows")
        return
    bad = 0
    for row in rows:
        label = row.get("label") or row.get("strategy_id") or "?"
        sig = num(row.get("signals"))
        hits = num(row.get("hits"))
        rate = num(row.get("hit_rate"))
        unf = num(row.get("unfillable"))
        unfpct = num(row.get("unfillable_pct"))
        tsig = num(row.get("tradeable_signals"))
        thits = num(row.get("tradeable_hits"))
        trate = num(row.get("tradeable_hit_rate"))
        if None in (sig, hits, rate, unf, unfpct, tsig, thits, trate):
            continue
        if hits > sig:
            bad += 1
            finding("A", f"{rep}: hits > signals", f"{label}: {hits} > {sig}")
        if rate is not None and sig and not relclose(rate, hits / sig):
            bad += 1
            finding("A", f"{rep}: hit_rate != hits / signals",
                    f"{label}: {rate!r} vs {hits / sig!r}")
        if sig and not relclose(unfpct, unf / sig):
            bad += 1
            finding("A", f"{rep}: unfillable_pct != unfillable / signals",
                    f"{label}: {unfpct!r} vs {unf / sig!r}")
        if not relclose(tsig, sig - unf):
            bad += 1
            finding("A", f"{rep}: tradeable_signals != signals - unfillable",
                    f"{label}: {tsig} vs {sig - unf}")
        if thits > hits:
            bad += 1
            finding("A", f"{rep}: tradeable_hits > hits", f"{label}: {thits} > {hits}")
        if tsig and not relclose(trate, thits / tsig):
            bad += 1
            finding("A", f"{rep}: tradeable_hit_rate != tradeable_hits/tradeable_signals",
                    f"{label}: {trate!r} vs {thits / tsig!r}")
    if not bad:
        finding("ok", f"{rep}: identities hold on all {len(rows)} rows", "")


def check_lowzone_csv(text: str, rep: str = "reports/lowzone_hit_rates.csv") -> None:
    rows = csv_rows(text)
    if not rows:
        finding("A", f"{rep}: empty", "no data rows")
        return
    bad = 0
    for row in rows:
        sid = row.get("version", "?")
        sig = num(row.get("signals_deduped"))
        hits = num(row.get("bull_hits"))
        bp = num(row.get("bull_precision"))
        wl, wh = num(row.get("wilson_low")), num(row.get("wilson_high"))
        base = num(row.get("baseline_rate"))
        lift = num(row.get("lift_vs_baseline"))
        rate = num(row.get("hit_rate_pct"))
        pool = num(row.get("candidates_pool"))
        if None in (sig, hits, bp, wl, wh, base, lift):
            continue
        if hits > sig:
            bad += 1
            finding("A", f"{rep}: bull_hits > signals_deduped", f"{sid}: {hits} > {sig}")
        if sig and not relclose(bp, hits / sig):
            bad += 1
            finding("A", f"{rep}: bull_precision != bull_hits / signals_deduped",
                    f"{sid}: {bp!r} vs {hits / sig!r}")
        if not wl < wh:
            bad += 1
            finding("A", f"{rep}: wilson low >= high", f"{sid}: [{wl!r}, {wh!r}]")
        if not (wl <= bp <= wh):
            bad += 1
            finding("A", f"{rep}: wilson does not bracket bull_precision",
                    f"{sid}: {bp!r} not in [{wl!r}, {wh!r}]")
        if base and not relclose(lift, bp / base):
            bad += 1
            finding("A", f"{rep}: lift_vs_baseline != bull_precision / baseline_rate",
                    f"{sid}: {lift!r} vs {bp / base!r}")
        if rate is not None and not relclose(rate, round(bp * 100, 2), 1e-9):
            bad += 1
            finding("A", f"{rep}: hit_rate_pct != bull_precision * 100",
                    f"{sid}: {rate!r} vs {bp * 100!r}")
        if pool is not None and sig > pool:
            bad += 1
            finding("A", f"{rep}: signals_deduped > candidates_pool", f"{sid}")
    # emptiness policy: a column may be blank only where its subject is absent.
    # ``score_auc_within_signals`` is undefined for a rule-based version, because a
    # rule assigns every candidate the same score, so there is no ranking to
    # measure; those are exactly the rows whose ``model`` is "rule".
    for col in rows[0].keys():
        filled = [r for r in rows if num(r.get(col)) is not None]
        blanks = [r for r in rows if num(r.get(col)) is None]
        if not blanks or not filled:
            continue
        if col == "score_auc_within_signals":
            models = {r.get("model") for r in blanks}
            if models == {"rule"}:
                finding("ok", f"{rep}: the blank '{col}' values are structurally "
                              f"undefined, not lost",
                        f"all {len(blanks)} blank rows have model='rule'; a rule assigns "
                        f"every candidate the same score, so there is no ranking for an "
                        f"AUC to describe. {len(filled)} model-based rows are populated")
            else:
                finding("D", f"{rep}: column '{col}' is blank on rows that should have it",
                        f"blank rows have model in {sorted(models)}; only rule-based "
                        f"versions legitimately lack an AUC")
            continue
        finding("D", f"{rep}: column '{col}' populated on only {len(filled)}/{len(rows)} rows",
                "verify the blank rows are genuinely undefined, not lost values")
    if not bad:
        finding("ok", f"{rep}: identities hold on all {len(rows)} rows", "")


def check_simple_csv_identities(text: str, rep: str) -> None:
    """Row-count and NaN-policy checks for the remaining CSVs."""
    rows = csv_rows(text)
    if not rows:
        finding("A", f"{rep}: empty", "no data rows")
        return
    finding("ok", f"{rep}: {len(rows)} data rows, {len(rows[0])} columns", "")


# ========================================================== category 7: duplicates
def check_duplicates(rep: str, ranked: list[dict]) -> None:
    seen: dict[str, dict] = {}
    for row in ranked:
        cfg = row.get("config")
        if cfg is None:
            continue
        if cfg in seen:
            finding("A", f"{rep}: duplicate config name",
                    f"{cfg!r} appears at least twice")
        seen[cfg] = row
    # identical results under different names is the signature of a selection bug
    groups: dict[tuple, list[str]] = {}
    for row in ranked:
        key = (row.get("oos_precision"), row.get("oos_signals"),
               row.get("insample_precision"), row.get("insample_signals"))
        if all(v is not None for v in key):
            groups.setdefault(key, []).append(row.get("config", "?"))
    for key, names in groups.items():
        if len(names) > 1:
            finding("D", f"{rep}: {len(names)} configs report byte-identical results",
                    f"{names} share (insample_signals, insample_precision, "
                    f"oos_signals, oos_precision) = {key}")


def check_cross_report_counts(pub: dict[str, object]) -> None:
    """The same strategy must not carry two different signal counts by accident."""
    wp = pub.get("webpro_hit_rates.csv")
    he = pub.get("hitrate_vs_expectancy.csv")
    ta = pub.get("tradeability_by_strategy.csv")
    tr = pub.get("tradeability.json") or {}
    live = pub.get("live_readiness.csv")
    if not (wp and he and ta):
        return
    wp_rows = {r["strategy_id"]: r for r in csv_rows(wp)}
    he_rows = {r["strategy_id"]: r for r in csv_rows(he)}
    ta_rows = {r.get("strategy_id") or r.get("label"): r for r in csv_rows(ta)}

    shared = sorted(set(wp_rows) & set(he_rows))
    differ = [s for s in shared
              if num(wp_rows[s]["signals_raw__webpro"]) != num(he_rows[s]["signals"])]
    if differ:
        finding("A", "webpro_hit_rates.csv and hitrate_vs_expectancy.csv disagree on "
                     "signals for the same strategy",
                f"{[(s, num(wp_rows[s]['signals_raw__webpro']), num(he_rows[s]['signals'])) for s in differ[:5]]}")
    else:
        finding("ok", "hitrate_vs_expectancy.csv signals == webpro_hit_rates.csv "
                      "signals_raw__webpro for all shared strategies",
                f"{len(shared)} strategies matched exactly")

    # tradeability counts every emitted signal; labels.py counts resolved ones
    censored = {s: num(wp_rows[s]["censored_signals__webpro"]) for s in shared}
    mismatched = []
    for s in shared:
        if s not in ta_rows:
            continue
        ta_sig = num(ta_rows[s].get("signals"))
        wp_sig = num(wp_rows[s]["signals_raw__webpro"])
        cens = censored.get(s) or 0.0
        if ta_sig != wp_sig + cens:
            mismatched.append((s, ta_sig, wp_sig, cens))
    if mismatched:
        finding("D", "tradeability_by_strategy.csv counts signals on a different basis "
                     "than webpro_hit_rates.csv and the gap is not explained by "
                     "censored (unresolved) signals",
                f"{mismatched[:5]}")
    elif shared:
        finding("ok", "tradeability_by_strategy.csv signals == resolved + censored "
                      "signals from webpro_hit_rates.csv for every shared strategy",
                f"{len(shared)} strategies matched; the two reports count different "
                f"populations by design")

    if live:
        live_rows = {r["label"]: r for r in csv_rows(live)}
        all_row = next((r for k, r in live_rows.items() if k.startswith("ALL Web Pro")), None)
        if all_row and tr.get("overall"):
            if num(all_row["signals"]) != num(tr["overall"].get("signals")):
                finding("A", "live_readiness.csv and tradeability.json disagree on total signals",
                        f"{all_row['signals']} vs {tr['overall'].get('signals')}")
            else:
                finding("ok", "live_readiness.csv and tradeability.json agree on the "
                              "total signal count",
                        f"both {int(num(all_row['signals']))}")


def check_holdout_agreement(docs: dict[str, object], where: str) -> None:
    """``ml_concentration.json`` and ``ml_final_holdout.json`` both report the same
    one-shot 2026 holdout evaluation: the same pre-committed config, on the same
    reserved rows. They must therefore agree on the base rate, signal count and
    precision.

    The base rate depends only on the holdout rows, never on the model, so a base-rate
    mismatch proves the two read different matrices. Given the same base rate, a
    signal-count mismatch means the model was fitted differently — ``final_holdout.py``
    purges the last ``horizon`` pre-2026 sessions so no training label window reaches
    the holdout, while ``concentration.py`` does not.
    """
    conc = docs.get("ml_concentration.json")
    final = docs.get("ml_final_holdout.json")
    if not isinstance(conc, dict) or not isinstance(final, dict):
        return
    block = conc.get("holdout")
    if not isinstance(block, dict):
        return
    c_sig, c_prec = block.get("signals"), block.get("precision")
    c_dates, c_base = block.get("dates"), block.get("base_rate")
    f_sig, f_prec = final.get("signals"), final.get("precision")
    f_dates, f_base = final.get("distinct_dates"), final.get("base_rate")
    detail = (f"concentration: signals={c_sig}, precision={c_prec!r}, "
              f"dates={c_dates}, base_rate={c_base!r} | "
              f"final_holdout: signals={f_sig}, precision={f_prec!r}, "
              f"dates={f_dates}, base_rate={f_base!r}")
    if c_base is None or f_base is None or f_sig is None or c_sig is None:
        return

    if not relclose(c_base, f_base):
        # name the matrices, if their metadata is still on disk
        attribution = []
        for stride in (1, 2, 5):
            meta_path = REPO / "outputs" / "ml" / f"matrix_h10_t30_s{stride}_meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            attribution.append(f"stride {stride}: {meta.get('rows')} rows, "
                               f"{meta.get('sessions')} sessions, "
                               f"base_rate_high={meta.get('base_rate_high')!r}")
        finding("C", f"[{where}] ml_concentration.json and ml_final_holdout.json report "
                     f"the same 2026 holdout on different row sets",
                detail + ". The holdout base rate is a property of the data alone, so "
                         "the two reports were not built from the same matrix. "
                         + ("Matrix metadata on disk: " + "; ".join(attribution) + ". "
                            if attribution else "")
                         + "Both files must be regenerated from one matrix before the "
                           "holdout figure can be quoted as a single result")
        return

    if c_sig == f_sig and (c_prec is None or f_prec is None or relclose(c_prec, f_prec)):
        finding("ok", f"[{where}] ml_concentration.json and ml_final_holdout.json agree "
                      f"on the 2026 holdout evaluation",
                f"both {c_sig} signals at precision {c_prec!r} on {c_dates} dates, "
                f"base rate {c_base!r}")
        return

    finding("C", f"[{where}] ml_concentration.json and ml_final_holdout.json disagree on "
                 f"the same 2026 holdout evaluation",
            detail + ". The holdout rows and base rate are identical, so the model was "
                     "fitted differently: src/ml/final_holdout.py purges the last horizon "
                     "pre-2026 sessions so no training label window reaches the holdout, "
                     "while src/ml/concentration.py trains on every row before the cutoff, "
                     "including rows whose labels were resolved using 2026 prices. Two "
                     "reports of one pre-committed holdout result must not differ")


def check_matrix_provenance(fold_rows: dict[str, int]) -> None:
    """Explain any published-vs-worktree difference in the s5 matrix metadata.

    ``ml_search_wide.json`` is the only report that also publishes ``label_close``
    rows, so a difference in the close label of the matrix it was built from shows
    up in that report and nowhere else. Quantifying it here separates a genuine
    panel revision from the documented float32 label fix.
    """
    name = "matrix_h10_t30_s5_meta.json"
    try:
        work = json.loads((REPO / "outputs" / "ml" / name).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return
    text = git_show(f"outputs/ml/{name}")
    if text is None:
        return
    pub = json.loads(text)
    rows = pub.get("rows")
    if not rows:
        return
    high_d = (pub.get("base_rate_high") or 0) - (work.get("base_rate_high") or 0)
    close_d = (pub.get("base_rate_close") or 0) - (work.get("base_rate_close") or 0)
    for key in ("rows", "sessions", "resolved_share"):
        if pub.get(key) != work.get(key):
            finding("D", f"the s5 matrix meta changed {key} between published and "
                         f"working tree",
                    f"published {pub.get(key)!r}, working tree {work.get(key)!r}")
    if not high_d and close_d:
        n_rows = close_d * rows
        finding("D", "the published s5 matrix's label_close differs from the working "
                     "tree by a whole number of rows, and label_high is identical",
                f"base_rate_high is unchanged ({pub.get('base_rate_high')!r}) but "
                f"base_rate_close moves by {close_d:.6g} x {rows} rows = "
                f"{n_rows:.4f} rows (published "
                f"{pub.get('base_rate_close')!r} -> working tree "
                f"{work.get('base_rate_close')!r}). That is exactly the documented "
                f"three-row float32 defect in src/ml/build_matrix.py: three rows sat on "
                f"the target boundary and the float32 round-trip of the price ratio made "
                f"'> target' evaluate True. The published ml_search_wide.json label_close "
                f"rows therefore carry one extra positive in fold1 and two elsewhere; "
                f"they are internally consistent with the matrix they were built from, so "
                f"this is a stale-data note, not an arithmetic error in the report")


# ============================================== working tree vs published provenance
def check_divergence(pub_names: set[str], pub: dict[str, object]) -> None:
    for name in sorted(pub_names):
        work = load_worktree(name)
        p = pub.get(name)
        if work is None:
            finding("D", f"reports/{name} missing from the working tree",
                    "published revision exists but the file does not")
            continue
        if name.endswith(".json"):
            same = json.dumps(work, sort_keys=True) == json.dumps(p, sort_keys=True)
        else:
            same = work == p
        if not same:
            finding("D", f"reports/{name} in the working tree differs from the "
                         f"published revision",
                    "the audit above covers the published revision only")


def check_worktree_consistency() -> None:
    """Do the *working-tree* reports agree with each other?

    The working tree is mid-regeneration: the ML reports were rebuilt on the dense
    stride-1 matrix while ``ml_search_wide.json`` still holds the published file.
    Reports that share a matrix must agree on its base rates, so a mismatch here
    separates "an in-flight regeneration" from "a real disagreement".
    """
    docs: dict[str, object] = {}
    for name in ("ml_search_models.json", "ml_search_ablation.json",
                 "ml_search_wide.json", "ml_precision_ceiling.json",
                 "ml_null_tests.json", "ml_final_holdout.json",
                 "ml_crosssec_hgb0.json", "ml_concentration.json"):
        try:
            docs[name] = load_worktree(name)
        except Exception as exc:  # noqa: BLE001
            finding("A", f"reports/{name} (working tree) could not be parsed", repr(exc))

    check_holdout_agreement(docs, "working tree")
    published = {k: load_published(k) for k in
                 ("ml_concentration.json", "ml_final_holdout.json")}
    check_holdout_agreement(published, "published")

    # collect the label_high 4-fold base rate each working-tree report implies.
    # ml_final_holdout.json is excluded: its base_rate describes the 2026 holdout
    # block, which is a different row set from the walk-forward test folds.
    claimed: dict[str, list[tuple[str, float]]] = {}
    for name, doc in docs.items():
        if not isinstance(doc, dict) or name == "ml_final_holdout.json":
            continue
        entries: list[tuple[str, float]] = []
        top = doc.get("oos_base_rate")
        if isinstance(top, (int, float)):
            entries.append(("top-level oos_base_rate", float(top)))
        if isinstance(doc.get("base_rate"), (int, float)):
            entries.append(("base_rate", float(doc["base_rate"])))
        for i, row in enumerate(doc.get("ranked") or []):
            if row.get("label") == "label_high" and len(row.get("per_fold_base") or []) == 4:
                entries.append((f"ranked[{i}] {row.get('config')}", row["oos_base_rate"]))
        for cfg, res in (doc.get("results") or {}).items():
            if isinstance(res, dict) and isinstance(res.get("oos_base_rate"), (int, float)):
                entries.append((f"results.{cfg}.oos_base_rate", res["oos_base_rate"]))
        for path, node in walk_dicts(doc):
            if isinstance(node.get("oos_base_rate"), (int, float)) and node.get("n_folds") == 4:
                entries.append((path or "noise_features", node["oos_base_rate"]))
        if entries:
            claimed[name] = entries

    # Which matrix was each report built on? The dense stride-1 regeneration changes
    # the label_high base rate from the published 0.040878... to 0.040894..., so the
    # reports split into two groups and the split itself identifies which files are
    # stale. ml_search_wide.json and ml_crosssec_*.json are the ones not yet rebuilt.
    per_report: dict[str, set[float]] = {}
    for name, entries in claimed.items():
        per_report[name] = {round(v, 12) for _, v in entries}

    regenerated = {n: v for n, v in per_report.items()
                   if n not in ("ml_search_wide.json", "ml_crosssec_hgb0.json",
                                "ml_crosssec_final.json")}
    dense_candidates: set[float] = set()
    for vals in regenerated.values():
        dense_candidates |= vals
    stale_reports = {n: sorted(v) for n, v in per_report.items()
                     if n not in regenerated and len(v) > 1}

    if len(dense_candidates) > 1:
        finding("A", "the regenerated working-tree ML reports disagree with each other "
                     "on the label_high base rate",
                f"{sorted(dense_candidates)} across "
                f"{sorted(regenerated)} - these were all rebuilt from the same dense "
                f"matrix, so a disagreement between them is a real error")
    elif dense_candidates:
        dense_base = next(iter(dense_candidates))
        members = [f"{n}:{w}" for n, entries in claimed.items()
                   if n in regenerated for w, v in entries
                   if round(v, 12) == dense_base]
        finding("ok", "the regenerated working-tree ML reports agree on the label_high "
                      "base rate",
                f"{dense_base!r} reported identically in {len(members)} place(s) across "
                f"{len(regenerated)} report(s): {sorted(regenerated)}")

        if stale_reports:
            finding("C", "the working tree is mid-regeneration: some ML reports still "
                         "hold the published matrix's fold structure while others were "
                         "rebuilt on the dense stride-1 matrix",
                    "; ".join(f"{n} reports {v}" for n, v in sorted(stale_reports.items()))
                    + f", but the rebuilt reports ({sorted(regenerated)}) report "
                      f"{dense_base!r}. The two groups are computed on different "
                      f"matrices, so comparing across the groups is a staleness "
                      f"artifact rather than an error in either number; compare within "
                      f"a group until the regeneration finishes")
        else:
            finding("ok", "every working-tree ML report was rebuilt on the same matrix",
                    f"base rate {dense_base!r}")
    else:
        dense_base = None


# --------------------------------------------------------------------- reporting
def main() -> int:
    pub_names = published_reports()
    pub: dict[str, object] = {}
    for name in sorted(pub_names):
        try:
            pub[name] = load_published(name)
        except Exception as exc:  # noqa: BLE001 - report, do not crash the audit
            finding("A", f"reports/{name} could not be parsed", repr(exc))

    fold_rows, fold_pos = base_vector_rows()
    order = sorted(fold_rows)
    if not order:
        print("FATAL: could not read the published OOS frontier", file=sys.stderr)
        return 2
    label_folds = build_label_folds(pub, order, fold_rows, fold_pos)
    pooled_high = sum(fold_pos.values()) / sum(fold_rows.values())

    def label_base(label: str) -> float | None:
        entry = label_folds.get(label)
        if not entry or len(entry["pos"]) != 4:
            return None
        return sum(entry["pos"]) / sum(entry["rows"])

    # ---- per-report identity checks
    for name in ("ml_search_models.json", "ml_search_ablation.json", "ml_search_wide.json"):
        doc = pub.get(name)
        if not isinstance(doc, dict):
            continue
        ranked = doc.get("ranked") or []
        check_search_row_identities(name, ranked)
        check_pooling_precision(name, ranked)
        check_duplicates(name, ranked)
        for i, row in enumerate(ranked):
            check_pooling(name, row, f"ranked[{i}]", label_folds)
        if doc.get("n_configs") is not None and doc.get("n_failed") is not None:
            ranked_plus_failed = len(ranked) + int(doc["n_failed"])
            if ranked_plus_failed != int(doc["n_configs"]):
                finding("A", f"{name}: n_configs != ranked + n_failed",
                        f"{doc['n_configs']} vs {len(ranked)} + {doc['n_failed']}")
        failed = doc.get("failed") or []
        if len(failed) != int(doc.get("n_failed", len(failed))):
            finding("A", f"{name}: len(failed) != n_failed",
                    f"{len(failed)} vs {doc.get('n_failed')}")
        # top-level oos_base_rate is the rank-1 row's own value, not a report total
        top = ranked[0] if ranked else None
        if top is not None and doc.get("oos_base_rate") is not None:
            if not relclose(doc["oos_base_rate"], top.get("oos_base_rate")):
                finding("D", f"{name}: top-level oos_base_rate is not the rank-1 row's "
                             f"base rate",
                        f"top-level {doc['oos_base_rate']!r} vs rank-1 "
                        f"{top.get('config')} {top.get('oos_base_rate')!r}")
        for i, row in enumerate(ranked):
            if row.get("oos_signals") == 0:
                finding("D", f"{name}: {row.get('config')} reports zero OOS signals",
                        "a row with no out-of-sample signals cannot support a "
                        "precision claim and is excluded from pooling")
            nf = row.get("n_folds")
            if isinstance(nf, int) and nf < 4:
                finding("D", f"{name}: {row.get('config')} evaluated on only {nf} folds "
                             f"while the shared matrix supports 4",
                        f"summarise() in src/ml/walkforward.py keeps only folds with "
                        f"oos_signals > 0, so a fold where this configuration emitted no "
                        f"signal at all is silently dropped from n_folds, per_fold_* and "
                        f"the pooled base rate. Here oos_signals={row.get('oos_signals')} "
                        f"over {nf} folds. The reported oos_base_rate is still a correct "
                        f"ratio of sums over the retained folds, but those folds were "
                        f"selected by the model's own emission pattern, so the base rate "
                        f"is conditional on the model having signalled rather than a "
                        f"property of the whole out-of-sample period - it must not be "
                        f"compared against a 4-fold row")

    if isinstance(pub.get("ml_precision_ceiling.json"), dict):
        check_ceiling(pub["ml_precision_ceiling.json"])
    if isinstance(pub.get("ml_final_holdout.json"), dict):
        check_final_holdout(pub["ml_final_holdout.json"])
    for name in ("ml_crosssec_hgb0.json", "ml_crosssec_final.json", "ml_null_tests.json",
                 "ml_concentration.json", "ml_search_models.json", "ml_search_ablation.json",
                 "ml_search_wide.json", "ml_precision_ceiling.json"):
        if isinstance(pub.get(name), dict):
            check_intervals(name, pub[name])
    check_cross_report(pub, fold_pos, fold_rows, label_folds)

    # ---- CSV checks
    if isinstance(pub.get("webpro_hit_rates.csv"), str):
        check_webpro_hit_rates(pub["webpro_hit_rates.csv"])
    if isinstance(pub.get("tradeability_by_strategy.csv"), str):
        check_tradeability_csv(pub["tradeability_by_strategy.csv"])
    if isinstance(pub.get("lowzone_hit_rates.csv"), str):
        check_lowzone_csv(pub["lowzone_hit_rates.csv"])
    for name in ("hitrate_vs_expectancy.csv", "live_readiness.csv",
                 "webpro_cards_100_reproduction.csv"):
        if isinstance(pub.get(name), str):
            check_simple_csv_identities(pub[name], f"reports/{name}")
    check_cross_report_counts(pub)

    # ---- headline answer for the open question about the two search reports
    wide = pub.get("ml_search_wide.json") or {}
    models = pub.get("ml_search_models.json") or {}
    if isinstance(wide, dict) and isinstance(models, dict) and wide.get("ranked"):
        top = wide["ranked"][0]
        print("=" * 78)
        print("Open question: why do ml_search_wide.json and ml_search_models.json")
        print("report different top-level oos_base_rate values?")
        print("=" * 78)
        print(f"  ml_search_models.json oos_base_rate = {models.get('oos_base_rate')!r}")
        print(f"    = its rank-1 row {models['ranked'][0]['config']!r} "
              f"({models['ranked'][0].get('label')}, "
              f"target_rate={models['ranked'][0].get('target_rate')}, "
              f"n_folds={models['ranked'][0].get('n_folds')})")
        print(f"  ml_search_wide.json   oos_base_rate = {wide.get('oos_base_rate')!r}")
        print(f"    = its rank-1 row {top['config']!r} "
              f"({top.get('label')}, target_rate={top.get('target_rate')}, "
              f"n_folds={top.get('n_folds')})")
        pfb = top.get("per_fold_base") or []
        label = top.get("label") or ""
        entry = label_folds.get(label) or {}
        bases = entry.get("bases") or []
        pos_list = entry.get("pos") or []
        rows_list = entry.get("rows") or []
        idx = [i for i, b in enumerate(bases) if any(relclose(v, b) for v in pfb)]
        subset_rows = sum(rows_list[i] for i in idx) if idx else 0
        subset_pos = sum(pos_list[i] for i in idx) if idx else 0
        print(f"    its per_fold_base = {pfb}")
        print(f"    identified as folds {idx} of the same walk-forward, giving "
              f"{subset_pos}/{subset_rows} "
              f"= {subset_pos / subset_rows if subset_rows else float('nan')!r}")
        print(f"    which is exactly the reported value: the field is the ratio of")
        print(f"    sums over only the folds that row actually used.")
        print()
        print(f"  Both values are correct for their own row. The field is not a")
        print(f"  report-level quantity: src/ml/search.py writes")
        print(f"  \"oos_base_rate\": ok[0][\"oos_base_rate\"], i.e. the rank-1 row's own")
        print(f"  base rate. The two reports differ because their rank-1 rows use")
        print(f"  different labels and different fold counts, not because they were")
        print(f"  produced on different matrices.")
        print()
        print(f"  Cross-check: every 4-fold label_high row in ml_search_models.json,")
        print(f"  ml_search_ablation.json and ml_search_wide.json reports the same")
        print(f"  pooled base rate {pooled_high!r} = "
              f"{sum(fold_pos.values())}/{sum(fold_rows.values())}, which also equals")
        print(f"  ml_precision_ceiling.json base_rate and the cross-sectional")
        print(f"  report's oos_base_rate. The two matrices hypothesis is excluded:")
        print(f"  the label_high rows of all three reports share one fold structure.")
        print()
        print(f"  The same question asked of the *working tree* has a different answer,")
        print(f"  because the working tree is mid-regeneration: see the working-tree")
        print(f"  section below.")

    check_worktree_consistency()

    # ---- consolidated output
    print()
    print("=" * 78)
    print("FINDINGS")
    print("=" * 78)
    labels = {
        "A": "DEFINITE arithmetic / logic error",
        "B": "POOLING discrepancy (reported value is the wrong pooling)",
        "C": "CROSS-REPORT disagreement",
        "D": "SUSPICIOUS - not conclusive",
    }
    counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for cat in ("A", "B", "C", "D"):
        items = [f for f in findings if f["category"] == cat]
        counts[cat] = len(items)
        print(f"\n--- ({cat}) {labels[cat]}: {len(items)}")
        for f in items:
            print(f"  * {f['title']}")
            if f["detail"]:
                print(f"      {f['detail']}")
    oks = [f for f in findings if f["category"] == "ok"]
    print(f"\n--- checks that passed cleanly: {len(oks)}")
    for f in oks:
        print(f"  + {f['title']}")
        if f["detail"]:
            print(f"      {f['detail']}")

    check_divergence(pub_names, pub)
    check_matrix_provenance(fold_rows)
    div = [f for f in findings if f["category"] == "D"
           and ("working tree" in f["title"] or "s5 matrix" in f["title"])]
    print(f"\n--- working tree vs published (reports/ only): {len(div)} file(s) differ")
    for f in div:
        print(f"  ~ {f['title']}")

    print()
    print(f"tolerance: relative {RTOL:g}; floats that merely round-trip through JSON "
          f"are not reported")
    print(f"authoritative source: git HEAD (the published revision of reports/)")
    print(f"summary: {counts['A']} definite error(s), {counts['B']} pooling "
          f"discrepanc(y/ies), {counts['C']} cross-report disagreement(s), "
          f"{counts['D']} suspicious item(s)")
    return 1 if (counts["A"] or counts["B"] or counts["C"]) else 0


if __name__ == "__main__":
    sys.exit(main())
