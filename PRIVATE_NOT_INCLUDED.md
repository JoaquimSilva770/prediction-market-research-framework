# Private Components Not Included

I keep this repo synthetic and public-safe. It does not copy private strategy code, live data, exact case-study results, or internal research outputs.

## Excluded Data

| Original Path | Reason Excluded | Sensitivity |
|---|---|---|
| `data/raw/` | Real market-data exports and case-study inputs | High |
| `data/outputs/` | Derived markouts, joined datasets, and result tables | High |
| `data/live/` | Live/paper-trading database artifacts | High |

## Excluded Signal Logic

| Original Path | Reason Excluded | Sensitivity |
|---|---|---|
| `src/config.py` | Exact market identifiers, horizons, and research parameters | High |
| `src/analysis/aggressive_markout.py` | Monetisation and markout workflow from private research | High |
| `notebooks/` | Real case-study analysis and strategy construction notebooks | High |

## Excluded Backtests / Results

| Original Path | Reason Excluded | Sensitivity |
|---|---|---|
| `reports/` | Private result interpretation, hit rates, and strategy viability notes | High |
| `reports/assets/` | Plots produced from private research data | High |

## Excluded Startup IP

| Original Path | Reason Excluded | Sensitivity |
|---|---|---|
| `src/live/` | Live collection, signal-engine, dashboard, and paper-execution structure | High |
| `src/agent/` | Market-discovery and research-agent workflow | High |

## Excluded Credentials / Config

| Original Path | Reason Excluded | Sensitivity |
|---|---|---|
| `.env` and environment-specific configs | Credentials and local settings are never public | High |
| Any API-key plumbing from private workflows | Not required for synthetic public examples | Medium |
