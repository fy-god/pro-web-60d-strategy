# Pro Web 60-Day Strategy — Verification

Re-runs **every** strategy from two research lineages against real A-share daily
bars, reports the measured hit rate for each version, and plots a 120-session
K-line chart per signal with the signal bar marked and each strategy named
separately.

This repository is an **audit**, not a product. Its most important output is
which strategies do *not* work, and why the numbers that were previously
reported for them do not support the claims attached to them.

> **Can this be traded intraday? No — see §9.** Three findings make that
> conclusive: the signal needs the daily *close* (so the earliest possible fill
> is the next session's open), 15.8% of the highest-hit-rate strategy's signals
> are unbuyable limit-up opens, and **the hit-rate ranking is inverted against
> realised return** (Spearman −0.511) — the strategies with the best hit rates
> lose the most money.

---

## 1. What was verified

Two independent strategy families, both taken from the same source archive
(`D:\xm`) so nothing is re-implemented from memory:

| Family | Count | Source | Contract |
| --- | ---: | --- | --- |
| **Web Pro** | 36 | `exports/Luna_Max_Kline_Practice_Web_Pro_20260818/experts/` | 60 visible bars, 10-session horizon, +30% target |
| **60-Day Low-Zone** (V00–V08) | 7 | `60日预测/09_bull_lowzone_model/` | causal 60-day low zone, nested L1–L5 tiers, 4x target |

The Web Pro strategy source is vendored **byte-identical** under `experts/`, and
its published 100-card evaluation is reproduced exactly before any new
backtesting is trusted (see §3).

---

## 2. Data

Wired up first, before any strategy was run.

| Source file | Rows | Codes | Coverage |
| --- | ---: | ---: | --- |
| `mainboard_tencent_daily_2023_2024.csv` | 1,406,622 | 2,939 | 2023-01-03 → 2024-12-31 |
| `mainboard_tencent_daily_2025_20260831.csv` | 1,274,093 | 3,193 | 2025-01-02 → 2026-08-31 |
| **unified panel** | **2,680,715** | **3,193** | **2023-01-03 → 2026-08-31, 887 sessions** |

`python -m src.data_pipeline --build --verify` rebuilds and re-checks it. The
verification re-reads the raw CSVs and confirms, against a deterministic
2,000-row sample, **0 close mismatches, 0 volume mismatches**, plus 0 duplicate
`(code, date)` keys, 0 null closes, 0 broken high/low brackets and 0
close-outside-bracket rows.

### Two data limitations, stated up front

1. **`turnover` does not exist in any local source.** Every Tencent daily file
   in `D:\xm` carries an empty `amount` column. The original project explicitly
   refused to fabricate it (*"成交额字段为空，因此没有把成交额伪装成换手率"* —
   `volume_causal_filter_search_86.py`). We expose `turnover := volume` as a
   documented proxy. Of the five turnover-consuming strategies, three read only
   scale-invariant ratios and are provably unaffected; `tests/test_engine.py`
   pins this, and `leader_momentum` (which reads the turnover *level*) is
   flagged as proxy-sensitive in the results.
2. **Survivorship.** The universe is whatever was listed in the source files.
   Delisted names are absent, and the point-in-time universe is not available,
   so every hit rate here is optimistic by an unquantified amount.

---

## 3. Correctness gate: reproduce the published 100-card result first

Before trusting any new backtest, the vendored strategy code is run against the
same 100 real cards and sealed labels the original bundle used.

**Result: 11/11 published selectors reproduced exactly** — identical yes-count
*and* yes-precision to 4 decimal places:

| Strategy | Published | Reproduced | Yes-predictions |
| --- | ---: | ---: | ---: |
| `strict_bollinger_release_v2` | 80.00% | 80.00% | 5 |
| `strict_accumulation_base_v2` | 73.33% | 73.33% | 15 |
| `strict_gap_follow_through_v2` | 72.73% | 72.73% | 22 |
| `strict_leader_momentum_v2` | 72.73% | 72.73% | 11 |
| `strict_platform_breakout_v2` | 72.73% | 72.73% | 11 |
| `strict_relative_strength_v2` | 72.73% | 72.73% | 11 |
| `strict_washout_complete_v2` | 72.22% | 72.22% | 18 |
| `strict_first_board_breakout_v2` | 71.43% | 71.43% | 7 |
| `strict_oversold_rebound_v2` | 70.59% | 70.59% | 17 |
| `strict_obv_volume_price_v2` | 70.00% | 70.00% | 10 |
| `strict_turnover_weak_to_strong_v2` | 68.42% | 68.42% | 19 |

`python -m src.validate_cards` reproduces this table. This proves the vendored
source is unmodified, card assembly is correct, and the accounting agrees.

**But read the caveat the bundle itself records:** those v2 thresholds were
selected on the same 100 cards being reported. It is a fixed exploratory quiz,
not an out-of-sample test. A 70–80% number from 5–22 yes-predictions on
self-selected thresholds is not evidence of future performance.

---

## 4. Engine rules (each one fixes a documented past defect)

`src/labels.py` and `src/features.py` implement these; `tests/test_engine.py`
pins each with a test (9/9 passing).

| Rule | Why |
| --- | --- |
| Entry = **next session's open**, never the signal close | A signal is only actionable after the bar closes |
| Target is **strictly greater than** 4x, not `>=` | The original mixed the two and mislabelled exact-4x bars |
| Censored rows are **NaN, excluded from denominators** | A truncated future window is not a negative |
| **Continuous KDJ** — no reset at year or card boundaries | Resetting `K=D=50` every 40 bars made extended stocks look oversold again |
| **Event dedup by session distance**, not calendar days | Holidays silently shortened the original cooldown |
| Report **distinct stocks and distinct dates** alongside precision | "13 signals" was really 3 distinct market dates; one date carried 7 of 9 hits |
| Wilson interval on every rate | 78% of 100 does not clear a 70% lower bound; ~79% does |
| **Lift vs. base rate** reported for every precision | 4% precision means opposite things at a 1.6% vs 0.2% base rate |

---

## 5. Results

Full tables: [`RESULTS.md`](RESULTS.md), regenerated from the backtest CSVs by
`python -m src.render_results`.

### Natural base rates

The population every strategy is scored against. Nothing here is interpretable
without these.

| Regime | Contract | Evaluated points | Natural success rate |
| --- | --- | ---: | ---: |
| `webpro` | 10 sessions, +30% | 493,246 | **3.0348%** |
| `low60` | 60 sessions, 4x (+300%) | 461,416 | **0.0752%** |
| `low504` | 504 sessions, 4x | 187,729 | **4.6956%** |

These were recomputed a second time from the raw panel by a separate script and
matched to six decimal places.

### Web Pro family — 36 strategies, 3,193 stocks, 493,246 evaluated points

Top of the ranking, by lift over the 3.035% base rate:

| Strategy | Signals | Hits | Hit rate | Lift | Wilson 95% low |
| --- | ---: | ---: | ---: | ---: | ---: |
| `leader_momentum` | 553 | 106 | **19.17%** | 6.32x | 16.10% |
| `strict_leader_momentum_v2` | 2,502 | 401 | **16.03%** | 5.28x | 14.64% |
| `strict_relative_strength` | 1,955 | 308 | **15.75%** | 5.19x | 14.21% |
| `strict_relative_strength_v2` | 2,167 | 334 | **15.41%** | 5.08x | 13.95% |
| `strict_gap_follow_through` | 2,586 | 342 | **13.23%** | 4.36x | 11.97% |
| `gap_follow_through` | 3,198 | 398 | **12.45%** | 4.10x | 11.35% |

All 36 are in `RESULTS.md`. **The best strategy reaches 19.17%, not 70–80%.**

Why this differs so sharply from the published 70–80% table: those numbers came
from 5–22 hand-picked yes-predictions on a self-selected 100-card quiz, where
the threshold was tuned on the very cards being reported. Here every strategy is
run on all 493,246 evaluable stock-days across 3,193 stocks and every emitted
signal counts. `leader_momentum` keeps its 6.3x edge but at 106/553 — and it is
the one strategy whose turnover input is a proxy (§2), so its exact level is the
least trustworthy of the six.

The bottom of the table matters just as much: `strict_oversold_rebound_v2`,
`rsi_mean_reversion` and `strict_accumulation_base_v2` all score **below 1.0x
lift** — they are worse than picking at random, despite two of them appearing in
the published 70%+ table.

### 60-Day Low-Zone family — V00–V08

| Version | Regime | Signals | Hits | Hit rate | Lift | Protocol |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| V00 | webpro | 71,841 | 2,245 | 3.12% | 1.01x | rule, all tiers |
| V01 | webpro | 48,838 | 1,437 | 2.94% | 0.95x | rule, L3+ |
| V02 | webpro | 14,799 | 485 | 3.28% | 1.06x | rule, L5 |
| V03 | webpro | 26,897 | 1,176 | **4.37%** | 1.42x | gain model (best honest) |
| V06 | webpro | 18,734 | 543 | 2.90% | 0.94x | competitive, cross-year |
| V07 | webpro | 8,666 | 367 | 4.23% | 1.37x | **in-sample fit** |
| V08 | webpro | 4,907 | 200 | 4.08% | 1.32x | **in-sample fit** |
| V02 | low60 (4x) | 8,237 | 12 | 0.15% | 2.01x | rule, L5 |
| V07 | low60 (4x) | 4,968 | 7 | 0.14% | 1.94x | **in-sample fit** |

**The 4x target is essentially unreachable.** Under the 60-session/4x contract
the natural base rate is 0.0752% — the best version achieves 0.15% on 12 hits,
with a Wilson lower bound of 0.083%. No version gets a hit rate above 0.15%.

**V07/V08's apparent advantage is the in-sample protocol.** Their thresholds are
chosen on the evaluation year's own labels, exactly as the source project's V08
record does. Under that protocol they reach 4.23%/4.08% versus 4.37% for the
honest walk-forward V03 — i.e. the per-year tuning buys *nothing*, and V03
gained on the same footing as V07/V08 is still the better result. This is
consistent with the independent audit's finding that V08's claimed
`PASS_YEARWISE_IN_SAMPLE` rests on same-year fitting.

### What this means

1. **No strategy in either family reaches 70%.** Across 43 strategy versions and
   1,286,000+ evaluated stock-days, the ceiling is 19.17%, and the honest
   walk-forward low-zone ceiling is 4.37%.
2. **The 4x-in-60-sessions target has effectively no signal.** Base rate 0.0752%;
   the best lift is 2.0x on 12 hits, which is not distinguishable from noise.
3. **Several published "winners" are below chance** on the full population.
4. **A few strategies show a real, modest edge.** `leader_momentum` (6.3x),
   `strict_leader_momentum_v2` (5.3x) and `strict_relative_strength` (5.2x) beat
   the base rate by a wide margin on thousands of independent signals across
   500–1,800 distinct stocks and 217–389 distinct market dates. That is the only
   class of result here with a plausible claim to being a real effect — and at
   16–19%, it is a long way from 70%.

---

## 6. Charts

`outputs/charts_120d/` — one folder per strategy, each chart showing **120
sessions (60 before / 60 after the signal)**, the signal bar, the next-open
entry, the target line, and the first target touch.

Filenames are `<code>_<YYYYMMDD>_<hit|miss>.png` inside a per-strategy folder,
and each chart carries its own strategy name and id in the title, so charts can
never be confused across strategies. `outputs/charts_120d/index.html` indexes
them grouped by strategy with the hit rate in each heading.

Both hits **and** misses are rendered deliberately: a chart set containing only
winners is the exact failure mode this audit exists to prevent.

---

## 7. Reproduce

```bash
python -m src.data_pipeline --build --verify     # wire up + verify the panel
python -m tests.test_engine                      # 10/10 engine unit tests
python -m src.validate_cards                     # 11/11 published selectors reproduced
python -m src.build_shards --shards 8            # shard by code for bounded memory
python -m src.scan_all --stride 5                # 36 Web Pro strategies, full universe
python -m src.backtest_lowzone                   # V00-V08 low-zone family
python -m src.make_charts                        # 120-session charts per strategy
python -m src.tradeability                       # can the signals be filled?
python -m src.live_readiness                     # realised expectancy net of costs
python -m src.hitrate_vs_expectancy              # hit rate vs. what it earns
python -m src.render_results                     # regenerate RESULTS.md
```

Requires `pandas`, `numpy`, `scikit-learn`, `pyarrow`, `matplotlib`.
Set `PWS_DATA_ROOT` to relocate the raw OHLCV source.

---

## 8. Interpretation boundary

Every number in §5 is a **retrospective, in-sample or pooled** measurement on a
survivorship-biased universe, with no transaction costs, no slippage, no
limit-up unfillability filter and no point-in-time index membership. Nothing
here is a forecast, a recommendation, or evidence of profitability.

Hit rate is reported per version with its denominator, its distinct-stock and
distinct-date counts, its Wilson interval, and its lift over the natural base
rate, because precision without those four things cannot be interpreted.

---

## 9. Can this be used in live trading, including intraday?

**No.** Not "not yet" and not "with more tuning" — the measurements below rule
out intraday use structurally, and rule out end-of-day use on the evidence
available.

### 9.1 The signal is not knowable until the close

Every strategy consumes a 60-bar **daily** card (`src/runner.make_card`), and the
signal bar is the last visible bar. Evaluating the rule requires that bar's
**close** and its full-day high/low/volume. Mid-session you do not have them.

Substituting the current price for the close changes the rule. A strategy tested
on `close > ma20` is a different strategy from one tested on `price_so_far >
ma20`, and the difference is not a rounding error: it decides membership in
every band, breakout and low-zone condition. **Nothing in §5 was backtested that
way**, so intraday use would be running unvalidated logic.

Consequence: the earliest moment a signal can be acted on is **the next
session's open** — one overnight gap after the information arrives. That gap is
not captured by any hit rate here, because entry is *defined* as that open.

The original project's own intraday documentation makes the same distinction
explicitly, describing a *different* system: the signal "is confirmed at the close
of a one-minute candle and the fill window is the next minute". That is a
one-minute strategy with a one-minute holding latency. This one is a daily
strategy. They are not interchangeable.

### 9.2 15.8% of the best strategy's signals cannot be bought

A share that gaps to its price limit at the open has no sellers, so the stated
entry — the next open — does not exist. The original project's entry test
(`next_day_volume > 0 and next_day_open > 0`) accepts such bars as valid, which
biases its precision upward. Measuring it on the actual emitted signals
(`src/tradeability.py`, 646,718 signals):

| Strategy | Signals | Unfillable | Share | One-word limit boards | Hit rate as reported | Excluding unfillable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `leader_momentum` | 619 | 98 | **15.83%** | 32 | 20.52% | **18.23%** |
| `strict_gap_follow_through` | 3,172 | 430 | 13.56% | 171 | 14.06% | 12.33% |
| `gap_follow_through` | 4,022 | 487 | 12.11% | 193 | 12.85% | 11.17% |
| `strict_leader_momentum_v2` | 3,261 | 368 | 11.28% | 123 | 15.85% | 14.62% |

Family-wide: **10,976 of 646,718 signals (1.70%) are unfillable**, of which 4,410
are one-word limit boards where the entire session is pinned. Concretely, the
highest-hit-rate strategy in the whole family loses **2.3 percentage points** of
its headline precisely because the best signal is the one you cannot get filled
on. ST names are treated as 10% boards for lack of status data, so their true 5%
limit makes this an **underestimate**.

### 9.3 The headline number is inverted against what you earn

Hit rate counts a signal as a success if the forward **maximum high** touches
+30% within 10 sessions. It never asks what the other signals did, or what the
holder actually got. Computing the realised next-open-to-horizon-close return on
the *same* signals, net of 10.2 bp round-trip cost (`src/hitrate_vs_expectancy.py`):

| Strategy | Hit rate | Net 10d return | If hit | If miss | Net win rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `leader_momentum` | 20.62% | **−4.65%** | +22.37% | −11.54% | 32.79% |
| `strict_leader_momentum_v2` | 15.96% | **−1.82%** | +26.33% | −7.05% | 37.76% |
| `strict_relative_strength` | 15.75% | **−1.80%** | +27.74% | −7.20% | 37.01% |
| `strict_relative_strength_v2` | 15.24% | **−1.86%** | +27.69% | −7.06% | 36.70% |
| `rsi_mean_reversion` | 4.10% | **+1.69%** | +29.06% | +0.63% | 52.61% |
| `strict_oversold_rebound_v2` | 3.51% | **+0.74%** | +27.50% | −0.12% | 49.78% |

**Spearman rank correlation between hit rate and net expectancy: −0.511.** The
reporting metric orders the strategies almost exactly backwards. Four of the top
five hit rates lose money; `leader_momentum` is simultaneously the best hit rate
and the worst expectancy in the family. Only **15 of 35** strategies have
positive net expectancy, and only **20 of 35** stay positive even when every hit
is credited with a perfect +30% exit.

The mechanism is plain in the conditional columns: winners are held to their
+30% touch (+22% to +29%) while losers run to the horizon close (−7% to −12%).
These are high-variance, negatively-skewed signals. A 20% chance of +30% does not
compensate for an 80% chance of −11.5%.

### 9.4 What would be required first

| Requirement | Status |
| --- | --- |
| Point-in-time universe (no survivorship bias) | **not met** — universe is today's listed set |
| Transaction costs and slippage | **partly met** — 10.2 bp modelled; slippage not |
| Limit-up / unfillable entry filter | **met** — `src/tradeability.py` (§9.2) |
| True out-of-sample period (never used for selection) | **not met** — one pooled 2023–2026 sample |
| Independent confirmation on unseen data | **not met** |
| Intraday-minute validation of the daily rules | **not met** — and the local minute data is 2 weeks × 100 stocks, which cannot support it |

The one strategy family with a genuinely frozen cross-year test in the source
material failed it (7/50 = 14.0%, with 48/50 loss false alerts), and two lockbox
sweeps passed 0 of 48 variants. So the honest expectation for unseen data is
**worse** than anything in the table above.

**Verdict: research artifact only.** Intraday use is ruled out by §9.1 (the rule
needs the close) and §9.2 (the best entries are unfillable); end-of-day use is
ruled out by §9.3 (the metric that looks best earns the least). Any live use
would need a point-in-time universe, a true holdout, slippage modelling and
intraday validation first.
