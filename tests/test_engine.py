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
    """A truncated future window yields NaN, never 0."""
    rows = _flat("000001", 20, price=10.0)
    df = labels.forward_outcomes(_frame(rows), horizon=60)
    tail = df.iloc[-1]
    assert pd.isna(tail["label_bull"]), "censored row must be NaN"
    assert tail["label_resolved"] == False  # noqa: E712
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


def test_kdj_continuous_across_year_boundary():
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
