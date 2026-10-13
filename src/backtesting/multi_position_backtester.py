"""Multi-position backtesting helpers for synthetic prediction-market examples."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def minutes_between(earlier_time: Any, later_time: Any) -> float:
    """Return elapsed minutes between two timestamp-like values."""

    earlier = pd.Timestamp(earlier_time)
    later = pd.Timestamp(later_time)
    return float((later - earlier).total_seconds() / 60)


def max_allowed_spread(
    row: pd.Series,
    *,
    base_spread: float = 0.02,
    safe_max_spread: float = 0.08,
    signal_bonus_per_z: float = 0.01,
) -> float:
    """Add a signal-proportional allowance to the base spread, subject to a cap."""

    deviation = _as_float(row.get("rolling_deviation"))
    if deviation is None:
        return np.nan
    allowed = base_spread + abs(deviation) * signal_bonus_per_z
    return float(min(allowed, safe_max_spread))


def estimate_buy_fill(
    row: pd.Series,
    trade_size: float,
    *,
    max_spread: float,
    max_levels: int = 3,
) -> dict[str, float | bool | int]:
    """Estimate a marketable buy by walking acceptable ask levels."""

    if pd.isna(max_spread) or trade_size <= 0:
        return _empty_fill()

    reference_bid = _as_float(row.get("bid_price_1"))
    if reference_bid is None:
        return _empty_fill()

    remaining = float(trade_size)
    total_cost = 0.0
    filled_size = 0.0
    levels_used = 0

    for level in range(1, max_levels + 1):
        price = _as_float(row.get(f"ask_price_{level}"))
        size = _as_float(row.get(f"ask_size_{level}"))
        if price is None or size is None or size <= 0:
            continue
        if price - reference_bid > max_spread:
            break

        fill_size = min(remaining, size)
        filled_size += fill_size
        total_cost += fill_size * price
        remaining -= fill_size
        levels_used += 1

        if remaining <= 0:
            break

    return _fill_result(filled_size, trade_size, total_cost, levels_used)


def estimate_sell_fill(
    row: pd.Series,
    trade_size: float,
    *,
    max_levels: int = 3,
    consume_depth: bool = False,
) -> dict[str, float | bool | int]:
    """Walk available bids without an entry-spread gate; optionally deduct depth."""

    if trade_size <= 0:
        return _empty_fill()

    remaining = float(trade_size)
    total_proceeds = 0.0
    filled_size = 0.0
    levels_used = 0

    for level in range(1, max_levels + 1):
        price = _as_float(row.get(f"bid_price_{level}"))
        size = _as_float(row.get(f"bid_size_{level}"))
        if price is None or size is None or size <= 0:
            continue
        fill_size = min(remaining, size)
        filled_size += fill_size
        total_proceeds += fill_size * price
        remaining -= fill_size
        levels_used += 1
        if consume_depth:
            row[f"bid_size_{level}"] = size - fill_size

        if remaining <= 0:
            break

    return _fill_result(filled_size, trade_size, total_proceeds, levels_used)


def run_multi_position_backtest(
    frame: pd.DataFrame,
    *,
    entry_z: float = 1.96,
    max_stale_minutes: float = 8.0,
    saturation_price: float = 0.99,
    allow_overnight_returns: bool = False,
    max_hold_minutes: float = 60.0,
    take_profit: float = 0.20,
    stop_loss: float = 0.04,
    stop_loss_activation_minutes: float = 10.0,
    force_close_at_end: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run a compact multi-position backtest on synthetic order-book rows.

    The input frame should contain one row per timestamp/outcome side. Entry
    direction is derived from ``rolling_deviation`` and checked against the
    row's outcome, quote freshness, book quality and timing flags. Returns exit
    fills, row diagnostics and remaining positions with indicative bid marks.
    """

    data = frame.sort_values(["timestamp_utc", "outcome"]).reset_index(drop=True)
    if data.duplicated(["timestamp_utc", "outcome"]).any():
        raise ValueError("Expected one book row per timestamp and outcome")
    open_positions: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    debug_rows: list[dict[str, Any]] = []
    next_position_id = 1
    last_books: dict[str, pd.Series] = {}

    last_outcome_indices = set(data.groupby("outcome", sort=False).tail(1).index)

    for idx, row in data.iterrows():
        last_books[row["outcome"]] = row
        # All exits on this row share the remaining displayed bid sizes.
        available_book = row.copy()
        exit_reasons: list[str] = []
        survivors: list[dict[str, Any]] = []
        entry_signal = _entry_side(
            row,
            entry_z=entry_z,
            max_stale_minutes=max_stale_minutes,
            saturation_price=saturation_price,
            allow_overnight_returns=allow_overnight_returns,
        )
        can_enter = entry_signal is not None and idx not in last_outcome_indices
        entry_taken = False
        entry_filled_size = 0.0

        for position in open_positions:
            exit_reason = _exit_reason(
                row,
                position,
                max_hold_minutes=max_hold_minutes,
                stop_loss_activation_minutes=stop_loss_activation_minutes,
                max_stale_minutes=max_stale_minutes,
            )
            if exit_reason is None:
                survivors.append(position)
                continue

            trade, remaining_position = _close_position(
                available_book,
                position,
                exit_reason=exit_reason,
                max_stale_minutes=max_stale_minutes,
            )
            if trade is None:
                survivors.append(position)
                continue

            trades.append(trade)
            exit_reasons.append(exit_reason)
            if remaining_position is not None:
                survivors.append(remaining_position)

        open_positions = survivors

        if can_enter and row["outcome"] == entry_signal:
            if "adjusted_max_spread" in row.index:
                max_spread = row["adjusted_max_spread"]
            else:
                max_spread = max_allowed_spread(row)
            fill = estimate_buy_fill(
                row,
                float(row["trade_size"]),
                max_spread=max_spread,
            )
            if float(fill["filled_size"]) > 0:
                open_positions.append(
                    {
                        "position_id": next_position_id,
                        "entry_timestamp": row["timestamp_utc"],
                        "entry_side": entry_signal,
                        "entry_price": float(fill["avg_fill_price"]),
                        "entry_bid": float(row["bid_price_1"]),
                        "stop_loss_price": float(row["bid_price_1"]) - stop_loss,
                        "take_profit_price": float(fill["avg_fill_price"]) + take_profit,
                        "trade_size": float(fill["filled_size"]),
                        "entry_cost": float(fill["total_value"]),
                        "max_spread": float(max_spread),
                    }
                )
                next_position_id += 1
                entry_taken = True
                entry_filled_size = float(fill["filled_size"])

        if force_close_at_end and idx in last_outcome_indices and open_positions:
            end_survivors: list[dict[str, Any]] = []
            for position in open_positions:
                if row["outcome"] != position["entry_side"]:
                    end_survivors.append(position)
                    continue
                trade, remaining_position = _close_position(
                    available_book,
                    position,
                    exit_reason="end_of_window",
                    max_stale_minutes=max_stale_minutes,
                )
                if trade is None:
                    end_survivors.append(position)
                    continue
                trades.append(trade)
                exit_reasons.append("end_of_window")
                if remaining_position is not None:
                    end_survivors.append(remaining_position)
            open_positions = end_survivors

        debug_rows.append(
            {
                "timestamp_utc": row["timestamp_utc"],
                "outcome": row["outcome"],
                "entry_signal": entry_signal,
                "entry_eligible": can_enter,
                "entry_taken": entry_taken,
                "entry_filled_size": entry_filled_size,
                "open_positions": len(open_positions),
                "num_exits_this_row": len(exit_reasons),
                "exit_reasons": ",".join(exit_reasons),
            }
        )

    remaining_positions = _mark_open_positions(
        open_positions, last_books, max_stale_minutes=max_stale_minutes
    )
    return pd.DataFrame(trades), pd.DataFrame(debug_rows), remaining_positions


def _entry_side(
    row: pd.Series,
    *,
    entry_z: float,
    max_stale_minutes: float,
    saturation_price: float,
    allow_overnight_returns: bool,
) -> str | None:
    """Return the outcome side permitted by the row's signal and safeguards."""

    ask = _as_float(row.get("ask_price_1"))
    bid = _as_float(row.get("bid_price_1"))
    deviation = _as_float(row.get("rolling_deviation"))
    trade_size = _as_float(row.get("trade_size"))
    valid_history = bool(row.get("valid_history", True))
    valid_holding_time = bool(row.get("valid_holding_time", True))

    valid_window = valid_history and valid_holding_time
    if allow_overnight_returns:
        valid_window = True

    if (
        ask is None
        or bid is None
        or deviation is None
        or trade_size is None
        or trade_size <= 0
        or not _quote_is_fresh(row, max_stale_minutes)
        or ask > saturation_price
        or not bool(row.get("liquid_book", False))
        or not valid_window
    ):
        return None

    signal_side: str | None = None
    if deviation >= entry_z:
        signal_side = "Yes"
    elif deviation <= -entry_z:
        signal_side = "No"

    return signal_side if row.get("outcome") == signal_side else None


def summarise_trade_ledger(
    trades: pd.DataFrame, open_positions: pd.DataFrame
) -> dict[str, float]:
    """Separate exit fills, completed-position results and outstanding exposure."""

    summary = {
        "closed_positions": 0.0,
        "exit_fills": float(len(trades)),
        "realised_pnl": 0.0,
        "average_pnl": math.nan,
        "win_rate": math.nan,
        "exit_volume": 0.0,
        "open_positions": float(len(open_positions)),
        "open_size": 0.0,
        "open_cost": 0.0,
        "unmarked_positions": 0.0,
        "marked_value": 0.0,
        "unrealised_pnl": 0.0,
        "total_pnl": 0.0,
    }
    if len(trades) > 0:
        closed_ids = trades.loc[trades["exit_type"].eq("full_exit"), "position_id"]
        position_pnl = trades.groupby("position_id")["pnl"].sum()
        closed_pnl = position_pnl.loc[position_pnl.index.isin(closed_ids)]
        summary["closed_positions"] = float(len(closed_pnl))
        summary["realised_pnl"] = float(trades["pnl"].sum())
        summary["average_pnl"] = float(closed_pnl.mean())
        summary["win_rate"] = float((closed_pnl > 0).mean())
        summary["exit_volume"] = float(trades["trade_size"].sum())
    if len(open_positions) > 0:
        summary["open_size"] = float(open_positions["trade_size"].sum())
        summary["open_cost"] = float(open_positions["entry_cost"].sum())
        summary["unmarked_positions"] = float(open_positions["mark_price"].isna().sum())
        # An unavailable mark must not become a zero valuation through sum().
        summary["marked_value"] = float(
            open_positions["marked_value"].sum(min_count=len(open_positions))
        )
        summary["unrealised_pnl"] = float(
            open_positions["unrealised_pnl"].sum(min_count=len(open_positions))
        )
    summary["total_pnl"] = summary["realised_pnl"] + summary["unrealised_pnl"]
    return summary


def _mark_open_positions(
    positions: list[dict[str, Any]],
    last_books: dict[str, pd.Series],
    *,
    max_stale_minutes: float,
) -> pd.DataFrame:
    """Mark residual positions at their own outcome's final fresh bid, if present."""

    rows = []
    for position in positions:
        book = last_books[position["entry_side"]]
        mark_price = _as_float(book.get("bid_price_1"))
        quote_age = _as_float(book.get("poly_stale_mins"))
        if (
            mark_price is None
            or not math.isfinite(mark_price)
            or not _quote_is_fresh(book, max_stale_minutes)
        ):
            mark_price = math.nan
        marked_value = position["trade_size"] * mark_price
        rows.append(
            {
                **position,
                "mark_timestamp": book["timestamp_utc"],
                "mark_stale_minutes": quote_age,
                "mark_price": mark_price,
                "marked_value": marked_value,
                "unrealised_pnl": marked_value - position["entry_cost"],
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "position_id",
            "entry_timestamp",
            "entry_side",
            "entry_price",
            "entry_bid",
            "stop_loss_price",
            "take_profit_price",
            "trade_size",
            "entry_cost",
            "max_spread",
            "mark_timestamp",
            "mark_stale_minutes",
            "mark_price",
            "marked_value",
            "unrealised_pnl",
        ],
    )


def _exit_reason(
    row: pd.Series,
    position: dict[str, Any],
    *,
    max_hold_minutes: float,
    stop_loss_activation_minutes: float,
    max_stale_minutes: float,
) -> str | None:
    if row["outcome"] != position["entry_side"]:
        return None
    if not _quote_is_fresh(row, max_stale_minutes):
        return None

    current_exit_price = _as_float(row.get("bid_price_1"))
    if current_exit_price is None:
        return None

    time_held = minutes_between(position["entry_timestamp"], row["timestamp_utc"])

    if (
        time_held >= stop_loss_activation_minutes
        and current_exit_price <= float(position["stop_loss_price"])
    ):
        return "stop_loss"
    if current_exit_price >= float(position["take_profit_price"]):
        return "take_profit"
    if time_held >= max_hold_minutes:
        return "max_hold"
    return None


def _close_position(
    row: pd.Series,
    position: dict[str, Any],
    *,
    exit_reason: str,
    max_stale_minutes: float,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not _quote_is_fresh(row, max_stale_minutes):
        return None, position
    if _as_float(row.get("bid_price_1")) is None:
        return None, position
    fill = estimate_sell_fill(
        row,
        float(position["trade_size"]),
        consume_depth=True,
    )
    filled_size = float(fill["filled_size"])
    if filled_size <= 0:
        return None, position

    exit_price = float(fill["avg_fill_price"])
    entry_price = float(position["entry_price"])
    original_size = float(position["trade_size"])
    remaining_size = original_size - filled_size
    pnl = (exit_price - entry_price) * filled_size
    trade = {
        "position_id": position["position_id"],
        "entry_time": position["entry_timestamp"],
        "exit_time": row["timestamp_utc"],
        "entry_side": position["entry_side"],
        "entry_price": float(position["entry_price"]),
        "entry_bid": float(position["entry_bid"]),
        "stop_loss_price": float(position["stop_loss_price"]),
        "take_profit_price": float(position["take_profit_price"]),
        "exit_price": exit_price,
        "trade_size": filled_size,
        "entry_cost": entry_price * filled_size,
        "exit_value": float(fill["total_value"]),
        "pnl": float(pnl),
        "time_held": minutes_between(position["entry_timestamp"], row["timestamp_utc"]),
        "exit_reason": exit_reason,
        "exit_type": "full_exit" if remaining_size <= 0 else "partial_exit",
    }

    if remaining_size <= 0:
        return trade, None

    remaining_position = position.copy()
    remaining_position["trade_size"] = remaining_size
    remaining_position["entry_cost"] = entry_price * remaining_size
    return trade, remaining_position


def _fill_result(
    filled_size: float,
    requested_size: float,
    total_value: float,
    levels_used: int,
) -> dict[str, float | bool | int]:
    avg_price = total_value / filled_size if filled_size > 0 else np.nan
    return {
        "filled_size": float(filled_size),
        "avg_fill_price": float(avg_price) if filled_size > 0 else np.nan,
        "total_value": float(total_value),
        "full_fill": bool(filled_size >= requested_size and requested_size > 0),
        "levels_used": int(levels_used),
    }


def _empty_fill() -> dict[str, float | bool | int]:
    return {
        "filled_size": 0.0,
        "avg_fill_price": np.nan,
        "total_value": 0.0,
        "full_fill": False,
        "levels_used": 0,
    }


def _quote_is_fresh(row: pd.Series, max_stale_minutes: float) -> bool:
    age = _as_float(row.get("poly_stale_mins"))
    return age is not None and 0 <= age <= max_stale_minutes


def _as_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    return number if math.isfinite(number) else None
