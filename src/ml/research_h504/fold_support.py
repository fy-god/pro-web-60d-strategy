from __future__ import annotations

import numpy as np
import pandas as pd


def minimum_dense_sessions_for_full_maturity_split(horizon: int) -> int:
    """Closed-form minimum N for one train and one later mature dev candidate.

    Dense candidate dates, zero embargo, one train candidate at t=0. Its full
    follow-up ends at H. Dev must start strictly after that at H+1 and itself have
    H future sessions, so last required index is 2H+1 and N >= 2H+2.
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    return 2 * horizon + 2


def enumerate_mature_splits(
    calendar,
    candidate_dates,
    *,
    horizon: int = 504,
    min_train_candidates: int = 1,
    min_dev_candidates: int = 1,
    dev_block_sessions: int = 63,
) -> pd.DataFrame:
    """Enumerate full-follow-up BCE train->dev splits.

    This function answers a deliberately narrow question: can the conservative
    fixed-deadline BCE baseline form a historical time-out-of-sample split from
    THIS supplied calendar/candidate set? It must not be generalized to "the
    repository has insufficient data" because a user's authorized local history
    may be longer than the checked-in panel, and auxiliary tasks have different
    horizons.
    """
    cal = pd.DatetimeIndex(sorted(pd.to_datetime(list(calendar)).unique()))
    if len(cal) == 0:
        return pd.DataFrame(columns=["dev_start", "dev_end", "n_train", "n_dev"])
    pos = {pd.Timestamp(d): i for i, d in enumerate(cal)}
    cand = pd.DatetimeIndex(pd.to_datetime(list(candidate_dates)))
    cand_pos = np.array([pos[d] for d in cand if d in pos], dtype=int)
    if len(cand_pos) == 0:
        return pd.DataFrame(columns=["dev_start", "dev_end", "n_train", "n_dev"])
    last_signal_i = len(cal) - 1 - horizon
    mature = cand_pos[cand_pos <= last_signal_i]
    out: list[dict] = []
    for dev_start_i in range(1, len(cal)):
        dev_end_i = min(len(cal) - 1, dev_start_i + dev_block_sessions - 1)
        n_train = int(np.sum(mature + horizon < dev_start_i))
        n_dev = int(np.sum((mature >= dev_start_i) & (mature <= dev_end_i)))
        if n_train >= min_train_candidates and n_dev >= min_dev_candidates:
            out.append({
                "dev_start": pd.Timestamp(cal[dev_start_i]),
                "dev_end": pd.Timestamp(cal[dev_end_i]),
                "n_train": n_train,
                "n_dev": n_dev,
                "horizon": horizon,
            })
    return pd.DataFrame(out)


def fold_support_summary(calendar, candidate_dates, *, horizon: int = 504, min_train_candidates: int = 1, min_dev_candidates: int = 1, dev_block_sessions: int = 63) -> dict:
    cal = pd.DatetimeIndex(sorted(pd.to_datetime(list(calendar)).unique()))
    splits = enumerate_mature_splits(cal, candidate_dates, horizon=horizon, min_train_candidates=min_train_candidates, min_dev_candidates=min_dev_candidates, dev_block_sessions=dev_block_sessions)
    return {
        "calendar_sessions": int(len(cal)),
        "horizon": int(horizon),
        "minimum_dense_sessions_for_one_full_maturity_split": int(
            minimum_dense_sessions_for_full_maturity_split(horizon)
        ),
        "n_legal_full_followup_splits": int(len(splits)),
        "min_train_candidates": int(min_train_candidates),
        "min_dev_candidates": int(min_dev_candidates),
        "dev_block_sessions": int(dev_block_sessions),
        "scope": "full_followup_bce_on_supplied_calendar_only",
        "does_not_imply_repository_or_local_history_absence": True,
    }
