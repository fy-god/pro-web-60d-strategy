from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


class FeatureSpecError(ValueError):
    pass


_FORBIDDEN_EXACT = {
    "code", "date", "candidate_id", "signal_date",
    "entry_open", "entry_session", "deadline", "label_end", "known_at",
    "label_known_at", "training_eligible_at", "training_eligible",
    "target_price", "risk_floor", "label_joint", "label_bull",
    "label_resolved", "outcome_class", "terminal_session", "bars_to_target",
    "forward_max_return", "forward_min_return", "future_bars",
}
_FORBIDDEN_PREFIXES = (
    "label_", "forward_", "fwd_", "future_", "target_", "outcome_", "execution_", "publication_",
)


def _forbidden(name: str) -> bool:
    low = name.lower()
    return low in _FORBIDDEN_EXACT or any(low.startswith(p) for p in _FORBIDDEN_PREFIXES)


@dataclass(frozen=True)
class FeatureSpec:
    """Explicit feature allow-list.

    The caller must enumerate feature names.  Adding metadata columns to a frame
    never makes them model inputs implicitly.
    """

    names: tuple[str, ...]
    version: str = "h504-feature-spec-v1"

    @classmethod
    def from_names(cls, names: Iterable[str], *, version: str = "h504-feature-spec-v1") -> "FeatureSpec":
        ordered = tuple(dict.fromkeys(str(x) for x in names))
        if not ordered:
            raise FeatureSpecError("feature allow-list is empty")
        bad = [x for x in ordered if _forbidden(x)]
        if bad:
            raise FeatureSpecError(f"forbidden target/metadata features: {bad}")
        return cls(ordered, version=version)

    def validate(self, frame: pd.DataFrame) -> None:
        absent = [x for x in self.names if x not in frame.columns]
        if absent:
            raise FeatureSpecError(f"declared features missing from frame: {absent}")
        bad = [x for x in self.names if _forbidden(x)]
        if bad:
            raise FeatureSpecError(f"forbidden features: {bad}")

    def select(self, frame: pd.DataFrame) -> pd.DataFrame:
        self.validate(frame)
        return frame.loc[:, list(self.names)].copy()
