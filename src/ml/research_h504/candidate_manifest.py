from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

import pandas as pd

REQUIRED = ("code", "date", "recall_tier")
DEFAULT_VERSION = "lowzone-tier-v1"

@dataclass(frozen=True)
class CandidateSpec:
    min_tier: int = 1
    version: str = DEFAULT_VERSION
    decision_time: str = "close"


def _candidate_id(code: str, date: pd.Timestamp, version: str) -> str:
    raw = f"{code}|{pd.Timestamp(date).strftime('%Y-%m-%d')}|{version}".encode("utf-8")
    return sha256(raw).hexdigest()[:24]


def build_candidate_manifest(layers: pd.DataFrame, spec: CandidateSpec = CandidateSpec()) -> pd.DataFrame:
    """Build a PIT candidate ledger from causal low-zone layers only.

    This function intentionally does NOT inspect any label/outcome/entry/future columns.
    It preserves every eligible stock-session candidate; cooldown/publication is a
    downstream policy and must not mutate the natural candidate denominator.
    """
    missing = [c for c in REQUIRED if c not in layers.columns]
    if missing:
        raise ValueError(f"missing required layer columns: {missing}")
    if spec.min_tier < 1:
        raise ValueError("min_tier must be >= 1")

    src = layers.loc[:, list(REQUIRED)].copy()
    src["date"] = pd.to_datetime(src["date"], errors="raise")
    src["code"] = src["code"].astype(str).str.zfill(6)
    src["recall_tier"] = pd.to_numeric(src["recall_tier"], errors="raise").astype(int)

    out = src[src["recall_tier"] >= spec.min_tier].copy()
    out = out.sort_values(["date", "code"], kind="mergesort").reset_index(drop=True)
    out["candidate_version"] = spec.version
    out["decision_time"] = spec.decision_time
    out["candidate_known_at"] = out["date"]
    out["candidate_reason"] = f"recall_tier>={spec.min_tier}"
    out["candidate_id"] = [
        _candidate_id(code, date, spec.version)
        for code, date in zip(out["code"], out["date"], strict=True)
    ]

    cols = [
        "candidate_id", "code", "date", "candidate_known_at", "decision_time",
        "candidate_version", "candidate_reason", "recall_tier",
    ]
    out = out.loc[:, cols]
    if out["candidate_id"].duplicated().any():
        dup = out.loc[out["candidate_id"].duplicated(keep=False), ["code", "date"]]
        raise ValueError(f"duplicate candidate key(s): {dup.to_dict('records')[:5]}")
    return out


def prefix_invariant(full_layers: pd.DataFrame, cutoff, spec: CandidateSpec = CandidateSpec()) -> bool:
    """Check that adding future rows cannot rewrite candidates dated <= cutoff.

    This validates the manifest layer itself. Causality of lowzone.build_layers must
    be tested separately on its own feature implementation.
    """
    cutoff = pd.Timestamp(cutoff)
    prefix = full_layers[pd.to_datetime(full_layers["date"]) <= cutoff].copy()
    a = build_candidate_manifest(prefix, spec)
    b = build_candidate_manifest(full_layers, spec)
    b = b[b["date"] <= cutoff].reset_index(drop=True)
    return a.reset_index(drop=True).equals(b)
