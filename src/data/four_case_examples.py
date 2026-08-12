"""Deterministic illustrative inputs for the four case-study designs."""

from __future__ import annotations

import numpy as np
import pandas as pd

from case_studies import CASE_STUDY_BY_ID


CASE_SEEDS = {
    "tesla": 11,
    "bitcoin": 23,
    "crude_oil": 37,
    "federal_reserve": 53,
}


def make_case_trade_table(
    case_id: str,
    *,
    periods: int = 240,
    start: str = "2026-01-05 14:30:00+00:00",
    seed: int | None = None,
) -> pd.DataFrame:
    """Build a toy one-minute trade table for one economic mapping.

    Every timestamp has separate Yes and No rows, three displayed price levels,
    displayed size, a stale-quote measure and a rolling discrepancy signal. The
    values are generated and are not historical market observations.
    """

    if case_id not in CASE_STUDY_BY_ID:
        raise ValueError(f"unknown case_id: {case_id}")
    if periods < 40:
        raise ValueError("periods must be at least 40")

    spec = CASE_STUDY_BY_ID[case_id]
    rng = np.random.default_rng(CASE_SEEDS[case_id] if seed is None else seed)
    timestamps = pd.date_range(start=start, periods=periods, freq="1min")

    raw_return = rng.normal(0.0, 0.0016, periods)
    shock_indices = np.arange(35, periods, 47)
    raw_return[shock_indices] += rng.choice([-1.0, 1.0], len(shock_indices)) * 0.008
    adjusted_return = raw_return * spec.signal_multiplier

    update_interval = 4
    update_mask = np.arange(periods) % update_interval == 0
    response = pd.Series(adjusted_return).rolling(5, min_periods=1).sum().shift(2)
    response = response.fillna(0.0).to_numpy()
    probability_updates = np.where(update_mask, response * 2.8, 0.0)
    yes_mid = np.clip(0.50 + np.cumsum(probability_updates), 0.08, 0.92)
    yes_mid = pd.Series(np.where(update_mask, yes_mid, np.nan)).ffill().to_numpy()

    prediction_change = pd.Series(yes_mid).diff().fillna(0.0).to_numpy()
    discrepancy = adjusted_return - prediction_change
    discrepancy_series = pd.Series(discrepancy)
    past_mean = discrepancy_series.rolling(30, min_periods=10).mean().shift(1)
    past_std = discrepancy_series.rolling(30, min_periods=10).std(ddof=0).shift(1)
    rolling_deviation = (
        (discrepancy_series - past_mean) / past_std.replace(0.0, np.nan)
    ).to_numpy()

    abs_signal = np.abs(np.nan_to_num(rolling_deviation))
    trade_size = np.select(
        [abs_signal >= 3.0, abs_signal >= 2.576, abs_signal >= 2.326, abs_signal >= 1.96],
        [20.0, 15.0, 10.0, 5.0],
        default=0.0,
    )
    stale_minutes = np.arange(periods) % update_interval
    rows: list[dict[str, object]] = []
    for index, timestamp in enumerate(timestamps):
        for outcome, mid in (("Yes", yes_mid[index]), ("No", 1.0 - yes_mid[index])):
            spread = 0.018 + 0.004 * (stale_minutes[index] > 1)
            top_bid = max(mid - spread / 2.0, 0.001)
            top_ask = min(mid + spread / 2.0, 0.999)
            base_depth = 12.0 + float(rng.integers(0, 9))
            rows.append(
                {
                    "case_id": case_id,
                    "case_name": spec.case_name,
                    "linked_symbol": spec.linked_symbol,
                    "timestamp_utc": timestamp,
                    "outcome": outcome,
                    "bid_price_1": top_bid,
                    "bid_size_1": base_depth,
                    "bid_price_2": max(top_bid - 0.01, 0.001),
                    "bid_size_2": base_depth + 8.0,
                    "bid_price_3": max(top_bid - 0.02, 0.001),
                    "bid_size_3": base_depth + 16.0,
                    "ask_price_1": top_ask,
                    "ask_size_1": base_depth,
                    "ask_price_2": min(top_ask + 0.01, 0.999),
                    "ask_size_2": base_depth + 8.0,
                    "ask_price_3": min(top_ask + 0.02, 0.999),
                    "ask_size_3": base_depth + 16.0,
                    "poly_stale_mins": float(stale_minutes[index]),
                    "underlying_return_raw": raw_return[index],
                    "underlying_return_adjusted": adjusted_return[index],
                    "prediction_change": prediction_change[index],
                    "rolling_deviation": rolling_deviation[index],
                    "trade_size": trade_size[index],
                    "liquid_book": True,
                    "valid_history": bool(index >= 30),
                    "valid_holding_time": bool(index < periods - 60),
                }
            )

    return pd.DataFrame(rows).sort_values(["timestamp_utc", "outcome"]).reset_index(
        drop=True
    )


def make_all_case_trade_tables(*, periods: int = 240) -> dict[str, pd.DataFrame]:
    """Build one illustrative trade table for each case study."""

    return {
        case_id: make_case_trade_table(case_id, periods=periods)
        for case_id in CASE_STUDY_BY_ID
    }
