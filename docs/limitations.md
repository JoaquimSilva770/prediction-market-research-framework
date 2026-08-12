# Limitations

I use generated examples only.

The four named cases are illustrative economic designs, not empirical results. Their generated order books do not reproduce the markets' liquidity, update frequency or return distributions.

The mappings are also imperfect. Tesla is a terminal threshold, Bitcoin and crude oil are monitored barriers with source differences, and the Treasury-futures series is an indirect inverse proxy for the Federal Reserve decision. They should not be pooled as interchangeable observations.

This does not prove that a prediction-market strategy works. It does not include live execution, real market selection, production thresholds, or realised trading performance. The point is to show clean research mechanics and good judgement around how to test this kind of idea.

Public-safe extensions that fit this repo:

- richer synthetic data generators
- more explicit walk-forward validation examples
- notebooks with explanatory charts
- additional tests for edge cases around stale data and trading-session gaps
