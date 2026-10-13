from __future__ import annotations

import pandas as pd
import pytest

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


def test_backtest_opens_a_partial_entry_and_records_filled_size() -> None:
    rows = []
    for minute in range(3):
        timestamp = pd.Timestamp("2026-01-05 14:30:00+00:00") + pd.Timedelta(
            minutes=minute
        )
        for outcome in ["Yes", "No"]:
            row = _book_row(
                timestamp_utc=timestamp,
                outcome=outcome,
                rolling_deviation=5.0,
                trade_size=20.0 if minute == 0 else 0.0,
                ask_size_1=4.0,
                ask_size_2=6.0,
                ask_price_3=0.70,
                valid_history=True,
                valid_holding_time=True,
            ).to_dict()
            rows.append(row)

    trades, debug, remaining = run_multi_position_backtest(
        pd.DataFrame(rows),
        max_hold_minutes=100.0,
        take_profit=0.50,
        stop_loss=0.50,
    )

    assert debug["entry_taken"].any()
    assert debug.loc[debug["entry_taken"], "entry_filled_size"].iloc[0] == 10.0
    assert trades["trade_size"].sum() == 10.0
    assert remaining.empty


def test_sell_fill_uses_bid_levels_without_mutating_the_book() -> None:
    row = _book_row()
    original = row.copy(deep=True)

    fill = estimate_sell_fill(row, 15.0)

    assert fill["full_fill"] is True
    assert fill["filled_size"] == 15.0
    assert round(float(fill["avg_fill_price"]), 4) == 0.4933
    pd.testing.assert_series_equal(row, original)


def test_max_allowed_spread_respects_hard_cap() -> None:
    row = _book_row(rolling_deviation=20.0)

    allowed = max_allowed_spread(row, safe_max_spread=0.08)

    assert allowed == 0.08


@pytest.mark.parametrize("deviation, expected", [
    (-3.0, 0.05), (0.0, 0.02), (2.0, 0.04), (20.0, 0.08),
])
def test_spread_allowance_depends_on_absolute_signal(
    deviation: float, expected: float
) -> None:
    row = _book_row(rolling_deviation=deviation)
    assert max_allowed_spread(row) == pytest.approx(expected)
    row["bid_size_1"] = 1000.0
    row["ask_size_1"] = 1000.0
    row["poly_stale_mins"] = 7.0
    assert max_allowed_spread(row) == pytest.approx(expected)


def test_missing_signal_does_not_receive_a_spread_allowance() -> None:
    assert pd.isna(max_allowed_spread(_book_row(rolling_deviation=float("nan"))))


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
                    "rolling_deviation": 2.2 if minute == 0 else 0.0,
                    "poly_stale_mins": 0.0,
                    "trade_size": 5.0,
                    "liquid_book": True,
                }
            )
    frame = pd.DataFrame(rows)

    trades, debug, remaining = run_multi_position_backtest(
        frame,
        max_hold_minutes=100.0,
        take_profit=0.50,
        stop_loss=0.50,
    )

    assert len(trades) == 1
    assert trades.loc[0, "exit_reason"] == "end_of_window"
    assert debug["open_positions"].iloc[-1] == 0
    assert remaining.empty
    assert summarise_trade_ledger(trades, remaining)["closed_positions"] == 1.0


def _execution_frame(*overrides: dict[str, object]) -> pd.DataFrame:
    rows = []
    for minute, changes in enumerate(overrides):
        values = {
            "timestamp_utc": pd.Timestamp("2026-01-05 14:30:00+00:00")
            + pd.Timedelta(minutes=minute),
            "bid_size_1": 30.0,
            "bid_size_2": 0.0,
            "bid_size_3": 0.0,
            "ask_size_1": 30.0,
            "ask_size_2": 0.0,
            "ask_size_3": 0.0,
            "rolling_deviation": 3.0,
            "trade_size": 10.0,
        }
        values.update(changes)
        rows.append(_book_row(**values).to_dict())
    return pd.DataFrame(rows)


@pytest.mark.parametrize("displayed_size", [3.0, 15.0])
def test_positions_share_displayed_exit_depth(displayed_size: float) -> None:
    frame = _execution_frame({}, {}, {"trade_size": 0.0, "bid_size_1": displayed_size})
    original = frame.copy(deep=True)

    trades, debug, remaining = run_multi_position_backtest(frame, max_hold_minutes=100)

    assert trades["trade_size"].sum() == displayed_size
    assert remaining["trade_size"].sum() == 20.0 - displayed_size
    assert debug["entry_filled_size"].sum() == 20.0
    assert trades["entry_cost"].sum() + remaining["entry_cost"].sum() == pytest.approx(10.4)
    pd.testing.assert_frame_equal(frame, original)


def test_shared_depth_is_deducted_at_each_price_level() -> None:
    frame = _execution_frame({}, {}, {
        "trade_size": 0.0,
        "bid_size_1": 4.0,
        "bid_price_2": 0.49,
        "bid_size_2": 8.0,
        "bid_price_3": 0.48,
        "bid_size_3": 5.0,
    })

    trades, _, remaining = run_multi_position_backtest(frame, max_hold_minutes=100)

    assert trades["trade_size"].tolist() == [10.0, 7.0]
    assert trades["exit_value"].sum() == pytest.approx(4 * 0.50 + 8 * 0.49 + 5 * 0.48)
    assert remaining["trade_size"].sum() == 3.0


def test_final_close_does_not_reuse_depth_after_a_timed_exit() -> None:
    frame = _execution_frame({}, {"trade_size": 0.0, "bid_size_1": 3.0})

    trades, debug, remaining = run_multi_position_backtest(frame, max_hold_minutes=1)

    assert trades["trade_size"].tolist() == [3.0]
    assert trades["exit_reason"].tolist() == ["max_hold"]
    assert debug["num_exits_this_row"].iloc[-1] == 1
    assert remaining["trade_size"].tolist() == [7.0]
    assert remaining["entry_cost"].iloc[0] == pytest.approx(7 * 0.52)


def test_unfilled_exit_remains_in_exposure_and_pnl() -> None:
    frame = _execution_frame({}, {
        "trade_size": 0.0, "bid_price_1": 0.40, "bid_size_1": 0.0,
    })

    trades, debug, remaining = run_multi_position_backtest(frame, max_hold_minutes=1)
    summary = summarise_trade_ledger(trades, remaining)

    assert trades.empty
    assert debug["open_positions"].iloc[-1] == 1
    assert summary["closed_positions"] == 0
    assert summary["open_positions"] == 1
    assert summary["open_size"] == 10
    assert summary["open_cost"] == pytest.approx(5.2)
    assert summary["marked_value"] == pytest.approx(4.0)
    assert summary["realised_pnl"] == 0
    assert summary["unrealised_pnl"] == pytest.approx(-1.2)
    assert summary["total_pnl"] == pytest.approx(-1.2)
    assert pd.isna(summary["win_rate"])


@pytest.mark.parametrize("ask", [0.90, None])
def test_exit_is_not_blocked_by_a_wide_or_missing_ask(ask: float | None) -> None:
    frame = _execution_frame({}, {
        "trade_size": 0.0, "bid_price_1": 0.40, "ask_price_1": ask,
    })

    trades, _, remaining = run_multi_position_backtest(frame, max_hold_minutes=1)

    assert remaining.empty
    assert trades["exit_price"].tolist() == [0.40]
    assert trades["exit_reason"].tolist() == ["max_hold"]
    assert trades["pnl"].sum() == pytest.approx(-1.2)


@pytest.mark.parametrize("allowed_spread", [0.01, None, float("nan")])
def test_entry_uses_the_prepared_spread_allowance(allowed_spread: float | None) -> None:
    frame = _execution_frame(
        {"adjusted_max_spread": allowed_spread}, {"trade_size": 0.0},
    )
    trades, debug, remaining = run_multi_position_backtest(frame)
    assert not debug["entry_taken"].any()
    assert trades.empty and remaining.empty


@pytest.mark.parametrize("outcome, deviation, expected", [
    ("Yes", 3.0, True), ("No", -3.0, True),
    ("Yes", -3.0, False), ("No", 3.0, False), ("Yes", 0.0, False),
])
def test_entry_direction_comes_from_the_signal(
    outcome: str, deviation: float, expected: bool
) -> None:
    frame = _execution_frame(
        {"outcome": outcome, "rolling_deviation": deviation, "entry_side": "Yes"},
        {"outcome": outcome, "trade_size": 0.0},
    )
    _, debug, _ = run_multi_position_backtest(frame)
    assert bool(debug["entry_taken"].iloc[0]) == expected


def test_stop_loss_is_anchored_to_entry_bid_not_entry_cost() -> None:
    start = pd.Timestamp("2026-01-05 14:30:00+00:00")
    frame = _execution_frame(
        {"ask_price_1": 0.54},
        {"timestamp_utc": start + pd.Timedelta(minutes=10),
         "trade_size": 0.0, "bid_price_1": 0.48},
        {"timestamp_utc": start + pd.Timedelta(minutes=11),
         "trade_size": 0.0, "bid_price_1": 0.46},
    )
    trades, _, remaining = run_multi_position_backtest(
        frame, max_hold_minutes=100, force_close_at_end=False,
    )

    assert remaining.empty
    assert trades["exit_time"].tolist() == [start + pd.Timedelta(minutes=11)]
    assert trades["exit_reason"].tolist() == ["stop_loss"]
    assert trades["entry_price"].iloc[0] == pytest.approx(0.54)
    assert trades["entry_bid"].iloc[0] == pytest.approx(0.50)
    assert trades["stop_loss_price"].iloc[0] == pytest.approx(0.46)


def test_stop_loss_waits_for_activation_and_preserves_residual_thresholds() -> None:
    start = pd.Timestamp("2026-01-05 14:30:00+00:00")
    frame = _execution_frame(
        {},
        {"timestamp_utc": start + pd.Timedelta(minutes=5),
         "trade_size": 0.0, "bid_price_1": 0.45, "bid_size_1": 3.0},
        {"timestamp_utc": start + pd.Timedelta(minutes=10),
         "trade_size": 0.0, "bid_price_1": 0.45, "bid_size_1": 3.0},
        {"timestamp_utc": start + pd.Timedelta(minutes=11),
         "trade_size": 0.0, "bid_price_1": 0.47},
    )
    trades, _, remaining = run_multi_position_backtest(
        frame, max_hold_minutes=100, force_close_at_end=False,
    )

    assert trades["exit_time"].tolist() == [start + pd.Timedelta(minutes=10)]
    assert trades["trade_size"].tolist() == [3.0]
    assert remaining["trade_size"].tolist() == [7.0]
    assert remaining["entry_bid"].iloc[0] == pytest.approx(0.50)
    assert remaining["stop_loss_price"].iloc[0] == pytest.approx(0.46)
    assert remaining["take_profit_price"].iloc[0] == pytest.approx(0.72)


def test_take_profit_uses_average_fill_price_and_has_no_activation_delay() -> None:
    frame = _execution_frame(
        {"trade_size": 8.0, "ask_size_1": 4.0, "ask_size_2": 4.0},
        {"trade_size": 0.0, "bid_price_1": 0.55},
        {"trade_size": 0.0, "bid_price_1": 0.56},
    )
    trades, _, remaining = run_multi_position_backtest(
        frame, max_hold_minutes=100, take_profit=0.025, force_close_at_end=False,
    )

    assert remaining.empty
    assert trades["exit_time"].tolist() == [frame.loc[2, "timestamp_utc"]]
    assert trades["entry_price"].iloc[0] == pytest.approx(0.53)
    assert trades["take_profit_price"].iloc[0] == pytest.approx(0.555)
    assert trades["exit_reason"].tolist() == ["take_profit"]


@pytest.mark.parametrize("age", [60.0, None, -1.0])
def test_stale_quotes_cannot_fill_timed_or_final_exits(age: float | None) -> None:
    frame = _execution_frame({}, {"trade_size": 0.0, "poly_stale_mins": age})
    trades, debug, remaining = run_multi_position_backtest(frame, max_hold_minutes=1)

    assert trades.empty
    assert debug["num_exits_this_row"].sum() == 0
    assert remaining["trade_size"].tolist() == [10.0]
    assert remaining["mark_price"].isna().all()


@pytest.mark.parametrize("final_quote", [
    {"bid_price_1": None},
    {"bid_price_1": float("inf")},
    {"poly_stale_mins": 60.0},
    {"poly_stale_mins": None},
    {"poly_stale_mins": -1.0},
])
def test_missing_or_stale_marks_do_not_become_zero_pnl(final_quote: dict) -> None:
    frame = _execution_frame({}, {"trade_size": 0.0, "bid_size_1": 0.0, **final_quote})

    trades, _, remaining = run_multi_position_backtest(
        frame, max_hold_minutes=100, take_profit=10, force_close_at_end=False,
    )
    summary = summarise_trade_ledger(trades, remaining)

    assert remaining["mark_price"].isna().all()
    assert summary["open_size"] == 10
    assert summary["unmarked_positions"] == 1
    assert pd.isna(summary["marked_value"])
    assert pd.isna(summary["unrealised_pnl"])
    assert pd.isna(summary["total_pnl"])


def test_zero_bid_is_a_valid_mark() -> None:
    frame = _execution_frame({}, {"trade_size": 0.0, "bid_price_1": 0.0})
    trades, _, remaining = run_multi_position_backtest(
        frame, max_hold_minutes=100, force_close_at_end=False,
    )

    summary = summarise_trade_ledger(trades, remaining)
    assert summary["marked_value"] == 0
    assert summary["unmarked_positions"] == 0
    assert summary["total_pnl"] == pytest.approx(-5.2)


@pytest.mark.parametrize("yes_bid", [0.48, None])
def test_remaining_positions_use_their_own_outcome_marks(yes_bid: float | None) -> None:
    frame = _execution_frame(
        {},
        {"outcome": "No", "rolling_deviation": -3.0},
        {"trade_size": 0.0, "bid_price_1": yes_bid},
        {"outcome": "No", "trade_size": 0.0, "bid_price_1": 0.60},
    )

    trades, _, remaining = run_multi_position_backtest(
        frame, max_hold_minutes=100, force_close_at_end=False,
    )
    summary = summarise_trade_ledger(trades, remaining)
    marks = remaining.set_index("entry_side")

    assert trades.empty
    assert summary["open_positions"] == 2
    assert summary["open_cost"] == pytest.approx(10.4)
    assert marks.loc["Yes", "mark_timestamp"] == frame.loc[2, "timestamp_utc"]
    assert marks.loc["No", "mark_timestamp"] == frame.loc[3, "timestamp_utc"]
    assert marks.loc["No", "mark_price"] == 0.60
    if yes_bid is None:
        assert pd.isna(marks.loc["Yes", "mark_price"])
        assert summary["unmarked_positions"] == 1
        assert pd.isna(summary["total_pnl"])
    else:
        assert marks.loc["Yes", "mark_price"] == yes_bid
        assert summary["total_pnl"] == pytest.approx(0.40)


def test_partial_fills_are_summarised_by_completed_position() -> None:
    trades = pd.DataFrame([
        {"position_id": 1, "trade_size": 3.0, "pnl": 0.24, "exit_type": "partial_exit"},
        {"position_id": 1, "trade_size": 7.0, "pnl": -0.84, "exit_type": "full_exit"},
        {"position_id": 2, "trade_size": 2.0, "pnl": 0.20, "exit_type": "partial_exit"},
    ])
    remaining = pd.DataFrame([{
        "position_id": 2, "trade_size": 8.0, "entry_cost": 4.0,
        "mark_price": 0.50, "marked_value": 4.0, "unrealised_pnl": 0.0,
    }])

    summary = summarise_trade_ledger(trades, remaining)

    assert summary["closed_positions"] == 1
    assert summary["exit_fills"] == 3
    assert summary["win_rate"] == 0
    assert summary["average_pnl"] == pytest.approx(-0.60)
    assert summary["realised_pnl"] == pytest.approx(-0.40)
    assert summary["exit_volume"] == 12
    assert summary["open_positions"] == 1


def test_final_rows_are_independent_of_input_index_labels() -> None:
    frame = _execution_frame({}, {"trade_size": 0.0})
    frame.index = [0, 0]

    trades, debug, remaining = run_multi_position_backtest(frame)

    assert debug["entry_taken"].sum() == 1
    assert trades["trade_size"].sum() == 10
    assert remaining.empty


def test_duplicate_book_rows_are_rejected() -> None:
    frame = _execution_frame({})
    with pytest.raises(ValueError, match="one book row"):
        run_multi_position_backtest(pd.concat([frame, frame], ignore_index=True))


def test_empty_input_has_no_positions_or_pnl() -> None:
    frame = _execution_frame({}).iloc[:0]
    trades, debug, remaining = run_multi_position_backtest(frame)
    summary = summarise_trade_ledger(trades, remaining)

    assert trades.empty and debug.empty and remaining.empty
    assert "entry_cost" in remaining
    assert summary["closed_positions"] == summary["open_positions"] == 0
    assert summary["total_pnl"] == 0
    assert pd.isna(summary["win_rate"])
