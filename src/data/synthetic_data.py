"""Synthetic market-data generators for public examples.

The functions in this module deliberately create toy data. They are useful for
demonstrating research mechanics without exposing private datasets, market
selection, or strategy-specific parameters.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _logistic(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values))


def make_synthetic_market_data(
    *,
    start: str = "2026-01-05 14:30:00+00:00",
    periods: int = 240,
    frequency: str = "1min",
    seed: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create paired synthetic underlying and prediction-market data.

    The generated prediction series updates less frequently than the underlying
    series to make timestamp alignment and stale-price handling visible.
    """

    rng = np.random.default_rng(seed)
    timestamps = pd.date_range(start=start, periods=periods, freq=frequency)

    shocks = rng.normal(loc=0.0, scale=0.0018, size=periods)
    underlying_price = 100.0 * np.exp(np.cumsum(shocks))
    underlying = pd.DataFrame(
        {
            "timestamp_utc": timestamps,
            "underlying_price": underlying_price,
        }
    )
    underlying["underlying_return"] = np.log(
        underlying["underlying_price"] / underlying["underlying_price"].shift(1)
    ).fillna(0.0)

    update_mask = (np.arange(periods) % 5 == 0) | (rng.random(periods) < 0.08)
    prediction_timestamps = timestamps[update_mask]
    signal = pd.Series(shocks, index=timestamps).rolling(20, min_periods=5).sum()
    signal = signal.reindex(prediction_timestamps).fillna(0.0).to_numpy()
    noise = rng.normal(loc=0.0, scale=0.08, size=len(prediction_timestamps))
    probability = np.clip(_logistic(signal * 120.0 + noise), 0.01, 0.99)

    prediction = pd.DataFrame(
        {
            "timestamp_utc": prediction_timestamps,
            "prediction_price": probability,
        }
    )
    prediction["bid"] = np.clip(prediction["prediction_price"] - 0.015, 0.0, 1.0)
    prediction["ask"] = np.clip(prediction["prediction_price"] + 0.015, 0.0, 1.0)
    prediction["spread"] = prediction["ask"] - prediction["bid"]

    return underlying, prediction


def make_synthetic_event_windows(
    timestamps: pd.Series,
    *,
    event_every: int = 60,
    window_minutes: int = 20,
) -> pd.DataFrame:
    """Create toy event windows over a timestamp series."""

    ts = pd.to_datetime(timestamps).sort_values().reset_index(drop=True)
    rows: list[dict[str, object]] = []
    for event_id, start_idx in enumerate(range(0, len(ts), event_every), start=1):
        start_ts = ts.iloc[start_idx]
        end_ts = start_ts + pd.Timedelta(minutes=window_minutes)
        rows.append(
            {
                "event_id": f"synthetic_event_{event_id}",
                "event_start_utc": start_ts,
                "event_end_utc": end_ts,
            }
        )
    return pd.DataFrame(rows)

