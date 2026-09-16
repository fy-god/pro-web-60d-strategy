"""Build the unified daily OHLCV panel from the local D:/xm source files.

The two source CSVs are the Tencent mainboard daily bars that back every
documented strategy version in this project's lineage:

  * ``mainboard_tencent_daily_2023_2024.csv``    (2023-01-03 .. 2024-12-31)
  * ``mainboard_tencent_daily_2025_20260831.csv`` (2025-01-02 .. 2026-08-31)

They are adjacent, not overlapping, so the panel is a straight concatenation
plus normalisation. Output is a single parquet panel keyed on (code, date).

Usage
-----
    python -m src.data_pipeline --build
    python -m src.data_pipeline --verify
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------
# Source locations. Override with the PWS_DATA_ROOT environment variable.
# --------------------------------------------------------------------------
DEFAULT_SOURCE_ROOT = Path(
    os.environ.get("PWS_DATA_ROOT", r"D:\xm\_a_share_86_custom_50pct\a_share_86_custom_50pct")
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = REPO_ROOT / "data" / "panel_daily.parquet"
MANIFEST_PATH = REPO_ROOT / "data" / "panel_manifest.json"

SOURCES = [
    "output_86_real/mainboard_tencent_daily_2023_2024.csv",
    "output_86_real/mainboard_tencent_daily_2025_20260831.csv",
]

REQUIRED_COLUMNS = ["code", "date", "open", "high", "low", "close", "volume"]


def _normalise_code(series: pd.Series) -> pd.Series:
    """Zero-pad integer codes to the six-digit exchange form.

    The source files store ``000017`` as ``17``; precision is lost on read, so
    the original string is unrecoverable and padding is the only faithful
    reconstruction for a mainboard universe (all six-digit codes).
    """
    return series.astype("int64").astype(str).str.zfill(6)


def load_source(path: Path) -> pd.DataFrame:
    """Read one source CSV into a typed, normalised frame."""
    if not path.exists():
        raise FileNotFoundError(f"source data file not found: {path}")

    frame = pd.read_csv(
        path,
        usecols=REQUIRED_COLUMNS,
        dtype={"code": "int64", "date": "string"},
    )
    frame["code"] = _normalise_code(frame["code"])
    frame["date"] = pd.to_datetime(frame["date"], format="%Y-%m-%d")
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["source_file"] = path.name
    return frame


def build(source_root: Path = DEFAULT_SOURCE_ROOT) -> pd.DataFrame:
    """Concatenate every source file into one de-duplicated panel."""
    frames = [load_source(source_root / rel) for rel in SOURCES]
    panel = pd.concat(frames, ignore_index=True)

    before = len(panel)
    panel = panel.sort_values(["code", "date"]).drop_duplicates(
        subset=["code", "date"], keep="last"
    )
    dropped = before - len(panel)

    # Drop rows that cannot support a bar: no price at all, or a degenerate
    # high/low bracket. Suspended days are absent from the source rather than
    # zero-filled, so volume == 0 is left intact for the caller to judge.
    panel = panel[panel["close"].notna() & (panel["close"] > 0)]
    panel = panel[panel["high"].notna() & panel["low"].notna() & (panel["high"] >= panel["low"])]

    panel = panel.reset_index(drop=True)
    panel["amount"] = pd.NA  # never populated by the source; kept for schema parity

    meta = {
        "rows_before_dedup": int(before),
        "duplicate_rows_dropped": int(dropped),
        "rows": int(len(panel)),
        "codes": int(panel["code"].nunique()),
        "date_min": panel["date"].min().strftime("%Y-%m-%d"),
        "date_max": panel["date"].max().strftime("%Y-%m-%d"),
        "trading_days": int(panel["date"].nunique()),
        "sources": SOURCES,
        "source_root": str(source_root),
    }
    return panel, meta


def write(panel: pd.DataFrame, meta: dict) -> None:
    PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL_PATH, index=False, compression="zstd")
    MANIFEST_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def load_panel() -> pd.DataFrame:
    """Load the built panel, building it first if it is absent."""
    if not PANEL_PATH.exists():
        panel, meta = build()
        write(panel, meta)
    return pd.read_parquet(PANEL_PATH)


def verify(source_root: Path = DEFAULT_SOURCE_ROOT) -> dict:
    """Independently re-check the panel against the raw sources."""
    panel = load_panel()
    raw = pd.concat([load_source(source_root / rel) for rel in SOURCES], ignore_index=True)
    raw = raw.sort_values(["code", "date"]).drop_duplicates(["code", "date"], keep="last")

    report = {
        "panel_rows": int(len(panel)),
        "raw_rows": int(len(raw)),
        "panel_codes": int(panel["code"].nunique()),
        "raw_codes": int(raw["code"].nunique()),
        "date_min": panel["date"].min().strftime("%Y-%m-%d"),
        "date_max": panel["date"].max().strftime("%Y-%m-%d"),
        "duplicate_code_date": int(panel.duplicated(["code", "date"]).sum()),
        "null_close": int(panel["close"].isna().sum()),
        "nonpositive_close": int((panel["close"] <= 0).sum()),
        "bad_hl_bracket": int((panel["high"] < panel["low"]).sum()),
        "close_outside_bracket": int(
            ((panel["close"] > panel["high"]) | (panel["close"] < panel["low"])).sum()
        ),
        "zero_volume_rows": int((panel["volume"] == 0).sum()),
        "monotonic_dates_per_code": bool(
            panel.groupby("code", sort=False)["date"].is_monotonic_increasing.all()
        ),
    }

    # Cross-check a deterministic sample of (code, date) keys against raw values.
    sample = panel.sample(n=min(2000, len(panel)), random_state=20260916)
    merged = sample.merge(raw, on=["code", "date"], suffixes=("_p", "_r"))
    report["sample_checked"] = int(len(merged))
    report["sample_close_mismatch"] = int(
        (merged["close_p"].round(6) != merged["close_r"].round(6)).sum()
    )
    report["sample_volume_mismatch"] = int(
        (merged["volume_p"].round(6) != merged["volume_r"].round(6)).sum()
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="build the panel parquet")
    parser.add_argument("--verify", action="store_true", help="re-check the panel")
    args = parser.parse_args()

    if args.build or not PANEL_PATH.exists():
        panel, meta = build()
        write(panel, meta)
        print(json.dumps(meta, indent=2, ensure_ascii=False))

    if args.verify:
        print(json.dumps(verify(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
