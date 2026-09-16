"""Timing probe (scratch, not part of the deliverable): how does HGB fit time
scale with thread count on the largest-ish training block?"""
import os
import sys
import time

import numpy as np

from src.ml import walkforward as wf

sys.path.insert(0, ".")
from sklearn.ensemble import HistGradientBoostingClassifier

iters = int(sys.argv[1]) if len(sys.argv) > 1 else 100
fold_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
m = wf.load_matrix()
sessions = np.sort(m["date"].unique())
fo = wf.folds(sessions, n_folds=5, horizon=10, embargo=2,
              min_train_sessions=150, final_holdout_start="2026-01-01")
cols = wf.feature_columns(m)
f = fo[fold_idx]
tr = m[m["date"].isin(f.train_sessions)]
tr = tr[tr["label_high"].notna() & tr["resolved"].fillna(0).astype(bool)]
x = tr[cols].to_numpy("float32")
y = tr["label_high"].to_numpy("float64")
del m, tr
t0 = time.time()
model = HistGradientBoostingClassifier(
    max_leaf_nodes=15, min_samples_leaf=300, l2_regularization=10.0,
    learning_rate=0.03, max_iter=iters, early_stopping=False, random_state=0,
)
model.fit(x, y)
dt = time.time() - t0
print(f"threads={os.environ.get('OMP_NUM_THREADS','default')} fold={fold_idx} "
      f"rows={x.shape[0]} iters={iters} fit={dt:.1f}s "
      f"per_iter={dt/iters:.3f}s", flush=True)
