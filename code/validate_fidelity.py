"""Validate MAKIEval metric fidelity against paper-level reference checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loading import (  # noqa: E402
    GROUP_COLUMNS,
    filter_entities_for_metrics,
    iter_makieval_parquet_frames,
    parse_entities_field,
)
from metrics import collect_qids, culture_consensus  # noqa: E402

TARGET_DEEPSEEK_SLICE = {
    "model": "DeepSeek-V3",
    "topic": "book",
    "language": "en",
    "country_region": "united states",
}

REFERENCE_NOTES = {
    "deepseek_us_book": (
        "Paper Section 6.2: DeepSeek-V3, English, book, US is dominated by "
        "To Kill a Mockingbird (~499/500), diversity approx 1."
    ),
    "diversity": (
        "Paper Table 12 order-of-magnitude: Llama-3.1-8B highest (~36-39), "
        "DeepSeek lowest (~14-17)."
    ),
    "consensus": (
        "Paper Table 3 order-of-magnitude: model averages roughly 0.11-0.21; "
        "larger models around 0.20."
    ),
}


def _group_key(row: Any) -> tuple[str, str, str, str]:
    return tuple(getattr(row, column) for column in GROUP_COLUMNS)


def _cache_path(cache_dir: Path, full: bool, limit: int | None) -> Path:
    suffix = "full" if full else f"limit_{limit}"
    return cache_dir / f"fidelity_cache_{suffix}.json"


def _serialize_group_qids(group_qids: dict[tuple[str, str, str, str], set[str]]) -> dict[str, list[str]]:
    return {"||".join(key): sorted(qids) for key, qids in group_qids.items()}


def _deserialize_group_qids(raw: dict[str, list[str]]) -> dict[tuple[str, str, str, str], set[str]]:
    return {tuple(key.split("||")): set(qids) for key, qids in raw.items()}


def _compute_cache(full: bool, limit: int | None, cache_file: Path) -> dict[str, Any]:
    group_qids: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    deepseek_qid_row_counts: Counter[str] = Counter()
    deepseek_rows = 0
    rows_seen = 0

    columns = GROUP_COLUMNS + ["entities"]
    for frame in tqdm(
        iter_makieval_parquet_frames(columns=columns),
        desc="Reading MAKIEval parquet shards",
        unit="shard",
    ):
        if frame.empty:
            continue

        for row in frame.itertuples(index=False):
            if not full and limit is not None and rows_seen >= limit:
                break
            rows_seen += 1

            entities, ok = parse_entities_field(getattr(row, "entities"))
            if not ok:
                continue
            filtered_entities, _ = filter_entities_for_metrics(entities)
            qids = collect_qids(filtered_entities)

            key = _group_key(row)
            if dict(zip(GROUP_COLUMNS, key)) == TARGET_DEEPSEEK_SLICE:
                deepseek_rows += 1
                deepseek_qid_row_counts.update(qids)

            if not qids:
                continue
            group_qids[key].update(qids)

        if not full and limit is not None and rows_seen >= limit:
            break

    payload = {
        "full": full,
        "limit": limit,
        "rows_seen": rows_seen,
        "group_qids": _serialize_group_qids(group_qids),
        "deepseek_us_book": {
            "rows": deepseek_rows,
            "qid_row_counts": dict(deepseek_qid_row_counts),
        },
    }
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return payload


def _load_or_compute_cache(args: argparse.Namespace) -> dict[str, Any]:
    cache_dir = Path(args.cache_dir)
    cache_file = _cache_path(cache_dir, args.full, args.limit)
    if cache_file.exists() and not args.force_refresh:
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)
    return _compute_cache(full=args.full, limit=args.limit, cache_file=cache_file)


def _deepseek_us_book_row(payload: dict[str, Any], group_qids: dict[tuple[str, str, str, str], set[str]]) -> dict[str, str]:
    target_key = tuple(TARGET_DEEPSEEK_SLICE[column] for column in GROUP_COLUMNS)
    qids = group_qids.get(target_key, set())
    diversity_value = len(qids)

    slice_payload = payload.get("deepseek_us_book", {})
    qid_counts = Counter(slice_payload.get("qid_row_counts", {}))
    total_rows = int(slice_payload.get("rows", 0))
    dominant_qid = "NA"
    dominant_count = 0
    if qid_counts:
        dominant_qid, dominant_count = qid_counts.most_common(1)[0]

    dominant_rate = dominant_count / total_rows if total_rows else 0.0
    status = "PASS" if diversity_value <= 2 and dominant_rate >= 0.9 else "MISMATCH"
    return {
        "metric": "DeepSeek US book dominance",
        "slice": "DeepSeek-V3 / book / en / US",
        "computed": (
            f"diversity={diversity_value}; dominant={dominant_qid} "
            f"{dominant_count}/{total_rows} ({dominant_rate:.1%})"
        ),
        "paper_reference": REFERENCE_NOTES["deepseek_us_book"],
        "status": status,
        "comment": "PASS threshold: diversity <= 2 and dominant QID row frequency >= 90%.",
    }


def _average_diversity_rows(group_qids: dict[tuple[str, str, str, str], set[str]]) -> list[dict[str, str]]:
    values_by_model: dict[str, list[int]] = defaultdict(list)
    for (model, _topic, _language, _country), qids in group_qids.items():
        values_by_model[model].append(len(qids))

    averages = {model: mean(values) for model, values in values_by_model.items() if values}
    if not averages:
        return []

    highest_model = max(averages, key=averages.get)
    lowest_model = min(averages, key=averages.get)
    rows = []
    for model, value in sorted(averages.items()):
        if model == "Llama-3.1-8B-Instruct":
            status = "PASS" if highest_model == model and 25 <= value <= 50 else "MISMATCH"
            comment = f"Highest model observed: {highest_model}."
        elif model == "DeepSeek-V3":
            status = "PASS" if lowest_model == model and value <= 25 else "MISMATCH"
            comment = f"Lowest model observed: {lowest_model}."
        else:
            status = "PASS" if 5 <= value <= 60 else "MISMATCH"
            comment = "Broad order-of-magnitude check; no exact per-model target asserted."

        rows.append(
            {
                "metric": "Average diversity",
                "slice": model,
                "computed": f"{value:.2f}",
                "paper_reference": REFERENCE_NOTES["diversity"],
                "status": status,
                "comment": comment,
            }
        )
    return rows


def _average_consensus_rows(group_qids: dict[tuple[str, str, str, str], set[str]]) -> list[dict[str, str]]:
    by_model_topic_country: dict[tuple[str, str, str], dict[str, set[str]]] = defaultdict(dict)
    for (model, topic, language, country), qids in group_qids.items():
        by_model_topic_country[(model, topic, country)][language] = qids

    consensus_by_model: dict[str, list[float]] = defaultdict(list)
    for (model, _topic, _country), lang_qids in by_model_topic_country.items():
        languages = sorted(lang_qids)
        for idx, lang_a in enumerate(languages):
            for lang_b in languages[idx + 1 :]:
                consensus_by_model[model].append(
                    culture_consensus(lang_qids[lang_a], lang_qids[lang_b])
                )

    rows = []
    for model, values in sorted(consensus_by_model.items()):
        if not values:
            continue
        value = mean(values)
        status = "PASS" if 0.08 <= value <= 0.25 else "MISMATCH"
        rows.append(
            {
                "metric": "Average consensus",
                "slice": model,
                "computed": f"{value:.3f}",
                "paper_reference": REFERENCE_NOTES["consensus"],
                "status": status,
                "comment": "Band check only; exact values may differ with released linking.",
            }
        )
    return rows


def _markdown_table(rows: list[dict[str, str]]) -> str:
    headers = ["metric", "slice", "computed", "paper_reference", "status", "comment"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        values = [row.get(header, "").replace("|", "\\|") for header in headers]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _write_report(rows: list[dict[str, str]], output_path: Path, payload: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = [
        "# MAKIEval Fidelity Report",
        "",
        "Source: `code/validate_fidelity.py`.",
        "",
        f"- Full dataset mode: `{payload.get('full')}`",
        f"- Rows scanned: `{payload.get('rows_seen')}`",
        f"- Group count with non-null metric QIDs: `{len(payload.get('group_qids', {}))}`",
        "",
        _markdown_table(rows),
        "",
    ]
    output_path.write_text("\n".join(body), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate MAKIEval metric fidelity checks.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Scan the full Hugging Face parquet release.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100000,
        help="Development limit used only without --full.",
    )
    parser.add_argument(
        "--cache-dir",
        default="results/fidelity",
        help="Directory for slice/group-QID cache files.",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignore existing cache and rescan parquet shards.",
    )
    parser.add_argument(
        "--output",
        default="docs/FIDELITY_REPORT.md",
        help="Markdown report path.",
    )
    args = parser.parse_args()

    if not args.full:
        print(
            "WARNING: validate_fidelity.py without --full is a development smoke test; "
            "paper-facing checks require --full.",
            file=sys.stderr,
        )

    payload = _load_or_compute_cache(args)
    group_qids = _deserialize_group_qids(payload.get("group_qids", {}))
    rows = [_deepseek_us_book_row(payload, group_qids)]
    rows.extend(_average_diversity_rows(group_qids))
    rows.extend(_average_consensus_rows(group_qids))

    output_path = Path(args.output)
    _write_report(rows, output_path, payload)

    statuses = Counter(row["status"] for row in rows)
    print(f"Wrote fidelity report to {output_path}")
    print(
        "Summary: "
        + ", ".join(f"{status}={count}" for status, count in sorted(statuses.items()))
    )


if __name__ == "__main__":
    main()
