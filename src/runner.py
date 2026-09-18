"""Strategy execution harness.

Adapts the daily panel into the two contracts this project verifies:

* :class:`experts.contracts.ExpertCard` — 60 visible bars, the **Web Pro**
  family (36 strategies). Indicators are supplied from causal features so the
  strategy modules stay byte-identical to their published source.
* A flat feature row — the **60-day low-zone** family (V00-V08 lineage), whose
  strategies read wide context columns rather than a 60-bar card.

Nothing here computes outcomes. Outcomes are attached afterwards by
:mod:`src.labels`, so a strategy can never see its own label.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from experts.contracts import ExpertCard, VisibleBar
from experts.registry import STRATEGY_IDS, get_strategy

VISIBLE_BARS = 60

# Error tally for the current process, keyed by strategy id ("__card__" for card
# assembly failures). The driver reports these so a broken column cannot hide.
LAST_ERRORS: Counter = Counter()
LAST_ERROR_SAMPLES: dict[str, str] = {}


def record_error(key: str, exc: BaseException) -> None:
    LAST_ERRORS[key] += 1
    LAST_ERROR_SAMPLES.setdefault(key, f"{type(exc).__name__}: {exc}")


def reset_errors() -> None:
    LAST_ERRORS.clear()
    LAST_ERROR_SAMPLES.clear()


def make_card(
    window: pd.DataFrame,
    code: str,
    name: str = "",
) -> ExpertCard:
    """Build one ExpertCard from a 60-row slice ending at the observation bar.

    ``window`` must be chronological and already contain the causal indicator
    columns produced by :mod:`src.features`. The indicator series are sliced
    from the *same* continuous history, never recomputed per card, so KDJ here
    matches the KDJ the strategies were designed against.
    """
    if len(window) != VISIBLE_BARS:
        raise ValueError(f"window must hold exactly {VISIBLE_BARS} bars, got {len(window)}")

    bars = tuple(
        VisibleBar(
            date=row.date.strftime("%Y-%m-%d"),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
            amount=float(row.amount) if pd.notna(row.amount) else 0.0,
            turnover=float(row.turnover) if pd.notna(row.turnover) else 0.0,
        )
        for row in window.itertuples()
    )
    indicators = {
        "kdj_k": tuple(float(v) for v in window["kdj_k"]),
        "kdj_d": tuple(float(v) for v in window["kdj_d"]),
        "kdj_j": tuple(float(v) for v in window["kdj_j"]),
        "turnover": tuple(float(v) if pd.notna(v) else 0.0 for v in window["turnover"]),
        "volume_ratio": tuple(float(v) for v in window["volume_ratio"]),
    }
    last = window.iloc[-1]
    return ExpertCard(
        sample_id=f"{code}:{last.date.strftime('%Y-%m-%d')}",
        code=code,
        name=name or code,
        observation_date=last.date.strftime("%Y-%m-%d"),
        bars=bars,
        indicators=indicators,
        horizon_sessions=10,
        target_gain=0.30,
    )


def run_strategies(
    window: pd.DataFrame,
    code: str,
    strategy_ids: Sequence[str] | None = None,
    name: str = "",
) -> dict[str, dict]:
    """Evaluate every requested strategy on one card.

    Returns ``{strategy_id: {"prediction": int, "score": float}}``. A strategy
    that raises is recorded as ``None`` and its exception is collected in
    ``LAST_ERRORS`` — never silently counted as a negative. A silent ``except``
    here previously hid a missing feature column for an entire scan, so errors
    are counted and surfaced by the driver.
    """
    ids = list(strategy_ids) if strategy_ids is not None else list(STRATEGY_IDS)
    try:
        card = make_card(window, code, name=name)
    except Exception as exc:  # noqa: BLE001 - surfaced via LAST_ERRORS
        record_error("__card__", exc)
        return {sid: None for sid in ids}

    out: dict[str, dict] = {}
    for sid in ids:
        try:
            decision = get_strategy(sid).predict(card)
            out[sid] = {"prediction": int(decision.prediction), "score": float(decision.score)}
        except Exception as exc:  # noqa: BLE001 - surfaced via LAST_ERRORS
            record_error(sid, exc)
            out[sid] = None
    return out


def select_scan_mask(
    panel: pd.DataFrame,
    stride: int = 5,
    min_history: int = VISIBLE_BARS,
) -> pd.Series:
    """Boolean mask of the (code, date) rows a screener would actually scan.

    The single source of truth for scan-target selection. ``build_scan_targets``
    and ``scan_all.population_baselines`` must select the SAME rows, or a published
    lift divides a scan-grid hit rate by a differently-defined base rate. They were
    two hand-written copies until a review found they disagreed at ``stride=1``:
    ``build_scan_targets`` applied ``_seq >= min_history`` unconditionally while the
    baseline gated the whole filter behind ``if stride > 1``, so at stride 1 the
    baseline also counted each stock's warm-up bars.

    Warm-up is therefore applied FIRST and unconditionally; ``stride`` only thins
    what survives. The mask is aligned to ``panel.index``, so callers that have
    already sorted can use ``frame[mask.to_numpy()]``.
    """
    if panel.empty:
        return pd.Series([], dtype=bool, index=panel.index)
    frame = panel.sort_values(["code", "date"])
    seq = frame.groupby("code", sort=False).cumcount()
    keep = seq >= min_history
    if stride > 1:
        keep &= (seq % stride == 0)
    # Return in the caller's original order so `mask.to_numpy()` lines up.
    return keep.reindex(panel.index, fill_value=False)


def build_scan_targets(
    panel: pd.DataFrame,
    stride: int = 5,
    min_history: int = VISIBLE_BARS,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Pick the (code, date) observation points a screener would actually scan.

    ``stride`` samples every Nth session per stock. A real screener does not
    re-decide on every single bar for every stock, and scoring all 2.68M bars
    would multiply runtime with almost no information gain. ``stride=5`` gives
    a weekly decision cadence.

    Selection goes through :func:`select_scan_mask` so it cannot drift from the
    population baseline that every published lift is divided by.
    """
    frame = panel
    if start is not None:
        frame = frame[frame["date"] >= pd.Timestamp(start)]
    if end is not None:
        frame = frame[frame["date"] <= pd.Timestamp(end)]

    frame = frame.sort_values(["code", "date"])
    targets = frame[select_scan_mask(frame, stride=stride,
                                     min_history=min_history).to_numpy()]
    return targets[["code", "date"]].reset_index(drop=True)


def scan(
    panel: pd.DataFrame,
    targets: pd.DataFrame,
    strategy_ids: Sequence[str] | None = None,
    progress: bool = False,
) -> pd.DataFrame:
    """Evaluate every strategy at every target point, in a single pass.

    The panel is grouped by code once and each code's rows are materialised
    into NumPy-free slices only when a card is built, which keeps the inner
    loop free of per-row pandas indexing.
    """
    ids = list(strategy_ids) if strategy_ids is not None else list(STRATEGY_IDS)
    by_code = {code: grp for code, grp in panel.groupby("code", sort=False)}
    target_by_code = {
        code: set(grp["date"].tolist()) for code, grp in targets.groupby("code", sort=False)
    }

    rows: list[dict] = []
    total = len(target_by_code)
    for i, (code, dates) in enumerate(target_by_code.items()):
        if progress and i % 200 == 0:
            print(f"  [{i}/{total}] {code}", flush=True)
        grp = by_code.get(code)
        if grp is None:
            continue
        grp = grp.reset_index(drop=True)
        positions = {d: p for p, d in enumerate(grp["date"].tolist())}
        for d in dates:
            pos = positions[d]
            if pos + 1 < VISIBLE_BARS:
                continue
            window = grp.iloc[pos + 1 - VISIBLE_BARS : pos + 1]
            result = run_strategies(window, code, strategy_ids=ids)
            for sid, value in result.items():
                if value is None:
                    continue
                rows.append(
                    {
                        "code": code,
                        "date": d,
                        "strategy_id": sid,
                        "prediction": value["prediction"],
                        "score": value["score"],
                    }
                )
    return pd.DataFrame(rows)


def scan_code_chunk(
    panel: pd.DataFrame,
    targets: pd.DataFrame,
    strategy_ids: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Same as :func:`scan` but used by the multiprocessing worker pool."""
    return scan(panel, targets, strategy_ids=strategy_ids, progress=False)
