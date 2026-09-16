# ZIP Artifact Audit — A-share Yearwise Gain/Avoid-Loss & 60-Day Low-Zone Runs

Audit date: performed against the local archives listed below.
Extraction target: `D:\ccc\_zip_audit\<archive_name>\`. **Nothing under `D:\xm` was modified** (read-only inspection + `zipfile` reads only).

---

## 0. Headline answer

**The most important finding is not a look-ahead bug in the feature code — it is a defect in the outcome metric itself.**

The published "跌幅前50 ±10 误触 0/150" (loss-bucket false-alert rate = 0.0%) is **arithmetically correct but semantically vacuous**. The loss case's anchor is the *trough* (`anchor_kind = low_end`), and the code applies the *same* `abs(distance) <= 10` proximity test used for gain cases. Because any signal the rule emits on a stock that later falls 50%+ is emitted *on the way down* — i.e. long before the eventual trough — its distance is automatically far from the anchor, so it can never be counted as a false alert. I verified this exhaustively: **155 loss signals across all v4 archives, distance range −25 to −236 bars, zero counted as false.** Meanwhile 33/150 (22%) of the "loss" stocks did receive a buy signal, and in `round_overall` that is 70/150 (47%).

Full quotes and line references in [§5](#5-look-ahead-and-methodology-defects).

**Reproducibility: yes, exactly.** Every published number I checked reconciles to the digit from the raw rows shipped alongside it. The archives are internally consistent — the problem is the metric definition, not the arithmetic.

### Archive inventory (all 11)

| Archive | Entries | Uncompressed | Encrypted | Path traversal | testzip | `.py` files |
|---|---|---|---|---|---|---|
| `overall_yearwise_ensemble.zip` | 304 | 24,802,547 | no | none | OK | **0** |
| `round_2023.zip` | 503 | 22,361,442 | no | none | OK | **0** |
| `round_2024.zip` | 482 | 21,547,734 | no | none | OK | **0** |
| `round_2025.zip` | 489 | 22,066,321 | no | none | OK | **0** |
| `round_overall.zip` | 1356 | 55,842,586 | no | none | OK | **0** |
| `V2-FULL86.zip` | 364 | 18,806,893 | no | none | OK | **0** |
| `V2-SMOKE20.zip` | 138 | 6,948,997 | no | none | OK | **0** |
| `V3-YEARWISE-CHARTS.zip` | 236 | 12,461,898 | no | none | OK | **0** |
| `V3-YEARWISE.zip` | 5 | 221,721 | no | none | OK | **0** |
| `round_2026.zip` | 495 | 20,489,400 | no | none | OK | **0** |
| `round_2026_charts_120d.zip` | 67 | 5,686,869 | no | none | OK | **0** |

**No archive was corrupt, password-protected, or contained path-traversal entries.** All 11 passed `ZipFile.testzip()`.

**Encoding: no mojibake.** Every entry was written without the UTF-8 flag (`flag_bits & 0x800 == 0`), i.e. nominally CP437 — but the stored bytes are UTF-8 and `zipfile` round-tripped them correctly. I additionally decoded each name via `cp437 → utf-8/gbk/big5` and confirmed the names were already clean, so extraction used the `zipfile`-provided names directly. Chinese filenames (e.g. `2023_000526_gain_top50_28.png`) and Chinese CSV content (股票名称 like `万泰生物`, `TCL中环`) read correctly with `encoding='utf-8-sig'`.

**The critical structural fact: there is not a single `.py` file in any of the 11 archives.** The archives are *output-only*. I therefore located the generating scripts in the live source tree (read-only) and audited those; every script maps to an archive by an embedded absolute path (see §1).

---

## 1. Code provenance — which script generated which archive

Each v4 `summary.json` embeds the zip path it wrote, which pins the script:

- `D:\ccc\_zip_audit\round_2026\round_2026\summary.json:35` → `"zip_path": "D:\\xm\\60日预测\\outputs\\v4_2026_compare86_fixed2\\round_2026.zip"`
- `round_2023/summary.json:35` → `...yearwise_gain_avoid_loss_2023_2025_v4_insample\\round_2023.zip`

| Archive | Generating script (in `D:\xm`, read-only) |
|---|---|
| `round_2023/2024/2025/overall`, `round_2026` | `yearwise_gain_avoid_loss_training_v4_insample.py` |
| ↑ (all core logic) | `yearwise_gain_avoid_loss_training_v3.py` (imported as `base`, line 22) |
| ↑ (features, charts, loading) | `yearwise_training_2023_2025.py`, `multi_tier_recall_filter_search_86.py` |
| ↑ (case manifest / anchors) | `annual_interval_extreme_blind_test_2023_2025.py` |
| `overall_yearwise_ensemble.zip` | `build_yearwise_ensemble_artifact.py` |
| `V2-*`, `V3-*` | `09_bull_lowzone_model/v2_bull_lowzone_competitive_60d.py` (imports `v1_bull_lowzone_60d.py`) |

`yearwise_gain_avoid_loss_training_v4_insample.py:22`:
```python
import yearwise_gain_avoid_loss_training_v3 as base
```
`build_yearwise_ensemble_artifact.py:30-33` (proves the ensemble is pure concatenation):
```python
        frame = pd.read_csv(round_dir / "signal_results.csv", encoding="utf-8-sig", dtype={"code": str})
        frame["code"] = frame["code"].str.zfill(6)
        frame.insert(0, "source_round", str(year))
        frames.append(frame)
```

---

## 2. Per-archive contents inventory

### 2.1 `overall_yearwise_ensemble.zip` — 304 entries, 24,802,547 B
Type breakdown: 300 × `.png`, 1 × `.html`, 1 × `.md`, 1 × `.csv`, 1 × `.json`.

```
overall_yearwise_ensemble/
├── REPORT.md
├── signal_results.csv           (300 rows + header, 62,662 B)
├── summary.json
└── charts_60d/                  (300 PNG + index.html)
```

### 2.2 `round_2023.zip` — 503 entries, 22,361,442 B
Breakdown: 393 × `.csv`, 103 × `.png`, 3 × `.svg`, 2 × `.json`, 1 × `.md`, 1 × `.html`.

```
round_2023/
├── REPORT.md  best_params.json  summary.json
├── candidate_rows.csv           (7,186 rows, 4,364,591 B)
├── parameter_leaderboard.csv    (28,880 rows, 4,580,012 B)
├── case_manifest.csv            (100 rows)
├── signal_results.csv           (100 rows)
├── charts_60d/                  (100 PNG + index.csv + index.html)
├── data_by_stock/{2023,2024,2025,2026}/   (97 CSVs each = 388)
└── figures/                     (3 PNG + 3 SVG)
```

### 2.3 `round_2024.zip` — 482 entries, 21,547,734 B
Same shape as 2023: 372 `.csv`, 103 `.png`, 3 `.svg`, 2 `.json`, 1 `.md`, 1 `.html`. `candidate_rows.csv` = 4,088,318 B; `parameter_leaderboard.csv` = 4,384,325 B.

### 2.4 `round_2025.zip` — 489 entries, 22,066,321 B
Same shape: 379 `.csv`, 103 `.png`, 3 `.svg`, 2 `.json`, 1 `.md`, 1 `.html`. `candidate_rows.csv` = 4,383,316 B.

### 2.5 `round_overall.zip` — 1356 entries, 55,842,586 B
Breakdown: 1046 × `.csv`, 303 × `.png`, 3 × `.svg`, 2 × `.json`, 1 × `.md`, 1 × `.html`.

```
round_overall/
├── REPORT.md  best_params.json  summary.json
├── candidate_rows.csv           (12,835,263 B)
├── parameter_leaderboard.csv    (28,880 rows, 5,478,304 B)
├── case_manifest.csv            (300 rows, 43,730 B)
├── signal_results.csv           (300 rows, 63,364 B)
├── charts_60d/                  (300 PNG + index.csv + index.html)
├── data_by_stock/{2023,2024,2025,2026}/
└── figures/
```

### 2.6 `V2-FULL86.zip` — 364 entries, 18,806,893 B
Breakdown: 358 × `.png`, 3 × `.csv`, 2 × `.json`, 1 × `.html`.

```
├── summary.csv  parameters.json  round_manifest.json
├── signals_all.csv              (400 rows, 72,324 B)
├── selected_candidates.csv      (221,567 B)
└── charts_120d/                 (358 PNG + index.html)
```
`round_manifest.json`: `mode = pooled_insample`, `model = extra`, `candidate_rows = 26121`.

### 2.7 `V2-SMOKE20.zip` — 138 entries, 6,948,997 B
132 × `.png`, 3 × `.csv`, 2 × `.json`, 1 × `.html`. `signals_all.csv` = 158 rows (20-case-per-year smoke subset).

### 2.8 `V3-YEARWISE-CHARTS.zip` — 236 entries, 12,461,898 B
230 × `.png`, 3 × `.csv`, 2 × `.json`, 1 × `.html`. `mode = yearwise`, `chart_count = 230`.

### 2.9 `V3-YEARWISE.zip` — 5 entries, 221,721 B
Smallest archive, **no charts at all**: `parameters.json`, `round_manifest.json`, `selected_candidates.csv`, `signals_all.csv`, `summary.csv`. `mode = yearwise`, `chart_count = 0`.

### 2.10 `round_2026.zip` — 495 entries, 20,489,400 B
Same shape as the other v4 rounds. `candidate_rows.csv` = 2,657,233 B (4,300 rows); `parameter_leaderboard.csv` = 4,539,515 B (28,880 rows). 100 cases.

### 2.11 `round_2026_charts_120d.zip` — 67 entries, 5,686,869 B
65 × `.png`, 1 × `.csv`, 1 × `.html`. Charts + `index.csv` only — **no summary, no signals table, no code**. Header:
```
code,bucket,signal_date,anchor_date,distance,path
600522,gain_top50,2026-01-05,2026-01-15,-8.0,2026_600522_gain_top50_727.png
```

---

## 3. What the code actually does

### 3.1 The signal rule (exact transcription)

Five nested tiers, all sharing one base low-zone mask. `yearwise_gain_avoid_loss_training_v3.py:61-72`:

```python
TIER_RULES: list[dict[str, Any]] = [
    dict(tier=1, low_margin=.15, close_margin=.20, drawdown_max=-.02,
         close_position_min=.35, lower_wick_min=0.00, bullish=False, rebound=False),
    dict(tier=2, low_margin=.15, close_margin=.20, drawdown_max=-.02,
         close_position_min=.35, lower_wick_min=.10, bullish=False, rebound=False),
    dict(tier=3, low_margin=.15, close_margin=.20, drawdown_max=-.02,
         close_position_min=.35, lower_wick_min=.20, bullish=False, rebound=False),
    dict(tier=4, low_margin=.15, close_margin=.20, drawdown_max=-.02,
         close_position_min=.35, lower_wick_min=.20, bullish=True, rebound=False),
    dict(tier=5, low_margin=.15, close_margin=.20, drawdown_max=-.02,
         close_position_min=.35, lower_wick_min=.20, bullish=True, rebound=True),
]
```

Base mask, `yearwise_gain_avoid_loss_training_v3.py:98-111`:
```python
    rolling_low, rolling_high = _rolling(group, int(window), prior=False)
    close = group.close
    low = group.low
    low_margin = 0.30 if int(window) <= 10 else 0.15
    close_margin = 0.35 if int(window) <= 10 else 0.20
    base = (
        (low <= rolling_low * (1.0 + low_margin))
        & (close <= rolling_low * (1.0 + close_margin))
        & ((close / rolling_high - 1.0) <= -0.02)
        & (group.close_position >= .35)
    )
```

Tier escalation and the **crossing** requirement, `:115-126`:
```python
    for rule in TIER_RULES:
        mask = base.copy()
        mask &= group.lower_wick >= float(rule["lower_wick_min"])
        if bool(rule["bullish"]):
            mask &= close >= group.open_
        if bool(rule["rebound"]):
            mask &= close > group.prior_close
        mask = np.nan_to_num(mask, nan=False).astype(bool)
        rules[f"L{rule['tier']}"] = mask
        strength[mask] = int(rule["tier"])
        crossing_parts.append(mask & ~np.r_[False, mask[:-1]])
    crossings = np.logical_or.reduce(crossing_parts) if crossing_parts else np.zeros(len(close), dtype=bool)
```

Window scan, `:205`: `windows: tuple[int, ...] = (3, 5, 7, 10, 15, 20, 30, 40)`.

Candidate de-duplication across windows, `:261-268`:
```python
    table = (
        table.sort_values(
            ["year", "code", "pos", "tier_strength", "signal_window"],
            ascending=[True, True, True, False, True],
        )
        .drop_duplicates(["year", "code", "pos"], keep="first")
        .reset_index(drop=True)
    )
```

The gated selection — first qualifying bar per (year, code). `:328-336`:
```python
    for _, group in scored.sort_values(["year", "code", "pos"]).groupby(["year", "code"], sort=False):
        eligible = group[
            (group["tier_strength"] >= int(min_tier))
            & (group["gain_score"] >= float(gain_threshold))
            & (group["loss_score"] <= float(loss_max))
            & (group["pos"] >= group["year_first_pos"] + int(min_bars))
        ]
        if not eligible.empty:
            chosen.append(eligible.iloc[0])
```

### 3.2 Label / outcome definition

Two labels, both built on the **annual extreme anchor**. `yearwise_gain_avoid_loss_training_v3.py:241-254`:
```python
            if gain_anchor is None:
                part["gain_label_pm5"] = 0
                part["gain_label_pm10"] = 0
            else:
                dist = positions - gain_anchor
                part["gain_label_pm5"] = (np.abs(dist) <= 5).astype(int)
                part["gain_label_pm10"] = (np.abs(dist) <= 10).astype(int)
            if loss_anchor is None:
                part["loss_label_pm5"] = 0
                part["loss_label_pm10"] = 0
            else:
                dist = positions - loss_anchor
                part["loss_label_pm5"] = (np.abs(dist) <= 5).astype(int)
                part["loss_label_pm10"] = (np.abs(dist) <= 10).astype(int)
```

The anchor's *meaning* differs by bucket — `annual_interval_extreme_blind_test_2023_2025.py:201-216`:
```python
        gain = {
            "interval_return": float(best_gain),
            ...
            "anchor_pos": int(start),
            "anchor_kind": "low_start",
        }
    if best_loss_pair is not None:
        start, end = best_loss_pair
        loss = {
            "interval_return": float(best_loss),
            ...
            "anchor_pos": int(end),
            "anchor_kind": "low_end",
        }
```
Confirmed in the shipped data: `overall_yearwise_ensemble/signal_results.csv` has `anchor_kind = low_start` for all 150 `gain_top50` rows and `low_end` for all 150 `loss_bottom50` rows.

The hit test, `yearwise_gain_avoid_loss_training_v3.py:349-365`:
```python
        distance = np.nan if not signal_found or anchor_pos is None else int(signal_pos - anchor_pos)
        ...
            "distance_trading_days": distance,
            "hit_pm2": bool(pd.notna(distance) and abs(float(distance)) <= 2),
            "hit_pm5": bool(pd.notna(distance) and abs(float(distance)) <= 5),
            "hit_pm10": bool(pd.notna(distance) and abs(float(distance)) <= 10),
```

**Answering the task's specific questions:**

- **Is the target `>= 4x` or `> 4x`?** Neither, in the v4 archives — the v4 headline is *anchor proximity* (`hit_pm10`), never a multiple. The 4x test exists only in the v1/v2/v3 60-day family, and it is **strictly greater than**: `v1_bull_lowzone_60d.py:40` `GAIN_THRESHOLD = 3.0` and `:149` `"gain_gt300": bool(row["interval_return"] > GAIN_THRESHOLD)`, where `interval_return = highs[end] / min_low - 1.0` (`:87`). Multiple > 4.0 exactly. In practice this flag is almost never true: `V3-YEARWISE/summary.csv` shows `gain_cases_gt300` = 0, 1, 6, 39 for 2023–2026.
- **Entry: next-day OPEN or signal-day CLOSE?** The recorded execution price is the **next-day open** — `yearwise_gain_avoid_loss_training_v3.py:358-360`:
  ```python
            "execution_date": "" if not signal_found or signal_pos + 1 >= len(group.frame) else str(group.frame.iloc[signal_pos + 1]["date"].date()),
            "signal_price": np.nan if not signal_found else float(group.close[signal_pos]),
            "next_day_open": np.nan if not signal_found or signal_pos + 1 >= len(group.frame) else float(group.open_[signal_pos + 1]),
  ```
  **However, the hit test never uses `next_day_open`** — it uses only bar indices (§5, defect D3). In the v3/V2 family the same is true: `v1_bull_lowzone_60d.py:374` computes `forward = future["high"].max() / next_open - 1.0`, using the open, but the `hit_pm10` metric again uses index distance only.

### 3.3 Look-ahead search

I grepped the five generating modules for `shift(-`, `center=True`, `iloc[::-1]`, `bfill`/`backfill`. Results:

- `yearwise_gain_avoid_loss_training_v3.py`: **0 hits**
- `yearwise_gain_avoid_loss_training_v4_insample.py`: **0 hits**
- `multi_tier_recall_filter_search_86.py`: **0 hits**
- `annual_interval_extreme_blind_test_2023_2025.py`: **0 hits**
- `yearwise_training_2023_2025.py`: 1 hit, `:567` `top = leaderboard.head(12).iloc[::-1]` — a **plot label reversal**, not a data operation.

I verified the shipped `candidate_rows.csv` **does contain** `gain_anchor_pos, loss_anchor_pos, gain_label_pm5, gain_label_pm10, loss_label_pm5, loss_label_pm10` in all five rounds, but confirmed these are **not** in the model's feature list. `yearwise_gain_avoid_loss_training_v3.py:74-82`:
```python
FEATURE_COLUMNS = [
    "tier_strength", "ret1", "ret3", "ret5", "ret10", "ret20",
    "low_gap20", "drawdown20", "close_position", "lower_wick", "body_ratio",
    "gap", "volume_ratio20", "volume_contract5", "volume_contract10",
    "volume_expand1", "range_contract5", "range_contract10",
    "down_volume_ratio5", "obv_slope10", "ema10_gap", "ema20_gap", "ema_slope10",
    "rsi2", "rsi14", "z20", "atr_pct", "efficiency10", "adx14", "di_spread",
    "signal_window", "year_pos",
]
```
No anchor or label column appears. **No feature-level look-ahead bias was found** — the features are genuinely current/past-bar only, and the anchors enter solely as labels and audit fields, exactly as the docstrings claim.

### 3.4 Hit-rate denominator

`_fast_score_selection`, `yearwise_gain_avoid_loss_training_v3.py:499-517`:
```python
    for year, code, bucket, anchor in context["case_meta"]:
        key = (year, code)
        signal_pos = selected_map.get(key)
        if signal_pos is None:
            continue
        if bucket == "gain_top50":
            gain_signals += 1
            if anchor is not None:
                distance = float(signal_pos - anchor)
                gain_distances.append(distance)
                gain_hits5 += int(abs(distance) <= 5)
                gain_hits10 += int(abs(distance) <= 10)
        if bucket == "loss_bottom50":
            loss_signals += 1
            ...
```
and `:536-542`:
```python
        "gain_hits_pm10": int(gain_hits10),
        ...
        "gain_hit_rate_pm10": gain_hits10 / gain_cases if gain_cases else 0.0,
        ...
        "gain_signal_precision_pm10": gain_hits10 / gain_signals if gain_signals else 0.0,
```

The denominator is literally **`gain_cases` = the count of gain cases (50 per year, 150 overall)** — i.e. **count of stocks** (one row per stock-year), explicitly *not* the count of signals and *not* the count of days. The separate signal-conditioned figure `gain_signal_precision_pm10 = gain_hits10 / gain_signals` is also published, which is good practice.

### 3.5 Signal de-duplication / cooldown

There is **no cooldown and no re-arm mechanism**. The only de-duplication is:
1. per-bar: `drop_duplicates(["year", "code", "pos"], keep="first")` (`:266`) collapses the 8 overlapping recall windows to one row per bar;
2. per-case: `if not eligible.empty: chosen.append(eligible.iloc[0])` (`:336`) takes the **first** qualifying bar in the year.

Note the window comparison is **trading sessions, not calendar days**: `drop_duplicates` is on `pos` (a row index into the trading-session series) and `distance_trading_days = signal_pos - anchor_pos` is also a session count. Verified in the shipped data: one row per `(year, code)` at most (100 rows / 97 unique keys in `round_2023`; the duplicates are genuinely the same stock in both the gain and loss bucket).

### 3.6 Limit-up / unfillable-entry filtering

**None exists in the audited scripts.** A targeted grep across both generating trees for `limit`, `涨停`, `unfillable`, `pct_chg`, `prev_close`, `0.098`, `一字`, `tradable` returned only unrelated hits (e.g. the constant `LOSS_FALSE_LIMIT`) in `09_bull_lowzone_model/` and `_a_share_86_custom_50pct/`. Confirmed structurally: `signal_results.csv` **has no tradability column**, and the hit test at `:365` consults only `distance`.

The only limit-up handling in the whole project lives in a *different* script that did **not** generate these archives — `custom_86_backtest.py:232-248` defines `add_one_price_limit_flags` and `:285` returns `{"trade_status": "untradable_locked", "counted": False, ...}`, and `a_share_three_system_backtest.py:670-672` does:
```python
    entry_gap = raw_open / prev_close - 1.0
    ...
        return {"tradable": False, "skip_reason": "gap_or_limit_up", "entry_gap": entry_gap}
```
Neither is in the lineage of the 11 audited archives.

I did empirically bound the exposure from the shipped `next_day_open` vs `signal_price`: among the 105 gain hits, exactly **1** had a next-day open gap ≥ +9.8% (`round_2024`, code `000759`, signal date `2024-02-01`, gap +10.1%) and 3 more were ≥ +5%. So the *realised* unfillable-entry distortion is small in these particular samples — but the code provides no guarantee, and no `limit_up` flag is recorded to audit it.

---

## 4. Recomputing published numbers from the raw rows

Method: for every `signal_results.csv`, treat a row as a hit iff `signal_found == True` **and** `abs(signal_pos - anchor_pos) <= tol`, recomputed from the raw integer positions rather than trusting the `hit_pm10` column. I also cross-checked the `hit_pm10` column against the recomputed distance: **0 mismatches in every archive.**

### 4.1 v4 rounds — published `summary.json` vs recomputed

| Archive | metric | published | recomputed | verdict |
|---|---|---|---|---|
| `round_2023` | gain_hits_pm10 | 31 | 31 | **exact** |
| | gain_hits_pm5 | 17 | 17 | **exact** |
| | gain_signals | 38 | 38 | **exact** |
| | loss_false_pm10 / pm5 | 0 / 0 | 0 / 0 | **exact** |
| | loss_signals | 4 | 4 | **exact** |
| `round_2024` | gain_hits_pm10 | 35 | 35 | **exact** |
| | gain_hits_pm5 | 33 | 33 | **exact** |
| | gain_signals | 46 | 46 | **exact** |
| | loss_false_pm10 / pm5 | 0 / 0 | 0 / 0 | **exact** |
| | loss_signals | 18 | 18 | **exact** |
| `round_2025` | gain_hits_pm10 | 39 | 39 | **exact** |
| | gain_hits_pm5 | 27 | 27 | **exact** |
| | gain_signals | 47 | 47 | **exact** |
| | loss_false_pm10 / pm5 | 0 / 0 | 0 / 0 | **exact** |
| | loss_signals | 11 | 11 | **exact** |
| `round_overall` | gain_hits_pm10 | 85 | 85 | **exact** |
| | gain_hits_pm5 | 52 | 52 | **exact** |
| | gain_signals | 128 | 128 | **exact** |
| | loss_false_pm10 / pm5 | 0 / 0 | 0 / 0 | **exact** |
| | loss_signals | 70 | 70 | **exact** |
| `round_2026` | gain_hits_pm10 | 33 | 33 | **exact** |
| | gain_hits_pm5 | 19 | 19 | **exact** |
| | gain_signals | 46 | 46 | **exact** |
| | loss_false_pm10 / pm5 | 0 / 0 | 0 / 0 | **exact** |
| | loss_signals | 19 | 19 | **exact** |

### 4.2 `overall_yearwise_ensemble`

`summary.json` claims `gain_hits_pm10 = 105`, `gain_hits_pm5 = 77`, `gain_signals = 131`, `loss_false_pm10 = 0`, `loss_signals = 33`, `gain_hit_rate_pm10 = 0.7`, `chart_count = 300`.

Recomputed from `signal_results.csv` (300 rows): **105 / 77 / 131 / 0 / 33 — exact agreement on every field.**

Two further integrity checks passed:
- The ensemble row set is **value-identical** (not merely key-identical) to the concatenation of `round_2023` + `round_2024` + `round_2025` `signal_results.csv`: sorted-multiset comparison `identical = True`, 0 rows only-in-ensemble, 0 rows only-in-rounds.
- `31 + 35 + 39 = 105` — the ensemble headline is exactly the sum of the per-round headlines, consistent with `build_yearwise_ensemble_artifact.py:48-58` which is a pure concatenation and refits nothing.

The archive's own `REPORT.md:9` is honest about the in-sample nature, and it **volunteers the negative result**:
> 注意：三年统一重新训练的 `round_overall` 只有 85/150 = 56.7%，未过60%；本目录的70%来自三套年度规则的冻结组合，仍是同年度样本内拟合，不能当跨年样本外成绩。

### 4.3 V2 / V3 (60-day family) — published `summary.csv` vs recomputed `signals_all.csv`

All four years recomputed exactly for every archive:

| Archive | gain_hits_pm10 | gain_signals | loss_false_signals | gain_forward20_rate |
|---|---|---|---|---|
| `V3-YEARWISE` / `V3-YEARWISE-CHARTS` | 5, 12, 13, 31 — **exact** | 19, 12, 41, 49 — **exact** | 18, 4, 40, 47 — **exact** | 0.6111, 0.75, 0.9714, 1.0 — **exact** |
| `V2-FULL86` | 0, 5, 6, 25 — **exact** | 50, 41, 49, 42 — **exact** | 50, 41, 49, 36 — **exact** | 0.5625, 0.70, 0.8667, 1.0 — **exact** |
| `V2-SMOKE20` | 1, 4, 4, 16 — **exact** | 18, 13, 17, 18 — **exact** | 18, 13, 17, 18 — **exact** | 0.3529, 0.90, 0.8333, 1.0 — **exact** |

Every `gain_forward20_rate` reproduces to 1e-9 from `signals_all.csv` columns `forward_max_return` and `forward_complete`.

### 4.4 Artifact-integrity anomaly: `V3-YEARWISE` vs `V3-YEARWISE-CHARTS`

These two archives describe the same run (`mode = yearwise`, `candidate_rows = 26121`, identical `parameters.json` SHA-256). Byte comparison:

| File | Verdict |
|---|---|
| `parameters.json` | **IDENTICAL** (`34FB3AA34A775211…`) |
| `summary.csv` | **IDENTICAL** (`D551E0789966645C…`) |
| `round_manifest.json` | DIFFERENT |
| `signals_all.csv` | DIFFERENT — 81 of 401 lines |
| `selected_candidates.csv` | DIFFERENT — 71 of 206 lines |

The differences are **floating-point only** and are confined to score columns; the keys, dates, signal identity, distances and `hit_*` flags are unchanged (full-tuple comparison of `year, code, bucket, signal_found, distance`: **identical**, 0 rows unique to either side). Example:

```
L19: - 2023,603045,gain_top50,18,...,0.9581521826762394,0.3220831665756657,0.764
L19: + 2023,603045,gain_top50,18,...,0.9581521826762394,0.32208316657566566,0.76
```

So the two runs fitted slightly different models but landed on the same signal set and published byte-identical headline numbers. This is a **reproducibility/lineage gap, not a numerical error** — but it means the archive cannot be used to re-derive the published number from the shipped per-row scores alone; only the outcome columns are stable.

### 4.5 Parameter-search multiplicity

`parameter_leaderboard.csv` in every v4 round contains **28,880 configurations** (4 model specs × 5 `min_tier` × 19 `gain_threshold` × 19 `loss_max` × 4 `min_bars`). The selection rule is `_sort_key` (`:413-424`), which prioritises `qualified` first, then *minimises* `loss_false_pm10` and `loss_false_pm5`.

Crucially, the loss criterion barely discriminates — share of the 28,880 configs scoring `loss_false_pm10 == 0`:

| Round | configs with 0 loss false alerts | share |
|---|---|---|
| `round_2023` | 27,450 | 95.0% |
| `round_2024` | 22,133 | 76.6% |
| `round_2025` | 22,420 | 77.6% |
| `round_overall` | 19,623 | 67.9% |

Because `abs(distance) <= 10` against a *trough* anchor is so easy to satisfy, the "loss avoidance" gate that the search optimises is close to a constant — the search is effectively selecting on the gain side within a nearly unconstrained loss set.

---

## 5. Look-ahead and methodology defects

### D1 — Loss-bucket false-alert metric measures the wrong thing (severity: high; this is the headline defect)

**File:** `yearwise_gain_avoid_loss_training_v3.py`, lines 349 and 365 (metric construction), plus `annual_interval_extreme_blind_test_2023_2025.py:214` (anchor definition).

```python
# line 214 — the loss anchor is the TROUGH
            "anchor_pos": int(end),
            "anchor_kind": "low_end",
```
```python
# line 349
        distance = np.nan if not signal_found or anchor_pos is None else int(signal_pos - anchor_pos)
```
```python
# line 365
            "hit_pm10": bool(pd.notna(distance) and abs(float(distance)) <= 10),
```

**Why it is a defect:** the *same* `abs(distance) <= 10` test is applied to both buckets, but the anchors mean opposite things. The gain anchor is where the run **starts** (`low_start`), so ±10 sessions is a meaningful "did you get in near the bottom" window. The loss anchor is where the fall **ends** (`low_end`), so ±10 sessions means "did you buy within 10 sessions of the exact bottom of a −50% move" — which is not the failure mode anyone cares about. The failure mode is "did you buy a stock that then fell 50%", and that signal is necessarily issued in the −25 to −236-bar range, i.e. structurally outside the ±10 window.

**Empirical proof** (recomputed from the shipped CSVs):

| Archive | loss cases | loss cases that got a buy signal | reported "false alerts" |
|---|---|---|---|
| `round_2023` | 50 | 4 (8%) | 0 |
| `round_2024` | 50 | 18 (36%) | 0 |
| `round_2025` | 50 | 11 (22%) | 0 |
| `round_2026` | 50 | 19 (38%) | 0 |
| `round_overall` | 150 | 70 (47%) | 0 |
| `overall_yearwise_ensemble` | 150 | 33 (22%) | 0 |

Distance distribution of all 33 ensemble loss signals: `min=-230, p25=-150, median=-102, p75=-88, max=-25`. **All 33 are negative** (signalled before the trough). Counts within tolerance: `|d|<=10 → 0`, `|d|<=30 → 1`, `|d|<=60 → 2`. Across all six v4 archives: **155 loss signals, 0 counted as false.**

The correct test would be a forward-looking outcome on the loss cases (e.g. does the stock fall by X% within N sessions of the signal), exactly as the v3/V2 family already does with `forward_max_return` — but the v4 leaderboard does not compute it, so the headline "跌幅前50 ±10 误触 0/150 = 0.0%" is not evidence of loss avoidance.

### D2 — Headline is same-year in-sample fit, and the code says so (severity: high, but disclosed)

**File:** `yearwise_gain_avoid_loss_training_v4_insample.py`, lines 30-36:
```python
def _fit_scores(table: pd.DataFrame, spec: dict[str, Any], seed: int) -> tuple[np.ndarray, np.ndarray]:
    x = table.loc[:, base.FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).fillna(-999.0).to_numpy(float)
    gain_model = base.make_model(spec, seed, n_jobs=-1)
    loss_model = base.make_model(spec, seed + 1000, n_jobs=-1)
    gain_model.fit(x, table["gain_label_pm10"].to_numpy(int))
    loss_model.fit(x, table["loss_label_pm10"].to_numpy(int))
    return gain_model.predict_proba(x)[:, 1], loss_model.predict_proba(x)[:, 1]
```
Note `predict_proba(x)` on line 36 — scoring the **same rows** the models were fit on. Contrast v3's honest cross-fitting (`:303-319`, `crossfit_scores`, "Code-grouped cross-fitting ... folds grouped by code"). The v4 module replaces that with in-sample scoring and labels itself `"training_mode": "same_year_in_sample"` (line 66).

This is **disclosed** in the artifacts, not hidden: `round_2023/REPORT.md:7` says 本轮是同年度样本内拟合上限 … 不能当作样本外预测成绩, and the ensemble `REPORT.md:9` repeats the warning. But anyone quoting "70%" without that caveat is quoting an in-sample fit.

### D3 — Entry price is recorded but never used in the outcome test (severity: medium)

**File:** `yearwise_gain_avoid_loss_training_v3.py`, lines 358-360 record `execution_date`, `signal_price`, `next_day_open`, and line 365's hit test uses only bar indices. Consequently the headline is a **bar-index coincidence metric, not a tradable return**. A signal whose next-day open gapped +10% counts identically to one that opened flat. This also means the next-day-open execution convention only affects the *display* columns; the metric would be unchanged if execution were at the signal-day close. Empirically the distortion here is small (1 of 105 gain hits had a ≥+9.8% gap) but it is not controlled for.

### D4 — No limit-up / unfillable-entry filter (severity: medium)

**File:** `yearwise_gain_avoid_loss_training_v3.py` — no limit logic anywhere; `candidate_rows.csv` and `signal_results.csv` carry no tradability flag.

`custom_86_backtest.py:285` shows the project knows how to do this:
```python
    return {"trade_status": "untradable_locked", "counted": False, "success": np.nan}
```
and `a_share_three_system_backtest.py:670-672`:
```python
    entry_gap = raw_open / prev_close - 1.0
    ...
        return {"tradable": False, "skip_reason": "gap_or_limit_up", "entry_gap": entry_gap}
```
Neither is used by the audited pipeline. A signal fired on a limit-up bar cannot be bought at the next open, yet such a case still counts as a hit.

### D5 — Massive parameter search with no multiple-testing correction (severity: medium)

**File:** `yearwise_gain_avoid_loss_training_v4_insample.py`, lines 51-58 and 69:
```python
    gain_thresholds = np.arange(.05, .96, .05)
    loss_maxes = np.arange(.05, .96, .05)
    ...
                    for min_bars in (0, 5, 10, 20):
                        metrics, selected_indices = base._fast_score_selection(
```
28,880 configs per round, best-of selected on the same data used for scoring. Combined with D1 (the loss gate being satisfied by 68-95% of configs), the effective selection is over the gain side alone, and the reported best-of number carries no out-of-sample correction. The v4 `REPORT.md` discloses the in-sample nature (D2) but not the search multiplicity.

### D6 — Cost model is recorded yet unused (severity: medium)

The shipped records are all **gross of fees, slippage and stamp duty**. The metric is a bar-distance coincidence, negative gaps (gap-down entries) are not distinguished from gap-ups, and no commission or A-share stamp duty enters any published figure. For a strategy whose headline rests on buying small-cap low-zone breakouts, this materially overstates net performance.

### D7 — Cross-bucket case overlap is counted in both denominators (severity: low, disclosed)

`yearwise_gain_avoid_loss_training_v3.py:385`:
```python
    overlap = int(details.groupby(["year", "code"])["bucket"].nunique().eq(2).sum())
```
`round_2023/summary.json` reports `"overlap_code_years": 3`, `round_2026` reports 2. The design doc (`:98`) states 涨幅前50和跌幅前50是两个独立 case 桶；重叠代码/年度不删除、不合并 — so this is a deliberate choice and it is disclosed. It does mean a single stock-year can be counted once as a "hit" and once as a "miss".

### D8 — `gain_forward20_rate` is a perfect-hindsight exit (severity: medium)

**File:** `v2_bull_lowzone_competitive_60d.py:239-242`:
```python
    future = next_rows.iloc[:OUTCOME_HORIZON]
    if next_open <= 0 or future.empty:
        return np.nan, len(future) >= OUTCOME_HORIZON, next_open
    return float(future["high"].max() / next_open - 1.0), len(future) >= OUTCOME_HORIZON, next_open
```
The outcome is the **maximum high over the next 120 bars** — you must sell at the single best bar. `V3-YEARWISE/summary.csv` reports `gain_forward20_rate` of 0.97 (2025) and 1.00 (2026) on this basis. These are upper bounds, not achievable returns, and they are not labelled as such in the CSV.

### D9 — Survivorship / universe definition is not in the archives (severity: unknown → see §7)

The manifest is built from whatever codes are present in the daily CSVs; `load_daily` only validates OHLC sanity (`annual_interval_extreme_blind_test_2023_2025.py:89`). Because the top-50 is selected *retrospectively* from within the loaded universe, delisted or suspended names that would have been in a live universe may be absent. The archives ship `data_by_stock/` **only for the 97 selected codes**, so the universe cannot be reconstructed from the artifact.

---

## 6. Reconciliation — which published number is supported

**Supported (reproduce exactly from shipped raw rows):**

- `overall_yearwise_ensemble` gain ±10 = **105/150 = 70.0%** — supported, *as an in-sample case-level hit rate*. Sums exactly from the three per-round tables, and the ensemble is a verified pure concatenation.
- `overall_yearwise_ensemble` gain ±5 = **77/150** — supported.
- Per-round gain ±10: 2023 **31/50 = 62.0%**, 2024 **35/50 = 70.0%**, 2025 **39/50 = 78.0%** — all supported.
- Per-round gain ±5 and gain-signal counts — all supported.
- `round_overall` gain ±10 = **85/150 = 56.7%** — supported, and it is the honest cross-year-retrained figure that **fails** the 60% gate. `round_overall/parameter_leaderboard.csv` indeed contains **0 qualified configs**, consistent with the ensemble `REPORT.md:9` explanation.
- V3/V2 `summary.csv` entirely (gain hits, signals, loss_false_signals, `gain_forward20_rate`) — supported to 1e-9.
- `gain_signal_precision_pm10` — supported (105/131 = 80.2% for the ensemble).

**Not supported / misleading as published:**

- **"跌幅前50 ±10 误触 0/150 = 0.0%"** — arithmetically reproducible, but **not** evidence of loss avoidance. 33/150 ensemble loss cases (22%) and 70/150 `round_overall` loss cases (47%) received a buy signal; the metric simply places them outside a ±10-bar window around a trough they had not reached yet. See D1.
- **The reported `loss_signals` vs `loss_false_pm10` pair invites a misread.** In `round_overall`, 70 of 150 loss cases were signalled and the artifact still reports `loss_false_rate_pm10 = 0.0`. Anyone reading only the rate would conclude the rule never touches falling stocks.
- **`gain_forward20_rate` near 1.0** (V3 2025 = 0.97, 2026 = 1.00) — numerically correct but a perfect-hindsight maximum-high exit. Not a realisable return.
- **Any cross-year out-of-sample reading of the 70%** — contradicted by the archive's own `round_overall` result (56.7%, 0 qualified configs). The archive says this itself.

**Internal inconsistency found:** `V3-YEARWISE` and `V3-YEARWISE-CHARTS` share a byte-identical `summary.csv` but differ on 81/401 lines of `signals_all.csv` (floating-point scores only; signal identity and all outcome columns unchanged). Published numbers unaffected.

---

## 7. Could not determine

1. **The source code is absent from every archive.** All 11 archives are output-only. The code quoted above comes from the live tree at `D:\xm\_a_share_86_custom_50pct\a_share_86_custom_50pct\` and `D:\xm\60日预测\09_bull_lowzone_model\`. **I could not verify that the tree's current version is byte-identical to what produced the archives** — there is no hash of the generating script inside any archive. `repro_manifest.json` (written by `yearwise_gain_avoid_loss_training_v4_insample.py:174`) would have hashed the *inputs*, but `repro_manifest.json` is **not present in any of the 11 archives**. The only hash-like evidence is the embedded `zip_path` and the `input_quality.json` / `overall_gate.json` files, which are also absent from the archives. Treat the code→artifact mapping as strong but not cryptographically proven. (The numeric agreement in §4 is circumstantial support that the tree still matches.)

2. **Exact model random state per archive.** `SEED = 20260907` for v1-based and `SEED = 20260915` for the 60-day family, with per-round offsets (`args.seed + year`, `seed + model_index * 101`), but the archives do not record the realised seed or an sklearn version, so bit-exact re-fitting is not possible. This is what D4/reconciliation §4.4 shows up as.

3. **Universe / survivorship.** Cannot be assessed from the archives: `data_by_stock/` contains only the 97 *selected* codes, not the candidate universe, and `mainboard_universe.csv` is not shipped. Whether delisted names were excluded upstream is undeterminable here.

4. **Whether a limit-up filter was applied before the daily CSVs were written.** The archives contain no `limit_up` column and no pre-processing script, so while I can prove the *audited* code applies no filter, I cannot rule out that the upstream `mainboard_tencent_daily_*.csv` inputs were pre-filtered. Given §3.6 found only one ≥+9.8% next-day open among the 105 gain hits, upstream filtering is unlikely but unproven.

5. **`round_2026_charts_120d.zip` is orphaned.** It contains 65 charts + `index.csv` and **no summary, no signals table, and no manifest**. The `index.csv` distances (e.g. `600522 … distance = -8.0`) do not correspond to any `signals_all.csv` shipped in the other archives, and its filename convention (`_727`, `_759`) differs from the v4 convention (`_%02d` rank). I could not attribute it to a specific published number. It is not covered by any reconciliation above.

6. **Whether the `hit_pm10` definition was ever intended to be a loss metric.** The v3/V2 family computes a proper forward return (`forward_max_return`) for loss cases too, so the machinery existed; why the v4 leaderboard optimised the trough-proximity test instead is not documented anywhere in the artifacts or the source docstrings.

---

## 8. Reproduction commands

All findings above are reproducible:

```powershell
python D:\ccc\_zip_audit\inventory.py    # entry counts, sizes, encoding, traversal, testzip
python D:\ccc\_zip_audit\extract.py      # safe extraction to D:\ccc\_zip_audit\<name>\
python D:\ccc\_zip_audit\recompute.py    # §4.1/4.2 headline recomputation
python D:\ccc\_zip_audit\deep.py         # §5 D1 loss-bucket forensics, search multiplicity
python D:\ccc\_zip_audit\forensic.py     # §3.2 anchor kinds, §3.6 fillability
python D:\ccc\_zip_audit\target.py       # §3.2 4x threshold, §4.3 V2/V3 recomputation
python D:\ccc\_zip_audit\final.py        # §5 look-ahead grep, integrity checks
python D:\ccc\_zip_audit\reconcile.py    # §4.4 V3 diff, ensemble reconciliation
```

Scratch artifacts and extracted trees live under `D:\ccc\_zip_audit\`. `D:\xm` was opened read-only throughout.
