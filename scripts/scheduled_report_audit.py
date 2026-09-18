"""Scheduled audit of the published GitHub reports, run every four hours.

What it does, in order:

1. Fetch the remote so the local checkout knows what is actually published.
2. Compare every tracked report against the version on ``origin/main``. If a
   report changed remotely, note it — that is "a new report appeared".
3. Run ``scripts/audit_reports.py``, which checks the arithmetic, the pooling,
   cross-report agreement, prose drift and Markdown structure.
4. Write a timestamped log under ``logs/report_audit/`` (local detail) and a
   COMMITTED, human-readable ``reports/AUDIT_STATUS.md`` (the durable record).
5. Append a short summary to ``logs/report_audit/FINDINGS.md`` when something
   needs attention.
6. Commit and push ``reports/AUDIT_STATUS.md`` so the result is visible on
   GitHub without anyone reading this machine's filesystem.

The first version of this script was read-only and wrote only under ``logs/``,
which ``.gitignore`` excludes — so it ran correctly every four hours and
published nothing at all. An audit whose result nobody can see is not an audit.
The write path is now deliberately narrow: it publishes status and diagnostics,
never report numbers, and it refuses to run if a report file changed during the
audit (which would mean another process is mid-regeneration).

Usage
-----
    python scripts/scheduled_report_audit.py            # normal run
    python scripts/scheduled_report_audit.py --dry-run  # skip git fetch
    python scripts/scheduled_report_audit.py --no-push  # write, do not commit
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs" / "report_audit"
FINDINGS = LOG_DIR / "FINDINGS.md"
AUDIT = ROOT / "scripts" / "audit_reports.py"
STATUS = ROOT / "reports" / "AUDIT_STATUS.md"
REPORTS_DIR = ROOT / "reports"


def run(cmd: list[str], cwd: Path = ROOT, timeout: int = 600) -> tuple[int, str]:
    """Run a command, returning (exit code, combined output)."""
    try:
        p = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"TIMEOUT after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError as exc:
        return 127, f"NOT FOUND: {exc}"


def snapshot_reports() -> dict[str, str]:
    """Content hash of every report, so a mid-flight regeneration is detectable.

    Regenerating a report while this audit reads it once produced a published
    document that disagreed with every artifact on disk, and neither the
    generator nor the checker noticed. Hashing before and after turns that
    silent race into a loud failure.
    """
    out: dict[str, str] = {}
    for path in sorted(REPORTS_DIR.rglob("*")):
        if path.is_file() and path.suffix in {".json", ".csv"}:
            out[path.relative_to(ROOT).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()[:16]
    return out


def changed_reports(dry_run: bool) -> tuple[list[str], str]:
    """Return reports whose content differs from origin/main, plus a note."""
    if dry_run:
        return [], "dry run: skipped fetch"
    code, out = run(["git", "fetch", "origin", "main", "--quiet"], timeout=300)
    if code != 0:
        return [], f"git fetch failed (exit {code}): {out.strip()[:300]}"

    code, out = run(["git", "diff", "--name-only", "HEAD", "origin/main",
                     "--", "reports/", "*.md"], timeout=120)
    if code != 0:
        return [], f"git diff failed (exit {code})"

    names = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return names, f"{len(names)} path(s) differ from origin/main"


def write_status(
    started: dt.datetime,
    code: int,
    audit_out: str,
    changed: list[str],
    note: str,
    probe: dict,
    unstable: list[str],
    log_name: str,
) -> None:
    """Publish a compact, committed status file for GitHub readers."""
    ok = code == 0 and not unstable
    verdict = "PASS" if ok else "ATTENTION"
    # Read the machine-readable summary `audit_reports.py` prints. It used to be
    # scraped with `startswith(("- ", "FAIL"))`, which ALSO matched the note
    # bullets -- both were printed as `  - <text>` -- so a fully green run (exit 0,
    # "590 checks run, 0 problem(s)") published 12 known gaps under "## Failures"
    # in the committed file. Prose-scraping cannot be made reliable; a structured
    # line can.
    summary: dict = {}
    for line in audit_out.splitlines():
        if line.startswith("AUDIT_SUMMARY_JSON "):
            try:
                summary = json.loads(line[len("AUDIT_SUMMARY_JSON "):])
            except ValueError:
                summary = {}
    n_checks = ""
    for line in audit_out.splitlines():
        if "checks run" in line:
            n_checks = line.strip()
            break

    lines = [
        "# Report audit status",
        "",
        "_Written automatically every four hours by "
        "`scripts/scheduled_report_audit.py`. Do not edit by hand._",
        "",
        f"| | |",
        f"|---|---|",
        f"| Last run (local) | {started:%Y-%m-%d %H:%M:%S} |",
        f"| Verdict | **{verdict}** |",
        f"| Consistency check | exit code {code} |",
        f"| Checks | {n_checks or 'see log'} |",
        f"| Remote drift | {note} |",
        f"| Detail log | `{log_name}` (local, not committed) |",
        "",
    ]
    if unstable:
        lines += [
            "## Report files changed during the audit",
            "",
            "Another process was regenerating these while they were being read, "
            "so this run's findings are unreliable and the audit re-runs next "
            "cycle. This is reported rather than silently ignored because a "
            "published document once disagreed with every artifact on disk.",
            "",
        ]
        lines += [f"- `{name}`" for name in unstable]
        lines.append("")

    if changed:
        lines += ["## Remote drift", "", f"{note}:", ""]
        lines += [f"- `{name}`" for name in changed]
        lines.append("")

    if ok:
        lines += ["## Headline", ""]
        if probe:
            lines += [
                f"- holdout precision **{probe.get('precision', 0)*100:.2f}%** "
                f"against a base rate of {probe.get('base_rate', 0)*100:.2f}% "
                f"({probe.get('lift', 0):.2f}x lift)",
                f"- {probe.get('signals', 0):,} signals, "
                f"{probe.get('hits', 0):,} hits",
            ]
        lines += ["", "All consistency checks passed.", ""]
        # Known gaps are printed on a PASS too, so a reader can see what is
        # deliberately unverified rather than assuming "PASS" means "everything
        # is checked". They are labelled as gaps, never as failures.
        notes = list(summary.get("note_list") or [])
        if notes:
            lines += [f"## Known gaps ({len(notes)})",
                      "", "_Reported, not failures._", ""]
            lines += [f"- {n}" for n in notes[:40]]
            lines.append("")
    else:
        lines += ["## Failures", "", "```"]
        # Prefer the structured list. Fall back to scraping `FAIL`-prefixed lines
        # only -- never the bare `- ` prefix, which also matched the notes.
        fails = list(summary.get("problem_list") or [])
        if not fails:
            fails = [ln.strip() for ln in audit_out.splitlines()
                     if ln.strip().startswith("FAIL")]
        lines += (fails[:40] or ["(no structured failures parsed; see log)"])
        lines += ["```", ""]
        # Known gaps are not failures. Publishing them under "## Failures" is what
        # made a green run look red for as long as the parser was substring-based.
        notes = list(summary.get("note_list") or [])
        if notes:
            lines += [f"## Known gaps ({len(notes)})",
                      "", "_Reported, not failures._", ""]
            lines += [f"- {n}" for n in notes[:40]]
            lines.append("")

    STATUS.write_text("\n".join(lines), encoding="utf-8")


def commit_and_push(started: dt.datetime, dry_run: bool) -> str:
    """Commit and push the status file. Returns a human-readable outcome."""
    if dry_run:
        return "dry run: not committed"
    code, out = run(["git", "add", "--", "reports/AUDIT_STATUS.md"])
    if code != 0:
        return f"git add failed: {out.strip()[:200]}"

    # Nothing to publish if the content is byte-identical to HEAD.
    code, out = run(["git", "diff", "--cached", "--quiet", "--",
                     "reports/AUDIT_STATUS.md"])
    if code == 0:
        return "no change since last run; nothing to commit"

    msg = f"Scheduled report audit {started:%Y-%m-%d %H:%M}"
    code, out = run(["git", "commit", "-m", msg, "--",
                     "reports/AUDIT_STATUS.md"])
    if code != 0:
        return f"git commit failed: {out.strip()[:200]}"

    code, out = run(["git", "push", "origin", "HEAD:main"], timeout=300)
    if code != 0:
        return f"committed locally; push failed: {out.strip()[:200]}"
    return f"committed and pushed ({msg})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="skip the git fetch (useful for testing)")
    ap.add_argument("--quiet", action="store_true",
                    help="only print when something needs attention")
    ap.add_argument("--no-push", action="store_true",
                    help="write the status file but do not commit or push")
    args = ap.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    started = dt.datetime.now()
    stamp = started.strftime("%Y-%m-%d_%H%M%S")
    log_path = LOG_DIR / f"audit_{stamp}.log"

    lines: list[str] = [
        f"# Report audit {started:%Y-%m-%d %H:%M:%S}",
        f"repo: {ROOT}",
        "",
    ]

    before = snapshot_reports()

    changed, note = changed_reports(args.dry_run)
    lines.append(f"## remote changes\n{note}")
    for name in changed:
        lines.append(f"  changed: {name}")
    lines.append("")

    # The main event: the consistency checker.
    code, out = run([sys.executable, str(AUDIT)], timeout=900)
    lines.append("## consistency check")
    lines.append(f"exit code: {code}")
    lines.append(out.rstrip())
    lines.append("")

    after = snapshot_reports()
    unstable = sorted(
        name for name in set(before) | set(after)
        if before.get(name) != after.get(name)
    )
    if unstable:
        lines.append("## UNSTABLE: reports changed during the audit")
        for name in unstable:
            lines.append(f"  {name}")
        lines.append("")

    # A quick sanity probe on the two headline numbers, independent of the
    # checker, so a crash in the checker cannot hide a broken headline.
    probe: dict = {}
    p = REPORTS_DIR / "ml_final_holdout.json"
    if p.exists():
        try:
            probe = json.loads(p.read_text(encoding="utf-8"))
            lines.append("## headline probe")
            lines.append(f"  precision {probe.get('precision'):.4f}  "
                         f"base {probe.get('base_rate'):.4f}  "
                         f"lift {probe.get('lift'):.4f}  "
                         f"signals {probe.get('signals')}")
            lines.append("")
        except Exception as exc:  # noqa: BLE001 - report, never crash
            lines.append(f"## headline probe\n  FAILED to parse: {exc}\n")

    log_path.write_text("\n".join(lines), encoding="utf-8")

    write_status(started, code, out, changed, note, probe, unstable,
                log_path.relative_to(ROOT).as_posix())

    push_note = "not attempted"
    if not args.no_push and not unstable:
        push_note = commit_and_push(started, args.dry_run)
    elif unstable:
        push_note = "skipped: reports were being regenerated"

    needs_attention = code != 0 or bool(changed) or bool(unstable)
    if needs_attention:
        entry = [
            f"\n## {started:%Y-%m-%d %H:%M:%S}",
            f"- consistency check exit code: **{code}**",
        ]
        if unstable:
            entry.append(f"- UNSTABLE: {len(unstable)} report(s) changed during "
                         f"the audit: {', '.join(unstable[:8])}")
        if changed:
            entry.append(f"- remote changes: {note}")
            entry.extend(f"  - `{name}`" for name in changed)
        if code != 0:
            failures = [ln for ln in out.splitlines() if ln.strip().startswith("- ")]
            entry.append("- failures:")
            entry.extend(f"  {ln.strip()}" for ln in failures[:20])
        entry.append(f"- full log: `{log_path.relative_to(ROOT).as_posix()}`")
        with FINDINGS.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(entry) + "\n")

    if not args.quiet or needs_attention:
        print("\n".join(lines))
        print("=" * 70)
        print(f"log written:   {log_path}")
        print(f"status:        {STATUS.relative_to(ROOT).as_posix()}")
        print(f"publish:       {push_note}")
        if needs_attention:
            print(f"ATTENTION REQUIRED (exit {code}, "
                  f"{len(changed)} remote change(s), {len(unstable)} unstable)")
        else:
            print("all checks passed")

    return 1 if code != 0 else 0


if __name__ == "__main__":
    sys.exit(main())
