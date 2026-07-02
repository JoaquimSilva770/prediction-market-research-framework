# Backtesting Principles

The backtesting code in this repository is intentionally simple. It is a structure for thinking, not a claim of profitability.

Key principles:

- Use only information available at the decision timestamp.
- Apply transaction costs before interpreting P&L.
- Track exposure, inventory, and turnover.
- Avoid day-specific or timestamp-specific rules.
- Treat stale prediction-market prices as a risk, not free signal.
- Prefer robustness and explainability over maximum in-sample P&L.

