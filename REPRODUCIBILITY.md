# Reproducing this repository

This file exists because two prior reviews raised the same HIGH finding: there was
no dependency manifest, no stated Python version, and the project's own correctness
gate could not be run by anyone who did not have this machine's `D:\xm\` directory.
Everything below was verified on the machine that produced the shipped reports.

## What you need

| Requirement | Value used here |
| --- | --- |
| Python | **3.13.12** |
| Packages | `pip install -r requirements.txt` |
| RAM | **~4 GB free** for the full scan; **~2.8 GB** for the ML matrix |
| Disk | ~4 GB of regenerable caches under `data/` and `outputs/` |

Exact versions the shipped reports were produced with:

```
pandas 3.0.2     numpy 2.4.4        scikit-learn 1.8.0
pyarrow 20.0.0   scipy 1.17.1       matplotlib 3.10.8
pytest 9.1.1
```

`requirements.txt` pins these with `>=` on the minor series. The project uses only
stable public APIs, but if you need the reports to match bit-for-bit, install these
exact versions — the ML reports in particular are sensitive to `scikit-learn`'s
histogram-binning implementation, and `ml_final_holdout.json`'s 13.6085% was
produced with 1.8.0.

## Two run tiers

### Tier 1 — verify the shipped numbers (no raw market data, ~2 minutes)

This is the tier that matters for audit. It needs only the tracked files:

```bash
pip install -r requirements.txt
python -m pytest tests/ -q          # 10 engine unit tests
python -m src.validate_cards        # 11/11 published selectors reproduced exactly
python scripts/audit_reports.py     # checks every published number
```

`validate_cards` reads `data/cards_100/cards.json` and
`data/cards_100/outcomes.json`, which are **vendored in this repository** (1.6 MB).
They are the frozen 100-card bundle the original project published, and the gate
re-runs all 36 strategies against those cards and their sealed labels, then diffs
the 11 development-only `*_v2` selectors against the published table. A match
proves the vendored strategy source is unmodified, card assembly is correct, and
the accounting agrees with the original.

`audit_reports.py` reads only `reports/*.json`, `reports/*.csv`,
`outputs/ml/audit/*.json` and the markdown documents. It does not need the panel.

### Tier 2 — rebuild everything from raw OHLCV (needs the market data)

The full pipeline needs a raw A-share OHLCV source. It is **not** vendored: it is
several gigabytes and is not redistributable. Point `PWS_DATA_ROOT` at a directory
containing the source files `src/data_pipeline.py` declares:

```bash
export PWS_DATA_ROOT=/path/to/ohlcv        # Windows: $env:PWS_DATA_ROOT="D:\..."
python -m src.data_pipeline --build --verify
python -m src.build_shards --shards 8
python -m src.scan_all --stride 5
python -m src.backtest_lowzone
python -m src.ml.build_matrix --stride 1
```

Then the remaining producers, in the order README §7 lists them. Expect **every
rate to be reproduced bit-for-bit** and only new columns to appear; the audit's
cross-file identity checks will fail if any number moves for a legitimate reason,
which is by design.

## What cannot be reproduced from this repository

1. **The raw OHLCV panel.** Not vendored, not redistributable. Everything derived
   from it (Tier 2) requires you to supply your own equivalent source. The
   *vendored* inputs are enough to run the correctness gate and the audit, which is
   why Tier 1 is separated out.
2. **The 2026 holdout evaluation** in the exact original sense. `ml_final_holdout.json`
   is labelled `historical_holdout_with_prior_project_exposure`: the 2026 window was
   already visible to earlier project decisions, so it is a historical OOS
   diagnostic, not a pristine lockbox. Re-running it reproduces the number; it does
   not restore the property that the window was unseen.
3. **The original published bundle's own artefacts** beyond the two files vendored
   here. The full bundle additionally holds `expert_evaluation/scores.json` and
   per-strategy spec files; set `WEBPRO_CARD_BUNDLE` to a full bundle directory if
   you have one. The gate itself needs only the two vendored files.
4. **Timing.** `webpro_scan_summary.json` records `elapsed_seconds`, and the ML
   searches report wall time. Those are machine-specific and will differ; no check
   asserts them.

## Tracked vs regenerated

Tracked, because they hold every published number:

- `reports/*.json` and `reports/*.csv` — 24 aggregate reports, all small.
- `outputs/ml/audit/*.json` — the ML audit toolkit's evidence.
- `outputs/charts_120d/` — the requested 120-session K-line charts with signal
  markers (~86 KB each), a deliverable rather than a cache.
- `data/cards_100/` — the vendored correctness-gate bundle.

Ignored, because they are large and fully regenerable (see `.gitignore`):

- `data/*.parquet`, `data/shards/` — the panel, labelled cache, layer cache, shards.
- `outputs/*.parquet`, `outputs/*_signals*.csv` — the signal CSVs exceed 140 MB,
  above GitHub's 100 MB per-file limit.
- `outputs/ml/*.parquet` — the feature matrices are 176 MB and 855 MB.
- `logs/` — the 4-hourly audit log.

## Verifying without trusting this document

The commands above are the documentation; the checks are the authority. If this file
and `scripts/audit_reports.py` ever disagree, the script is right. Every number in
`README.md`/`RESULTS.md`/`TARGET_70PCT.md` that the audit can bind to an artifact is
bound, and the audit fails on a mismatch rather than warning.
