# Measured Results

Every number below is regenerated from the backtest output CSVs by `python -m src.render_results`, so it cannot drift from the data.

## Natural base rates (the population each strategy is scored against)

| Regime | Contract | Evaluated points | Natural bull rate | Natural joint rate |
| --- | --- | ---: | ---: | ---: |
| `webpro` | 10 sessions, **+30%** | 493,246 | 3.0348% | 3.0311% |
| `low60` | 60 sessions, **4x** (i.e. +300%) | 461,416 | 0.0752% | 0.0748% |
| `low504` | 504 sessions, **4x** | 187,729 | 4.6956% | 2.4855% |


## Web Pro family — 36 strategies, full universe

Horizon 10 sessions, target +30%, entry at the next session's open, signals de-duplicated at a 60-session cooldown. **Lift** is the hit rate divided by the natural base rate of 3.035%: a lift of 1.0 means the strategy is indistinguishable from picking at random.

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
