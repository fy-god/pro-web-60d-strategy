"""Time the walk-forward harness stages, so the search can be sized to the machine.

Run this before launching any large grid. An earlier grid was launched on a
guess, saturated all 16 cores, starved six parallel agents to death, and
produced a timing estimate that was itself measured under contention. Measure
first.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd

from src.ml import walkforward as wf


def main() -> None:
    t0 = time.perf_counter()
    frame = wf.load_matrix()
    t_load = time.perf_counter() - t0
    print(f"load matrix          {t_load:6.2f}s  {len(frame):,} rows x {len(frame.columns)} cols")

    sessions = np.sort(frame["date"].unique())
    folds = wf.folds(sessions, n_folds=5, horizon=10, embargo=2,
                     min_train_sessions=150, final_holdout_start="2026-01-01")
    cols = wf.feature_columns(frame)
    print(f"features             {len(cols)}")

    for fold in folds[:2]:
        t0 = time.perf_counter()
        train = frame[frame["date"].isin(fold.train_sessions)]
        test = frame[frame["date"].isin(fold.test_sessions)]
        t_split = time.perf_counter() - t0

        tr = train[train["label_high"].notna() & train["resolved"].fillna(0).astype(bool)]
        te = test[test["label_high"].notna()]
        t_mask = time.perf_counter() - t0 - t_split

        x_tr = tr[cols].to_numpy("float32")
        y_tr = tr["label_high"].to_numpy("float64")
        x_te = te[cols].to_numpy("float32")

        t0 = time.perf_counter()
        model = wf.make_model(wf.Config(name="t", model="hgb"), 0)
        model.fit(x_tr, y_tr)
        t_fit = time.perf_counter() - t0

        t0 = time.perf_counter()
        s_tr = model.predict_proba(x_tr)[:, 1]
        s_te = model.predict_proba(x_te)[:, 1]
        t_pred = time.perf_counter() - t0

        print(
            f"{fold.name[:34]:34s} split {t_split:5.2f}s mask {t_mask:5.2f}s "
            f"fit {t_fit:6.2f}s pred {t_pred:5.2f}s  "
            f"train={len(tr):,} test={len(te):,}"
        )

    print("\nInterpretation: if fit dominates, reduce max_iter or rows; if split "
          "dominates, precompute fold indices once.")


if __name__ == "__main__":
    main()
