from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            h.update(block)
    return h.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')


def hash_tree(root: Path, *, suffixes: tuple[str, ...] = ('.json', '.jsonl', '.csv', '.gz', '.pkl', '.pt', '.parquet')) -> list[dict[str, Any]]:
    root = Path(root)
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return rows
    for p in sorted(root.rglob('*')):
        if not p.is_file() or (suffixes and p.suffix.lower() not in suffixes):
            continue
        try:
            rows.append({
                'path': str(p.relative_to(root)).replace('\\', '/'),
                'bytes': p.stat().st_size,
                'sha256': sha256_file(p),
            })
        except OSError:
            rows.append({'path': str(p), 'error': 'stat_or_hash_failed'})
    return rows


@dataclass
class ResearchSessionReceipt:
    out_dir: Path
    target_active_seconds: int = 10800
    normal_wall_limit_seconds: int = 12600
    hard_runner_timeout_seconds: int = 13200
    evidence_type: str = 'UNSPECIFIED'
    source_sha: str = 'UNKNOWN'
    effective_prompt_sha256: str = 'UNKNOWN'
    registered_task_timeout_seconds: int | None = None
    session_id: str | None = None
    started_wall: float = field(default_factory=time.time)
    started_mono: float = field(default_factory=time.monotonic)
    phases: list[dict[str, Any]] = field(default_factory=list)
    fits_started: int = 0
    fits_completed: int = 0
    fits_interrupted: int = 0

    def __post_init__(self):
        self.out_dir = Path(self.out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        if self.session_id is None:
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            self.session_id = f'EML-{stamp}-{os.getpid()}'
        self.write_start_receipt()

    @property
    def deadline_monotonic(self) -> float:
        return self.started_mono + float(self.normal_wall_limit_seconds)

    @property
    def elapsed_wall_seconds(self) -> float:
        return max(0.0, time.monotonic() - self.started_mono)

    def begin_phase(self, name: str, category: str) -> dict[str, Any]:
        token = {
            'name': name,
            'category': category,
            'started_at': _utc_now(),
            '_start_mono': time.monotonic(),
        }
        self.phases.append(token)
        return token

    def end_phase(self, token: dict[str, Any], *, status: str = 'COMPLETE', detail: Any = None) -> None:
        if 'elapsed_seconds' in token:
            return
        token['ended_at'] = _utc_now()
        token['elapsed_seconds'] = max(0.0, time.monotonic() - float(token.pop('_start_mono')))
        token['status'] = status
        if detail is not None:
            token['detail'] = detail
        self.write_progress_receipt()

    def count_fit(self, status: str) -> None:
        self.fits_started += 1
        if str(status).startswith('COMPLETE'):
            self.fits_completed += 1
        elif str(status).startswith('INTERRUPTED'):
            self.fits_interrupted += 1

    def phase_seconds(self) -> dict[str, float]:
        sums: dict[str, float] = {}
        for row in self.phases:
            if 'elapsed_seconds' not in row:
                continue
            sums[row['category']] = sums.get(row['category'], 0.0) + float(row['elapsed_seconds'])
        return sums

    def write_start_receipt(self) -> None:
        payload = {
            'schema_version': 1,
            'session_id': self.session_id,
            'started_at': _utc_now(),
            'pid': os.getpid(),
            'python': sys.version,
            'platform': platform.platform(),
            'source_sha': self.source_sha,
            'effective_prompt_sha256': self.effective_prompt_sha256,
            'registered_task_timeout_seconds': self.registered_task_timeout_seconds,
            'target_active_seconds': self.target_active_seconds,
            'normal_wall_limit_seconds': self.normal_wall_limit_seconds,
            'hard_runner_timeout_seconds': self.hard_runner_timeout_seconds,
            'evidence_type': self.evidence_type,
            'argv': sys.argv,
        }
        write_json(self.out_dir / 'local_start_receipt.json', payload)

    def write_progress_receipt(self) -> None:
        payload = {
            'schema_version': 1,
            'session_id': self.session_id,
            'updated_at': _utc_now(),
            'elapsed_wall_seconds': self.elapsed_wall_seconds,
            'fits_started': self.fits_started,
            'fits_completed': self.fits_completed,
            'fits_interrupted': self.fits_interrupted,
            'phase_seconds': self.phase_seconds(),
            'phases': self.phases,
        }
        write_json(self.out_dir / 'session_progress.json', payload)

    def finalize(self, *, stop_reason: str, result_status: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        phase_seconds = self.phase_seconds()
        # Effective research excludes categories that are explicitly waiting/admin-only.
        excluded = {'idle', 'network_wait', 'git', 'markdown', 'llm_wait'}
        effective = sum(v for k, v in phase_seconds.items() if k not in excluded)
        training_seconds = sum(v for k, v in phase_seconds.items() if k in {'training_h504', 'training_aux', 'training_mlp', 'training_tcn'})
        real_training = training_seconds if self.evidence_type in {'REAL_MARKET', 'AUX_REAL_HISTORY'} else 0.0
        synthetic_training = training_seconds if self.evidence_type == 'SYNTHETIC' else 0.0
        payload: dict[str, Any] = {
            'schema_version': 1,
            'session_id': self.session_id,
            'ended_at': _utc_now(),
            'stop_reason': stop_reason,
            'result_status': result_status,
            'target_active_seconds': self.target_active_seconds,
            'normal_wall_limit_seconds': self.normal_wall_limit_seconds,
            'hard_runner_timeout_seconds': self.hard_runner_timeout_seconds,
            'elapsed_wall_seconds': self.elapsed_wall_seconds,
            'effective_seconds': effective,
            'target_met': effective >= self.target_active_seconds,
            'phase_seconds': phase_seconds,
            'data_compute_seconds': float(phase_seconds.get('data_compute', 0.0)),
            'test_analysis_seconds': float(phase_seconds.get('test_analysis', 0.0)),
            'real_train_seconds': float(real_training),
            'synthetic_train_seconds': float(synthetic_training),
            'idle_seconds': float(phase_seconds.get('idle', 0.0) + phase_seconds.get('network_wait', 0.0) + phase_seconds.get('llm_wait', 0.0)),
            'fits_started': self.fits_started,
            'fits_completed': self.fits_completed,
            'fits_interrupted': self.fits_interrupted,
            'evidence_type': self.evidence_type,
            'artifacts': hash_tree(self.out_dir),
            'phases': self.phases,
        }
        if extra:
            payload['extra'] = extra
        write_json(self.out_dir / 'execution_receipt.json', payload)
        return payload
