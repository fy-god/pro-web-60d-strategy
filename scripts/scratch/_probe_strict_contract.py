"""Does each base strategy actually USE its THRESHOLD, and on what scale?

Before calling a lower `strict_*` threshold a defect, establish that comparing the
two numbers means anything:

  * does the base module's predict() read its own THRESHOLD, or is THRESHOLD
    vestigial?  If vestigial, the comparison is meaningless.
  * if it is read, is the gate `score >= T`?  Then a lower T on the same score is
    unambiguously a LOOSER selector.
  * is the score on a 0..1 probability scale, or a raw/veto scale?  A base
    THRESHOLD of 0.90 that is unreachable (max score 0.68) is a different defect
    from a reachable one.

Reads source only; no panel is loaded.
"""
from __future__ import annotations

import importlib
import pathlib
import re

STRAT = pathlib.Path("experts/strategies")
PAIRS = [
    ("accumulation_base", "strict_accumulation_base_v2"),
    ("bollinger_squeeze", "strict_bollinger_release_v2"),
    ("first_board_breakout", "strict_first_board_breakout_v2"),
    ("gap_follow_through", "strict_gap_follow_through"),
    ("gap_follow_through", "strict_gap_follow_through_v2"),
    ("leader_momentum", "strict_leader_momentum_v2"),
    ("obv_volume_price", "strict_obv_volume_price"),
    ("obv_volume_price", "strict_obv_volume_price_v2"),
    ("oversold_rebound", "strict_oversold_rebound_v2"),
    ("platform_breakout", "strict_platform_breakout"),
    ("platform_breakout", "strict_platform_breakout_v2"),
    ("relative_strength_rank", "strict_relative_strength"),
    ("relative_strength_rank", "strict_relative_strength_v2"),
    ("turnover_weak_to_strong", "strict_turnover_weak_to_strong_v2"),
    ("washout_complete", "strict_washout_complete"),
    ("washout_complete", "strict_washout_complete_v2"),
]

print("=== does the base read its THRESHOLD in a gate? ===")
print(f"{'base':<26}{'T':>9}  {'score_fn':<28}{'gate?':<22}{'THRESHOLD refs inside score'}")
print("-" * 104)
for base, _ in PAIRS:
    src = (STRAT / f"{base}.py").read_text(encoding="utf-8")
    mod = importlib.import_module(f"experts.strategies.{base}")
    t = getattr(mod, "THRESHOLD", None)
    # Strip comments so a comment mentioning THRESHOLD cannot masquerade as a use.
    code = "\n".join(l for l in src.splitlines()
                     if not l.lstrip().startswith("#"))
    gates = [l.strip() for l in code.splitlines()
             if "THRESHOLD" in l and (">=" in l or ">" in l or "<" in l)]
    print(f"{base:<26}{t if t is None else f'{t:.4f}':>9}  "
          f"{'':<28}{(gates[0][:44] if gates else 'NO THRESHOLD GATE'):<22}"
          f"{len(gates)}")

print("\n=== deduplicated: the base's gate line ===")
seen = {}
for base, _ in PAIRS:
    if base in seen:
        continue
    src = (STRAT / f"{base}.py").read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines()
                     if not l.lstrip().startswith("#"))
    gates = [l.strip() for l in code.splitlines() if "THRESHOLD" in l]
    seen[base] = gates
for base, gates in seen.items():
    print(f"\n  {base}:")
    for g in gates[:4]:
        print(f"      {g}")

print("\n=== _strict_selector: the shared contract ===")
p = STRAT / "_strict_selector.py"
if p.exists():
    s = p.read_text(encoding="utf-8")
    print("\n".join("  " + l for l in s.splitlines()[:40]))
