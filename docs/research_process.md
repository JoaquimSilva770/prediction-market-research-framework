# Research Process

I treat prediction-market research as a data-alignment and hypothesis-testing problem, not as a search for one lucky backtest.

The workflow:

1. Define a clean research question.
2. Generate or load time series with known timestamp semantics.
3. Align observations without using future information.
4. Build rolling features using only data available at each timestamp.
5. Simulate execution with transaction costs and stale-data checks.
6. Inspect robustness before interpreting any result.

This public repo uses synthetic data so the process can be reviewed without relying on live datasets or production strategy details.

## No-Overfit Principle

I do not choose thresholds, horizons, or filters because they maximise one historical result. Serious research separates discovery, validation, and stress testing.
