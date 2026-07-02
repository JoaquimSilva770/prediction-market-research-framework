from __future__ import annotations

import pandas as pd

from data.timestamp_alignment import align_prediction_to_underlying


def test_align_prediction_to_underlying_uses_last_observed_value() -> None:
    underlying = pd.DataFrame(
        {
            "timestamp_utc": pd.to_datetime(
                [
                    "2026-01-01 00:00:00+00:00",
                    "2026-01-01 00:01:00+00:00",
                    "2026-01-01 00:02:00+00:00",
                ]
            ),
            "underlying_price": [100.0, 101.0, 102.0],
        }
    )
    prediction = pd.DataFrame(
        {
            "timestamp_utc": pd.to_datetime(
                [
                    "2026-01-01 00:00:00+00:00",
                    "2026-01-01 00:02:00+00:00",
                ]
            ),
            "prediction_price": [0.40, 0.45],
        }
    )

    aligned = align_prediction_to_underlying(underlying, prediction)

    assert aligned["prediction_price"].tolist() == [0.40, 0.40, 0.45]
    assert aligned["prediction_stale_minutes"].tolist() == [0.0, 1.0, 0.0]


def test_align_prediction_to_underlying_marks_too_stale_values() -> None:
    underlying = pd.DataFrame(
        {
            "timestamp_utc": pd.to_datetime(
                ["2026-01-01 00:00:00+00:00", "2026-01-01 00:10:00+00:00"]
            ),
            "underlying_price": [100.0, 101.0],
        }
    )
    prediction = pd.DataFrame(
        {
            "timestamp_utc": pd.to_datetime(["2026-01-01 00:00:00+00:00"]),
            "prediction_price": [0.40],
        }
    )

    aligned = align_prediction_to_underlying(
        underlying,
        prediction,
        max_stale_minutes=5,
    )

    assert aligned.loc[0, "prediction_price"] == 0.40
    assert pd.isna(aligned.loc[1, "prediction_price"])

