"""Run the delayed fix-up agent: read the newest expert/ML report, fix, push.

WHY THIS EXISTS
---------------
The expert/ML review is produced by GPT Pro in a web browser, not here. This
process is the OTHER half of that division of labour: it starts one hour after
the audit slot, reads whatever report the web review published, fixes the code
it points at, verifies, and pushes. It never writes an audit report itself --
`docs/audits/expert-ml/` belongs to the web review, and this script only reads
from it.

WHY A LAUNCHER AND NOT A ONE-LINE SCHTASKS COMMAND
--------------------------------------------------
The `dsh` entry point lives under a VERSION-HASHED directory:

    %APPDATA%\\DSH Desktop\\host-commands\\desktop\\generations\\<sha>-<sha>\\bin\\dsh.cmd

Measured: exactly one generation directory exists, and the hash changes whenever
DSH Desktop updates. A scheduled task that hard-codes that path silently stops
working after the next app update -- it would fail every run with "not found",
and because nobody watches a background task, the failure would look like
"the automation quietly stopped". So the launcher DISCOVERS the newest
generation on every run instead.

The instruction text is also deliberately short. Passing the whole prompt as a
command-line argument is fragile (quoting, length limits, escaping), so the
agent is told to read `scripts/fixup_prompt.txt`, which is a tracked file and
therefore reviewable and versioned alongside the code it governs.

Usage:
    python scripts/run_fixup.py            # normal scheduled run
    python scripts/run_fixup.py --dry-run  # resolve everything, start nothing
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
PROMPT_FILE = REPO / "scripts" / "fixup_prompt.txt"
LOG_DIR = REPO / "logs" / "fixup"

# The single short instruction handed to the agent. Everything else it needs is
# in the prompt file, which it reads itself.
TASK = (
    "读取 {prompt} 并严格按其中的全部指示执行。"
    "你是修复执行者，不是审计者：只读 docs/audits/expert-ml/ 下最新的报告，"
    "改代码、验证、推送。绝对不要写审计报告。"
).format(prompt=str(PROMPT_FILE))


def _path_candidates() -> list[pathlib.Path]:
    """Existing `dsh` launchers found through PATH."""
    found: list[pathlib.Path] = []
    for name in ("dsh.cmd", "dsh.exe", "dsh"):
        try:
            completed = subprocess.run(
                ["where", name], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        if completed.returncode != 0:
            continue
        for line in completed.stdout.strip().splitlines():
            candidate = pathlib.Path(line.strip())
            if candidate.exists():
                found.append(candidate)
    return found


def _generation_candidates() -> list[pathlib.Path]:
    """Existing launchers inside %APPDATA%\\DSH Desktop host-commands generations.

    This is the fallback for when PATH does not carry `dsh` -- PATH is how the
    installed app normally exposes it, but it is also the part a user or an
    installer can drop.
    """
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return []
    root = pathlib.Path(appdata) / "DSH Desktop" / "host-commands"
    if not root.is_dir():
        return []
    found: list[pathlib.Path] = []
    for profile_dir in root.iterdir():
        generations = profile_dir / "generations"
        if not generations.is_dir():
            continue
        for generation in generations.iterdir():
            for name in ("dsh.cmd", "dsh.exe", "dsh"):
                candidate = generation / "bin" / name
                if candidate.exists():
                    found.append(candidate)
    return found


def find_dsh() -> tuple[pathlib.Path | None, str]:
    """Locate the `dsh` launcher, and say HOW it was found.

    Precedence, most to least specific:
      1. `DSH_BIN` -- an explicit pin, so the value is used verbatim.
      2. PATH -- the app-managed shim. Authoritative when present, because that
         is the launcher the installed app itself intends to be used.
      3. The newest generation directory -- a fallback for when PATH has no
         `dsh`. Generations are content-addressed, so "newest" means highest
         mtime: that is the one the most recent install wrote.

    Returning the source as well as the path is deliberate. An earlier version
    returned early on a PATH hit, which made the generation scan unreachable in
    practice -- the fallback was dead code that no test exercised. The source
    label is what the tests assert on to prove each branch actually runs.
    """
    override = os.environ.get("DSH_BIN")
    if override:
        candidate = pathlib.Path(override)
        if candidate.exists():
            return candidate, "DSH_BIN"

    from_path = _path_candidates()
    if from_path:
        return max(from_path, key=lambda p: p.stat().st_mtime), "PATH"

    from_generations = _generation_candidates()
    if from_generations:
        return max(from_generations, key=lambda p: p.stat().st_mtime), "generation"

    return None, "not-found"


def run_git(args: list[str], log) -> int:
    completed = subprocess.run(
        ["git", *args], cwd=str(REPO), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=600,
    )
    if completed.stdout:
        log.write(completed.stdout)
    if completed.stderr:
        log.write(completed.stderr)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="resolve the launcher and prompt but start no agent")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    started = dt.datetime.now()
    log_path = LOG_DIR / f"fixup_{started:%Y-%m-%d_%H%M%S}.log"

    with io.open(log_path, "w", encoding="utf-8") as log:
        log.write(f"# fix-up run {started:%Y-%m-%d %H:%M:%S}\n")
        log.write(f"repo: {REPO}\n\n")

        if not PROMPT_FILE.exists():
            log.write(f"FATAL: prompt file missing: {PROMPT_FILE}\n")
            print(f"prompt file missing: {PROMPT_FILE}", file=sys.stderr)
            return 2

        dsh, source = find_dsh()
        if dsh is None:
            log.write("FATAL: could not locate the dsh launcher.\n")
            log.write("Checked DSH_BIN, PATH, and "
                      "%APPDATA%\\DSH Desktop\\host-commands\\*\\generations\\*\\bin.\n")
            print("could not locate the dsh launcher", file=sys.stderr)
            return 3
        log.write(f"dsh: {dsh}\n")
        log.write(f"dsh found via: {source}\n")
        log.write(f"prompt: {PROMPT_FILE}\n\n")

        # Sync to the remote BEFORE the agent starts. The web review commits its
        # report to this repo, so without this the agent would read a stale tree
        # and could re-process the previous round.
        log.write("## git sync before the run\n")
        run_git(["fetch", "origin", "main"], log)
        # --autostash: the four-hourly audit task may have just rewritten
        # reports/AUDIT_STATUS.md, and it must not be lost or block the rebase.
        sync_code = run_git(["rebase", "--autostash", "origin/main"], log)
        log.write(f"rebase exit: {sync_code}\n\n")

        # List the reports visible now, so the log alone shows what the agent
        # could have chosen from.
        report_dir = REPO / "docs" / "audits" / "expert-ml"
        log.write("## available reports\n")
        if report_dir.is_dir():
            names = sorted(
                (p.name for p in report_dir.iterdir()
                 if p.is_file() and p.suffix == ".md"
                 and p.name not in ("LATEST.md", "SCHEDULE.md")),
                reverse=True)
            for name in names[:8]:
                log.write(f"  {name}\n")
            log.write(f"  newest: {names[0] if names else '(none)'}\n")
        else:
            log.write(f"  directory missing: {report_dir}\n")
        log.write("\n")

        if args.dry_run:
            log.write("dry run: not starting the agent\n")
            print(f"dry run ok; dsh={dsh}")
            return 0

        log.write("## agent run\n")
        log.flush()
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO)
        # An unattended push must never block on a credential prompt: with no
        # terminal it would hang until the task's time limit killed it.
        env["GIT_TERMINAL_PROMPT"] = "0"
        env.setdefault("DSH_HOME", str(pathlib.Path.home() / ".dsh"))

        # REQUIRED, not a preference. The headless profile reads its sandbox mode
        # from this variable and otherwise defaults to `workspace-write`, whose
        # approval policy is `ask`. With nobody present there is no one to answer,
        # so the shell is refused -- and because the confined sandbox also blocks
        # piping a child process's stdio on Windows, the pwsh tool returns EMPTY
        # OUTPUT instead of an error. Measured on this machine:
        #
        #   workspace-write    -> agent sees a mute shell, burns its budget
        #                         retrying, gives up, exits 1
        #   danger-full-access -> `echo SHELL_WORKS` prints SHELL_WORKS
        #
        # A mute shell is worse than a refused one: the agent cannot distinguish
        # "denied" from "the command printed nothing". Since this process exists
        # to edit files and run `git push`, it needs a working shell by definition.
        env["DSH_PERMISSION_MODE"] = "danger-full-access"

        try:
            completed = subprocess.run(
                [str(dsh), "--profile", "headless", TASK],
                cwd=str(REPO), capture_output=True, text=True,
                encoding="utf-8", errors="replace", env=env, timeout=5400,
            )
        except subprocess.TimeoutExpired:
            log.write("TIMEOUT: the agent exceeded 90 minutes and was killed.\n")
            print("agent timed out", file=sys.stderr)
            return 4

        log.write(f"exit code: {completed.returncode}\n\n")
        if completed.stdout:
            log.write("--- stdout ---\n")
            log.write(completed.stdout)
            log.write("\n")
        if completed.stderr:
            log.write("--- stderr ---\n")
            log.write(completed.stderr)
            log.write("\n")

        # A DeprecationWarning on stderr is normal and does NOT indicate failure,
        # so the exit code is what decides -- never the presence of stderr text.
        ok = completed.returncode == 0
        log.write(f"\nresult: {'OK' if ok else 'FAILED'}\n")
        print(f"fix-up {'ok' if ok else 'failed'}; log: {log_path}")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
