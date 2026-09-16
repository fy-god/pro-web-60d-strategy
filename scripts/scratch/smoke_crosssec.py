import time, numpy as np, pandas as pd
from src.ml import crosssec as xs, walkforward as wf
from src.ml import search_crosssec as sc

t0 = time.time()
m = xs.load()
print('load', round(time.time() - t0, 1), 's', m.shape, flush=True)
folds = xs.build_folds(m)
print('folds', len(folds), flush=True)
f = folds[0]
train = m[m['date'].isin(f.train_sessions)]
test = m[m['date'].isin(f.test_sessions)]
cfg = wf.Config(name='fam_hgb_0', model='hgb', params={}, label='label_high', target_rate=0.02)
t0 = time.time()
s_tr, s_te = xs.fit_scores(train, test, cfg)
print('fit', round(time.time() - t0, 1), 's  train', len(s_tr), 'test', len(s_te), flush=True)
y = s_te['label_high'].to_numpy('float64')
print('test base rate', y.mean(), flush=True)
for k in (1, 3, 5, 10, 20, 50):
    mk = xs.topk_mask(s_te, k)
    print('  top', k, 'sig', int(mk.sum()), 'prec %.4f' % xs.precision(y, mk), flush=True)
r = xs.per_session_rank(s_te)
print('rank min/max', r.min(), r.max(), 'rows', len(s_te), flush=True)
print('auc', sc.session_auc(s_te, 'label_high'), flush=True)
h = y[xs.topk_mask(s_te, 5)]
d = s_te['date'].to_numpy()[xs.topk_mask(s_te, 5)]
print('boot block1', xs.date_clustered_bootstrap(h, d, np.unique(s_te['date'].to_numpy()), n_boot=400, seed=0), flush=True)
print('boot block5', xs.date_clustered_bootstrap(h, d, np.unique(s_te['date'].to_numpy()), n_boot=400, seed=0, block=5), flush=True)
print('conc', xs.concentration(h, d, s_te['code'].to_numpy()[xs.topk_mask(s_te, 5)]), flush=True)
print('DONE', flush=True)
