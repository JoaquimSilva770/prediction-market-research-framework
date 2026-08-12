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
    entry_z: float = 1.96,
    max_stale_minutes: float = 8.0,
    saturation_price: float = 0.99,
    allow_overnight_returns: bool = False,
    max_hold_minutes: float = 60.0,
    take_profit: float = 0.20,
    stop_loss: float = 0.04,
    stop_loss_activation_minutes: float = 10.0,
    force_close_at_end: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run a compact multi-position backtest on synthetic order-book rows.

    The input frame should contain one row per timestamp/outcome side. Entry
    direction is derived from ``rolling_deviation`` and checked against the
    row's outcome, quote freshness, book quality and timing flags.
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
                take_profit=take_profit,
                stop_loss=stop_loss,
                stop_loss_activation_minutes=stop_loss_activation_minutes,
            )
            if exit_reason is None:
                survivors.append(position)
                continue

            trade, remaining_position = _close_position(
                row,
                position,
                exit_reason=exit_reason,
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
                    row,
                    position,
                    exit_reason="end_of_window",
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

    return pd.DataFrame(trades), pd.DataFrame(debug_rows)


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
    stale_minutes = _as_float(row.get("poly_stale_mins"))
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
        or stale_minutes is None
        or trade_size is None
        or trade_size <= 0
        or stale_minutes > max_stale_minutes
        or ask > saturation_price
        or not bool(row.get("liquid_book", False))
        or not valid_window
    ):
        return None

    signal_side: str | None = None
    if "entry_side" in row.index:
        explicit_side = row.get("entry_side")
        signal_side = explicit_side if explicit_side in {"Yes", "No"} else None
    elif deviation >= entry_z:
        signal_side = "Yes"
    elif deviation <= -entry_z:
        signal_side = "No"

    return signal_side if row.get("outcome") == signal_side else None


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

    current_exit_price = _as_float(row.get("bid_price_1"))
    if current_exit_price is None:
        return None

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
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    fill = estimate_sell_fill(
        row,
        float(position["trade_size"]),
        max_spread=float(position["max_spread"]),
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


def _as_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
