"""Locate how TARGET_70PCT.md's recall-floor table was computed.

The table claims, per recall floor, a max precision and a published-signal count:

    >=50%  11.46%   43,989
    >=30%  13.42%   23,834
    >=20%  14.15%   15,436
    >=10%  16.64%    7,493
    >= 5%  19.42%    3,831
    >= 2%  28.57%      735

Recomputing the obvious rule (per fold take the highest-precision row whose
recall meets the floor, then pool hits/published) gives 8.53%/342,529 for the 50%
floor, so the published table uses some other rule. This script tests candidate
rules against the stated pairs and reports which one reproduces them.
"""
from __future__ import annotations

import csv
import io
import itertools

DOC = {
    0.50: (11.46, 43989),
    0.30: (13.42, 23834),
    0.20: (14.15, 15436),
    0.10: (16.64, 7493),
    0.05: (19.42, 3831),
    0.02: (28.57, 735),
}


def load(name):
    return list(csv.DictReader(io.open(f"reports/{name}", encoding="utf-8")))


def pool(sel):
    """precision pooled over selected rows, and total published."""
    pub = sum(int(r["n_published"]) for r in sel)
    if pub == 0:
        return 0.0, 0
    hits = sum(round(float(r["precision"]) * int(r["n_published"])) for r in sel)
    return 100.0 * hits / pub, pub


def main() -> None:
    oos = load("ml_precision_frontier_oos.csv")
    ins = load("ml_precision_frontier_insample.csv")
    folds = sorted({r["fold"] for r in oos})
    print(f"folds in oos frontier: {len(folds)}")
    for f in folds:
        print("   ", f)

    def try_rule(label, picker):
        ok = 0
        out = []
        for floor, (want_p, want_n) in DOC.items():
            sel = picker(floor)
            if not sel:
                out.append(f"    floor {floor:.2f}: no rows")
                continue
            p, n = pool(sel)
            hit = abs(p - want_p) < 0.02 and abs(n - want_n) < 2
            ok += hit
            out.append(f"    floor {floor:.2f}: got {p:6.2f}% / {n:7,}   "
                       f"doc {want_p:6.2f}% / {want_n:7,}   "
                       f"{'MATCH' if hit else ''}")
        print(f"\n  [{label}] {ok}/6 match")
        for line in out:
            print(line)

    # Rule A: pooled - best precision row per fold under the recall floor.
    def rule_a(floor):
        sel = []
        for f in folds:
            cand = [r for r in oos if r["fold"] == f and float(r["recall"]) >= floor]
            if cand:
                sel.append(max(cand, key=lambda r: float(r["precision"])))
        return sel

    # Rule B: single global row (no per-fold split) maximising precision.
    def rule_b(floor):
        cand = [r for r in oos if float(r["recall"]) >= floor]
        return [max(cand, key=lambda r: float(r["precision"]))] if cand else []

    # Rule C: sum published across folds for every row meeting the floor, take the
    # pooled precision of the whole prefix (i.e. publish everything above floor).
    def rule_c(floor):
        return [r for r in oos if float(r["recall"]) >= floor]

    # Rule D: same as A but on the in-sample frontier.
    def rule_d(floor):
        sel = []
        for f in folds:
            cand = [r for r in ins if r["fold"] == f and float(r["recall"]) >= floor]
            if cand:
                sel.append(max(cand, key=lambda r: float(r["precision"])))
        return sel

    # Rule E: per fold the single highest precision anywhere, subject to the
    # POOLED recall (sum hits / sum positives) meeting the floor.
    for label, fn in (("A per-fold best precision, pooled", rule_a),
                      ("B one global best-precision row", rule_b),
                      ("C all rows meeting floor, pooled", rule_c),
                      ("D in-sample per-fold best", rule_d)):
        try_rule(label, fn)

    # Rule F: brute-force search for which 4 rows (one per fold) reproduce a
    # stated (precision, published) pair, to learn the real selection rule.
    print("\n  [F] brute force: which rows reproduce the 50% row 11.46%/43,989?")
    for f in folds:
        rows = [r for r in oos if r["fold"] == f]
        # rows whose published count is near a quarter of 43,989
        near = [r for r in rows if abs(int(r["n_published"]) - 43989 / len(folds)) < 43989]
        print(f"    {f}: {len(rows)} rows, {len(near)} near a quarter of the total")


if __name__ == "__main__":
    main()
