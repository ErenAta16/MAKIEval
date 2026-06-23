"""CLI to compute MAKIEval metrics from the Hugging Face dataset."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loading import GROUP_COLUMNS, load_expected_group_keys, load_makieval_dataset
from metrics import (
    collect_qids,
    culture_consensus,
    culture_specificity,
    diversity,
    granularity,
)


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def _aggregate_group_metrics(
    group_df: pd.DataFrame,
    country_lookup: dict[str, str],
) -> dict:
    all_entities: list[dict] = []
    for entities in group_df["entities_parsed"]:
        all_entities.extend(entities)

    target_country = str(group_df["country_region"].iloc[0])
    return {
        "granularity": granularity(all_entities),
        "diversity": diversity(all_entities),
        "culture_specificity": culture_specificity(
            all_entities, target_country, country_lookup
        ),
        "entity_count": len(all_entities),
        "unique_qids": len(collect_qids(all_entities)),
    }


def _compute_consensus_rows(df: pd.DataFrame) -> list[dict]:
    """Pairwise culture consensus across languages for each (model, topic, country)."""
    rows = []
    group_cols = ["model", "topic", "country_region"]
    for (model, topic, country), group in df.groupby(group_cols):
        lang_qids: dict[str, set[str]] = {}
        for language, lang_df in group.groupby("language"):
            qids: set[str] = set()
            for entities in lang_df["entities_parsed"]:
                qids.update(collect_qids(entities))
            lang_qids[language] = qids

        languages = sorted(lang_qids)
        for i, lang_a in enumerate(languages):
            for lang_b in languages[i + 1 :]:
                rows.append(
                    {
                        "model": model,
                        "topic": topic,
                        "country_region": country,
                        "language_a": lang_a,
                        "language_b": lang_b,
                        "culture_consensus": culture_consensus(
                            lang_qids[lang_a], lang_qids[lang_b]
                        ),
                    }
                )
    return rows


def _add_run_metadata(
    df: pd.DataFrame,
    is_partial_sample: bool,
    n_rows_used: int,
    warning: str,
) -> pd.DataFrame:
    result = df.copy()
    result["is_partial_sample"] = is_partial_sample
    result["n_rows_used"] = n_rows_used
    result["warning"] = warning
    return result


def _computed_group_keys(metrics_df: pd.DataFrame) -> set[tuple[str, str, str, str]]:
    if metrics_df.empty:
        return set()
    return {
        tuple(row)
        for row in metrics_df[GROUP_COLUMNS].itertuples(index=False, name=None)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute MAKIEval metrics from HF data.")
    parser.add_argument("--model", default=None, help="Filter by model name")
    parser.add_argument("--topic", default=None, help="Filter by topic")
    parser.add_argument("--language", default=None, help="Filter by language")
    parser.add_argument("--country", default=None, help="Filter by country_region")
    parser.add_argument(
        "--limit",
        type=int,
        default=5000,
        help="Optional row limit for quick reproducibility checks (default: 5000)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Process all rows matching the filters instead of the default quick limit",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--output-dir",
        default="results/metrics",
        help="Directory for CSV/JSON outputs",
    )
    parser.add_argument(
        "--country-lookup",
        default=None,
        help="Optional JSON file mapping QID -> origin country label",
    )
    args = parser.parse_args()
    _set_seed(args.seed)
    if args.full:
        args.limit = None

    filters = {
        k: v
        for k, v in {
            "model": args.model,
            "topic": args.topic,
            "language": args.language,
            "country_region": args.country,
        }.items()
        if v
    }

    df, report = load_makieval_dataset(filters=filters or None, limit=args.limit)
    if df.empty:
        print("No rows matched the provided filters.")
        return

    country_lookup: dict[str, str] = {}
    if args.country_lookup and os.path.exists(args.country_lookup):
        with open(args.country_lookup, encoding="utf-8") as f:
            country_lookup = json.load(f)

    metric_rows = []
    group_cols = GROUP_COLUMNS
    for keys, group in df.groupby(group_cols):
        if not isinstance(keys, tuple):
            keys = (keys,)
        metrics = _aggregate_group_metrics(group, country_lookup)
        row = dict(zip(group_cols, keys))
        row.update(metrics)
        metric_rows.append(row)

    metrics_df = pd.DataFrame(metric_rows)
    consensus_df = pd.DataFrame(_compute_consensus_rows(df))
    is_partial_sample = args.limit is not None
    warning = ""
    if is_partial_sample:
        warning = (
            f"WARNING: partial sample ({len(df)} rows); diversity/consensus NOT "
            "comparable to paper. Use --full."
        )
        print(warning, file=sys.stderr)

    expected_groups = load_expected_group_keys(filters=filters or None, exact=True)
    computed_groups = _computed_group_keys(metrics_df)
    missing_groups = sorted(set(expected_groups) - computed_groups)
    completeness_warning = ""
    if len(expected_groups) != len(computed_groups):
        completeness_warning = (
            f"WARNING: expected {len(expected_groups)} groups, computed "
            f"{len(computed_groups)}; missing: {missing_groups}"
        )
        print(completeness_warning, file=sys.stderr)

    combined_warning = " ".join(
        message for message in [warning, completeness_warning] if message
    )
    metrics_df = _add_run_metadata(
        metrics_df,
        is_partial_sample=is_partial_sample,
        n_rows_used=len(df),
        warning=combined_warning,
    )
    consensus_df = _add_run_metadata(
        consensus_df,
        is_partial_sample=is_partial_sample,
        n_rows_used=len(df),
        warning=combined_warning,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = output_dir / "group_metrics.csv"
    consensus_path = output_dir / "culture_consensus.csv"
    report_path = output_dir / "parse_report.json"

    metrics_df.to_csv(metrics_path, index=False)
    consensus_df.to_csv(consensus_path, index=False)
    report_payload = report.__dict__ | {
        "is_partial_sample": is_partial_sample,
        "n_rows_used": len(df),
        "warning": combined_warning,
        "expected_group_count": len(expected_groups),
        "computed_group_count": len(computed_groups),
        "missing_groups": [list(group) for group in missing_groups],
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)

    print(f"Wrote {len(metrics_df)} group metric rows to {metrics_path}")
    print(f"Wrote {len(consensus_df)} consensus rows to {consensus_path}")
    print(
        f"Parse report: {report.parse_errors} parse errors / "
        f"{report.total_rows} rows"
    )


if __name__ == "__main__":
    main()
