"""Timestamp alignment helpers for asynchronous market data."""

from __future__ import annotations

import pandas as pd


def align_prediction_to_underlying(
    underlying: pd.DataFrame,
    prediction: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp_utc",
    max_stale_minutes: int | None = 30,
) -> pd.DataFrame:
    """Align latest observed prediction-market row to each underlying timestamp.

    This uses a backward as-of merge: each underlying row receives the most
    recent prediction-market observation that was known at or before that time.
    A `prediction_stale_minutes` column is included so downstream analysis can
    filter or penalise stale observations explicitly.
    """

    left = underlying.copy()
    right = prediction.copy()
    left[timestamp_col] = pd.to_datetime(left[timestamp_col], utc=True)
    right[timestamp_col] = pd.to_datetime(right[timestamp_col], utc=True)

    right = right.rename(columns={timestamp_col: "prediction_timestamp_utc"})
    aligned = pd.merge_asof(
        left.sort_values(timestamp_col),
        right.sort_values("prediction_timestamp_utc"),
        left_on=timestamp_col,
        right_on="prediction_timestamp_utc",
        direction="backward",
    )
    aligned["prediction_stale_minutes"] = (
        aligned[timestamp_col] - aligned["prediction_timestamp_utc"]
    ).dt.total_seconds() / 60.0

    if max_stale_minutes is not None:
        aligned.loc[
            aligned["prediction_stale_minutes"] > max_stale_minutes,
            prediction.columns.drop(timestamp_col, errors="ignore"),
        ] = pd.NA

    return aligned


def resample_last_observation(
    frame: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp_utc",
    frequency: str = "1min",
) -> pd.DataFrame:
    """Resample a time series to regular intervals using the last observation."""

    data = frame.copy()
    data[timestamp_col] = pd.to_datetime(data[timestamp_col], utc=True)
    return (
        data.set_index(timestamp_col)
        .sort_index()
        .resample(frequency)
        .last()
        .reset_index()
    )

