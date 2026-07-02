# Prediction Market Research Framework

A sanitised research framework for studying information transmission between financial markets and prediction markets.

This repository is designed as a public, recruiter-facing version of private prediction-market research work. It demonstrates data handling, timestamp alignment, rolling feature construction, event-driven backtesting structure, transaction-cost modelling, and inventory-aware market-making concepts using synthetic data only.

It does not contain a live trading strategy, private datasets, market-selection logic, exact thresholds, sizing rules, coefficients, or realised performance.

## Research Question

Can movements in related financial markets provide useful information about the pricing of prediction-market contracts around discrete events?

The public version focuses on the research process rather than any deployable edge:

- aligning asynchronous market data safely
- handling stale prediction-market observations
- building rolling statistics without lookahead bias
- modelling transaction costs and spread-aware execution
- testing simple event-driven trade mechanics
- tracking inventory and exposure in a market-making setting
- documenting limitations before interpreting results

## What This Repo Demonstrates

- Python market-data handling with `pandas` and `numpy`
- timestamp-safe joins between synthetic financial and prediction-market data
- rolling mean, rolling volatility, and placeholder z-score scaffolding
- intentionally simple placeholder signals
- event-driven backtesting structure
- transaction-cost and slippage-aware P&L accounting
- capped exposure and inventory bookkeeping
- market-making simulator skeleton
- research hygiene around overfitting, stale data, and lookahead bias

## What Is Intentionally Excluded

The private research project contains material that is not appropriate for a public CV repository. This repo excludes:

- exact live signals
- exact thresholds or trigger values
- exact position-sizing rules
- exact market-selection logic
- private datasets
- raw market-data exports
- live or historical strategy performance
- hit rates, Sharpe ratios, or private P&L
- startup-specific internal code
- credentials, API keys, or private endpoints

See [PRIVATE_NOT_INCLUDED.md](PRIVATE_NOT_INCLUDED.md) for the public exclusion ledger.

## Repository Layout

```text
prediction-market-research-framework/
  docs/                 Research-process notes and methodology
  notebooks/            Synthetic notebooks, added progressively
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

The notebooks use generated data and are safe to run without credentials:

1. `notebooks/01_synthetic_prediction_market_signal.ipynb`: asynchronous market alignment, rolling features, placeholder signals, and toy P&L.
2. `notebooks/02_synthetic_event_backtest.ipynb`: event windows, one-position-at-a-time trade logging, transaction costs, and validation split structure.
3. `notebooks/03_market_making_backtester_skeleton.ipynb`: synthetic fair value, bid/ask quoting, fills, inventory, costs, and mark-to-market accounting.

## Disclaimer

This repository is educational and sanitised. It is not investment advice, not a live trading system, and not a deployable strategy. The examples use synthetic data and intentionally simple placeholder logic to demonstrate research structure without disclosing proprietary work.
