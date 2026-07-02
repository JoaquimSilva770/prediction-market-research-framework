"""A small event-driven backtester skeleton for synthetic data."""

from __future__ import annotations

import pandas as pd

from backtesting.costs import proportional_cost


def run_position_backtest(
    frame: pd.DataFrame,
    *,
    price_col: str,
    position_col: str,
    cost_rate: float = 0.001,
) -> pd.DataFrame:
    """Backtest a position series against a price series.

    Positions are shifted by one row before applying returns to avoid allowing a
    signal and the execution price move to happen in the same instant.
    """

    data = frame.copy()
    data["return"] = data[price_col].pct_change().fillna(0.0)
    data["held_position"] = data[position_col].shift(1).fillna(0.0)
    data["gross_pnl"] = data["held_position"] * data["return"]
    data["turnover"] = data[position_col].diff().abs().fillna(data[position_col].abs())
    data["cost"] = proportional_cost(data["turnover"], cost_rate=cost_rate)
    data["net_pnl"] = data["gross_pnl"] - data["cost"]
    data["equity_curve"] = data["net_pnl"].cumsum()
    return data


def summarise_backtest(backtest: pd.DataFrame) -> dict[str, float]:
    """Summarise a synthetic backtest without overclaiming."""

    return {
        "rows": float(len(backtest)),
        "gross_pnl": float(backtest["gross_pnl"].sum()),
        "net_pnl": float(backtest["net_pnl"].sum()),
        "turnover": float(backtest["turnover"].sum()),
        "max_drawdown": float(
            (backtest["equity_curve"] - backtest["equity_curve"].cummax()).min()
        ),
    }

