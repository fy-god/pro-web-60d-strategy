"""Show the wide preset's config mix and how far the dense regen has got."""
from __future__ import annotations

import re

from src.ml.search import presets

cfg = presets()["wide"]
print(f"wide preset: {len(cfg)} configs\n")

done = set()
for line in open("logs/regen/wide3.log", encoding="utf-8", errors="replace"):
    m = re.match(r"\[(\d+)/\d+\]\s+(\S+)", line.strip())
    if m:
        done.add(int(m.group(1)))

models = {}
for i, c in enumerate(cfg, 1):
    name = c["name"] if isinstance(c, dict) else c.name
    model = c["model"] if isinstance(c, dict) else c.model
    models.setdefault(model, []).append(i)

print("index ranges by model:")
for model, idx in sorted(models.items()):
    n_remaining = sum(1 for i in idx if i not in done)
    print(f"  {model:12s} {len(idx):>2} configs  indices {min(idx)}-{max(idx)}  "
          f"remaining {n_remaining}")

remaining = [c for i, c in enumerate(cfg, 1) if i not in done]
print(f"\ndone: {len(done)}  remaining: {len(remaining)}")
print("\nremaining configs:")
for c in remaining:
    name = c["name"] if isinstance(c, dict) else c.name
    model = c["model"] if isinstance(c, dict) else c.model
    print(f"   {name:<24} {model}")
