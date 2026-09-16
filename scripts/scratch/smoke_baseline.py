"""Recompute the published pooled baseline per fold and check its fragility."""
import numpy as np, pandas as pd
from src.ml import crosssec as xs, walkforward as wf

m = xs.load()
folds = xs.build_folds(m)
cfg = wf.Config(name='fam_hgb_0', model='hgb', params={}, label='label_high', target_rate=0.02)
out = []
for i, f in enumerate(folds, 1):
    train = m[m['date'].isin(f.train_sessions)]
    test = m[m['date'].isin(f.test_sessions)]
    s_tr, s_te = xs.fit_scores(train, test, cfg)
    y = s_te['label_high'].to_numpy('float64')
    thr = wf.pick_threshold(s_tr['score'].to_numpy('float64'), s_tr['label_high'].to_numpy('float64'), cfg.target_rate)
    mask = s_te['score'].to_numpy('float64') >= thr
    d = s_te['date'].to_numpy(); c = s_te['code'].to_numpy()
    n = int(mask.sum())
    p = xs.precision(y, mask)
    h = y[mask]
    conc = xs.concentration(h, d[mask], c[mask])
    ci = xs.date_clustered_bootstrap(h, d[mask], np.unique(d), n_boot=4000, seed=0)
    ci5 = xs.date_clustered_bootstrap(h, d[mask], np.unique(d), n_boot=4000, seed=0, block=5)
    print(f'fold{i} {f.name}', flush=True)
    print(f'  base {y.mean()*100:.3f}%  thr {thr:.5f}  sig {n}  prec {p*100:.2f}%  '
          f'dates {conc["n_distinct_dates"]} stocks {conc["n_distinct_stocks"]} HHI {conc["herfindahl_dates"]:.4f}', flush=True)
    print(f'  CI95 [{ci["ci_low"]*100:.2f}%, {ci["ci_high"]*100:.2f}%]  block5 [{ci5["ci_low"]*100:.2f}%, {ci5["ci_high"]*100:.2f}%]  '
          f'drop busiest {conc["precision_drop_busiest_date"]*100:.2f}%  median daily {conc["median_daily_precision"]*100:.2f}%', flush=True)
    out.append((n, p))
tot_n = sum(o[0] for o in out); tot_h = sum(o[0]*o[1] for o in out)
print(f'POOLED {tot_n} sig  precision {tot_h/tot_n*100:.4f}%  (published 15.9777%)', flush=True)
