# Backtesting Principles

I keep the backtesting code simple on purpose. I use it as a structure for thinking, not as a claim of profitability.

Key principles:

- Use only information available at the decision timestamp.
- Apply transaction costs and execution costs before interpreting P&L.
- Separate raw signals from actual entries taken by the simulator.
- Track exposure, open positions, closed trades, inventory, and turnover.
- Avoid day-specific or timestamp-specific rules.
- Treat stale prediction-market prices as a risk, not free signal.
- Close or explicitly report any open positions at the end of the tested window.
- Prefer robustness and explainability over maximum in-sample P&L.
