"""Prove the fix-up agent can actually fix / commit / push -- end to end.

WHY A LOCAL BARE REMOTE
The scheduled run so far only ever proved the no-op branch (NO_NEW_REPORT). The
branch that matters -- a new report appears, the agent edits code, verifies, and
pushes -- has never executed. Testing it against the real GitHub repo would mean
publishing junk, so this builds a throwaway repo whose `origin` is a local bare
repository. A push to a bare repo exercises the same git plumbing (rebase,
non-fast-forward rejection, push) with zero blast radius.

The defect planted here is deliberately a REAL class of bug the audit reports
call out: an off-by-one `<` that should be `<=`, plus a test that does not cover
it. A correct agent must reproduce, fix, add regression coverage, and push.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

DSH = None  # resolved below


def run(args, cwd=None, env=None, timeout=900):
    completed = subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", env=env, timeout=timeout)
    return completed


def git(args, cwd):
    return run(["git", *args], cwd=cwd)


def find_dsh():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "run_fixup", r"D:\ccc\pro-web-60d-strategy\scripts\run_fixup.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.find_dsh()


fails = 0


def check(label, ok, detail=""):
    global fails
    if not ok:
        fails += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {label}{'  -> ' + detail if detail else ''}")


def main() -> int:
    global fails
    dsh, source = find_dsh()
    print(f"dsh: {dsh}\n  (found via {source})\n")
    if dsh is None:
        print("cannot locate dsh")
        return 2

    root = pathlib.Path(tempfile.mkdtemp(prefix="fixup_e2e_"))
    remote = root / "remote.git"
    work = root / "work"
    try:
        # --- throwaway origin -------------------------------------------------
        run(["git", "init", "--bare", "-b", "main", str(remote)])
        run(["git", "init", "-b", "main", str(work)])
        git(["config", "user.email", "probe@local"], work)
        git(["config", "user.name", "probe"], work)

        # A price-style module with a real off-by-one: a bar counts as a hit only
        # when it STRICTLY exceeds the target, so an exact touch is missed.
        (work / "strategy.py").write_text(
            "def hit(high, target):\n"
            "    # BUG: strict > drops bars that touch the target exactly.\n"
            "    return high > target\n",
            encoding="utf-8")
        # A weak test that passes either way -- the report's complaint.
        (work / "test_strategy.py").write_text(
            "from strategy import hit\n\n\n"
            "def test_hit_clear_exceed():\n"
            "    assert hit(10.5, 10.0) is True\n",
            encoding="utf-8")

        report_dir = work / "docs" / "audits" / "expert-ml"
        report_dir.mkdir(parents=True)
        (report_dir / "LATEST.md").write_text("LATEST\n", encoding="utf-8")
        (report_dir / "SCHEDULE.md").write_text("SCHEDULE\n", encoding="utf-8")
        (report_dir / "2026-09-19_10-00-00_JST.md").write_text(
            "# 专家/ML 轮审\n\n"
            "## P0-1 exact-touch 被漏判\n\n"
            "- 文件：`strategy.py`\n"
            "- 函数：`hit`\n"
            "- 行号：第 3 行\n"
            "- 触发条件：`high == target`\n"
            "- 机制：使用严格 `>`，等于目标价的那根K线不计入命中。\n"
            "- 影响：命中率被系统性低估。\n"
            "- 改法：改为 `>=`，并与多头标签的判定保持一致。\n"
            "- 验收测试：新增用例断言 `hit(10.0, 10.0) is True`。\n\n"
            "## P1-1 测试覆盖不足\n\n"
            "- 只有严格超过的用例，缺少相等用例。\n",
            encoding="utf-8")

        git(["add", "-A"], work)
        git(["commit", "-m", "seed: strategy + report"], work)
        git(["remote", "add", "origin", str(remote)], work)
        push0 = git(["push", "-u", "origin", "main"], work)
        check("throwaway remote seeded", push0.returncode == 0,
              push0.stderr.strip()[-120:])

        before = git(["rev-parse", "HEAD"], work).stdout.strip()

        # --- scale the prompt down to this toy repo --------------------------
        prompt = f"""你是修复执行者，不是审计者。仓库是 {work}。

1. 读 `docs/audits/expert-ml/` 下最新的报告（文件名形如 YYYY-MM-DD_HH-mm-ss_JST.md，
   忽略 LATEST.md 和 SCHEDULE.md）。这里最新的报告指出 `strategy.py` 的 `hit`
   在第 3 行用了严格 `>`，导致 `high == target` 的精确触碰被漏判为未命中。
2. 先复现：运行 `python test_strategy.py` 并确认现有测试通过（说明测试抓不住这个缺陷）。
   写一个最小脚本证明 `hit(10.0, 10.0)` 返回 False，而被期望为 True。
3. 修 `strategy.py`：把严格 `>` 改成 `>=`，并用注释说明为什么（精确触碰应计为命中）。
4. 加回归测试到 `test_strategy.py`：断言 `hit(10.0, 10.0) is True`。
5. 验证：`python -m pytest test_strategy.py -q` 必须全绿。
6. 提交并推送：
   git add strategy.py test_strategy.py
   git commit -m "fix P0-1: exact touch counted as a hit"
   git push origin HEAD:main

只改这两个文件。不要碰 docs/audits/expert-ml/。完成后简短说明改了什么。
"""
        prompt_file = root / "probe_prompt.txt"
        prompt_file.write_text(prompt, encoding="utf-8")

        env = dict(os.environ)
        env["DSH_PERMISSION_MODE"] = "danger-full-access"
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["PYTHONPATH"] = str(work)
        task = f"读取 {prompt_file} 并严格按其指示执行。"

        print("\n=== running the agent against the throwaway repo ===")
        completed = run([str(dsh), "--profile", "headless", task],
                        cwd=str(work), env=env)
        tail = [ln for ln in (completed.stdout or "").splitlines() if ln.strip()][-6:]
        for line in tail:
            print(f"    | {line[:150]}")

        print("\n=== did it actually fix, test, and push? ===")
        check("agent exited 0", completed.returncode == 0, f"code={completed.returncode}")

        code = (work / "strategy.py").read_text(encoding="utf-8")
        check("strategy.py uses >= now", ">=" in code, code.replace("\n", " / ")[:90])
        check("the strict > is gone", "high > target" not in code, "")

        tests = (work / "test_strategy.py").read_text(encoding="utf-8")
        check("regression test for exact touch added",
              "10.0, 10.0" in tests or "10.0,10.0" in tests, "")

        head = git(["rev-parse", "HEAD"], work).stdout.strip()
        check("a new commit was created", head != before, f"{before[:8]} -> {head[:8]}")

        # The decisive one: the commit must exist in the REMOTE, not just locally.
        # Compare on the subject line, not a hash prefix: `git log --oneline`
        # abbreviates to 7 characters by default while rev-parse gives 40, so a
        # slice comparison is ambiguous (an earlier draft compared 8 chars and
        # reported a false FAIL against a push that had in fact succeeded).
        remote_log = run(["git", "--git-dir", str(remote), "log",
                          "--format=%H %s", "main"]).stdout
        remote_hashes = [ln.split()[0] for ln in remote_log.splitlines() if ln.strip()]
        check("the fix reached the remote (push worked)",
              head in remote_hashes,
              remote_log.strip().replace("\n", " | ")[:200])

        # The agent must not have touched the audit directory it does not own.
        touched = git(["show", "--name-only", "--format=", "HEAD"], work).stdout.split()
        check("audit reports untouched",
              not any(t.startswith("docs/audits") for t in touched), str(touched))

        # And the tests must genuinely pass in the fixed tree.
        verdict = run([sys.executable, "-m", "pytest", "test_strategy.py", "-q"], cwd=str(work))
        check("tests pass in the fixed tree", verdict.returncode == 0,
              (verdict.stdout or "").strip().splitlines()[-1][:100] if verdict.stdout else "")

    finally:
        shutil.rmtree(root, ignore_errors=True)

    print()
    print("FULL fix/commit/push PATH VERIFIED" if fails == 0 else f"{fails} CHECK(S) FAILED")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
