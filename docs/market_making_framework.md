# Market-Making Framework

The market-making module is a toy simulator. I use it to show the moving parts of an inventory-aware quoting process without turning the repo into a production strategy.

Generic components:

- an estimated fair value
- a bid/ask spread
- an inventory state
- quote skew based on inventory pressure
- a simplified fill model
- P&L decomposition into spread capture, mark-to-market, costs, and inventory penalty

A real strategy would require deeper modelling of queue priority, adverse selection, fill probability, market microstructure, and operational constraints.
