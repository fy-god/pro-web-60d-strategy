"""Build per-shard feature + label files for the strategy scan.

Why shards
----------
A single 2.68M-row panel with 52 feature columns and 27 label columns does not
fit comfortably alongside 14 worker processes on a 15 GB machine; the first
attempt died with ``ArrowMemoryError``. This module splits the universe into
``n`` code-disjoint shards, each with complete per-stock history, and writes one
parquet file per shard. A worker then loads only its own shard, so resident
memory scales as ``1/n`` instead of being duplicated per worker.

Splitting by **code** (not by date) is essential: KDJ recursions, rolling
windows and forward labels all require a stock's full contiguous history, and a
date split would truncate every window at the seam.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import pandas as pd

from src import data_pipeline, features, labels

REPO_ROOT = Path(__file__).resolve().parents[1]
SHARD_DIR = REPO_ROOT / "data" / "shards"

CARD_COLUMNS = [
    "code", "date", "open", "high", "low", "close", "volume", "amount",
    "turnover", "kdj_k", "kdj_d", "kdj_j", "volume_ratio",
]
LABEL_COLUMNS = [
    "entry_open", "forward_max_return", "forward_min_return", "bars_to_target",
    "label_bull", "label_strict_low", "label_joint", "label_resolved",
]


def shard_columns() -> list[str]:
    columns = list(CARD_COLUMNS)
    for regime in labels.REGIMES:
        columns += [f"{c}__{regime}" for c in LABEL_COLUMNS]
    return columns


def build(n_shards: int = 6, force: bool = False) -> dict:
    """Build every shard and return a manifest."""
    manifest_path = SHARD_DIR / "manifest.json"
    if manifest_path.exists() and not force:
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    if SHARD_DIR.exists() and force:
        shutil.rmtree(SHARD_DIR)
    SHARD_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    panel = data_pipeline.load_panel()
    codes = sorted(panel["code"].unique())
    groups = [codes[i::n_shards] for i in range(n_shards)]
    groups = [g for g in groups if g]
    print(f"panel {panel.shape}; {len(groups)} shards of ~{len(codes)//len(groups)} codes",
          flush=True)

    keep = shard_columns()
    index = []
    for i, group in enumerate(groups):
        t1 = time.time()
        chunk = panel[panel["code"].isin(group)]
        prepared = features.prepare(chunk)
        labelled = labels.forward_outcomes_multi(prepared)
        labelled = labelled[[c for c in keep if c in labelled.columns]]
        path = SHARD_DIR / f"shard_{i:02d}.parquet"
        labelled.to_parquet(path, index=False, compression="zstd")
        index.append({
            "shard": i,
            "path": str(path),
            "codes": len(group),
            "rows": int(len(labelled)),
            "mb": round(path.stat().st_size / 1e6, 1),
        })
        print(f"  shard {i}: {len(group)} codes, {len(labelled)} rows, "
              f"{index[-1]['mb']} MB ({time.time()-t1:.0f}s)", flush=True)

    manifest = {
        "n_shards": len(groups),
        "total_rows": int(sum(s["rows"] for s in index)),
        "shards": index,
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"built {len(groups)} shards in {time.time()-t0:.0f}s")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards", type=int, default=6)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(n_shards=args.shards, force=args.force), indent=2))


if __name__ == "__main__":
    main()
