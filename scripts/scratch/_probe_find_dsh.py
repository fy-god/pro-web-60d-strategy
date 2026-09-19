"""Prove each `find_dsh` branch actually runs -- the fallback must not be dead code.

The first version of find_dsh returned on a PATH hit, so the generation scan was
unreachable: my own update-resilience test "passed" against a fake newer
generation without ever calling that code. This drives each branch explicitly by
manipulating the things it reads (env var, PATH, APPDATA layout) rather than
trusting the precedence by inspection.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(r"D:\ccc\pro-web-60d-strategy")
spec = importlib.util.spec_from_file_location(
    "run_fixup", str(REPO / "scripts" / "run_fixup.py"))
run_fixup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_fixup)

fails = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global fails
    if not ok:
        fails += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {label}{'  -> ' + detail if detail else ''}")


def make_fake_launcher(path: pathlib.Path, mtime_offset_min: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("@echo off\necho fake\n", encoding="ascii")
    import datetime as dt
    stamp = dt.datetime.now() + dt.timedelta(minutes=mtime_offset_min)
    os.utime(path, (stamp.timestamp(), stamp.timestamp()))


saved_bin = os.environ.get("DSH_BIN")
saved_path = os.environ.get("PATH")
saved_appdata = os.environ.get("APPDATA")
tmp = pathlib.Path(tempfile.mkdtemp(prefix="fixup_probe_"))

try:
    print("=== branch 1: DSH_BIN wins ===")
    pinned = tmp / "pinned" / "dsh.cmd"
    make_fake_launcher(pinned)
    os.environ["DSH_BIN"] = str(pinned)
    found, source = run_fixup.find_dsh()
    check("DSH_BIN is used verbatim", found == pinned, str(found))
    check("source is reported as DSH_BIN", source == "DSH_BIN", source)

    print("\n=== branch 2: a non-existent DSH_BIN falls through ===")
    os.environ["DSH_BIN"] = str(tmp / "does-not-exist" / "dsh.cmd")
    found, source = run_fixup.find_dsh()
    check("bad DSH_BIN is ignored", source != "DSH_BIN" or found is None, source)

    print("\n=== branch 3: PATH is used when no DSH_BIN ===")
    del os.environ["DSH_BIN"]
    onpath_dir = tmp / "onpath"
    onpath = onpath_dir / "dsh.cmd"
    make_fake_launcher(onpath)
    # Prepend our dir, but leave the real PATH after it so `where` works at all.
    os.environ["PATH"] = str(onpath_dir) + os.pathsep + saved_path
    found, source = run_fixup.find_dsh()
    check("PATH branch is taken", source == "PATH", source)
    check("the PATH launcher is returned", found == onpath, str(found))

    print("\n=== branch 4: generation scan runs when PATH has no dsh ===")
    # This is the branch that was previously unreachable. Empty APPDATA layout
    # plus a PATH stripped of every dsh-bearing directory forces it.
    fake_appdata = tmp / "appdata"
    gen_dir = (fake_appdata / "DSH Desktop" / "host-commands" / "desktop"
               / "generations" / "aaaa-bbbb" / "bin")
    gen_launcher = gen_dir / "dsh.cmd"
    make_fake_launcher(gen_launcher)
    os.environ["APPDATA"] = str(fake_appdata)
    os.environ["PATH"] = str(tmp / "empty-dir")   # no dsh anywhere
    (tmp / "empty-dir").mkdir(exist_ok=True)
    found, source = run_fixup.find_dsh()
    check("generation branch is REACHABLE (was dead code)", source == "generation", source)
    check("the generation launcher is returned", found == gen_launcher, str(found))

    print("\n=== branch 5: newest generation wins ===")
    newer = (fake_appdata / "DSH Desktop" / "host-commands" / "desktop"
             / "generations" / "cccc-dddd" / "bin" / "dsh.cmd")
    make_fake_launcher(newer, mtime_offset_min=30)
    found, source = run_fixup.find_dsh()
    check("newest generation is chosen (survives an app update)",
          found == newer, f"{found}")
    check("older generation is NOT chosen", found != gen_launcher, "")

    print("\n=== branch 6: nothing found returns None, not a crash ===")
    os.environ["APPDATA"] = str(tmp / "barren")
    (tmp / "barren").mkdir(exist_ok=True)
    found, source = run_fixup.find_dsh()
    check("returns None when there is no launcher", found is None, str(found))
    check("source says not-found", source == "not-found", source)

finally:
    if saved_bin is None:
        os.environ.pop("DSH_BIN", None)
    else:
        os.environ["DSH_BIN"] = saved_bin
    if saved_path is not None:
        os.environ["PATH"] = saved_path
    if saved_appdata is not None:
        os.environ["APPDATA"] = saved_appdata
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("ALL BRANCHES COVERED" if fails == 0 else f"{fails} CHECK(S) FAILED")
sys.exit(0 if fails == 0 else 1)
