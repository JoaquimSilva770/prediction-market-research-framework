from __future__ import annotations

import pandas as pd

from backtesting.multi_position_backtester import (
    estimate_buy_fill,
    estimate_sell_fill,
    max_allowed_spread,
    run_multi_position_backtest,
    summarise_trade_ledger,
)


def _book_row(**overrides: object) -> pd.Series:
    row = {
        "timestamp_utc": pd.Timestamp("2026-01-05 14:30:00+00:00"),
        "outcome": "Yes",
        "bid_price_1": 0.50,
        "bid_size_1": 10.0,
        "bid_price_2": 0.48,
        "bid_size_2": 20.0,
        "bid_price_3": 0.45,
        "bid_size_3": 20.0,
        "ask_price_1": 0.52,
        "ask_size_1": 4.0,
        "ask_price_2": 0.54,
        "ask_size_2": 10.0,
        "ask_price_3": 0.62,
        "ask_size_3": 10.0,
        "rolling_deviation": 2.2,
        "poly_stale_mins": 1.0,
        "trade_size": 8.0,
        "liquid_book": True,
    }
    row.update(overrides)
    return pd.Series(row)


def test_buy_fill_walks_only_acceptable_ask_levels() -> None:
    row = _book_row()

    fill = estimate_buy_fill(row, 8.0, max_spread=0.05)

    assert fill["full_fill"] is True
    assert fill["filled_size"] == 8.0
    assert round(float(fill["avg_fill_price"]), 4) == 0.53
    assert fill["levels_used"] == 2


def test_buy_fill_rejects_deep_level_outside_spread_limit() -> None:
    row = _book_row()

    fill = estimate_buy_fill(row, 20.0, max_spread=0.05)

    assert fill["full_fill"] is False
    assert fill["filled_size"] == 14.0


def test_sell_fill_uses_bid_levels_with_same_spread_logic() -> None:
    row = _book_row()

    fill = estimate_sell_fill(row, 15.0, max_spread=0.05)

    assert fill["full_fill"] is True
    assert fill["filled_size"] == 15.0
    assert round(float(fill["avg_fill_price"]), 4) == 0.4933


def test_max_allowed_spread_respects_hard_cap() -> None:
    row = _book_row(rolling_deviation=20.0)

    allowed = max_allowed_spread(row, safe_max_spread=0.08)

    assert allowed == 0.08


def test_multi_position_backtest_closes_each_outcome_side_at_its_own_end() -> None:
    rows = []
    for minute in range(4):
        timestamp = pd.Timestamp("2026-01-05 14:30:00+00:00") + pd.Timedelta(
            minutes=minute
        )
        for outcome in ["Yes", "No"]:
            rows.append(
                {
                    "timestamp_utc": timestamp,
                    "outcome": outcome,
                    "bid_price_1": 0.50 + minute * 0.02,
                    "bid_size_1": 20.0,
                    "bid_price_2": 0.49 + minute * 0.02,
                    "bid_size_2": 20.0,
                    "bid_price_3": 0.48 + minute * 0.02,
                    "bid_size_3": 20.0,
                    "ask_price_1": 0.52 + minute * 0.02,
                    "ask_size_1": 20.0,
                    "ask_price_2": 0.53 + minute * 0.02,
                    "ask_size_2": 20.0,
                    "ask_price_3": 0.54 + minute * 0.02,
                    "ask_size_3": 20.0,
                    "rolling_deviation": 2.2 if outcome == "Yes" else -2.2,
                    "poly_stale_mins": 0.0,
                    "trade_size": 5.0,
                    "liquid_book": True,
                    "entry_side": "Yes" if minute == 0 and outcome == "Yes" else None,
                }
            )
    frame = pd.DataFrame(rows)

    trades, debug = run_multi_position_backtest(
        frame,
        max_hold_minutes=100.0,
        take_profit=0.50,
        stop_loss=0.50,
    )

    assert len(trades) == 1
    assert trades.loc[0, "exit_reason"] == "end_of_window"
    assert debug["open_positions"].iloc[-1] == 0
    assert summarise_trade_ledger(trades)["trades"] == 1.0
