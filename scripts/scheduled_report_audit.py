"""Scheduled audit of the published GitHub reports, run every four hours.

What it does, in order:

1. Fetch the remote so the local checkout knows what is actually published.
2. Compare every tracked report against the version on ``origin/main``. If a
   report changed remotely, note it — that is "a new report appeared".
3. Run ``scripts/audit_reports.py``, which checks the arithmetic, the pooling,
   cross-report agreement, prose drift and Markdown structure.
4. Write a timestamped log under ``logs/report_audit/``.
5. If anything failed, or a report changed remotely, append a short summary to
   ``logs/report_audit/FINDINGS.md`` so there is a durable record even when
   nobody reads the individual logs.

This script never modifies reports and never pushes. It is read-only with
respect to the repository's published content: it reports, and a human (or an
agent) decides what to change. That separation is deliberate — an unattended job
that can rewrite published numbers is how wrong numbers get published.

Usage
-----
    python scripts/scheduled_report_audit.py            # normal run
    python scripts/scheduled_report_audit.py --dry-run  # skip git fetch
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs" / "report_audit"
FINDINGS = LOG_DIR / "FINDINGS.md"
AUDIT = ROOT / "scripts" / "audit_reports.py"


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="skip the git fetch (useful for testing)")
    ap.add_argument("--quiet", action="store_true",
                    help="only print when something needs attention")
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

    # A quick sanity probe on the two headline numbers, independent of the
    # checker, so a crash in the checker cannot hide a broken headline.
    probe = ROOT / "reports" / "ml_final_holdout.json"
    if probe.exists():
        try:
            d = json.loads(probe.read_text(encoding="utf-8"))
            lines.append("## headline probe")
            lines.append(f"  precision {d.get('precision'):.4f}  "
                         f"base {d.get('base_rate'):.4f}  "
                         f"lift {d.get('lift'):.4f}  "
                         f"signals {d.get('signals')}")
            lines.append("")
        except Exception as exc:  # noqa: BLE001 - report, never crash
            lines.append(f"## headline probe\n  FAILED to parse: {exc}\n")

    log_path.write_text("\n".join(lines), encoding="utf-8")

    needs_attention = code != 0 or bool(changed)
    if needs_attention:
        entry = [
            f"\n## {started:%Y-%m-%d %H:%M:%S}",
            f"- consistency check exit code: **{code}**",
            f"- remote changes: {note}",
        ]
        for name in changed:
            entry.append(f"  - `{name}`")
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
        print(f"log written: {log_path}")
        if needs_attention:
            print(f"ATTENTION REQUIRED (exit {code}, {len(changed)} remote change(s))")
        else:
            print("all checks passed, no remote changes")

    return 1 if code != 0 else 0


if __name__ == "__main__":
    sys.exit(main())
