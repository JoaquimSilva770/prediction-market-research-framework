"""Toy transaction cost functions."""

from __future__ import annotations

import pandas as pd


def proportional_cost(turnover: pd.Series, *, cost_rate: float = 0.001) -> pd.Series:
    """Calculate simple proportional transaction costs."""

    return turnover.abs() * cost_rate

