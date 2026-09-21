"""Launch the local research agent; never claim remote training from a Git push.

The existing scheduler can still call this file. --dry-run is read-only.
Actual Windows task limits must be checked locally; editing this file does not
change a registered task or extend an already running parent process.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parent.parent
PROMPT_FILE = REPO / 'scripts' / 'fixup_prompt.txt'
LOG_DIR = REPO / 'logs' / 'fixup'
AGENT_TIMEOUT_SECONDS = 13200
TASK = ('读取 scripts/fixup_prompt.txt 和 RESEARCH_QUICKSTART.md。'
        '你是本项目本地研究执行者。继续未完成的真实研究队列，目标单次三小时；'
        '先核验数据、预算和期限。不能因报告已读或修完一个问题就结束，'
        '不得空等或伪造训练，最后回传实际日志和执行收据。')


def _path_candidates():
    found=[]
    for name in ('dsh.cmd','dsh.exe','dsh'):
        try:
            r=subprocess.run(['where' if os.name=='nt' else 'which',name],
                             capture_output=True,text=True,timeout=30)
        except (OSError,subprocess.SubprocessError):
            continue
        if r.returncode==0:
            found.extend(Path(x.strip()) for x in r.stdout.splitlines() if Path(x.strip()).is_file())
    return found


def _generation_candidates():
    appdata=os.environ.get('APPDATA')
    if not appdata:
        return []
    root=Path(appdata)/'DSH Desktop'/'host-commands'
    return [p for name in ('dsh.cmd','dsh.exe','dsh')
            for p in root.glob(f'*/generations/*/bin/{name}') if p.is_file()]


def find_dsh():
    override=os.environ.get('DSH_BIN')
    if override:
        p=Path(override)
        return (p,'DSH_BIN') if p.is_file() else (None,'invalid-DSH_BIN')
    for source,fn in (('PATH',_path_candidates),('generation',_generation_candidates)):
        candidates=fn()
        if candidates:
            return max(candidates,key=lambda p:p.stat().st_mtime),source
    return None,'not-found'


def run_git(args,log):
    r=subprocess.run(['git',*args],cwd=str(REPO),capture_output=True,text=True,
                     encoding='utf-8',errors='replace',timeout=120,
                     env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})
    log.write(r.stdout+r.stderr); log.flush()
    return r.returncode


def sync_before_agent(log):
    status=subprocess.run(['git','status','--porcelain=v1'],cwd=str(REPO),
                          capture_output=True,text=True,timeout=30)
    if status.returncode or status.stdout.strip():
        log.write('BLOCKED_DIRTY_WORKTREE: preserve local changes; no autostash/reset.\n')
        return False
    for args in (['fetch','origin','main'],['merge','--ff-only','origin/main']):
        if run_git(args,log)!=0:
            log.write('BLOCKED_SYNC: agent was not started.\n'); return False
    return True


@contextmanager
def local_lock(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as fh:
        if fh.tell()==0:
            fh.write(b'0'); fh.flush()
        try:
            if os.name=='nt':
                import msvcrt
                fh.seek(0); msvcrt.locking(fh.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('ALREADY_RUNNING: no second agent was started') from exc
        try:
            yield
        finally:
            if os.name=='nt':
                fh.seek(0); msvcrt.locking(fh.fileno(),msvcrt.LK_UNLCK,1)
            else:
                fcntl.flock(fh.fileno(),fcntl.LOCK_UN)


def stop_owned_process(process):
    if process.poll() is not None:
        return
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],
                       capture_output=True,timeout=30)
    else:
        try:
            os.killpg(process.pid,signal.SIGTERM)
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=30)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args(argv)
    dsh,source=find_dsh()
    info={'repo':str(REPO),'dsh':str(dsh) if dsh else None,'dsh_source':source,
          'runner_timeout_seconds':AGENT_TIMEOUT_SECONDS,
          'prompt_sha256':hashlib.sha256(PROMPT_FILE.read_bytes()).hexdigest() if PROMPT_FILE.is_file() else None,
          'registered_task_timeout':'NOT_CHECKED_BY_THIS_SCRIPT'}
    if args.dry_run:
        print(json.dumps(info,ensure_ascii=False)); return 0 if dsh and info['prompt_sha256'] else 3
    if not dsh or not info['prompt_sha256']:
        print(json.dumps({'status':'BLOCKED_LOCAL_SETUP',**info},ensure_ascii=False)); return 3
    started=time.monotonic(); LOG_DIR.mkdir(parents=True,exist_ok=True)
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    with local_lock(LOG_DIR/'agent.lock'), (LOG_DIR/f'research_{stamp}.log').open('w',encoding='utf-8') as log:
        log.write(json.dumps(info,ensure_ascii=False)+'\n')
        if not sync_before_agent(log):
            return 5
        info['prompt_sha256']=hashlib.sha256(PROMPT_FILE.read_bytes()).hexdigest()
        info['started_at']=dt.datetime.now(dt.timezone.utc).isoformat()
        (LOG_DIR/'launcher_start_receipt.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
        env={**os.environ,'PYTHONPATH':str(REPO),'GIT_TERMINAL_PROMPT':'0'}
        # Preserve the previously configured local DSH execution policy.
        env.setdefault('DSH_PERMISSION_MODE','danger-full-access')
        env.setdefault('DSH_HOME',str(Path.home()/'.dsh'))
        options={'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP} if os.name=='nt' else {'start_new_session':True}
        log.flush()
        process=subprocess.Popen([str(dsh),'--profile','headless',TASK],cwd=str(REPO),
                                 env=env,stdout=log,stderr=subprocess.STDOUT,**options)
        try:
            rc=process.wait(timeout=max(1,AGENT_TIMEOUT_SECONDS-(time.monotonic()-started)))
        except (subprocess.TimeoutExpired,KeyboardInterrupt):
            stop_owned_process(process); log.write('\nSTOPPED: owned process tree terminated.\n'); return 4
        log.write(f'\nagent_exit_code={rc}\n')
        print(json.dumps({'agent_exit_code':rc,'elapsed_seconds':time.monotonic()-started,
                          'training_status':'READ_RESEARCH_EXECUTION_RECEIPT'}))
        return 0 if rc==0 else 1


if __name__=='__main__':
    raise SystemExit(main())
