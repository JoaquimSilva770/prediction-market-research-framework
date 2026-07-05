"""Rolling statistics used by synthetic examples."""

from __future__ import annotations

import pandas as pd


def add_rolling_mean_std(
    frame: pd.DataFrame,
    *,
    column: str,
    window: int,
    min_periods: int | None = None,
) -> pd.DataFrame:
    """Add rolling mean and standard deviation columns."""

    if min_periods is None:
        min_periods = window

    data = frame.copy()
    rolling = data[column].rolling(window=window, min_periods=min_periods)
    data[f"{column}_rolling_mean_{window}"] = rolling.mean()
    data[f"{column}_rolling_std_{window}"] = rolling.std(ddof=0)
    return data


def add_rolling_zscore(
    frame: pd.DataFrame,
    *,
    column: str,
    window: int,
    min_periods: int | None = None,
) -> pd.DataFrame:
    """Add a rolling z-score column.

    The z-score is generic. Public examples avoid production trigger levels and
    strategy-specific transformations.
    """

    data = add_rolling_mean_std(
        frame,
        column=column,
        window=window,
        min_periods=min_periods,
    )
    mean_col = f"{column}_rolling_mean_{window}"
    std_col = f"{column}_rolling_std_{window}"
    z_col = f"{column}_zscore_{window}"
    data[z_col] = (data[column] - data[mean_col]) / data[std_col].replace(0, pd.NA)
    return data
