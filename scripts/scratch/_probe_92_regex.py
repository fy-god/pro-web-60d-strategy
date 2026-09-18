import io, pathlib, re

t = pathlib.Path("README.md").read_text(encoding="utf-8")
bt = chr(96)
rows = [l for l in t.splitlines()
        if l.startswith("| " + bt) and "**" in l and "%**" in l]
print("candidate rows:", len(rows))
for l in rows[:10]:
    print(repr(l))

# The audit's regex:
row_re = re.compile(
    r"^\|\s*`([a-z0-9_]+)`\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*"
    r"\*\*([\d.]+)%\*\*\s*\|\s*([\d,]+)\s*\|\s*([\d.]+)%\s*\|\s*"
    r"\*\*([\d.]+)%\*\*\s*\|",
    re.M)
found = row_re.findall(t)
print("\nregex matches:", len(found))
for x in found:
    print(" ", x)

print("\n--- why the others fail ---")
for l in rows[len(found):len(found) + 4]:
    print(repr(l))
    print("  direct search:", bool(row_re.search(l)))
