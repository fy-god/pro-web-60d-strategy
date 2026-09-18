"""Deterministic unit tests for the feature and label engines.

Each test pins a behaviour that the research record shows was previously wrong.
Run:  python -m tests.test_engine
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import features, labels


def _frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["code"] = df["code"].astype(str)
    df["date"] = pd.to_datetime(df["date"])
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    return df


def _flat(code: str, n: int, price: float = 10.0, start="2024-01-01") -> list[dict]:
    dates = pd.bdate_range(start, periods=n)
    return [
        {"code": code, "date": d, "open": price, "high": price, "low": price,
         "close": price, "volume": 1000.0}
        for d in dates
    ]


def test_strict_greater_than_4x():
    """Exactly 4x must NOT count as a bull label (strictly greater is required)."""
    rows = _flat("000001", 40, price=10.0)
    # bar index 5 rises to exactly 40.0 = 4x the entry open of 10.0
    rows[5]["high"] = 40.0
    df = labels.forward_outcomes(_frame(rows), horizon=30)
    row = df.iloc[0]
    assert abs(row["forward_max_return"] - 3.0) < 1e-9, row["forward_max_return"]
    assert row["label_bull"] == 0.0, "exactly 4x must not be a bull label"

    rows[5]["high"] = 41.0
    df2 = labels.forward_outcomes(_frame(rows), horizon=30)
    assert df2.iloc[0]["label_bull"] == 1.0, "above 4x must be a bull label"
    print("ok  strict_greater_than_4x")


def test_right_censoring_not_negative():
    """A truncated future window yields NaN, never 0.

    The subtlety that made the old version of this test weaker than it looked: it
    asserted only on ``df.iloc[-1]``, the final bar. That bar has *zero* future bars,
    so ``forward_high`` stays NaN by initialisation and the label is NaN however the
    code behaves -- including with the censoring mask at ``labels.py:199-200``
    deleted. Verified by direct comparison: removing the mask leaves
    ``label_bull``/``label_strict_low``/``label_joint`` finite (0.0/1.0) on every
    PARTIALLY-resolved row, and the old test still passed.

    The rows the mask actually governs are the ones with a *partial* window -- some
    future bars but fewer than ``horizon`` -- where ``forward_high`` IS finite and
    only the mask makes the label NaN. Those are asserted here.
    """
    rows = _flat("000001", 20, price=10.0)
    df = labels.forward_outcomes(_frame(rows), horizon=60)
    tail = df.iloc[-1]
    assert pd.isna(tail["label_bull"]), "censored row must be NaN"
    assert tail["label_resolved"] == False  # noqa: E712

    # EVERY row here is unresolved (20 bars, horizon 60), so every label must be
    # NaN -- including the partially-resolved rows that have a finite forward
    # window. This is what pins the mask.
    unresolved = df[~df["label_resolved"]]
    assert len(unresolved) == len(df), "fixture should be entirely unresolved"
    for col in ("label_bull", "label_strict_low", "label_joint"):
        assert unresolved[col].isna().all(), (
            f"{col} must be NaN on every unresolved row, not 0; "
            f"{int(unresolved[col].notna().sum())} resolved-looking value(s) "
            f"found")
    # At least one of them must have had a FINITE forward window, or this test
    # could not distinguish the mask from the NaN initialisation.
    partial = unresolved[unresolved["future_bars"] > 0]
    assert len(partial) > 0, "need partially-resolved rows to pin the mask"
    assert partial["forward_max_return"].notna().any(), (
        "a partially-resolved row must have a finite forward return, which is "
        "exactly the value the mask must suppress")
    print("ok  right_censoring_not_negative")


def test_strict_low_breaks_on_drawdown():
    """A 25% dip before the target must fail the 0.80 strict-low gate."""
    rows = _flat("000001", 40, price=10.0)
    rows[5]["low"] = 7.4   # -26% vs entry open 10.0
    rows[8]["high"] = 41.0
    df = labels.forward_outcomes(_frame(rows), horizon=30)
    row = df.iloc[0]
    assert row["label_bull"] == 1.0
    assert row["label_strict_low"] == 0.0, "dip beyond 20% must fail strict low"
    assert row["label_joint"] == 0.0
    print("ok  strict_low_breaks_on_drawdown")


def test_strict_low_boundary_inclusive():
    """A dip to exactly 0.80x entry passes; 0.7999 fails."""
    rows = _flat("000001", 40, price=10.0)
    rows[5]["low"] = 8.0
    rows[8]["high"] = 41.0
    df = labels.forward_outcomes(_frame(rows), horizon=30)
    assert df.iloc[0]["label_strict_low"] == 1.0

    rows[5]["low"] = 7.999
    df2 = labels.forward_outcomes(_frame(rows), horizon=30)
    assert df2.iloc[0]["label_strict_low"] == 0.0
    print("ok  strict_low_boundary_inclusive")


def test_entry_is_next_open_not_close():
    """Entry must be the next session's open."""
    rows = _flat("000001", 30, price=10.0)
    rows[1]["open"] = 20.0  # next open after bar 0
    df = labels.forward_outcomes(_frame(rows), horizon=20)
    assert df.iloc[0]["entry_open"] == 20.0, df.iloc[0]["entry_open"]
    print("ok  entry_is_next_open_not_close")


def test_cooldown_dedupes_clusters():
    """Signals inside the cooldown collapse to the first of the cluster."""
    dates = pd.bdate_range("2024-01-01", periods=100)
    sig = pd.DataFrame({
        "code": "000001",
        "date": dates[:10],
        "label_resolved": True,
        "label_bull": 1,
        "label_joint": 1,
        "label_strict_low": 1,
    })
    ded = labels.dedupe_signals(sig, cooldown=60)
    assert len(ded) == 1, f"expected 1 deduped signal, got {len(ded)}"
    print("ok  cooldown_dedupes_clusters")


def test_strict_greater_than_on_target_return():
    """Exactly +30% must NOT be a bull label on the ML ``target_return`` path.

    This is the *production* path: ``src/ml/build_matrix.py`` calls
    ``forward_outcomes(..., target_return=target)``, and the labels it produces are
    the target of every ML report. An adversarial review mutated the comparison at
    ``labels.py:186`` from ``>`` to ``>=`` -- making a bar that lands exactly on
    the threshold a bull -- and **all ten tests still passed**, because
    ``test_strict_greater_than_4x`` pins only the other branch (the ``target``
    multiple path at ``labels.py:188``). So the strict-inequality guarantee was
    enforced for the low-zone family and entirely unenforced for the ML family.

    The test compares against the SOURCE threshold, not the derived return. That
    matters: ``EPS = 1e-12`` in the denominator makes an exactly-4x bar report
    ``2.9999999999996``, so a probe written on ``forward_max_return`` would pass
    under either operator and could never catch this.
    """
    # Entry open is bar 0's next open, i.e. rows[1]["open"] = 10.0.
    rows = _flat("000001", 40, price=10.0)
    # Land exactly on +30%: 10.0 * 1.30 = 13.0.
    rows[5]["high"] = 13.0
    df = labels.forward_outcomes(_frame(rows), horizon=30, target_return=0.30)
    assert df.iloc[0]["label_bull"] == 0.0, (
        "a bar landing exactly on +30% must not be a bull label on the "
        "target_return path")

    # A hair above must be a bull.
    rows[5]["high"] = 13.0 + 1e-6
    df2 = labels.forward_outcomes(_frame(rows), horizon=30, target_return=0.30)
    assert df2.iloc[0]["label_bull"] == 1.0, "above +30% must be a bull label"

    # And a hair below must not be.
    rows[5]["high"] = 13.0 - 1e-6
    df3 = labels.forward_outcomes(_frame(rows), horizon=30, target_return=0.30)
    assert df3.iloc[0]["label_bull"] == 0.0, "below +30% must not be a bull label"
    print("ok  strict_greater_than_on_target_return")


def test_dedupe_respects_per_stock_boundary():
    """A cooldown cluster must never span two different stocks.

    ``dedupe_signals`` walks the frame sorted by (code, date) and keeps the first
    signal of each cluster, so it must start a NEW cluster when the code changes.
    An adversarial review removed that per-stock check at ``labels.py:226``
    (``if i == len(out) or codes[i] != codes[start]:`` -> ``if i == len(out):``)
    and **nothing caught it**: the previous fixture was single-code, so it could
    not distinguish "cluster per stock" from "one cluster for the whole frame".
    That mutant collapses an entire multi-stock signal set to its first row -- and
    ``dedupe_signals`` feeds ``score_signals``, i.e. every deduped hit rate in the
    published ledger.
    """
    # Two stocks interleaved in the input; both must survive.
    dates = pd.bdate_range("2024-01-01", periods=6)
    rows = []
    for i, d in enumerate(dates):
        rows.append({"code": "000001" if i % 2 == 0 else "000002", "date": d,
                     "label_resolved": True, "label_bull": 1, "label_joint": 1,
                     "label_strict_low": 1})
    sig = pd.DataFrame(rows)
    ded = labels.dedupe_signals(sig, cooldown=60)
    assert len(ded) == 2, (
        f"each stock must keep its own first signal; got {len(ded)} row(s) "
        f"for 2 stocks -- a single cluster can only mean the per-stock boundary "
        f"was dropped")
    assert sorted(ded["code"].unique()) == ["000001", "000002"]

    # Three stocks, several signals each: exactly three survive.
    rows = []
    for i, d in enumerate(pd.bdate_range("2024-01-01", periods=9)):
        rows.append({"code": f"{i % 3:06d}", "date": d,
                     "label_resolved": True, "label_bull": 1, "label_joint": 1,
                     "label_strict_low": 1})
    ded3 = labels.dedupe_signals(pd.DataFrame(rows), cooldown=60)
    assert len(ded3) == 3, f"expected 3 rows for 3 stocks, got {len(ded3)}"
    print("ok  dedupe_respects_per_stock_boundary")


def test_dedupe_cooldown_boundary_is_inclusive():
    """A signal exactly ``cooldown`` sessions after the kept one is itself KEPT.

    ``dedupe_signals`` keeps a row when ``positions[j] - last >= cooldown``, so the
    boundary is inclusive: exactly 60 sessions later starts a new cluster, 59 does
    not. The previous fixture spaced its dates one session apart against
    ``cooldown=60``, so the exact boundary was never exercised and ``>=`` -> ``>``
    at ``labels.py:229`` was caught by nothing.

    Note the distance is measured over the dates OBSERVED in the signal frame
    (``session_index`` is built from ``sorted(out["date"].unique())``), not over
    the exchange calendar. A frame whose only dates are day 0 and day 60 would
    therefore measure a distance of 1, not 60 -- which is exactly why this fixture
    plants a filler stock on every intervening session to make the grid dense.
    """
    dates = pd.bdate_range("2024-01-01", periods=400)

    def frame(second_offset: int) -> pd.DataFrame:
        rows = [{"code": "000001", "date": dates[0],
                 "label_resolved": True, "label_bull": 1, "label_joint": 1,
                 "label_strict_low": 1},
                {"code": "000001", "date": dates[second_offset],
                 "label_resolved": True, "label_bull": 1, "label_joint": 1,
                 "label_strict_low": 1}]
        # A filler stock on every session up to the second signal, so that the
        # observed-date grid is dense and `positions` counts real sessions.
        for d in dates[:second_offset]:
            rows.append({"code": "000002", "date": d,
                         "label_resolved": True, "label_bull": 1,
                         "label_joint": 1, "label_strict_low": 1})
        return pd.DataFrame(rows)

    # Exactly 60 sessions later: >= cooldown, so it is KEPT.
    ded = labels.dedupe_signals(frame(60), cooldown=60)
    kept = ded[ded["code"] == "000001"]
    assert len(kept) == 2, (
        f"a signal exactly 60 sessions after the kept one is at the cooldown "
        f"boundary and must be kept (>= is inclusive); got {len(kept)} of 2")

    # 59 sessions later: inside the cooldown, so it is SUPPRESSED. This is the
    # other side of the boundary and stops the test passing on an over-eager rule.
    ded2 = labels.dedupe_signals(frame(59), cooldown=60)
    kept2 = ded2[ded2["code"] == "000001"]
    assert len(kept2) == 1, (
        f"a signal 59 sessions later is inside the cooldown and must be "
        f"suppressed; got {len(kept2)} of the first signal only")
    print("ok  dedupe_cooldown_boundary_is_inclusive")


def test_wilson_upper_bound_is_not_a_constant():
    """The Wilson interval must actually respond to its inputs on BOTH ends.

    ``test_wilson_interval_sane`` asserted only ``lo < 0.79 < hi``, so replacing
    ``_wilson``'s upper return with the constant ``0.80`` passed. These assertions
    pin the upper bound to its value and to its monotonicity, so a constant (or a
    swapped/short-circuited bound) cannot pass.
    """
    lo, hi = labels._wilson(79, 100)
    # The published 79/100 -> 70.02% figure is the LOWER bound; the upper is
    # 0.8583. Asserting it against its real value is what makes this test bite:
    # the old version only checked `lo < 0.79 < hi`, which a constant 0.80 passes.
    assert 0.69 < lo < 0.71, lo
    assert 0.855 < hi < 0.862, hi
    assert hi > 0.79, hi

    # A constant upper bound cannot be monotone in the sample size.
    widths = []
    for n in (10, 100, 1000, 10000):
        lo_n, hi_n = labels._wilson(n // 2, n)
        widths.append(hi_n - lo_n)
    assert widths == sorted(widths, reverse=True), (
        f"the Wilson width must shrink as n grows; got {widths}")
    assert widths[0] > widths[-1] + 0.05, (
        f"n=10 and n=10000 must differ substantially in width; got {widths}")

    # Fully-predictive and fully-absent samples must not produce an inverted or
    # degenerate interval. The endpoints clamp to ~0 / ~1, not exactly, because the
    # clamp is `max(0.0, centre - half)` on a float that lands at 6.9e-18.
    for k, n in ((0, 50), (50, 50)):
        lo_k, hi_k = labels._wilson(k, n)
        assert 0.0 <= lo_k <= hi_k <= 1.0, (k, n, lo_k, hi_k)
    assert abs(labels._wilson(0, 50)[0]) < 1e-9
    assert abs(labels._wilson(50, 50)[1] - 1.0) < 1e-9
    print("ok  wilson_upper_bound_is_not_a_constant")



    """KDJ must not reset at a calendar boundary; a reset would be visible."""
    rows = []
    price = 10.0
    for i, d in enumerate(pd.bdate_range("2024-11-01", periods=120)):
        price = price * 1.004
        rows.append({"code": "000001", "date": d, "open": price, "high": price,
                     "low": price, "close": price, "volume": 1000.0})
    df = features.kdj(_frame(rows))
    # A reset to K=50 at the new year would create a discontinuity.
    around_new_year = df[(df["date"] >= "2024-12-20") & (df["date"] <= "2025-01-10")]
    diffs = around_new_year["kdj_k"].diff().abs().dropna()
    assert (diffs < 10).all(), "KDJ jumped across the year boundary (a reset)"
    assert df["kdj_k"].iloc[-1] > 70, "steady uptrend should leave K high"
    print("ok  kdj_continuous_across_year_boundary")


def test_kdj_flat_window_is_neutral():
    """A zero-range window must give RSV 50, not NaN or a division blowup."""
    df = features.kdj(_frame(_flat("000001", 30, price=10.0)))
    assert np.isfinite(df["kdj_k"]).all()
    assert abs(df["kdj_k"].iloc[-1] - 50.0) < 1e-6, df["kdj_k"].iloc[-1]
    print("ok  kdj_flat_window_is_neutral")


def test_wilson_interval_sane():
    lo, hi = labels._wilson(79, 100)
    assert 0.69 < lo < 0.71, lo          # matches the project's 79/100 -> 70.02%
    assert lo < 0.79 < hi
    print("ok  wilson_interval_sane")


def test_turnover_proxy_is_scale_invariant_for_ratio_strategies():
    """Volume is a valid turnover proxy for the ratio-based strategies.

    ``turnover`` is absent from every local OHLCV source, so we substitute
    ``volume``. This test proves the substitution is *exact* for the strategies
    that read only ratios, and records that ``leader_momentum`` (which reads the
    level) is the sole exception.
    """
    from experts.contracts import ExpertCard, VisibleBar
    from experts.registry import get_strategy

    ratio_strategies = [
        "accumulation_base", "turnover_weak_to_strong",
        "turnover_regime_switch", "strict_turnover_weak_to_strong_v2",
    ]

    def card(turnover_scale: float) -> ExpertCard:
        bars, kdj_k, kdj_d = [], [], []
        for i, d in enumerate(pd.bdate_range("2024-01-01", periods=60)):
            price = 10.0 + 0.05 * i
            bars.append(VisibleBar(
                date=d.strftime("%Y-%m-%d"), open=price, high=price * 1.01,
                low=price * 0.99, close=price, volume=1000.0 + 10 * i,
                amount=0.0, turnover=(1000.0 + 10 * i) * turnover_scale,
            ))
            kdj_k.append(50.0 + i * 0.1)
            kdj_d.append(50.0 + i * 0.05)
        return ExpertCard(
            sample_id="000001:2024-03-22", code="000001", name="x",
            observation_date=bars[-1].date, bars=tuple(bars),
            indicators={
                "kdj_k": tuple(kdj_k), "kdj_d": tuple(kdj_d),
                "kdj_j": tuple(3 * k - 2 * d for k, d in zip(kdj_k, kdj_d)),
                "turnover": tuple(b.turnover for b in bars),
                "volume_ratio": tuple(1.0 for _ in bars),
            },
            horizon_sessions=10, target_gain=0.30,
        )

    for sid in ratio_strategies:
        strategy = get_strategy(sid)
        a = strategy.predict(card(1.0))
        b = strategy.predict(card(1e-6))   # wildly different turnover *level*
        assert a.prediction == b.prediction, (
            f"{sid} is not scale-invariant in turnover; the volume proxy is invalid"
        )
        assert abs(a.score - b.score) < 1e-9, f"{sid} score shifted with turnover scale"
    print("ok  turnover_proxy_is_scale_invariant_for_ratio_strategies")


def main() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"\n{len(tests)}/{len(tests)} engine tests passed")


if __name__ == "__main__":
    main()
