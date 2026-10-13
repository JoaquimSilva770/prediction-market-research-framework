# Market-Making Framework

The market-making module simulates quotes, fills and inventory using generated prices. Fill probabilities and costs are illustrative, not calibrated to a real market.

Generic components:

- an estimated fair value
- a bid/ask spread
- an inventory state
- quote skew based on inventory pressure
- a simplified fill model
- P&L decomposition into spread capture, mark-to-market, costs, and inventory penalty

A real strategy would require deeper modelling of queue priority, adverse selection, fill probability, market microstructure, and operational constraints.
