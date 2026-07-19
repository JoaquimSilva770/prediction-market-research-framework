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
    entry_z: float = 1.96,
    signal_bonus_per_z: float = 0.01,
    depth_bonus: float = 0.01,
    stale_penalty: float = 0.005,
    desired_size_col: str = "trade_size",
) -> float:
    """Set a row-level execution-spread tolerance.

    The rule starts from a conservative base spread, adds tolerance for a
    stronger signal and healthier displayed depth, penalises stale books,
    and never exceeds a hard cap.
    """

    if not bool(row.get("liquid_book", False)):
        return np.nan

    signal_strength = abs(float(row.get("rolling_deviation", 0.0)))
    extra_signal = max(signal_strength - entry_z, 0.0) * signal_bonus_per_z

    desired_size = float(row.get(desired_size_col, 0.0) or 0.0)
    top_depth = float(row.get("bid_size_1", 0.0) or 0.0) + float(
        row.get("ask_size_1", 0.0) or 0.0
    )
    has_good_depth = desired_size > 0 and top_depth >= 2.0 * desired_size
    depth_component = depth_bonus if has_good_depth else 0.0

    stale_mins = float(row.get("poly_stale_mins", 0.0) or 0.0)
    stale_component = stale_penalty if stale_mins > 5 else 0.0

    allowed = base_spread + extra_signal + depth_component - stale_component
    allowed = max(base_spread, allowed)
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
    max_spread: float,
    max_levels: int = 3,
) -> dict[str, float | bool | int]:
    """Estimate a marketable sell by walking acceptable bid levels."""

    if pd.isna(max_spread) or trade_size <= 0:
        return _empty_fill()

    reference_ask = _as_float(row.get("ask_price_1"))
    if reference_ask is None:
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
        if reference_ask - price > max_spread:
            break

        fill_size = min(remaining, size)
        filled_size += fill_size
        total_proceeds += fill_size * price
        remaining -= fill_size
        levels_used += 1

        if remaining <= 0:
            break

    return _fill_result(filled_size, trade_size, total_proceeds, levels_used)


def run_multi_position_backtest(
    frame: pd.DataFrame,
    *,
    max_hold_minutes: float = 60.0,
    take_profit: float = 0.20,
    stop_loss: float = 0.04,
    stop_loss_activation_minutes: float = 10.0,
    force_close_at_end: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run a compact multi-position backtest on synthetic order-book rows.

    The input frame should contain one row per timestamp/outcome side and an
    ``entry_side`` column with "Yes", "No", or missing values.
    """

    data = frame.sort_values(["timestamp_utc", "outcome"]).copy()
    open_positions: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    debug_rows: list[dict[str, Any]] = []
    next_position_id = 1

    last_outcome_indices = set(data.groupby("outcome", sort=False).tail(1).index)

    for idx, row in data.iterrows():
        exit_reasons: list[str] = []
        survivors: list[dict[str, Any]] = []
        entry_side = row.get("entry_side")
        entry_signal = entry_side if entry_side in {"Yes", "No"} else None
        can_enter = entry_signal is not None and idx not in last_outcome_indices

        for position in open_positions:
            exit_reason = _exit_reason(
                row,
                position,
                max_hold_minutes=max_hold_minutes,
                take_profit=take_profit,
                stop_loss=stop_loss,
                stop_loss_activation_minutes=stop_loss_activation_minutes,
            )
            if exit_reason is None:
                survivors.append(position)
                continue

            trade = _close_position(row, position, exit_reason=exit_reason)
            if trade is None:
                survivors.append(position)
                continue

            trades.append(trade)
            exit_reasons.append(exit_reason)

        open_positions = survivors

        if can_enter and row["outcome"] == entry_signal:
            max_spread = max_allowed_spread(row)
            fill = estimate_buy_fill(
                row,
                float(row["trade_size"]),
                max_spread=max_spread,
            )
            if bool(fill["full_fill"]):
                open_positions.append(
                    {
                        "position_id": next_position_id,
                        "entry_timestamp": row["timestamp_utc"],
                        "entry_side": entry_signal,
                        "entry_price": float(fill["avg_fill_price"]),
                        "trade_size": float(fill["filled_size"]),
                        "entry_cost": float(fill["total_value"]),
                        "max_spread": float(max_spread),
                    }
                )
                next_position_id += 1

        if force_close_at_end and idx in last_outcome_indices and open_positions:
            end_survivors: list[dict[str, Any]] = []
            for position in open_positions:
                if row["outcome"] != position["entry_side"]:
                    end_survivors.append(position)
                    continue
                trade = _close_position(row, position, exit_reason="end_of_window")
                if trade is None:
                    end_survivors.append(position)
                    continue
                trades.append(trade)
                exit_reasons.append("end_of_window")
            open_positions = end_survivors

        debug_rows.append(
            {
                "timestamp_utc": row["timestamp_utc"],
                "outcome": row["outcome"],
                "entry_signal": entry_signal,
                "entry_taken": can_enter,
                "open_positions": len(open_positions),
                "num_exits_this_row": len(exit_reasons),
                "exit_reasons": ",".join(exit_reasons),
            }
        )

    return pd.DataFrame(trades), pd.DataFrame(debug_rows)


def summarise_trade_ledger(trades: pd.DataFrame) -> dict[str, float]:
    """Summarise a multi-position trade ledger."""

    summary = {
        "trades": 0.0,
        "total_pnl": 0.0,
        "average_pnl": math.nan,
        "win_rate": math.nan,
        "total_turnover": 0.0,
    }
    if len(trades) == 0:
        return summary

    summary["trades"] = float(len(trades))
    summary["total_pnl"] = float(trades["pnl"].sum())
    summary["average_pnl"] = float(trades["pnl"].mean())
    summary["win_rate"] = float((trades["pnl"] > 0).mean())
    summary["total_turnover"] = float(trades["trade_size"].sum())
    return summary


def _exit_reason(
    row: pd.Series,
    position: dict[str, Any],
    *,
    max_hold_minutes: float,
    take_profit: float,
    stop_loss: float,
    stop_loss_activation_minutes: float,
) -> str | None:
    if row["outcome"] != position["entry_side"]:
        return None

    sell_fill = estimate_sell_fill(
        row,
        float(position["trade_size"]),
        max_spread=float(position["max_spread"]),
    )
    if not bool(sell_fill["full_fill"]):
        return None

    current_exit_price = float(sell_fill["avg_fill_price"])
    time_held = minutes_between(position["entry_timestamp"], row["timestamp_utc"])

    if current_exit_price >= float(position["entry_price"]) + take_profit:
        return "take_profit"
    if (
        time_held >= stop_loss_activation_minutes
        and current_exit_price <= float(position["entry_price"]) - stop_loss
    ):
        return "stop_loss"
    if time_held >= max_hold_minutes:
        return "max_hold"
    return None


def _close_position(
    row: pd.Series,
    position: dict[str, Any],
    *,
    exit_reason: str,
) -> dict[str, Any] | None:
    fill = estimate_sell_fill(
        row,
        float(position["trade_size"]),
        max_spread=float(position["max_spread"]),
    )
    if not bool(fill["full_fill"]):
        return None

    exit_price = float(fill["avg_fill_price"])
    pnl = (exit_price - float(position["entry_price"])) * float(position["trade_size"])
    return {
        "position_id": position["position_id"],
        "entry_time": position["entry_timestamp"],
        "exit_time": row["timestamp_utc"],
        "entry_side": position["entry_side"],
        "entry_price": float(position["entry_price"]),
        "exit_price": exit_price,
        "trade_size": float(position["trade_size"]),
        "entry_cost": float(position["entry_cost"]),
        "exit_value": float(fill["total_value"]),
        "pnl": float(pnl),
        "time_held": minutes_between(position["entry_timestamp"], row["timestamp_utc"]),
        "exit_reason": exit_reason,
    }


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


def _as_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
