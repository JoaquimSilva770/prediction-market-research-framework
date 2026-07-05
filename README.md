# Prediction Market Research Framework

A public research framework for studying information transmission between financial markets and prediction markets.

I built this to show the engineering and research mechanics behind my prediction-market work: data handling, timestamp alignment, rolling features, event-driven backtesting, transaction costs, and inventory-aware market-making concepts.

All examples use synthetic data. The repo is designed to show the research process rather than a deployable trading strategy.

## Research Question

Can movements in related financial markets provide useful information about the pricing of prediction-market contracts around discrete events?

I focus on the research process rather than any deployable edge:

- aligning asynchronous market data safely
- handling stale prediction-market observations
- building rolling statistics without lookahead bias
- modelling transaction costs and spread-aware execution
- testing simple event-driven trade mechanics
- tracking inventory and exposure in a market-making setting
- documenting limitations before interpreting results

## What I Show Here

- Python market-data handling with `pandas` and `numpy`
- timestamp-safe joins between synthetic financial and prediction-market data
- rolling mean, rolling volatility, and z-score feature scaffolding
- simple example signals
- event-driven backtesting structure
- transaction-cost and slippage-aware P&L accounting
- capped exposure and inventory bookkeeping
- market-making simulator skeleton
- research hygiene around overfitting, stale data, and lookahead bias

## Scope

This repo is intentionally limited to public-safe research mechanics. It does not include:

- live trading or order-placement code
- API keys, credentials, or authenticated endpoints
- real market-data exports
- production strategy parameters
- market-selection rules
- realised strategy performance

## Repository Layout

```text
prediction-market-research-framework/
  docs/                 Research-process notes and methodology
  notebooks/            Synthetic notebooks
  src/                  Reusable synthetic research modules
  tests/                Unit tests for core mechanics
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the tests:

```bash
PYTHONPATH=src pytest
```

## Example Usage

```python
from data.synthetic_data import make_synthetic_market_data
from data.timestamp_alignment import align_prediction_to_underlying
from features.rolling_features import add_rolling_zscore

underlying, prediction = make_synthetic_market_data(seed=7)
aligned = align_prediction_to_underlying(underlying, prediction)
features = add_rolling_zscore(aligned, column="underlying_return", window=30)
```

## Notebooks

The notebooks use generated data and run without credentials:

1. `notebooks/01_synthetic_prediction_market_signal.ipynb`: asynchronous market alignment, rolling features, example signals, and toy P&L.
2. `notebooks/02_synthetic_event_backtest.ipynb`: event windows, one-position-at-a-time trade logging, transaction costs, and validation split structure.
3. `notebooks/03_market_making_backtester_skeleton.ipynb`: synthetic fair value, bid/ask quoting, fills, inventory, costs, and mark-to-market accounting.

## Disclaimer

I present this as an educational research framework. It is not investment advice, not a live trading system, and not a deployable strategy. The examples use synthetic data and simple example logic so the research structure is visible without relying on live market data.
