"""Load and clean the Raoyuan/MAKIEval Hugging Face dataset."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from typing import Any

import pandas as pd
import requests

EXCLUDED_ENTITY_TYPES = frozenset(
    {"place", "person_name", "listener_name", "reader_name"}
)

DEFAULT_COLUMNS = [
    "model",
    "topic",
    "language",
    "country_region",
    "prompt",
    "generated_text",
    "entities",
]

GROUP_COLUMNS = ["model", "topic", "language", "country_region"]

COUNTRY_ALIASES = {
    "us": "united states",
    "usa": "united states",
    "u.s.": "united states",
    "united states": "united states",
    "uk": "united kingdom",
    "u.k.": "united kingdom",
    "united kingdom": "united kingdom",
    "uae": "united arab emirates",
    "united arab emirates": "united arab emirates",
}

TOPIC_ALIASES = {
    "books": "book",
}


@dataclass
class ParseReport:
    total_rows: int
    parse_errors: int
    empty_entity_rows: int
    excluded_entity_count: int


def parse_entities_field(raw_entities: Any) -> tuple[list[dict[str, Any]], bool]:
    """
    Parse the entities column into a list of dicts.

    Returns (entities, ok) where ok is False when the raw value could not be parsed.
    """
    if raw_entities is None:
        return [], False

    if isinstance(raw_entities, list):
        return raw_entities, True

    if isinstance(raw_entities, str):
        text = raw_entities.strip()
        if not text:
            return [], True
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return [], False
        if isinstance(parsed, list):
            return parsed, True
        return [], False

    return [], False


def filter_entities_for_metrics(
    entities: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Drop entity types excluded from metric computation."""
    kept: list[dict[str, Any]] = []
    excluded = 0
    for entity in entities:
        entity_type = str(entity.get("entity_type", "")).lower()
        if entity_type in EXCLUDED_ENTITY_TYPES:
            excluded += 1
            continue
        kept.append(entity)
    return kept, excluded


def clean_entities_column(df: pd.DataFrame) -> tuple[pd.DataFrame, ParseReport]:
    """Parse entities JSON and attach metric-eligible entity lists."""
    parsed_entities: list[list[dict[str, Any]]] = []
    parse_errors = 0
    empty_rows = 0
    excluded_total = 0

    for raw in df["entities"]:
        entities, ok = parse_entities_field(raw)
        if not ok:
            parse_errors += 1
            parsed_entities.append([])
            continue
        if not entities:
            empty_rows += 1
        filtered, excluded = filter_entities_for_metrics(entities)
        excluded_total += excluded
        parsed_entities.append(filtered)

    result = df.copy()
    result["entities_parsed"] = parsed_entities
    report = ParseReport(
        total_rows=len(df),
        parse_errors=parse_errors,
        empty_entity_rows=empty_rows,
        excluded_entity_count=excluded_total,
    )
    return result, report


def _filter_tuples(filters: dict[str, str] | None) -> list[tuple[str, str, str]] | None:
    if not filters:
        return None
    return [(column, "==", value) for column, value in filters.items()]


def normalize_filters(filters: dict[str, str] | None) -> dict[str, str] | None:
    """Normalize user-facing filter aliases to Hugging Face column values."""
    if not filters:
        return None

    normalized = dict(filters)
    if "topic" in normalized:
        topic = normalized["topic"].strip().lower()
        normalized["topic"] = TOPIC_ALIASES.get(topic, topic)
    if "language" in normalized:
        normalized["language"] = normalized["language"].strip().lower()
    if "country_region" in normalized:
        country = " ".join(normalized["country_region"].strip().lower().split())
        normalized["country_region"] = COUNTRY_ALIASES.get(country, country)
    return normalized


def _hf_parquet_urls(split: str) -> list[str]:
    response = requests.get(
        "https://datasets-server.huggingface.co/parquet",
        params={"dataset": "Raoyuan/MAKIEval"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return [
        item["url"]
        for item in payload.get("parquet_files", [])
        if item.get("config") == "default" and item.get("split") == split
    ]


@lru_cache(maxsize=8)
def _hf_group_column_values(split: str) -> dict[str, list[str]]:
    response = requests.get(
        "https://datasets-server.huggingface.co/statistics",
        params={
            "dataset": "Raoyuan/MAKIEval",
            "config": "default",
            "split": split,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    values: dict[str, list[str]] = {}
    for item in payload.get("statistics", []):
        column_name = item.get("column_name")
        if column_name not in GROUP_COLUMNS:
            continue
        frequencies = item.get("column_statistics", {}).get("frequencies", {})
        values[column_name] = sorted(frequencies)
    return values


def _load_from_parquet(
    split: str,
    filters: dict[str, str] | None,
    limit: int | None,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    if columns is None:
        columns = DEFAULT_COLUMNS
    frames: list[pd.DataFrame] = []

    for shard in iter_makieval_parquet_frames(
        split=split,
        filters=filters,
        columns=columns,
    ):
        if shard.empty:
            continue
        frames.append(shard)
        if limit is not None and sum(len(frame) for frame in frames) >= limit:
            break

    if not frames:
        return pd.DataFrame(columns=columns)

    df = pd.concat(frames, ignore_index=True)
    if limit is not None:
        df = df.head(limit)
    return df


def iter_makieval_parquet_frames(
    split: str = "train",
    filters: dict[str, str] | None = None,
    columns: list[str] | None = None,
):
    """Yield filtered MAKIEval parquet shards as pandas DataFrames."""
    if columns is None:
        columns = DEFAULT_COLUMNS
    normalized_filters = normalize_filters(filters)
    parquet_filters = _filter_tuples(normalized_filters)

    for url in _hf_parquet_urls(split):
        yield pd.read_parquet(
            url,
            engine="pyarrow",
            columns=columns,
            filters=parquet_filters,
        )


def load_expected_group_keys(
    split: str = "train",
    filters: dict[str, str] | None = None,
    exact: bool = False,
) -> list[tuple[str, str, str, str]]:
    """Return expected group keys for the given filters.

    By default this uses HF Dataset Viewer statistics to build a fast group
    cross-product. Set exact=True for a slower filtered parquet scan of present keys.
    """
    normalized_filters = normalize_filters(filters)
    if not exact:
        column_values = _hf_group_column_values(split)
        values_by_column = []
        for column in GROUP_COLUMNS:
            if normalized_filters and normalized_filters.get(column):
                values_by_column.append([normalized_filters[column]])
            else:
                values_by_column.append(column_values.get(column, []))
        return [tuple(group) for group in product(*values_by_column)]

    groups: set[tuple[str, str, str, str]] = set()
    for shard in iter_makieval_parquet_frames(
        split=split,
        filters=normalized_filters,
        columns=GROUP_COLUMNS,
    ):
        if shard.empty:
            continue
        unique = shard.drop_duplicates(GROUP_COLUMNS).sort_values(GROUP_COLUMNS)
        groups.update(
            tuple(row)
            for row in unique[GROUP_COLUMNS].itertuples(index=False, name=None)
        )
    return sorted(groups)


def load_makieval_dataset(
    split: str = "train",
    streaming: bool | None = None,
    filters: dict[str, str] | None = None,
    limit: int | None = None,
) -> tuple[pd.DataFrame, ParseReport]:
    """
    Load Raoyuan/MAKIEval from Hugging Face and return a cleaned DataFrame.

    filters may include model, topic, language, country_region keys matching dataset columns.
    Uses filtered parquet reads when filters are provided, and streaming otherwise.
    """
    normalized_filters = normalize_filters(filters)
    if filters:
        try:
            df = _load_from_parquet(split=split, filters=normalized_filters, limit=limit)
            if df.empty:
                report = ParseReport(0, 0, 0, 0)
                return df, report
            return clean_entities_column(df)
        except Exception:
            # Fall back to datasets streaming if Dataset Viewer/parquet is unavailable.
            pass

    from datasets import load_dataset

    if streaming is None:
        streaming = True

    dataset = load_dataset("Raoyuan/MAKIEval", split=split, streaming=streaming)

    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(dataset):
        if normalized_filters:
            if normalized_filters.get("model") and row["model"] != normalized_filters["model"]:
                continue
            if normalized_filters.get("topic") and row["topic"] != normalized_filters["topic"]:
                continue
            if normalized_filters.get("language") and row["language"] != normalized_filters["language"]:
                continue
            if (
                normalized_filters.get("country_region")
                and row["country_region"] != normalized_filters["country_region"]
            ):
                continue
        rows.append(dict(row))
        if limit is not None and len(rows) >= limit:
            break

    df = pd.DataFrame(rows)
    if df.empty:
        report = ParseReport(0, 0, 0, 0)
        return df, report
    return clean_entities_column(df)
