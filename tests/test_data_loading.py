import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))

import data_loading


def test_load_expected_group_keys_exact_uses_present_filtered_groups(monkeypatch):
    frames = [
        pd.DataFrame(
            [
                {
                    "model": "Model-A",
                    "topic": "book",
                    "language": "en",
                    "country_region": "united states",
                },
                {
                    "model": "Model-A",
                    "topic": "book",
                    "language": "en",
                    "country_region": "united states",
                },
                {
                    "model": "Model-A",
                    "topic": "book",
                    "language": "de",
                    "country_region": "germany",
                },
            ]
        ),
        pd.DataFrame(
            [
                {
                    "model": "Model-A",
                    "topic": "book",
                    "language": "zh",
                    "country_region": "china",
                }
            ]
        ),
    ]

    def fake_iter_makieval_parquet_frames(split, filters, columns):
        assert split == "train"
        assert filters == {"model": "Model-A", "topic": "book"}
        assert columns == data_loading.GROUP_COLUMNS
        yield from frames

    monkeypatch.setattr(
        data_loading,
        "iter_makieval_parquet_frames",
        fake_iter_makieval_parquet_frames,
    )

    groups = data_loading.load_expected_group_keys(
        filters={"model": "Model-A", "topic": "books"},
        exact=True,
    )

    assert groups == [
        ("Model-A", "book", "de", "germany"),
        ("Model-A", "book", "en", "united states"),
        ("Model-A", "book", "zh", "china"),
    ]
