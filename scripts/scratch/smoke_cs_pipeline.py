"""Full-path smoke: run_config + pool_with_inference + report with an underfit model.

Validates every code path of src/ml/search_crosssec.py -- including the paired
date-clustered tests, the score cache, the report printer and JSON
serialisation -- in a few minutes. The model is capped at 20 iterations so the
numbers are meaningless by construction.
"""
import json
import shutil
import time
from pathlib import Path

from src.ml import crosssec as xs
from src.ml import search_crosssec as sc
from src.ml import walkforward as wf

CACHE = Path("outputs/ml/crosssec_cache_smoke")
if CACHE.exists():
    shutil.rmtree(CACHE)

m = xs.load()
cfg = wf.Config(name="smoke", model="hgb", params={"max_iter": 20},
                label="label_high", target_rate=0.02)

t0 = time.time()
res = sc.run_config(m, cfg, xs.TOP_K_GRID, xs.PERCENTILE_GRID, n_boot=300, seed=0,
                    cache_dir=CACHE)
t_first = time.time() - t0
print(f"run_config (cold cache) ok in {t_first:.0f}s", flush=True)
print("cached frames:", len(list(CACHE.glob('*.parquet'))), flush=True)
sc.report(res, xs.TOP_K_GRID, 300)

payload = sc.strip_private({"results": {"smoke": res}})
blob = json.dumps(payload, indent=2, default=str)
print(f"\nstrip_private + json ok ({len(blob)} bytes)", flush=True)
assert "_y" not in blob and "_score" not in blob and "_mask_global" not in blob

# cache hit: a second pass must be much faster and must reproduce the numbers
t0 = time.time()
res2 = sc.run_config(m, cfg, xs.TOP_K_GRID, xs.PERCENTILE_GRID, n_boot=300, seed=0,
                     verbose=False, cache_dir=CACHE)
t_second = time.time() - t0
same = abs(res2["topk"]["5"]["precision"] - res["topk"]["5"]["precision"]) < 1e-12
print(f"run_config (warm cache) ok in {t_second:.0f}s  "
      f"({t_first / max(t_second, 1e-9):.1f}x faster)  identical numbers: {same}",
      flush=True)
assert same, "cache changed the measured numbers"
print("DONE", flush=True)
