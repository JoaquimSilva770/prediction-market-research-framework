from __future__ import annotations

import pandas as pd

from features.rolling_features import add_rolling_zscore


def test_add_rolling_zscore_creates_expected_columns() -> None:
    frame = pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0]})

    result = add_rolling_zscore(frame, column="value", window=2, min_periods=2)

    assert "value_rolling_mean_2" in result.columns
    assert "value_rolling_std_2" in result.columns
    assert "value_zscore_2" in result.columns
    assert pd.isna(result.loc[0, "value_zscore_2"])
    assert result.loc[1, "value_zscore_2"] == 1.0

