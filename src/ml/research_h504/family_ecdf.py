from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class FrozenFamilyECDF:
    """Train-only empirical CDF transformer for de-duplicated expert families."""

    fitted_: dict[str, np.ndarray] | None = None

    def fit(self, frame: pd.DataFrame, family_columns: dict[str, str]) -> "FrozenFamilyECDF":
        fitted = {}
        for family, col in family_columns.items():
            x = pd.to_numeric(frame[col], errors="coerce").to_numpy(float)
            x = np.sort(x[np.isfinite(x)])
            if len(x):
                fitted[str(family)] = x
        self.fitted_ = fitted
        return self

    def transform(self, frame: pd.DataFrame, family_columns: dict[str, str]) -> pd.DataFrame:
        if self.fitted_ is None:
            raise RuntimeError("ECDF is not fitted")
        out = pd.DataFrame(index=frame.index)
        for family, col in family_columns.items():
            train = self.fitted_.get(str(family))
            x = pd.to_numeric(frame[col], errors="coerce").to_numpy(float)
            q = np.full(len(x), np.nan)
            if train is not None and len(train):
                ok = np.isfinite(x)
                q[ok] = np.searchsorted(train, x[ok], side="right") / len(train)
            out[f"family_q__{family}"] = q
        qcols = list(out.columns)
        coverage = out[qcols].notna().mean(axis=1)
        support = 1.0 / (1.0 + np.exp(-(out[qcols] - 0.75) / 0.10))
        out["meb"] = support.mean(axis=1, skipna=True)
        out["family_coverage"] = coverage
        out["family_support_count_75"] = (out[qcols] >= 0.75).sum(axis=1)
        out["family_support_count_90"] = (out[qcols] >= 0.90).sum(axis=1)
        out["family_dominance"] = out[qcols].max(axis=1, skipna=True) - out[qcols].median(axis=1, skipna=True)
        return out
