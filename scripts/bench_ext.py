"""Scratch benchmark: panel load cost, groupby-rolling cost, one HGB fold fit cost.

Not part of the deliverable; used only to size the feature grid.
"""
from __future__ import annotations

import time
import numpy as np
import pandas as pd
import sklearn

t0 = time.time()
from src import data_pipeline

panel = data_pipeline.load_panel()
print(f"load_panel {time.time()-t0:.1f}s rows={len(panel)}", flush=True)
frame = panel.sort_values(["code", "date"]).reset_index(drop=True)
frame["_ret1"] = frame["close"].pct_change().astype("float32")
print("sklearn", sklearn.__version__, flush=True)

t0 = time.time()
g = frame.groupby("code", sort=False)["_ret1"].rolling(20, min_periods=10)
r = g.mean().reset_index(level=0, drop=True).to_numpy("float32")
print(f"one groupby.rolling.mean(20) {time.time()-t0:.2f}s", flush=True)

t0 = time.time()
gstd = frame.groupby("code", sort=False)["_ret1"].rolling(20, min_periods=10).std()
r2 = gstd.reset_index(level=0, drop=True).to_numpy("float32")
print(f"one groupby.rolling.std(20) {time.time()-t0:.2f}s", flush=True)

t0 = time.time()
rng = (frame["high"] - frame["low"]).astype("float64")
rmax = rng.groupby(frame["code"], sort=False).rolling(250, min_periods=60).max()
rmax = rmax.reset_index(level=0, drop=True).to_numpy("float32")
print(f"one groupby.rolling.max(250) {time.time()-t0:.2f}s", flush=True)

t0 = time.time()
cm = pd.Series(np.arange(len(frame))).groupby(frame["code"].to_numpy(), sort=False).cummax()
print(f"one groupby.cummax {time.time()-t0:.2f}s", flush=True)

# --- baseline timing through the harness
from src.ml import walkforward as wf

t0 = time.time()
matrix = wf.load_matrix()
print(f"load_matrix {time.time()-t0:.1f}s shape={matrix.shape}", flush=True)
sessions = np.sort(matrix["date"].unique())
folds = wf.folds(sessions, n_folds=5, horizon=10, embargo=2,
                 min_train_sessions=150, final_holdout_start="2026-01-01")
for f in folds:
    print(f"  {f.name}: train={f.n_train_sessions} test={f.n_test_sessions}", flush=True)

cfg = wf.Config(name="baseline_82", model="hgb", target_rate=0.02)
t0 = time.time()
res = []
for f in folds:
    tr = matrix[matrix["date"].isin(f.train_sessions)]
    te = matrix[matrix["date"].isin(f.test_sessions)]
    r = wf.evaluate_fold(tr, te, cfg)
    res.append(r)
    print(f"  fold OOS {r['oos_precision']*100:.2f}% ({r['oos_signals']} sig, "
          f"base {r['oos_base_rate']*100:.2f}%) in-sample {r['insample_precision']*100:.2f}%",
          flush=True)
print(f"fold loop total {time.time()-t0:.1f}s", flush=True)
s = wf.summarise(res)
print("SUMMARY", {k: v for k, v in s.items() if k != "per_fold_oos"}, flush=True)

cfg2 = wf.Config(name="baseline_et", model="extratrees", target_rate=0.02)
t0 = time.time()
res2 = [wf.evaluate_fold(matrix[matrix["date"].isin(f.train_sessions)],
                         matrix[matrix["date"].isin(f.test_sessions)], cfg2) for f in folds]
print(f"extratrees loop {time.time()-t0:.1f}s", flush=True)
print("ET SUMMARY", wf.summarise(res2), flush=True)
