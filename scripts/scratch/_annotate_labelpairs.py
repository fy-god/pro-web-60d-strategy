"""Annotate the stale label_pairs_audit.json without altering its measurements.

The artifact records `label_close_defined_where_resolved_false = 5747`, measured on
a matrix that was rebuilt ~18 hours later; the shipped matrix measures 0. Its
`read_this` prose still told a reader to treat `> 0` as a live defect.

Rewriting the 5747 would destroy the record that the fix happened, so this:

  * leaves every measured value byte-identical;
  * replaces the misleading `read_this` prose with one that says the number is a
    PRE-FIX measurement and must not be read as a live defect;
  * adds a `matrix_vintage` block naming the matrix, the two timestamps, which
    field is stale, and the value the shipped matrix actually has.

Then it asserts no measured field moved.
"""
from __future__ import annotations

import io
import json
import pathlib

ART = pathlib.Path("outputs/ml/audit/label_pairs_audit.json")

OLD_TEXT = (
    "`label_high`/`resolved`/`entry_open`/`fwd_max_*` must match to float32 "
    "precision. `label_close_defined_where_resolved_false` > 0 is a genuine "
    "defect in build_matrix: label_close is censored on `seen` (>=1 forward bar) "
    "instead of `resolved` (>=10)."
)
NEW_READ_THIS = (
    "`label_high`/`resolved`/`entry_open`/`fwd_max_*` must match to float32 "
    "precision. NOTE ON `label_close_defined_where_resolved_false`: this artifact "
    "records 5747, which is a PRE-FIX measurement. The defect it named was real "
    "-- label_close was censored on `seen` (>=1 forward bar) instead of "
    "`resolved` (>=10) -- and it was fixed in c97de8c, after which the matrix was "
    "rebuilt, ~18h after this file was written. Measured on the SHIPPED matrix the "
    "value is 0: label_close is finite exactly where resolved == 1, over all "
    "536,143 rows. Do NOT read the stored 5747 as a live defect; it describes a "
    "matrix that no longer exists. The count is retained rather than rewritten "
    "because overwriting a measurement would destroy the record that the fix "
    "happened. See `matrix_vintage`."
)
VINTAGE = {
    "matrix": "outputs/ml/matrix_h10_t30_s5.parquet",
    "rows_at_measurement": 536143,
    "artifact_written": "2026-09-17 03:02:26",
    "matrix_rebuilt": "2026-09-17 21:46:51",
    "stale_fields": ["label_close_defined_where_resolved_false"],
    "shipped_matrix_value_for_stale_field": 0,
    "verified": (
        "label_close.notna() == resolved on all 536,143 rows; label_close mean "
        "0.020303647965192795 == meta base_rate_close"
    ),
    "why_this_is_recorded": (
        "The 4-hourly audit validates this artifact's COMPOSITION, never its "
        "vintage, so a stale measurement passes every check. The vintage block "
        "makes the staleness machine-visible."
    ),
}

OLD = json.load(io.open(ART, encoding="utf-8"))
ex = OLD.get("exhaustive")
if not isinstance(ex, dict):
    raise SystemExit("exhaustive block missing -- artifact shape changed")

already = "PRE-FIX measurement" in str(ex.get("read_this", ""))
if already:
    print("already annotated; nothing to do")
    raise SystemExit(0)
if str(ex.get("read_this")) != OLD_TEXT:
    raise SystemExit("read_this has changed; refusing to overwrite unseen text:\n"
                     + str(ex.get("read_this"))[:300])

NEW = json.loads(json.dumps(OLD))  # deep copy
NEW["exhaustive"]["read_this"] = NEW_READ_THIS
NEW["exhaustive"]["matrix_vintage"] = VINTAGE

# Nothing measured may move.
for key, before in OLD.items():
    assert key in NEW, f"{key} vanished"
    if key == "exhaustive":
        continue
    assert json.dumps(before, sort_keys=True) == json.dumps(NEW[key], sort_keys=True), \
        f"{key} changed"
for key, before in OLD["exhaustive"].items():
    if key in ("read_this",):
        continue
    assert json.dumps(before, sort_keys=True) == \
        json.dumps(NEW["exhaustive"][key], sort_keys=True), f"exhaustive.{key} changed"
assert NEW["exhaustive"]["label_close_defined_where_resolved_false"] == 5747

# Preserve the file's original formatting style as closely as possible.
ART.write_text(json.dumps(NEW, indent=2, ensure_ascii=False), encoding="utf-8")

REREAD = json.load(io.open(ART, encoding="utf-8"))
assert REREAD["exhaustive"]["label_close_defined_where_resolved_false"] == 5747
assert REREAD["exhaustive"]["matrix_vintage"]["shipped_matrix_value_for_stale_field"] == 0
print("annotated outputs/ml/audit/label_pairs_audit.json")
print("  label_close_defined_where_resolved_false still 5747 (measurement preserved)")
print("  read_this now states it is pre-fix")
print("  matrix_vintage block added")
