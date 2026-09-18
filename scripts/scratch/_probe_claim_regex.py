"""Find a regex that parses all four versions from audit/README.md's claim lines.

The document writes the in-sample pair slash-joined -- "V07/V08 in-sample hits
(4.23%/4.08%)" -- and V03 after a long phrase -- "the honest walk-forward V03
(4.37%)". So versions and percentages are not adjacent, and the text between them
contains parentheses. Any regex that forbids "(" between a version and its
percentage silently loses V03.
"""
from __future__ import annotations

line = open("audit/README.md", encoding="utf-8").read()
claim = next(ln for ln in line.splitlines() if "walk-forward V03" in ln)
print("line:")
print(f"  {claim}\n")

candidates = {
    "no-paren class, 24": r"V(\d\d)[^\d(]{0,24}?([\d.]+)%",
    "no-paren class, 64": r"V(\d\d)[^\d(]{0,64}?([\d.]+)%",
    "any chars, 64": r"V(\d\d).{0,64}?([\d.]+)%",
    "any chars, 80": r"V(\d\d).{0,80}?([\d.]+)%",
    "grouped then any": None,
}
import re

for label, pat in candidates.items():
    if pat is None:
        continue
    found = re.findall(pat, claim)
    print(f"{label:22s} -> {found}")

print()
print("with a grouped-first pass plus 'any chars, 64':")
found = {}
grp = re.search(r"V(\d\d)/V(\d\d)[^(]*\(([\d.]+)%\s*/\s*([\d.]+)%\)", claim)
if grp:
    v1, v2, p1, p2 = grp.groups()
    found[f"V{v1}"] = float(p1)
    found[f"V{v2}"] = float(p2)
for n, p in re.findall(r"V(\d\d).{0,64}?([\d.]+)%", claim):
    found.setdefault(f"V{n}", float(p))
print(f"  {found}")

want = {"V03": 4.37, "V07": 4.23, "V08": 4.08}
print(f"\nexpected {want}")
print("RESULT:", "PASS" if found == want else "FAIL")
raise SystemExit(0 if found == want else 1)
