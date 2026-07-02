"""Inventory bookkeeping for toy market-making examples."""

from __future__ import annotations


def update_inventory(current_inventory: float, fill_size: float, *, side: str) -> float:
    """Update inventory after a synthetic fill.

    `side` is from the market maker's perspective: buying increases inventory
    and selling decreases inventory.
    """

    if side not in {"buy", "sell"}:
        raise ValueError("side must be 'buy' or 'sell'")
    direction = 1.0 if side == "buy" else -1.0
    return current_inventory + direction * fill_size


def inventory_penalty(inventory: float, *, penalty_rate: float = 0.01) -> float:
    """Quadratic toy penalty for carrying inventory."""

    return penalty_rate * inventory**2

