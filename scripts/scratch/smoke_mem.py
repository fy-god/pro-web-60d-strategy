import os, time, numpy as np
from src.ml import crosssec as xs, walkforward as wf

m = xs.load()
folds = xs.build_folds(m)
f = folds[1]
train = m[m['date'].isin(f.train_sessions)]
test = m[m['date'].isin(f.test_sessions)]
cfg = wf.Config(name='fam_hgb_0', model='hgb', params={}, label='label_high', target_rate=0.02)
cols = wf.select_features(wf.feature_columns(train), cfg.feature_groups)
tr = train[train[cfg.label].notna() & train['resolved'].fillna(0).astype(bool)]
X = tr[cols].to_numpy('float32'); y = tr[cfg.label].to_numpy('float64')
print('X', X.shape, round(X.nbytes / 1e6, 1), 'MB', flush=True)

from sklearn.ensemble import HistGradientBoostingClassifier
import threadpoolctl
print('threadpool info', threadpoolctl.threadpool_info(), flush=True)

for nthreads in (1, 4):
    with threadpoolctl.threadpool_limits(limits=nthreads):
        mdl = HistGradientBoostingClassifier(max_leaf_nodes=15, min_samples_leaf=300,
            l2_regularization=10.0, learning_rate=0.03, max_iter=300,
            early_stopping=False, random_state=0)
        t0 = time.time(); mdl.fit(X, y)
        print('threads', nthreads, 'fit', round(time.time() - t0, 1), 's', flush=True)
