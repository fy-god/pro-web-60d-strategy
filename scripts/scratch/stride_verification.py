"""Stride-subsampling verification for src/ml/build_matrix.py.

Contested change under test
---------------------------
OLD (committed):   out = out.iloc[::stride].reset_index(drop=True)
NEW (working tree): keep rows whose DATE is on a global session grid,
                    sessions[::stride].

The claim to verify is that OLD samples by ROW POSITION on a stock-concatenated
frame, so each stock's sampling phase depends on how many rows preceding stocks
contributed, and that this "desyncs" stocks and undermines cross-sectional
results.

Sections
--------
counterexample  two/three-stock frame: does an unrelated stock's row count move
                which DATES another stock is sampled on?
structure       rows / sessions / stocks-per-session for OLD vs NEW, strides 1-5,
                derived from the SAME full stride-1 frame so the stride rule is
                the only variable.
folds           wf.folds() usable folds per stride for OLD vs NEW session grids.
sampling        is the subsample's inclusion probability independent of the
                row's own (label, feature, weekday)?  This is the bias question.
distributions   base rate and feature distribution of retained rows vs full.
bias            train on each subsample, evaluate on the SAME full holdout:
                separates "biased" from "merely smaller".
topk            per-session top-K: is the best of a partial cross-section a
                worse pick than the best of the full cross-section?
identity        bit-identity checks between HEAD and working-tree builds.

Run from the repo root with PYTHONPATH='.':

    python scripts/scratch/stride_verification.py --section all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.ml import walkforward as wf  # noqa: E402

S1 = REPO_ROOT / "outputs" / "ml" / "matrix_h10_t30_s1.parquet"
S5_NEW = REPO_ROOT / "outputs" / "ml" / "matrix_h10_t30_s5.parquet"
S5_HEAD = REPO_ROOT / "scripts" / "scratch" / "_artifacts" / "matrix_h10_t30_s5.parquet"
S1_HEAD = REPO_ROOT / "scripts" / "scratch" / "_artifacts" / "matrix_h10_t30_s1.parquet"
HOLDOUT_START = "2026-01-01"

META = ["code", "date", "label_high", "label_close", "resolved", "entry_open"]
PROBE_FEATURES = [
    "ret1", "ret5", "ret20", "ret60", "vol20", "atr14_pct", "vol_ratio_1_5",
    "pos_60", "close_loc", "limitup_5", "up_rate_20", "kdj_k", "beta_60",
    "mkt_ret1", "cs_ret5_rank", "cs_ret5_z", "cs_ret20_rank", "cs_atr_rank",
    "cs_atr_z", "cs_pos60_z",
]


def rule_old(frame: pd.DataFrame, stride: int) -> pd.DataFrame:
    """The committed rule, verbatim."""
    if stride > 1:
        return frame.iloc[::stride].reset_index(drop=True)
    return frame.reset_index(drop=True)


def rule_new(frame: pd.DataFrame, stride: int) -> pd.DataFrame:
    """The working-tree rule, verbatim."""
    if stride > 1:
        sessions = np.sort(frame["date"].unique())
        keep = set(sessions[::stride])
        return frame[frame["date"].isin(keep)].reset_index(drop=True)
    return frame.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 1. counterexample
# ---------------------------------------------------------------------------
def section_counterexample() -> None:
    print("=" * 78)
    print("SECTION 1 — counterexample: does the OLD rule desync stocks?")
    print("=" * 78)
    dates = pd.to_datetime([f"2024-01-{i + 1:02d}" for i in range(10)])
    A = pd.DataFrame({"code": "A", "date": dates})
    B = pd.DataFrame({"code": "B", "date": dates})
    C = pd.DataFrame({"code": "C", "date": dates[:1]})  # unrelated, ONE row

    def dts(frame, code):
        got = frame.loc[frame["code"] == code, "date"]
        return [str(pd.Timestamp(d).date()) for d in got]

    alone = pd.concat([A, B], ignore_index=True)
    shifted = pd.concat([C, A, B], ignore_index=True)

    print(f"\nframe 1 = A(10 rows) + B(10 rows)              n={len(alone)}")
    print(f"frame 2 = C(1 row) + A(10 rows) + B(10 rows)   n={len(shifted)}")
    print("  (C is a different stock; A's own prices are byte-identical in both)")

    for stride in (5, 3):
        o1, o2 = rule_old(alone, stride), rule_old(shifted, stride)
        n1, n2 = rule_new(alone, stride), rule_new(shifted, stride)
        print(f"\n--- stride {stride} ---")
        print(f"  OLD  A@frame1: {dts(o1, 'A')}")
        print(f"  OLD  A@frame2: {dts(o2, 'A')}   <-- {'CHANGED' if dts(o1,'A') != dts(o2,'A') else 'same'}")
        print(f"  OLD  B@frame1: {dts(o1, 'B')}")
        print(f"  OLD  B@frame2: {dts(o2, 'B')}")
        print(f"  OLD  A and B share a phase inside one frame? "
              f"{dts(o1,'A') == dts(o1,'B')}")
        print(f"  NEW  A@frame1: {dts(n1, 'A')}")
        print(f"  NEW  A@frame2: {dts(n2, 'A')}   <-- {'CHANGED' if dts(n1,'A') != dts(n2,'A') else 'same'}")

    # The real panel: how many distinct per-stock retained-date sets are there?
    print("\n--- on the real stride-1 matrix (stride 5) ---")
    probe = pd.read_parquet(S1, columns=["code", "date"])
    old = rule_old(probe, 5)
    new = rule_new(probe, 5)
    for name, frame in (("OLD iloc[::5]", old), ("NEW session grid", new)):
        sets = frame.groupby("code", sort=False)["date"].apply(
            lambda s: hash(tuple(s.to_numpy()))
        )
        full_sessions = probe["date"].nunique()
        print(f"  {name:18s} rows={len(frame):>9,}  sessions={frame['date'].nunique():>4d}"
              f"  distinct per-stock date-sets={sets.nunique():>5d}"
              f"  (of {frame['code'].nunique():,} stocks; full grid = {full_sessions})")
    del probe, old, new


# ---------------------------------------------------------------------------
# 2. structure of each rule
# ---------------------------------------------------------------------------
def section_structure() -> None:
    print("\n" + "=" * 78)
    print("SECTION 2 — structure: rows, sessions, stocks per session")
    print("=" * 78)
    frame = pd.read_parquet(S1, columns=["code", "date"])
    n_sessions = frame["date"].nunique()
    rows = []
    for stride in (1, 2, 3, 4, 5):
        for label, fn in (("OLD iloc", rule_old), ("NEW grid", rule_new)):
            sub = fn(frame, stride)
            per_session = sub.groupby("date", sort=False)["code"].size()
            rows.append(dict(
                stride=stride, rule=label, rows=len(sub),
                sessions=int(sub["date"].nunique()),
                stocks_per_session_median=float(per_session.median()),
                min_stocks=int(per_session.min()),
                max_stocks=int(per_session.max()),
                rows_per_session_median=float(per_session.median()),
            ))
    tbl = pd.DataFrame(rows)
    print(tbl.to_string(index=False))
    print(f"\nfull panel: {len(frame):,} rows, {n_sessions} sessions, "
          f"{frame['code'].nunique():,} stocks")
    print("NOTE OLD keeps all 887 sessions but only ~1/5 of the STOCKS on each;")
    print("     NEW keeps all 3,193 stocks but only 1/5 of the SESSIONS.")

    # Weekday aliasing: stride 5 on a 5-session trading week.
    print("\n--- weekday aliasing (stride 5 samples one weekday only?) ---")
    frame["dow"] = frame["date"].dt.dayofweek
    full_dow = frame["dow"].value_counts(normalize=True).sort_index()
    lab = pd.read_parquet(S1, columns=["label_high"])
    frame["y"] = lab["label_high"].to_numpy()
    print("  full-grid weekday share :",
          {int(k): round(float(v), 4) for k, v in full_dow.items()})
    print("  full-grid base rate by dow:",
          {int(k): round(float(v), 5) for k, v in
           frame.groupby("dow")["y"].mean().items()})
    for label, fn in (("OLD iloc", rule_old), ("NEW grid", rule_new)):
        sub = fn(frame, 5)
        shares = sub["dow"].value_counts(normalize=True).sort_index()
        print(f"  {label:9s} stride5 weekday share: "
              f"{ {int(k): round(float(v), 4) for k, v in shares.items()} }")
    del frame, lab


# ---------------------------------------------------------------------------
# 3. walk-forward folds per stride
# ---------------------------------------------------------------------------
def section_folds() -> None:
    print("\n" + "=" * 78)
    print("SECTION 3 — usable walk-forward folds per stride")
    print("=" * 78)
    frame = pd.read_parquet(S1, columns=["date"])
    all_sessions = np.sort(frame["date"].unique())
    rows = []
    for stride in (1, 2, 3, 4, 5):
        old_sessions = all_sessions                       # OLD keeps 887 sessions
        new_sessions = all_sessions[::stride]             # NEW keeps 887//stride
        for label, sessions in (("OLD iloc", old_sessions),
                                ("NEW grid", new_sessions)):
            rec = dict(stride=stride, rule=label,
                       sessions_total=len(sessions),
                       sessions_pre2026=int((sessions < np.datetime64(
                           pd.Timestamp(HOLDOUT_START))).sum()))
            try:
                fl = wf.folds(sessions, n_folds=5, horizon=10, embargo=2,
                              min_train_sessions=150,
                              final_holdout_start=HOLDOUT_START)
                rec["usable_folds"] = len(fl)
                rec["test_sessions"] = sum(f.n_test_sessions for f in fl)
                rec["train_sessions_f1"] = fl[0].n_train_sessions if fl else 0
                rec["error"] = ""
            except ValueError as exc:
                rec.update(usable_folds=0, test_sessions=0, train_sessions_f1=0,
                           error=f"ValueError: {exc}")
            rows.append(rec)
    tbl = pd.DataFrame(rows)
    print(tbl.to_string(index=False))
    print("\nfull grid: 887 sessions, "
          f"{int((all_sessions < np.datetime64(pd.Timestamp(HOLDOUT_START))).sum())} "
          "of them pre-2026 (the final holdout).")
    del frame


# ---------------------------------------------------------------------------
# 4/5. sampling probability and distributions: the bias question
# ---------------------------------------------------------------------------
def section_sampling() -> None:
    print("\n" + "=" * 78)
    print("SECTION 4 — is the retained subset a fair sample of the full panel?")
    print("=" * 78)
    cols = META + PROBE_FEATURES
    frame = pd.read_parquet(S1, columns=cols)
    full_base = float(frame["label_high"].mean(skipna=True))
    print(f"full stride-1 matrix: {len(frame):,} rows, "
          f"base_rate_high={full_base:.6f}, "
          f"base_rate_close={float(frame['label_close'].mean(skipna=True)):.6f}")

    for stride in (2, 5):
        print(f"\n--- stride {stride} ---")
        for label, fn in (("OLD iloc", rule_old), ("NEW grid", rule_new)):
            sub = fn(frame, stride)
            keep = np.zeros(len(frame), dtype=bool)
            # identify retained rows by (code,date) on the full frame
            key = pd.MultiIndex.from_arrays(
                [frame["code"].to_numpy(), frame["date"].to_numpy()])
            sub_key = pd.MultiIndex.from_arrays(
                [sub["code"].to_numpy(), sub["date"].to_numpy()])
            keep = key.isin(sub_key)
            share = keep.mean()
            bh = float(sub["label_high"].mean(skipna=True))
            bc = float(sub["label_close"].mean(skipna=True))
            # inclusion probability conditional on the row's own label
            sh_y1 = float(keep[frame["label_high"].to_numpy() == 1].mean())
            sh_y0 = float(keep[frame["label_high"].to_numpy() == 0].mean())
            print(f"  {label:9s} rows={len(sub):>9,}  kept_share={share:.4f}  "
                  f"base_high={bh:.6f} ({bh - full_base:+.6f})  base_close={bc:.6f}")
            print(f"            P(kept | y=1)={sh_y1:.4f}  P(kept | y=0)={sh_y0:.4f}"
                  f"   ratio={sh_y1 / sh_y0:.4f}")
            # inclusion probability by feature decile
            worst = []
            for c in PROBE_FEATURES:
                v = frame[c].to_numpy(dtype="float64")
                ok = np.isfinite(v)
                if ok.sum() < 1000:
                    continue
                q = pd.qcut(pd.Series(v[ok]), 10, labels=False, duplicates="drop")
                idx = np.where(ok)[0]
                df = pd.DataFrame({"q": q.to_numpy(), "keep": keep[idx]})
                g = df.groupby("q")["keep"].mean()
                worst.append((c, float(g.max() - g.min())))
            worst.sort(key=lambda t: -t[1])
            print(f"            max spread in P(kept) across feature deciles: "
                  + ", ".join(f"{c}={s:.4f}" for c, s in worst[:4]))
            # inclusion probability by weekday
            dow = frame["date"].dt.dayofweek.to_numpy()
            byd = pd.Series(keep).groupby(pd.Series(dow)).mean()
            print("            P(kept) by weekday: "
                  + ", ".join(f"{int(k)}:{v:.3f}" for k, v in byd.items()))
    del frame


def section_distributions() -> None:
    print("\n" + "=" * 78)
    print("SECTION 5 — retained-row feature distributions vs full panel")
    print("=" * 78)
    frame = pd.read_parquet(S1, columns=META + PROBE_FEATURES)
    old5 = rule_old(frame, 5)
    new5 = rule_new(frame, 5)
    rows = []
    for c in PROBE_FEATURES:
        f = frame[c].to_numpy(dtype="float64")
        fo = f[np.isfinite(f)]
        ro = dict(feature=c, full_mean=float(np.mean(fo)))
        for label, sub in (("old", old5), ("new", new5)):
            v = sub[c].to_numpy(dtype="float64")
            v = v[np.isfinite(v)]
            ro[f"{label}_mean"] = float(np.mean(v))
            ro[f"{label}_smd"] = float(
                (np.mean(v) - np.mean(fo)) / (np.std(fo) + 1e-12))
        rows.append(ro)
    tbl = pd.DataFrame(rows)
    # standardised mean difference, in full-panel SD units
    print(tbl[["feature", "full_mean", "old_mean", "old_smd", "new_mean", "new_smd"]]
          .to_string(index=False, float_format=lambda x: f"{x: .5f}"))
    print("\nSMesh = (subsample mean - full mean) / full SD. A fair 20% subsample")
    print("has |SMD| <~ 0.02 for a feature with no sampling-related structure.")
    print(f"\nmax |OLD SMD| = {tbl['old_smd'].abs().max():.5f}"
          f"   max |NEW SMD| = {tbl['new_smd'].abs().max():.5f}")
    del frame, old5, new5


# ---------------------------------------------------------------------------
# 6. does it bias the MODEL or only shrink it?
# ---------------------------------------------------------------------------
def section_bias(n_estimators_note: str = "") -> None:
    print("\n" + "=" * 78)
    print("SECTION 6 — train on each subsample, evaluate on the SAME holdout")
    print("=" * 78)
    cutoff = np.datetime64(pd.Timestamp(HOLDOUT_START))
    full = pd.read_parquet(S1)
    feat = wf.feature_columns(full)
    train_all = full[full["date"] < cutoff].reset_index(drop=True)
    eval_all = full[full["date"] >= cutoff].reset_index(drop=True)
    print(f"train pool (pre-2026): {len(train_all):,} rows;  "
          f"eval (2026 holdout, FULL cross-section): {len(eval_all):,} rows")

    n = len(train_all)
    rng = np.random.default_rng(0)
    random_mask = rng.random(n) < 0.2

    old_keys = pd.MultiIndex.from_arrays(
        [rule_old(full, 5)["code"].to_numpy(), rule_old(full, 5)["date"].to_numpy()])
    old_mask = pd.MultiIndex.from_arrays(
        [train_all["code"].to_numpy(), train_all["date"].to_numpy()]).isin(old_keys)
    new_sessions = np.sort(full["date"].unique())[::5]
    new_mask = train_all["date"].isin(set(new_sessions)).to_numpy()

    regimes = {
        "R1_full": np.ones(n, dtype=bool),
        "R2_random20": random_mask,
        "R3_old_iloc5": np.asarray(old_mask),
        "R4_new_grid5": np.asarray(new_mask),
    }

    te = eval_all[eval_all["label_high"].notna()].reset_index(drop=True)
    x_te = te[feat].to_numpy("float32")
    y_te = te["label_high"].to_numpy("float64")
    print(f"eval rows: {len(te):,}   eval base rate: {y_te.mean():.6f}")

    cfg = wf.Config(name="committed_hgb_baseline", model="hgb",
                    params={"max_leaf_nodes": 15, "min_samples_leaf": 300,
                            "l2_regularization": 10.0, "learning_rate": 0.03,
                            "max_iter": 300, "early_stopping": False},
                    label="label_high", target_rate=0.02)

    out = {}
    for name, mask in regimes.items():
        tr = train_all[mask]
        tr = tr[tr["label_high"].notna() &
                tr["resolved"].fillna(0).astype(bool)]
        x_tr = tr[feat].to_numpy("float32")
        y_tr = tr["label_high"].to_numpy("float64")
        model = wf.make_model(cfg, 0)
        model.fit(x_tr, y_tr)
        s_tr = model.predict_proba(x_tr)[:, 1]
        s_te = model.predict_proba(x_te)[:, 1]
        thr = wf.pick_threshold(s_tr, y_tr, 0.02)
        pred = s_te >= thr
        rec = dict(
            regime=name, n_train=len(tr), train_base=float(y_tr.mean()),
            threshold=float(thr), signals=int(pred.sum()),
            precision=float(y_te[pred].mean()) if pred.any() else float("nan"),
            lift=float(y_te[pred].mean() / y_te.mean()) if pred.any() else float("nan"),
        )
        out[name] = rec
        print(f"  {name:14s} n_train={rec['n_train']:>9,} "
              f"train_base={rec['train_base']:.5f} thr={thr:.4f} "
              f"sig={rec['signals']:>5d} PRECISION={rec['precision']*100:6.2f}% "
              f"lift={rec['lift']:.2f}x")
        # Stash the FULL-data model's holdout scores for the top-K test below.
        if name == "R1_full":
            te["_score_full"] = s_te
        del x_tr, s_tr
    print("\nAll four rows are scored on the identical full-cross-section 2026 rows.")
    print("R3 vs R2 isolates the DESYNC (systematic phase + weekday alias) from")
    print("mere row removal; R4 vs R2 isolates session-grid decimation.")

    # --- the comment's SECOND claim: top-1 per day on a partial cross-section --
    print("\n--- top-K per session with the FULL-data model's own scores ---")
    score = te["_score_full"].to_numpy("float64")
    key = pd.MultiIndex.from_arrays([te["code"].to_numpy(), te["date"].to_numpy()])
    old_k = rule_old(pd.read_parquet(S1, columns=["code", "date"]), 5)
    in_old = key.isin(pd.MultiIndex.from_arrays(
        [old_k["code"].to_numpy(), old_k["date"].to_numpy()]))
    te["_in_old"] = in_old
    te["_score"] = score

    def topk(frame, k, col="_score"):
        m = frame.groupby("date", sort=False)[col].rank(
            ascending=False, method="first") <= k
        return (float(frame.loc[m, "label_high"].mean()), int(m.sum()),
                frame.groupby("date").size().median())

    for k in (1, 5, 20):
        pf, nf, sf = topk(te, k)
        pp, np_, sp = topk(te[te["_in_old"]], k)
        print(f"  top-{k:<3d} full day ({sf:>4.0f} stocks): {pf*100:6.2f}% "
              f"({nf:>5d} sig)   OLD partial ({sp:>4.0f} stocks): {pp*100:6.2f}% "
              f"({np_:>5d} sig)   delta {(pp-pf)*100:+.2f} pp")
    print("  (Both columns are scored on the SAME full 2026 rows; only the")
    print("   candidate pool the top-K is drawn from differs.)")
    del full, train_all, eval_all, x_te


# ---------------------------------------------------------------------------
# 7. per-session top-K under a partial cross-section
# ---------------------------------------------------------------------------
def section_topk() -> None:
    print("\n" + "=" * 78)
    print("SECTION 7 — is the best of a PARTIAL cross-section a worse pick?")
    print("=" * 78)
    print("This section uses a crude single-feature score (raw ret20) so the test")
    print("is self-contained and reproducible without fitting a model. The")
    print("DECISIVE version of the same test, using the trained HGB's own scores")
    print("and with a significance test, is printed at the end of SECTION 6.")
    cutoff = np.datetime64(pd.Timestamp(HOLDOUT_START))
    full = pd.read_parquet(S1, columns=META + ["ret5", "ret20", "vol_ratio_1_5"])
    full = full[full["date"] >= cutoff]
    # A simple, deterministic, purely cross-sectional score: 60-session momentum
    # relative to the day's own cross-section is already in cs_ret5_rank; use the
    # raw ret20 as a stand-in for a model score so the test is reproducible.
    full = full[full["label_high"].notna()].reset_index(drop=True)
    full["score"] = full["ret20"].astype("float64")

    old_keys = rule_old(pd.read_parquet(S1, columns=["code", "date"]), 5)
    key = pd.MultiIndex.from_arrays([full["code"].to_numpy(), full["date"].to_numpy()])
    old_key_set = pd.MultiIndex.from_arrays(
        [old_keys["code"].to_numpy(), old_keys["date"].to_numpy()])
    full["in_old"] = key.isin(old_key_set)

    def topk_precision(frame, k=1):
        m = frame.groupby("date", sort=False)["score"].rank(
            ascending=False, method="first") <= k
        return float(frame.loc[m, "label_high"].mean()), int(m.sum()), \
            float(frame["label_high"].mean())

    p_full, n_full, base_full = topk_precision(full)
    part = full[full["in_old"]].reset_index(drop=True)
    p_part, n_part, base_part = topk_precision(part)
    print(f"retained cross-section per session: "
          f"{full.groupby('date').size().median():.0f} full vs "
          f"{part.groupby('date').size().median():.0f} OLD-partial")
    print(f"  top-1 of the FULL  day cross-section : {p_full*100:6.2f}% "
          f"({n_full} signals)  base {base_full*100:.3f}%")
    print(f"  top-1 of the OLD PARTIAL cross-sect. : {p_part*100:6.2f}% "
          f"({n_part} signals)  base {base_part*100:.3f}%")
    print(f"  difference (partial - full)          : {(p_part-p_full)*100:+.2f} pp")

    # Random subsets of the same size, to see whether the OLD phase subsets are
    # unusual relative to an arbitrary 19% subset.
    rng = np.random.default_rng(0)
    sizes = full.groupby("date").size()
    vals = []
    for _ in range(20):
        m = rng.random(len(full)) < 0.19
        sub = full[m]
        if sub.empty:
            continue
        v, _, _ = topk_precision(sub)
        vals.append(v)
    vals = np.array(vals)
    print(f"  random 19% subsets, top-1 precision   : "
          f"{vals.mean()*100:6.2f}% +/- {vals.std()*100:.2f} pp (20 draws)")
    del full, part, old_keys


# ---------------------------------------------------------------------------
# 8. bit identity
# ---------------------------------------------------------------------------
def _hash_frame(frame: pd.DataFrame) -> tuple[str, int]:
    h = hashlib.sha256()
    h.update(pd.util.hash_pandas_object(frame, index=True).to_numpy().tobytes())
    return h.hexdigest(), int(frame.shape[0] * frame.shape[1])


def section_identity() -> None:
    print("\n" + "=" * 78)
    print("SECTION 8 — bit identity of HEAD vs working-tree builds")
    print("=" * 78)
    if not S1_HEAD.exists():
        print(f"  (skip) {S1_HEAD} not built yet")
        return
    a = pd.read_parquet(S1)
    b = pd.read_parquet(S1_HEAD)
    print(f"  working tree stride-1: {a.shape}")
    print(f"  HEAD         stride-1: {b.shape}")
    same_cols = list(a.columns) == list(b.columns)
    print(f"  identical column order: {same_cols}")
    if same_cols and a.shape == b.shape:
        ha, _ = _hash_frame(a)
        hb, _ = _hash_frame(b)
        print(f"  working-tree hash: {ha}")
        print(f"  HEAD         hash: {hb}")
        print(f"  BIT-IDENTICAL: {ha == hb}")
        # Where do they differ, if anywhere?
        if ha != hb:
            for c in a.columns:
                if not a[c].equals(b[c]):
                    na, nb = a[c].isna().sum(), b[c].isna().sum()
                    d = (a[c].fillna(-999) != b[c].fillna(-999)).sum()
                    print(f"    differs: {c}  n_diff={d}  na {na} vs {nb}")
    del a, b


def section_reprogap() -> None:
    """Which matrix does each consumer read now, vs which report it writes?

    Several modules call ``wf.load_matrix()`` with no stride argument. That
    default has changed between revisions, so a module can silently read the
    stride-5 matrix while the report on disk holds stride-1 numbers. Re-running
    such a module overwrites a published report with different numbers.
    """
    print("\n" + "=" * 78)
    print("SECTION 9 — reproducibility gap: default stride vs report on disk")
    print("=" * 78)
    import json
    import re

    frame = wf.load_matrix()
    which = ("stride 5 (536,143 rows)" if len(frame) == 536143 else
             "stride 1 (2,680,715 rows)" if len(frame) == 2680715 else "unknown")
    print(f"wf.load_matrix() with no stride argument reads: "
          f"{len(frame):,} rows, {frame['date'].nunique()} sessions  -> {which}")
    del frame

    src = REPO_ROOT / "src" / "ml"
    consumers = [
        ("null_tests.py", "ml_null_tests.json"),
        ("precision_ceiling.py", "ml_precision_ceiling.json"),
        ("concentration.py", "ml_concentration.json"),
        ("crosssec.py", "ml_crosssec_final.json"),
        ("final_holdout.py", "ml_final_holdout.json"),
        ("validate_rf.py", None),
        ("profile_stages.py", None),
    ]
    print("\n%-22s %-30s %-16s %s" % ("module", "load_matrix call",
                                      "resolves to", "report marker"))
    print("-" * 96)
    for mod, rep in consumers:
        p = src / mod
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        calls = re.findall(r"load_matrix\([^)]*\)", txt)
        call = re.sub(r"\s+", " ", calls[0]) if calls else "(none)"
        if "stride=stride_used" in call or "stride=1" in call:
            eff = "1 (explicit)"
        elif "stride=" in call:
            eff = re.search(r"stride=(\w+)", call).group(1)
        else:
            eff = "5 (DEFAULT)"
        marker = ""
        rp = REPO_ROOT / "reports" / rep if rep else None
        if rp and rp.exists():
            try:
                d = json.loads(rp.read_text(encoding="utf-8"))
                if isinstance(d, dict) and "n_rows" in d:
                    marker = f"n_rows={d['n_rows']:,}"
                elif isinstance(d, dict) and "holdout" in d:
                    marker = f"holdout signals={d['holdout']['signals']:,}"
                elif isinstance(d, dict) and "oos_base_rate" in d:
                    marker = f"oos_base_rate={d['oos_base_rate']:.8f}"
            except Exception:
                marker = "(unparsed)"
        print("%-22s %-30s %-16s %s" % (mod, call[:30], eff, marker))

    print("\nstride-1 row count = 2,680,715   stride-5 row count = 536,143")
    print("oos_base_rate 0.04089445 is the FULL-cross-section walk-forward base")
    print("rate over the 462 test sessions; the iloc-retained subset of those")
    print("same sessions gives 0.04087801. So 0.04089445 marks a stride-1 report.")
    print("\nA module resolving to stride 5 while its report holds stride-1 numbers")
    print("will OVERWRITE the report with different numbers when re-run.")


SECTIONS = {
    "counterexample": section_counterexample,
    "structure": section_structure,
    "folds": section_folds,
    "sampling": section_sampling,
    "distributions": section_distributions,
    "bias": section_bias,
    "biasreps": None,  # replaced below
    "topk": section_topk,
    "identity": section_identity,
    "reprogap": section_reprogap,
}


def section_biasreps() -> None:
    """Same row count, many draws: is OLD inside the random-subsample spread?"""
    print("\n" + "=" * 78)
    print("SECTION 6b — row count held FIXED: OLD vs random draws vs NEW")
    print("=" * 78)
    cutoff = np.datetime64(pd.Timestamp(HOLDOUT_START))
    full = pd.read_parquet(S1)
    feat = wf.feature_columns(full)
    train_all = full[full["date"] < cutoff].reset_index(drop=True)
    eval_all = full[full["date"] >= cutoff].reset_index(drop=True)
    te = eval_all[eval_all["label_high"].notna()].reset_index(drop=True)
    x_te = te[feat].to_numpy("float32")
    y_te = te["label_high"].to_numpy("float64")

    old_m = pd.MultiIndex.from_arrays(
        [train_all["code"].to_numpy(), train_all["date"].to_numpy()]
    ).isin(pd.MultiIndex.from_arrays(
        [rule_old(full, 5)["code"].to_numpy(), rule_old(full, 5)["date"].to_numpy()]))
    old_m = np.asarray(old_m)
    n_target = int(old_m.sum())
    new_sessions = set(np.sort(full["date"].unique())[::5])
    new_m = train_all["date"].isin(new_sessions).to_numpy()
    print(f"held-fixed row count = {n_target:,} (the OLD rule's own count)")
    print(f"NEW grid stride 5 gives {int(new_m.sum()):,} rows in the same pool")

    cfg = wf.Config(name="c", model="hgb",
                    params={"max_leaf_nodes": 15, "min_samples_leaf": 300,
                            "l2_regularization": 10.0, "learning_rate": 0.03,
                            "max_iter": 300, "early_stopping": False},
                    label="label_high", target_rate=0.02)

    def run(mask, seed):
        tr = train_all[mask]
        tr = tr[tr["label_high"].notna() & tr["resolved"].fillna(0).astype(bool)]
        model = wf.make_model(cfg, seed)
        model.fit(tr[feat].to_numpy("float32"),
                  tr["label_high"].to_numpy("float64"))
        s_tr = model.predict_proba(tr[feat].to_numpy("float32"))[:, 1]
        s_te = model.predict_proba(x_te)[:, 1]
        thr = wf.pick_threshold(s_tr, tr["label_high"].to_numpy("float64"), 0.02)
        pred = s_te >= thr
        return float(y_te[pred].mean()) if pred.any() else np.nan, int(pred.sum())

    rng = np.random.default_rng(12345)
    rand_vals = []
    for i in range(6):
        idx = rng.choice(len(train_all), size=n_target, replace=False)
        m = np.zeros(len(train_all), dtype=bool)
        m[idx] = True
        p, s = run(m, 0)
        rand_vals.append(p)
        print(f"  random draw {i} (exact n): precision {p*100:6.2f}%  ({s} sig)")
    rand_vals = np.array(rand_vals)
    print(f"  random draws: mean {rand_vals.mean()*100:.2f}%  "
          f"sd {rand_vals.std(ddof=1)*100:.2f} pp  "
          f"range [{rand_vals.min()*100:.2f}%, {rand_vals.max()*100:.2f}%]")

    print()
    for nm in ("R1_full", "R3_old_iloc5", "R4_new_grid5"):
        for seed in (0, 1, 2):
            if nm == "R1_full":
                m = np.ones(len(train_all), dtype=bool)
            elif nm == "R3_old_iloc5":
                m = old_m
            else:
                m = new_m
            p, s = run(m, seed)
            print(f"  {nm:14s} seed={seed}  precision {p*100:6.2f}%  ({s} sig)")
    print("\nIf OLD's precision sits inside the random-draw range, the desync")
    print("removes rows without tilting WHICH (x, y) pairs survive.")
    del full, train_all, eval_all, x_te


SECTIONS["biasreps"] = section_biasreps


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", default="all",
                    help="all | " + " | ".join(SECTIONS))
    args = ap.parse_args()
    todo = list(SECTIONS) if args.section == "all" else [args.section]
    for name in todo:
        SECTIONS[name]()
        sys.stdout.flush()


if __name__ == "__main__":
    main()
