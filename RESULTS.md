# Measured Results

Every number below is regenerated from the backtest output CSVs by `python -m src.render_results`, so it cannot drift from the data.

## Natural base rates (the population each strategy is scored against)

| Regime | Contract | Evaluated points | Natural bull rate | Natural joint rate |
| --- | --- | ---: | ---: | ---: |
| `webpro` | 10 sessions, **+30%** | 493,246 | 3.0348% | 3.0311% |
| `low60` | 60 sessions, **4x** (i.e. +300%) | 461,416 | 0.0752% | 0.0748% |
| `low504` | 504 sessions, **4x** | 187,729 | 4.6956% | 2.4855% |

These are measured on the **scanned evaluation grid**: per-stock bar index `_seq >= 60` and then every 5th bar. That is the population the strategies were actually scored on, so it is the correct denominator for every lift below. It is *not* the whole panel — because almost every stock is present on the first session, the `_seq >= 60` filter also drops the 2023-Q1 warm-up window, which is why the scanned rate sits above the full-panel rate for `low504`. `reports/lowzone_baselines.json` publishes the full-panel figures (different populations, different numbers); a lift must not mix the two. See [README.md §5](README.md#5-results). (This file predates the `population` block now emitted by `src.scan_all`; the row set is inferred from the fact that `webpro_baselines.json` is written by `population_baselines`. Re-run `python -m src.scan_all --stride 5` to record it explicitly.)



## Web Pro family — 36 strategies registered, 35 signalled

Horizon 10 sessions, target +30%, entry at the next session's open, signals de-duplicated at a 60-session cooldown. **Lift** is the hit rate divided by the natural base rate of 3.035% *on the scanned evaluation grid* (the population above, and the grid these strategies were scored on): a lift of 1.0 means the strategy is indistinguishable from picking at random.

| # | Strategy | Signals | Hits | **Hit rate** | Base rate | Lift | Wilson 95% low | Stocks | Dates |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `leader_momentum` | 553 | 106 | **19.17%** | 3.035% | 6.32x | 16.10% | 520 | 217 |
| 2 | `strict_leader_momentum_v2` | 2502 | 401 | **16.03%** | 3.035% | 5.28x | 14.64% | 1775 | 389 |
| 3 | `strict_relative_strength` | 1955 | 308 | **15.75%** | 3.035% | 5.19x | 14.21% | 1502 | 337 |
| 4 | `strict_relative_strength_v2` | 2167 | 334 | **15.41%** | 3.035% | 5.08x | 13.95% | 1623 | 348 |
| 5 | `strict_gap_follow_through` | 2586 | 342 | **13.23%** | 3.035% | 4.36x | 11.97% | 1745 | 391 |
| 6 | `gap_follow_through` | 3198 | 398 | **12.45%** | 3.035% | 4.10x | 11.35% | 1981 | 430 |
| 7 | `oversold_rebound` | 310 | 37 | **11.94%** | 3.035% | 3.93x | 8.78% | 303 | 108 |
| 8 | `strict_obv_volume_price_v2` | 2453 | 287 | **11.70%** | 3.035% | 3.86x | 10.49% | 1810 | 358 |
| 9 | `strict_obv_volume_price` | 2427 | 283 | **11.66%** | 3.035% | 3.84x | 10.44% | 1793 | 357 |
| 10 | `strict_gap_follow_through_v2` | 4623 | 522 | **11.29%** | 3.035% | 3.72x | 10.41% | 2451 | 481 |
| 11 | `turnover_weak_to_strong` | 256 | 28 | **10.94%** | 3.035% | 3.60x | 7.68% | 250 | 118 |
| 12 | `relative_strength_rank` | 8977 | 904 | **10.07%** | 3.035% | 3.32x | 9.46% | 2954 | 572 |
| 13 | `limit_up_retest` | 6679 | 659 | **9.87%** | 3.035% | 3.25x | 9.17% | 2665 | 508 |
| 14 | `reversal_engulf` | 61 | 6 | **9.84%** | 3.035% | 3.24x | 4.59% | 61 | 40 |
| 15 | `strict_turnover_weak_to_strong_v2` | 5182 | 509 | **9.82%** | 3.035% | 3.24x | 9.04% | 2594 | 475 |
| 16 | `turnover_regime_switch` | 2465 | 209 | **8.48%** | 3.035% | 2.79x | 7.44% | 1811 | 344 |
| 17 | `main_wave_acceleration` | 9035 | 724 | **8.01%** | 3.035% | 2.64x | 7.47% | 3049 | 533 |
| 18 | `donchian_turtle` | 13582 | 942 | **6.94%** | 3.035% | 2.29x | 6.52% | 3153 | 622 |
| 19 | `high_level_consensus` | 158 | 10 | **6.33%** | 3.035% | 2.09x | 3.47% | 158 | 80 |
| 20 | `strict_bollinger_release_v2` | 3236 | 203 | **6.27%** | 3.035% | 2.07x | 5.49% | 2184 | 362 |
| 21 | `washout_complete` | 4499 | 281 | **6.25%** | 3.035% | 2.06x | 5.58% | 2567 | 405 |
| 22 | `atr_trend_follow` | 17431 | 994 | **5.70%** | 3.035% | 1.88x | 5.37% | 3168 | 633 |
| 23 | `strict_washout_complete` | 11019 | 616 | **5.59%** | 3.035% | 1.84x | 5.18% | 3114 | 532 |
| 24 | `platform_breakout` | 1361 | 76 | **5.58%** | 3.035% | 1.84x | 4.48% | 1213 | 238 |
| 25 | `strict_washout_complete_v2` | 12059 | 655 | **5.43%** | 3.035% | 1.79x | 5.04% | 3127 | 549 |
| 26 | `obv_volume_price` | 23588 | 1115 | **4.73%** | 3.035% | 1.56x | 4.46% | 3180 | 676 |
| 27 | `strict_first_board_breakout_v2` | 10962 | 515 | **4.70%** | 3.035% | 1.55x | 4.32% | 3133 | 569 |
| 28 | `bollinger_squeeze` | 21946 | 956 | **4.36%** | 3.035% | 1.44x | 4.09% | 3177 | 685 |
| 29 | `first_board_breakout` | 4556 | 192 | **4.21%** | 3.035% | 1.39x | 3.67% | 2584 | 410 |
| 30 | `strict_platform_breakout` | 9485 | 392 | **4.13%** | 3.035% | 1.36x | 3.75% | 3088 | 557 |
| 31 | `strict_platform_breakout_v2` | 12978 | 522 | **4.02%** | 3.035% | 1.33x | 3.70% | 3154 | 597 |
| 32 | `pullback_retest` | 5841 | 230 | **3.94%** | 3.035% | 1.30x | 3.47% | 2700 | 452 |
| 33 | `strict_accumulation_base_v2` | 27398 | 928 | **3.39%** | 3.035% | 1.12x | 3.18% | 3189 | 674 |
| 34 | `strict_oversold_rebound_v2` | 31754 | 930 | **2.93%** | 3.035% | 0.97x | 2.75% | 3186 | 689 |
| 35 | `rsi_mean_reversion` | 12553 | 351 | **2.80%** | 3.035% | 0.92x | 2.52% | 3147 | 535 |

_Base rate_ here is the **scanned evaluation grid** figure, matching the grid these strategies were scored on. The 60-day low-zone table below uses a base rate censused over the **full resolved panel** instead, because those versions are evaluated on every resolved bar rather than on a thinned grid. Both are internally consistent, but the two base-rate columns are **not interchangeable**: the same `webpro` contract reads 3.035% on the scanned grid and 3.089% on the full panel.


_The family declares **36** strategies; the table below ranks the **35 that emitted at least one signal**. `accumulation_base` fired **zero** times over the whole evaluated universe, so it has no row in `reports/webpro_hit_rates.csv` and cannot be ranked. Absence here means "never triggered", not "excluded"; it is still exercised by the 100-card reproduction in `README.md` §3._


## What a holder actually earns — the hit-rate inversion

Hit rate is the share of signals whose forward **maximum high** touches +30% within 10 sessions. It says nothing about what happens on the other signals. This table computes, on those same signals, the mean realised next-open-to-horizon-close return net of 10.2 bp round-trip cost.

**The two rankings are inverted** (Spearman rho = -0.511): the strategies with the highest hit rates lose the most money. `leader_momentum` has the best hit rate in the family and the worst expectancy; `rsi_mean_reversion` and `strict_oversold_rebound_v2` sit at or below the 3.035% base rate and are among the minority that make money.

**If hit** and **if miss** are conditional means and are therefore selection-biased by construction; they appear only to expose the lottery structure — winners are credited with their +30% touch while losers run to the horizon close.

| Strategy | Signals | Hit rate | **Net 10d return** | At-target | If hit | If miss | Net win rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `leader_momentum` | 616 | 20.62% | **-4.65%** | -3.08% | +22.37% | -11.54% | 32.79% |
| `strict_leader_momentum_v2` | 3239 | 15.96% | **-1.82%** | -1.24% | +26.33% | -7.05% | 37.76% |
| `strict_relative_strength` | 2864 | 15.75% | **-1.80%** | -1.44% | +27.74% | -7.20% | 37.01% |
| `strict_relative_strength_v2` | 3267 | 15.24% | **-1.86%** | -1.51% | +27.69% | -7.06% | 36.70% |
| `strict_gap_follow_through` | 3137 | 14.22% | **-0.05%** | +0.30% | +27.57% | -4.51% | 42.72% |
| `gap_follow_through` | 3978 | 13.00% | **+0.12%** | +0.43% | +27.63% | -3.87% | 43.49% |
| `strict_obv_volume_price_v2` | 2892 | 12.34% | **-0.90%** | -0.48% | +26.62% | -4.66% | 40.21% |
| `strict_obv_volume_price` | 2857 | 12.29% | **-0.92%** | -0.52% | +26.72% | -4.68% | 40.15% |
| `oversold_rebound` | 334 | 12.28% | **+3.96%** | +4.15% | +28.43% | +0.65% | 58.68% |
| `strict_gap_follow_through_v2` | 5981 | 11.67% | **+0.41%** | +0.74% | +27.20% | -3.02% | 45.24% |
| `turnover_weak_to_strong` | 269 | 11.15% | **-0.05%** | +0.10% | +28.68% | -3.54% | 41.64% |
| `relative_strength_rank` | 20112 | 11.11% | **-0.25%** | -0.05% | +28.16% | -3.69% | 41.71% |
| `limit_up_retest` | 12035 | 10.69% | **+0.05%** | +0.30% | +27.69% | -3.14% | 44.29% |
| `strict_turnover_weak_to_strong_v2` | 6792 | 10.17% | **-0.09%** | +0.23% | +26.86% | -3.03% | 43.83% |
| `reversal_engulf` | 62 | 9.68% | **-3.55%** | -2.64% | +20.55% | -6.02% | 32.26% |
| `main_wave_acceleration` | 14482 | 8.76% | **-0.26%** | -0.05% | +27.55% | -2.82% | 42.27% |
| `turnover_regime_switch` | 2844 | 8.72% | **-0.23%** | -0.11% | +28.70% | -2.88% | 42.97% |
| `donchian_turtle` | 24242 | 8.01% | **-0.24%** | -0.02% | +27.33% | -2.53% | 43.07% |
| `washout_complete` | 5755 | 6.64% | **-0.06%** | -0.05% | +29.92% | -2.08% | 42.52% |
| `atr_trend_follow` | 37800 | 6.57% | **-0.03%** | +0.13% | +27.51% | -1.86% | 44.28% |
| `strict_bollinger_release_v2` | 3722 | 6.31% | **-0.15%** | +0.20% | +24.42% | -1.69% | 44.25% |
| `strict_washout_complete` | 19351 | 6.26% | **+0.37%** | +0.43% | +29.18% | -1.44% | 45.55% |
| `high_level_consensus` | 162 | 6.17% | **+1.81%** | +1.16% | +40.54% | -0.63% | 47.53% |
| `strict_washout_complete_v2` | 22770 | 6.10% | **+0.35%** | +0.41% | +29.16% | -1.41% | 45.69% |
| `obv_volume_price` | 76693 | 5.84% | **+0.36%** | +0.46% | +28.26% | -1.27% | 45.83% |
| `platform_breakout` | 1514 | 5.75% | **-1.39%** | -1.08% | +24.70% | -2.87% | 35.80% |
| `strict_first_board_breakout_v2` | 16420 | 4.67% | **+0.59%** | +0.73% | +27.02% | -0.60% | 47.77% |
| `bollinger_squeeze` | 47903 | 4.65% | **+0.01%** | +0.17% | +26.57% | -1.18% | 45.31% |
| `first_board_breakout` | 5749 | 4.28% | **+0.64%** | +0.75% | +27.38% | -0.45% | 47.61% |
| `strict_platform_breakout` | 13034 | 4.25% | **-0.37%** | -0.23% | +26.72% | -1.46% | 42.70% |
| `pullback_retest` | 7948 | 4.15% | **+0.28%** | +0.31% | +29.45% | -0.87% | 46.14% |
| `strict_platform_breakout_v2` | 19538 | 4.13% | **-0.31%** | -0.17% | +26.63% | -1.36% | 43.47% |
| `rsi_mean_reversion` | 25476 | 4.10% | **+1.69%** | +1.73% | +29.06% | +0.63% | 52.61% |
| `strict_oversold_rebound_v2` | 146580 | 3.51% | **+0.74%** | +0.83% | +27.50% | -0.12% | 49.78% |
| `strict_accumulation_base_v2` | 77081 | 3.47% | **+0.78%** | +0.84% | +28.27% | -0.10% | 49.81% |


## Can the signals actually be bought?

Every hit rate above assumes the entry is the next session's open. A stock that gaps to its price limit at the open has no sellers, so that entry does not exist. This measures how much of each strategy's signal count is unfillable, and the hit rate once those are removed.

| Strategy | Signals | Unfillable | Share | One-word limit | Hit rate as reported | Hit rate excluding unfillable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `leader_momentum` | 616 | 98 | 15.91% | 32 | 20.62% | 18.34% |
| `strict_gap_follow_through` | 3137 | 425 | 13.55% | 167 | 14.22% | 12.46% |
| `gap_follow_through` | 3978 | 480 | 12.07% | 189 | 13.00% | 11.29% |
| `strict_leader_momentum_v2` | 3239 | 366 | 11.30% | 122 | 15.96% | 14.72% |
| `strict_gap_follow_through_v2` | 5981 | 560 | 9.36% | 222 | 11.67% | 10.24% |
| `strict_relative_strength` | 2864 | 188 | 6.56% | 63 | 15.75% | 14.69% |
| `strict_obv_volume_price` | 2857 | 181 | 6.34% | 57 | 12.29% | 11.55% |
| `strict_obv_volume_price_v2` | 2892 | 181 | 6.26% | 57 | 12.34% | 11.62% |
| `strict_relative_strength_v2` | 3267 | 201 | 6.15% | 69 | 15.24% | 14.22% |
| `turnover_weak_to_strong` | 269 | 12 | 4.46% | 8 | 11.15% | 10.51% |
| `turnover_regime_switch` | 2844 | 116 | 4.08% | 55 | 8.72% | 8.06% |
| `main_wave_acceleration` | 14482 | 578 | 3.99% | 252 | 8.76% | 7.98% |
| `relative_strength_rank` | 20112 | 786 | 3.91% | 332 | 11.11% | 10.44% |
| `donchian_turtle` | 24242 | 877 | 3.62% | 382 | 8.01% | 7.32% |
| `strict_turnover_weak_to_strong_v2` | 6792 | 218 | 3.21% | 80 | 10.17% | 9.84% |
| `limit_up_retest` | 12035 | 356 | 2.96% | 131 | 10.69% | 10.24% |
| `strict_bollinger_release_v2` | 3722 | 97 | 2.61% | 36 | 6.31% | 6.04% |
| `atr_trend_follow` | 37800 | 943 | 2.49% | 409 | 6.57% | 6.09% |
| `oversold_rebound` | 334 | 8 | 2.40% | 5 | 12.28% | 11.66% |
| `platform_breakout` | 1514 | 31 | 2.05% | 14 | 5.75% | 5.33% |
| `strict_washout_complete` | 19351 | 335 | 1.73% | 151 | 6.26% | 5.89% |
| `strict_washout_complete_v2` | 22770 | 383 | 1.68% | 170 | 6.10% | 5.74% |
| `washout_complete` | 5755 | 96 | 1.67% | 47 | 6.64% | 6.29% |
| `reversal_engulf` | 62 | 1 | 1.61% | 0 | 9.68% | 8.20% |
| `bollinger_squeeze` | 47903 | 660 | 1.38% | 281 | 4.65% | 4.40% |
| `strict_platform_breakout` | 13034 | 161 | 1.24% | 69 | 4.25% | 4.04% |
| `high_level_consensus` | 162 | 2 | 1.23% | 1 | 6.17% | 5.62% |
| `obv_volume_price` | 76693 | 897 | 1.17% | 373 | 5.84% | 5.61% |
| `strict_platform_breakout_v2` | 19538 | 228 | 1.17% | 92 | 4.13% | 3.94% |
| `strict_first_board_breakout_v2` | 16420 | 140 | 0.85% | 69 | 4.67% | 4.56% |
| `pullback_retest` | 7948 | 62 | 0.78% | 29 | 4.15% | 3.92% |
| `strict_accumulation_base_v2` | 77081 | 364 | 0.47% | 151 | 3.47% | 3.38% |
| `first_board_breakout` | 5749 | 18 | 0.31% | 9 | 4.28% | 4.26% |
| `strict_oversold_rebound_v2` | 146580 | 324 | 0.22% | 163 | 3.51% | 3.47% |
| `rsi_mean_reversion` | 25476 | 37 | 0.15% | 17 | 4.10% | 4.07% |


## 60-Day Low-Zone family — V00–V08

Scored under both contracts. V07/V08 use a per-year threshold chosen on the evaluation year itself and are flagged as in-sample fits, which is what the source project's own record does.

| Version | Regime | Signals | Hits | **Hit rate** | Base rate | Lift | Wilson 95% low | Stocks | Protocol |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **V00** | low60 | 18952 | 15 | **0.08%** | 0.073% | 1.09x | 0.05% | 3178 | walk-forward, prior-year threshold |
| **V01** | low60 | 15363 | 14 | **0.09%** | 0.073% | 1.26x | 0.05% | 3168 | walk-forward, prior-year threshold |
| **V02** | low60 | 8237 | 12 | **0.15%** | 0.073% | 2.01x | 0.08% | 3042 | walk-forward, prior-year threshold |
| **V03** | low60 | 17622 | 14 | **0.08%** | 0.073% | 1.10x | 0.05% | 3168 | walk-forward, prior-year threshold |
| **V06** | low60 | 9347 | 9 | **0.10%** | 0.073% | 1.33x | 0.05% | 3083 | walk-forward, prior-year threshold |
| **V07** | low60 | 4968 | 7 | **0.14%** | 0.073% | 1.94x | 0.07% | 2498 | per-year in-sample fit (NOT cross-year) |
| **V08** | low60 | 4136 | 3 | **0.07%** | 0.073% | 1.00x | 0.02% | 2498 | per-year in-sample fit (NOT cross-year) |
| **V00** | webpro | 71841 | 2245 | **3.12%** | 3.089% | 1.01x | 3.00% | 3186 | walk-forward, prior-year threshold |
| **V01** | webpro | 48838 | 1437 | **2.94%** | 3.089% | 0.95x | 2.80% | 3181 | walk-forward, prior-year threshold |
| **V02** | webpro | 14799 | 485 | **3.28%** | 3.089% | 1.06x | 3.00% | 3102 | walk-forward, prior-year threshold |
| **V03** | webpro | 26897 | 1176 | **4.37%** | 3.089% | 1.42x | 4.13% | 3061 | walk-forward, prior-year threshold |
| **V06** | webpro | 18734 | 543 | **2.90%** | 3.089% | 0.94x | 2.67% | 3016 | walk-forward, prior-year threshold |
| **V07** | webpro | 8666 | 367 | **4.23%** | 3.089% | 1.37x | 3.83% | 2610 | per-year in-sample fit (NOT cross-year) |
| **V08** | webpro | 4907 | 200 | **4.08%** | 3.089% | 1.32x | 3.56% | 2610 | per-year in-sample fit (NOT cross-year) |
