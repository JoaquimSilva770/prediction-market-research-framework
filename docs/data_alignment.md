# Data Alignment

Prediction-market and financial-market data often arrive on different clocks.

The alignment issues I care about:

- Prediction-market prices may update irregularly.
- Financial assets may trade only during exchange hours.
- A merged row must not use a prediction-market price that was not yet observable.
- Forward-filled values need an explicit staleness measure.
- Overnight and weekend gaps need deliberate handling.

The timestamp-alignment helpers make lookahead bias visible rather than hidden.
