from __future__ import annotations

import pandas as pd

from backtesting.event_backtester import run_position_backtest, summarise_backtest


def test_backtester_shifts_position_before_returns() -> None:
    frame = pd.DataFrame(
        {
            "price": [100.0, 110.0, 121.0],
            "position": [0.0, 1.0, 1.0],
        }
    )

    result = run_position_backtest(
        frame,
        price_col="price",
        position_col="position",
        cost_rate=0.0,
    )

    assert result.loc[1, "gross_pnl"] == 0.0
    assert round(result.loc[2, "gross_pnl"], 6) == 0.1


def test_summarise_backtest_returns_core_metrics() -> None:
    frame = pd.DataFrame(
        {
            "price": [100.0, 101.0, 100.0],
            "position": [0.0, 1.0, 0.0],
        }
    )
    result = run_position_backtest(
        frame,
        price_col="price",
        position_col="position",
        cost_rate=0.001,
    )

    summary = summarise_backtest(result)

    assert summary["rows"] == 3.0
    assert "net_pnl" in summary
    assert summary["turnover"] == 2.0

