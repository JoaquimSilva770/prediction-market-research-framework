# Execution Realism

The first version of the framework used top-of-book prices for simple examples. I extended the structure to separate signal generation from execution quality.

The execution model now treats a marketable order as a walk through displayed order-book levels:

- buys consume ask levels from the best ask upward
- sells consume bid levels from the best bid downward
- fills stop once the effective spread is wider than the row-level tolerance
- partial fills are recorded separately from full fills
- open positions are closed on the last available row for their own outcome side

The row-level spread tolerance starts with a conservative base value and can widen when the signal is stronger and displayed depth is healthier. It remains capped by a hard safety limit. This keeps the execution rule tied to market mechanics rather than fitted P&L.

The implementation is intentionally compact. It is designed to show the accounting logic behind multi-position event backtests, not to claim a live trading edge.
