# Market-Making Framework

The public market-making module is a toy simulator. It demonstrates the moving parts of an inventory-aware quoting process without publishing private quoting logic.

Generic components:

- an estimated fair value
- a bid/ask spread
- an inventory state
- quote skew based on inventory pressure
- a simplified fill model
- P&L decomposition into spread capture, mark-to-market, costs, and inventory penalty

Any real strategy would require deeper modelling of queue priority, adverse selection, fill probability, market microstructure, and operational constraints.

