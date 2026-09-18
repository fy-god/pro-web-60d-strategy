"""Persist the stride-verification evidence as a small JSON, then delete the
~1 GB of regenerable parquet artifacts under scripts/scratch/_artifacts.

scripts/scratch/_artifacts is NOT covered by .gitignore (only outputs/ml/*.parquet
is), so leaving those parquets on disk risks a `git add -A` staging 1 GB of
matrices into a repository whose .gitignore explicitly says they cannot be
pushed. The evidence that matters is numeric and lives here.
"""
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE / "_artifacts"

evidence = {
    "note": (
        "Evidence for the stride-subsampling verification. Large parquet "
        "artifacts under scripts/scratch/_artifacts were removed after this file "
        "was written; regenerate with "
        "`python scripts/scratch/_run_head_build.py --stride N` for the "
        "committed rule and "
        "`python -m src.ml.build_matrix --stride N` for the working tree."
    ),
    "counterexample": {
        "claim": "iloc[::stride] phase depends on other stocks' row counts",
        "verdict": True,
        "stride_5": {
            "frame_A_B": ["2024-01-01", "2024-01-06"],
            "frame_C_A_B": ["2024-01-05", "2024-01-10"],
            "A_prices_unchanged": True,
        },
        "stride_3": {
            "frame_A_B": ["2024-01-01", "2024-01-04", "2024-01-07", "2024-01-10"],
            "frame_C_A_B": ["2024-01-03", "2024-01-06", "2024-01-09"],
        },
        "session_grid_rule_stable": True,
    },
    "real_panel_structure": {
        "full": {"rows": 2680715, "stocks": 3193, "sessions": 887,
                 "base_rate_high": 0.030893409624695778},
        "old_iloc_stride5": {
            "rows": 536143, "sessions": 887, "stocks_per_session_median": 605,
            "min_stocks": 561, "max_stocks": 663,
            "distinct_per_stock_date_sets": 660,
            "median_calendar_gap_days": 7.0,
            "per_stock_sessions_median": 177,
            "base_rate_high": 0.030916061252355576,
            "weekday_share": {0: 0.1978, 1: 0.202, 2: 0.2018, 3: 0.201, 4: 0.1974},
            "P_kept_given_y1": 0.2001, "P_kept_given_y0": 0.2000,
            "max_abs_smd_over_20_features": 0.00062,
        },
        "new_session_grid_stride5": {
            "rows": 537946, "sessions": 178, "stocks_per_session_median": 2929,
            "distinct_per_stock_date_sets": 367,
            "base_rate_high": 0.029315544292330742,
            "weekday_share": {0: 0.2668, 1: 0.2392, 2: 0.1077, 3: 0.2178, 4: 0.1684},
            "P_kept_given_y1": 0.1904, "P_kept_given_y0": 0.2010,
            "max_abs_smd_over_20_features": 0.02310,
        },
    },
    "label_distribution_unbiased": {
        "walkforward_oos_462_sessions": {
            "full_cross_section_base_rate_high": 0.04089445,
            "old_retained_base_rate_high": 0.04087801,
            "relative_diff": -0.000402,
        },
        "holdout_2026_150_sessions": {
            "full_cross_section_base_rate_high": 0.02895818,
            "old_retained_base_rate_high": 0.02909598,
            "relative_diff": +0.004758,
        },
        "per_session_base_rate_old_minus_full": {
            "n_sessions": 877, "mean_diff": 0.00000541, "sd": 0.005550,
            "t": 0.03, "share_old_higher": 0.4960,
        },
    },
    "folds": {
        "protocol": {"n_folds": 5, "horizon": 10, "embargo": 2,
                     "min_train_sessions": 150,
                     "final_holdout_start": "2026-01-01"},
        "table": [
            {"stride": 1, "rule": "old", "sessions": 887, "folds": 4,
             "test_sessions": 462, "error": None},
            {"stride": 1, "rule": "new", "sessions": 887, "folds": 4,
             "test_sessions": 462, "error": None},
            {"stride": 2, "rule": "old", "sessions": 887, "folds": 4,
             "test_sessions": 462, "error": None},
            {"stride": 2, "rule": "new", "sessions": 444, "folds": 4,
             "test_sessions": 172, "error": None},
            {"stride": 3, "rule": "old", "sessions": 887, "folds": 4,
             "test_sessions": 462, "error": None},
            {"stride": 3, "rule": "new", "sessions": 296, "folds": 4,
             "test_sessions": 75, "error": None},
            {"stride": 4, "rule": "old", "sessions": 887, "folds": 4,
             "test_sessions": 462, "error": None},
            {"stride": 4, "rule": "new", "sessions": 222, "folds": 3,
             "test_sessions": 20, "error": None},
            {"stride": 5, "rule": "old", "sessions": 887, "folds": 4,
             "test_sessions": 462, "error": None},
            {"stride": 5, "rule": "new", "sessions": 178, "folds": 0,
             "test_sessions": 0,
             "error": "ValueError: only 0 sessions after the 150-session "
                      "warm-up; cannot build 5 folds"},
        ],
    },
    "model_bias": {
        "design": ("train the pre-committed HGB on each subsample of the "
                   "pre-2026 pool, score on the IDENTICAL full-cross-section "
                   "2026 rows (476,860 rows, base 0.028958)"),
        "seed0": {"R1_full": 0.1207, "R2_random20": 0.1079,
                  "R3_old_iloc5": 0.1262, "R4_new_grid5": 0.1103},
        "old_seeds": [0.1262, 0.1235, 0.1197],
        "new_seeds": [0.1103, 0.1100, 0.1129],
        "full_seeds": [0.1207, 0.1285, 0.1138],
        "exact_size_random_draws": {
            "n": 6, "mean": 0.1181, "sd": 0.0057,
            "range": [0.1114, 0.1244],
            "verdict": "OLD sits INSIDE the random-draw range; NEW sits at/below "
                       "its mean",
        },
        "topk_with_full_models_own_scores": {
            "top1": {"full_pool": 0.1667, "old_partial_pool": 0.1800,
                     "delta_pp": +1.33, "z": 0.30, "p": 0.761, "n": 150},
            "top5": {"full_pool": 0.1680, "old_partial_pool": 0.1720,
                     "delta_pp": +0.40, "z": 0.21, "p": 0.837, "n": 750},
            "top20": {"full_pool": 0.1690, "old_partial_pool": 0.1543,
                      "delta_pp": -1.47, "z": -1.55, "p": 0.122, "n": 3000},
            "verdict": "no significant degradation on a partial cross-section",
        },
    },
    "bit_identity": {
        "stride_1_head_vs_worktree": {
            "rows": 2680715, "columns_identical": True,
            "bit_identical": False,
            "columns_differing": ["fwd_max_close", "label_close"],
            "fwd_max_close_rows_differing": 2463995,
            "label_close_rows_differing": 17,
            "label_high_identical": True,
            "resolved_identical": True,
            "entry_open_identical": True,
            "cause": ("NOT the stride rule (stride=1 skips the branch entirely): "
                      "the working tree also changed label_close/fwd_max_close to "
                      "use a full-precision float64 entry price instead of a "
                      "float32 round trip"),
        },
        "stride_5_head_vs_worktree_row_mode": {
            "rows": 536143, "key_identical": True,
            "feature_columns_differing": [],
            "label_high_identical": True,
            "base_rate_high_identical": True,
            "base_rate_high": 0.030916061252356,
            "fwd_max_close_rows_differing": 492876,
            "label_close_rows_differing": 3,
            "label_close_flips_inside_walkforward_oos": 3,
            "label_close_flips_inside_2026_holdout": 0,
            "worst_case_precision_shift_on_a_label_close_config_pp": 0.018,
        },
        "published_holdout_reproduced": {
            "rule": "HEAD final_holdout.py + HEAD iloc[::5] matrix",
            "threshold": 0.16596081773308322,
            "base_rate": 0.02909598003648793,
            "signals": 1614, "hits": 196,
            "precision": 0.12143742255266418,
            "distinct_stocks": 802, "distinct_dates": 146,
            "matches_reports_ml_final_holdout_json_at_HEAD": True,
        },
    },
}

out = HERE / "stride_verification_evidence.json"
out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
print(f"wrote {out}  ({out.stat().st_size:,} bytes)")

removed = []
if ART.exists():
    for p in ART.rglob("*"):
        if p.is_file() and p.suffix == ".parquet":
            removed.append((p.name, p.stat().st_size))
            p.unlink()
total = sum(s for _, s in removed)
for n, s in removed:
    print(f"  removed {n}  ({s/1e6:.1f} MB)")
print(f"freed {total/1e9:.2f} GB; kept meta/report JSON under {ART}")
