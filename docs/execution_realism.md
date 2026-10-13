# Execution Realism

The first version of the framework used top-of-book prices for simple examples. I extended the structure to separate signal generation from execution quality.

The execution model now treats a marketable order as a walk through displayed order-book levels:

- buys consume ask levels from the best ask upward
- sells consume bid levels from the best bid downward
- entry fills stop once the effective spread is wider than the row-level tolerance
- exit fills use available bids without requiring an ask or reapplying the entry-spread limit
- partial fills are recorded separately from full fills
- residual size remains open after a partial exit
- multiple positions can remain open at the same time
- the engine attempts to close open positions on the last available row for their own outcome side

Positions share the remaining bid depth within each timestamp/outcome row, including the final close attempt. A fill reduces the size available to subsequent exits. Depth resets for the next input row; this does not model replenishment across repeated or carried-forward snapshots.

The backtest returns three tables: exit fills, row diagnostics and remaining positions. The summary counts completed positions separately from exit fills and combines a position's partial exits before calculating win rate or average P&L. Realised P&L includes all exits, including partial exits from positions that remain open. Exit volume measures shares sold, not two-sided cash turnover.

Remaining positions retain their size and cost basis. Their own outcome's final bid provides an indicative mark only when it is available and within the freshness limit. It does not assume enough depth to liquidate the full position. Total P&L combines realised and unrealised P&L; it is left missing if any remaining position cannot be marked.

The trade table supplies `adjusted_max_spread`: a base allowance plus a multiple of the absolute rolling deviation, capped at a maximum. The engine uses that column when present, otherwise it calculates the same rule. Depth determines the quantity filled; it does not increase the allowance. Quote freshness is a separate eligibility check, not a spread adjustment.

At entry, each position stores the observed bid, its average fill price and two fixed exit thresholds. The stop-loss threshold is the entry bid minus the stop-loss offset, so the initial spread is not counted as a new adverse move. It becomes active after the specified delay. The take-profit threshold is the average entry fill price plus the profit offset and has no activation delay. Exits must match the position's outcome and use a fresh bid, including final close attempts. Partial exits retain the original thresholds.

Entry direction comes from the rolling deviation and must match the row's outcome. Entries also require positive desired size, a two-sided book, acceptable freshness, the price-saturation check, liquidity and timing flags. An `entry_side` label does not override those conditions. The examples retain simplified generated signals and illustrative numerical settings rather than replaying historical trades.

The same implementation is used for all four case designs. This makes differences in payoff mapping explicit without changing the fill and position-accounting rules from case to case.

The implementation is intentionally compact. It is designed to show the accounting logic behind multi-position event backtests, not to claim a live trading edge.
