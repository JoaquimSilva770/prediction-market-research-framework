# Data Alignment

Prediction-market and financial-market data often arrive on different clocks.

Important alignment issues:

- Prediction-market prices may update irregularly.
- Financial assets may trade only during exchange hours.
- A merged row must not use a prediction-market price that was not yet observable.
- Forward-filled values should carry an explicit staleness measure.
- Overnight and weekend gaps should be handled deliberately.

This repo includes timestamp-alignment helpers for synthetic examples. They are designed to make lookahead bias visible rather than hidden.

