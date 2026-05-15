import json
from datetime import datetime

import pandas as pd
import pytest

from bullet_trade.server.adapters.qmt import dataframe_to_payload


@pytest.mark.unit
def test_dataframe_to_payload_handles_datetime():
    df = pd.DataFrame(
        {
            "start_date": [pd.Timestamp("2025-01-01")],
            "end_date": [pd.NaT],
            "value": [1],
        }
    )
    payload = dataframe_to_payload(df)
    encoded = json.dumps(payload)
    assert "2025-01-01" in encoded


@pytest.mark.unit
def test_dataframe_to_payload_preserves_price_multiindex_metadata():
    df = pd.DataFrame(
        [[5.4, 5.5, 4107.5]],
        columns=pd.MultiIndex.from_tuples(
            [
                ("600635.XSHG", "open"),
                ("600635.XSHG", "close"),
                ("000001.XSHG", "close"),
            ]
        ),
    )

    payload = dataframe_to_payload(df)

    assert payload["column_tuples"] == [
        ["open", "600635.XSHG"],
        ["close", "600635.XSHG"],
        ["close", "000001.XSHG"],
    ]
    assert payload["column_index_names"] == ["field", "code"]
    assert payload["records"] == [[5.4, 5.5, 4107.5]]
