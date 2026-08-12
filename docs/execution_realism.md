# Execution Realism

The first version of the framework used top-of-book prices for simple examples. I extended the structure to separate signal generation from execution quality.

The execution model now treats a marketable order as a walk through displayed order-book levels:

- buys consume ask levels from the best ask upward
- sells consume bid levels from the best bid downward
- fills stop once the effective spread is wider than the row-level tolerance
- partial fills are recorded separately from full fills
- residual size remains open after a partial exit
- multiple positions can remain open at the same time
- the engine attempts to close open positions on the last available row for their own outcome side

The row-level spread tolerance starts with a conservative base value and can widen when the signal is stronger and displayed depth is healthier. It remains capped by a hard safety limit. This keeps the execution rule tied to market mechanics rather than fitted P&L.

The same implementation is used for all four case designs. This makes differences in payoff mapping explicit without changing the fill and position-accounting rules from case to case.

The implementation is intentionally compact. It is designed to show the accounting logic behind multi-position event backtests, not to claim a live trading edge.
