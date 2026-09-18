"""Add BASE_STRATEGY_ID to every strict_* module's __all__.

The previous pass inserted the declaration but its __all__ regex expected
"THRESHOLD", on its own line at a fixed indent, which not every module matches.
This adds the name to whichever __all__ list exists, right after "THRESHOLD",
preserving that file's own indentation.
"""
from __future__ import annotations

import pathlib
import re

STRAT = pathlib.Path("experts/strategies")
changed = []
for p in sorted(STRAT.glob("strict_*.py")):
    src = p.read_text(encoding="utf-8")
    if '"BASE_STRATEGY_ID"' in src:
        continue
    m = re.search(r'^(__all__ = \[\n)(.*?)^\]', src, re.M | re.S)
    if not m:
        print(f"  no __all__ in {p.stem}")
        continue
    body = m.group(2)
    # Insert after THRESHOLD, using the indentation that line actually has.
    tline = re.search(r'^(\s*)"THRESHOLD",\n', body, re.M)
    if tline:
        indent = tline.group(1)
        newbody = (body[:tline.end()]
                   + f'{indent}"BASE_STRATEGY_ID",\n'
                   + body[tline.end():])
    else:
        # No THRESHOLD entry: append before the closing bracket.
        lines = body.rstrip("\n").split("\n")
        indent = re.match(r'^(\s*)', lines[-1]).group(1)
        lines.append(f'{indent}"BASE_STRATEGY_ID",')
        newbody = "\n".join(lines) + "\n"
    src = src[:m.start(2)] + newbody + src[m.end(2):]
    p.write_text(src, encoding="utf-8")
    changed.append(p.stem)

print(f"added to __all__ in {len(changed)} module(s)")
for c in changed:
    print("   ", c)
