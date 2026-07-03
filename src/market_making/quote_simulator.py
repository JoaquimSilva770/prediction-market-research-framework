"""Toy bid/ask quote simulation."""

from __future__ import annotations


def _clip_probability(value: float) -> float:
    return min(1.0, max(0.0, value))


def make_inventory_skewed_quote(
    *,
    fair_value: float,
    base_spread: float,
    inventory: float = 0.0,
    inventory_skew: float = 0.0,
) -> dict[str, float]:
    """Create a synthetic quote around fair value with inventory skew.

    Positive inventory shifts quotes lower in this toy model to encourage sells.
    I use this as a public-safe illustration, not as real quoting logic.
    """

    mid = fair_value - inventory * inventory_skew
    half_spread = base_spread / 2.0
    return {
        "bid": _clip_probability(mid - half_spread),
        "ask": _clip_probability(mid + half_spread),
        "mid": _clip_probability(mid),
    }
