"""Small Matplotlib plotting helpers."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd


def plot_price_and_probability(
    frame: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp_utc",
    price_col: str = "underlying_price",
    probability_col: str = "prediction_price",
) -> plt.Figure:
    """Plot synthetic underlying price and prediction-market probability."""

    fig, axes = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(10, 6))
    axes[0].plot(frame[timestamp_col], frame[price_col])
    axes[0].set_title("Synthetic underlying price")
    axes[1].plot(frame[timestamp_col], frame[probability_col])
    axes[1].set_title("Synthetic prediction-market probability")
    fig.tight_layout()
    return fig

