"""Toy signal functions for public examples.

The functions stay simple so they read as scaffolding rather than strategy
logic.
"""

from __future__ import annotations

import pandas as pd


def symmetric_threshold_signal(
    frame: pd.DataFrame,
    *,
    zscore_col: str,
    threshold: float = 1.0,
) -> pd.Series:
    """Return +1/-1/0 when a z-score crosses a toy symmetric threshold."""

    signal = pd.Series(0, index=frame.index, dtype="int64")
    signal.loc[frame[zscore_col] >= threshold] = 1
    signal.loc[frame[zscore_col] <= -threshold] = -1
    return signal


def capped_position_from_signal(
    signal: pd.Series,
    *,
    max_position: float = 1.0,
) -> pd.Series:
    """Convert a toy signal into a capped position series."""

    return signal.clip(lower=-1, upper=1).astype(float) * max_position
