# Four-Case Execution Design

I use one modular execution engine across four contrasting prediction-market relationships.

## Tesla

The contract asks whether Tesla closes above $390 at the end of June 2026. TSLA one-minute closes provide the linked financial series. This is the most direct mapping, but a threshold probability still responds nonlinearly to distance from the threshold, volatility and time remaining.

## Bitcoin

The contract asks whether Bitcoin reaches a new all-time high by 30 September 2026. BTC-USD one-minute closes provide the linked series. The contract is path dependent and its resolution source and high-price rule need not match the close-price proxy.

## Crude Oil

The contract asks whether crude oil reaches a new all-time high by 30 September 2026. CL=F one-minute closes provide the linked series. Active-contract rolls, vendor differences and high-versus-close measurement prevent a perfect mapping.

## Federal Reserve

The contract asks whether the Fed raises rates by 25 basis points at the September 2026 meeting. ZT=F two-year Treasury-futures closes provide an inverse policy proxy, so linked-market returns are multiplied by -1 before constructing the discrepancy signal. Two-year futures also reflect the expected policy path, term and risk premia, and other macroeconomic information.

## Shared Engine

Every case uses the same interface:

1. Construct one-minute linked-market returns and prediction-price changes.
2. Apply the case sign convention.
3. Compare the adjusted linked-market return with the prediction-price change.
4. Standardise the discrepancy using a shifted rolling benchmark.
5. Map positive signals to Yes rows and negative signals to No rows.
6. Gate entries using quote freshness, two-sided books, price saturation and timing checks.
7. Walk displayed asks for entries and displayed bids for exits.
8. Record partial fills, residual positions, holding time, exit reason and P&L.

The public notebook uses generated inputs so it demonstrates this architecture without presenting historical performance as evidence.
