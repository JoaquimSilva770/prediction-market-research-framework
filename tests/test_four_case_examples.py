from __future__ import annotations

import pandas as pd
import pytest

from backtesting.multi_position_backtester import run_multi_position_backtest
from case_studies import CASE_STUDY_BY_ID, case_study_table
from data.four_case_examples import make_all_case_trade_tables, make_case_trade_table


EXPECTED_CASES = {"tesla", "bitcoin", "crude_oil", "federal_reserve"}


def test_case_study_table_contains_four_distinct_mappings() -> None:
    cases = case_study_table()

    assert set(cases["case_id"]) == EXPECTED_CASES
    assert cases["linked_symbol"].nunique() == 4
    assert CASE_STUDY_BY_ID["federal_reserve"].signal_multiplier == -1.0
    assert (cases.loc[cases["case_id"] != "federal_reserve", "signal_multiplier"] == 1.0).all()


@pytest.mark.parametrize("case_id", sorted(EXPECTED_CASES))
def test_case_trade_table_has_two_sides_and_three_book_levels(case_id: str) -> None:
    table = make_case_trade_table(case_id, periods=80)

    assert len(table) == 160
    assert set(table["outcome"]) == {"Yes", "No"}
    assert table.groupby("timestamp_utc")["outcome"].nunique().eq(2).all()
    for side in ("bid", "ask"):
        for level in (1, 2, 3):
            assert f"{side}_price_{level}" in table
            assert f"{side}_size_{level}" in table
    assert isinstance(table["timestamp_utc"].dtype, pd.DatetimeTZDtype)


def test_all_four_cases_run_through_the_same_engine() -> None:
    tables = make_all_case_trade_tables(periods=100)

    assert set(tables) == EXPECTED_CASES
    for table in tables.values():
        trades, debug = run_multi_position_backtest(table, max_hold_minutes=20)
        assert len(debug) == len(table)
        assert debug["open_positions"].iloc[-1] == 0
        assert set(trades.columns).issuperset(
            {"entry_side", "entry_price", "exit_price", "trade_size", "pnl"}
        )
