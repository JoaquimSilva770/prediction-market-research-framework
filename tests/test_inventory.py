from __future__ import annotations

import pytest

from market_making.inventory import inventory_penalty, update_inventory
from market_making.quote_simulator import make_inventory_skewed_quote


def test_update_inventory_buy_and_sell() -> None:
    inventory = update_inventory(0.0, 2.0, side="buy")
    inventory = update_inventory(inventory, 0.5, side="sell")

    assert inventory == 1.5


def test_update_inventory_rejects_unknown_side() -> None:
    with pytest.raises(ValueError, match="side must be"):
        update_inventory(0.0, 1.0, side="hold")


def test_inventory_penalty_is_quadratic() -> None:
    assert inventory_penalty(2.0, penalty_rate=0.5) == 2.0


def test_quote_simulator_bounds_probability_quotes() -> None:
    quote = make_inventory_skewed_quote(
        fair_value=0.99,
        base_spread=0.10,
        inventory=-10.0,
        inventory_skew=0.01,
    )

    assert 0.0 <= quote["bid"] <= 1.0
    assert 0.0 <= quote["ask"] <= 1.0

