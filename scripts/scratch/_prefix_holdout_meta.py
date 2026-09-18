"""Forward-port the exposure metadata into the existing holdout report.

src/ml/final_holdout.py now writes `holdout_label`, `exposure` and a corrected
`note`. The report on disk was produced before that change, so it lacks them.

Regenerating it means loading the 815 MB dense matrix and refitting HGB -- heavy,
and the machine is in use. These three fields are pure METADATA: they depend only
on the project's provenance history, not on any fitted number. So they are added
directly, and this script proves it touched nothing else:

  * every pre-existing key must keep its exact value, and
  * the only keys that may appear are the three named above,
  * any numeric value must be bit-identical.

If the report is ever regenerated end-to-end, the producer writes the same values
and this script becomes a no-op. Refuses to run if the fields are already present
and disagree.
"""
from __future__ import annotations

import io
import json
import pathlib
import shutil

PATH = pathlib.Path("reports/ml_final_holdout.json")
BACKUP = pathlib.Path("reports/.ml_final_holdout.json.prefix_backup")

LABEL = "historical_holdout_with_prior_project_exposure"
EXPOSURE = {
    "model_selection": "none -- this block was excluded from every search",
    "feature_design": "none",
    "threshold_choice": "none",
    "prior_project_observation": (
        "yes -- rule backtests, charts and expectancy tables already covered "
        "2026 before this script existed"
    ),
}
NOTE_TAIL = (
    " This is a historical out-of-sample diagnostic, NOT a pristine final "
    "lockbox: the 2026 period had prior project exposure (see `exposure`). A "
    "genuine final block would have to be untouched by model, feature and "
    "threshold choice alike until frozen."
)

OLD = json.load(io.open(PATH, encoding="utf-8"))

already = (OLD.get("holdout_label") == LABEL
           and "not a pristine" in str(OLD.get("note", "")))
if already:
    print("already forward-ported; nothing to do")
    raise SystemExit(0)
if OLD.get("holdout_label") not in (None, LABEL):
    raise SystemExit(f"refusing: report carries a different label "
                     f"{OLD['holdout_label']!r}")

shutil.copy2(PATH, BACKUP)
NEW = dict(OLD)
NEW["holdout_label"] = LABEL
NEW["exposure"] = EXPOSURE
note = str(OLD.get("note") or "").rstrip()
if "not a pristine" not in note:
    NEW["note"] = note + NOTE_TAIL

# --- proof that nothing measured changed -------------------------------------
# `note` is MODIFIED rather than added (it is an existing key), so it is checked
# by the append test below rather than here.
added = set(NEW) - set(OLD)
assert added == {"holdout_label", "exposure"}, f"unexpected added keys {added}"
for key, before in OLD.items():
    after = NEW[key]
    if key == "note":
        assert str(after).startswith(str(before).rstrip()), "note was rewritten, not appended"
        continue
    assert type(before) is type(after), f"{key}: type changed"
    if isinstance(before, float):
        assert before == after, f"{key}: float changed {before!r} -> {after!r}"
    elif isinstance(before, (list, dict)):
        assert json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True), \
            f"{key}: structured value changed"
    else:
        assert before == after, f"{key}: value changed {before!r} -> {after!r}"

PATH.write_text(json.dumps(NEW, indent=2), encoding="utf-8")
REREAD = json.load(io.open(PATH, encoding="utf-8"))
assert REREAD["holdout_label"] == LABEL
assert REREAD["precision"] == OLD["precision"]
assert REREAD["signals"] == OLD["signals"]
assert REREAD["hits"] == OLD["hits"]
print(f"forward-ported: {len(OLD)} keys -> {len(NEW)} keys")
print(f"  precision unchanged: {REREAD['precision']!r}")
print(f"  signals/hits unchanged: {REREAD['signals']}/{REREAD['hits']}")
print(f"  backup at {BACKUP}")
