"""Quality checks for the published Raoyuan/MAKIEval Hugging Face dataset."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loading import (
    DEFAULT_COLUMNS,
    filter_entities_for_metrics,
    iter_makieval_parquet_frames,
    parse_entities_field,
)

try:
    import langid
except Exception:  # pragma: no cover - exercised only when optional dep is absent.
    langid = None


REPORT_NOTE = (
    "Scope: published HF dataset, version may differ from paper (per author)."
)

LANG_ALIASES = {
    "zh-tw": {"zh", "zh-tw"},
    "zh": {"zh", "zh-tw"},
}

SUSPICIOUS_LABELS = {
    "cocaine",
    "coca\u00edna",
    "kokain",
    "caffeine",
    "kafein",
    "curiosity",
    "merak",
}

SUSPICIOUS_QIDS = {
    "Q422",
    "Q60235",
}

SUSPICIOUS_TYPES = {
    "dish_name",
    "dish",
    "specific_ingredient",
    "drink_name",
    "beverage_category",
}


def normalize_label(label: str) -> str:
    """Normalize entity surface forms for rough cross-row comparisons."""
    text = unicodedata.normalize("NFKD", str(label).strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"^[\"'`]+|[\"'`]+$", "", text)
    text = re.sub(r"^(the|a|an)\s+", "", text)
    text = re.sub(r"^\u0627\u0644", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def entity_label(entity: dict[str, Any]) -> str:
    for key in ("entity", "label", "text", "name"):
        value = entity.get(key)
        if value:
            return str(value)
    return ""


def entity_qid(entity: dict[str, Any]) -> str | None:
    qid = entity.get("qid")
    if qid is None or qid == "" or str(qid).upper() == "NA":
        return None
    return str(qid)


def is_empty_text(text: Any) -> bool:
    return not str(text or "").strip()


def has_repeated_ngram_block(text: str, threshold: int = 10) -> bool:
    if re.search(r"(.)\1{30,}", text):
        return True
    tokens = re.findall(r"\w+|[^\w\s]", text.lower(), flags=re.UNICODE)
    if len(tokens) < threshold * 2:
        return False
    for n in (1, 2, 3):
        previous = None
        run = 0
        for idx in range(0, len(tokens) - n + 1, n):
            chunk = tuple(tokens[idx : idx + n])
            if chunk == previous:
                run += 1
            else:
                previous = chunk
                run = 1
            if run >= threshold:
                return True
    return False


def has_repeated_sentence(text: str, threshold: int = 3) -> bool:
    sentences = [
        re.sub(r"\s+", " ", part.strip().lower())
        for part in re.split(r"[.!?\n\u3002\uff01\uff1f]+", text)
        if part.strip()
    ]
    if not sentences:
        return False
    counts = Counter(sentences)
    return any(count >= threshold for count in counts.values())


def detect_language(text: str) -> str:
    if is_empty_text(text):
        return "und"
    if langid is not None:
        try:
            return langid.classify(text)[0].lower()
        except Exception:
            return "und"

    # Fallback keeps the report runnable when langid is not installed.
    if re.search(r"[\u0600-\u06ff]", text):
        return "ar"
    if re.search(r"[\u3040-\u30ff]", text):
        return "ja"
    if re.search(r"[\uac00-\ud7af]", text):
        return "ko"
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    if re.search(r"[\u0e00-\u0e7f]", text):
        return "th"
    if re.search(r"[\u0900-\u097f]", text):
        return "hi"
    return "unknown"


def language_matches(expected: str, detected: str) -> bool:
    expected_norm = str(expected).lower()
    detected_norm = str(detected).lower()
    if expected_norm == detected_norm:
        return True
    return detected_norm in LANG_ALIASES.get(expected_norm, set())


def short_text(text: Any, limit: int = 180) -> str:
    value = re.sub(r"\s+", " ", str(text or "").strip())
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


@dataclass
class BucketStats:
    rows: int = 0
    repeated_ngram_rows: int = 0
    repeated_sentence_rows: int = 0
    empty_entity_rows: int = 0
    language_checked_rows: int = 0
    language_mismatch_rows: int = 0
    entity_count_all_types: int = 0
    missing_qid_all_types: int = 0
    entity_count_cultural_only: int = 0
    missing_qid_cultural_only: int = 0
    suspicious_count: int = 0


@dataclass
class QualityState:
    overall: BucketStats = field(default_factory=BucketStats)
    by_slice: dict[tuple[str, str, str], BucketStats] = field(
        default_factory=lambda: defaultdict(BucketStats)
    )
    by_topic: dict[str, BucketStats] = field(default_factory=lambda: defaultdict(BucketStats))
    examples: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    label_qids: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    observed_groups: set[tuple[str, str, str, str]] = field(default_factory=set)


def add_example(state: QualityState, kind: str, row: dict[str, Any], extra: str = "") -> None:
    if len(state.examples[kind]) >= 3:
        return
    state.examples[kind].append(
        {
            "model": row.get("model"),
            "topic": row.get("topic"),
            "language": row.get("language"),
            "country_region": row.get("country_region"),
            "detail": extra,
            "generated_text": short_text(row.get("generated_text")),
        }
    )


def update_bucket(
    bucket: BucketStats,
    row_flags: dict[str, bool],
    entities: list[dict[str, Any]],
    cultural_entities: list[dict[str, Any]],
) -> None:
    bucket.rows += 1
    bucket.repeated_ngram_rows += int(row_flags["repeated_ngram"])
    bucket.repeated_sentence_rows += int(row_flags["repeated_sentence"])
    bucket.empty_entity_rows += int(row_flags["empty_entities"])
    bucket.language_checked_rows += int(row_flags["language_checked"])
    bucket.language_mismatch_rows += int(row_flags["language_mismatch"])
    bucket.suspicious_count += int(row_flags["suspicious"])
    bucket.entity_count_all_types += len(entities)
    bucket.missing_qid_all_types += sum(1 for entity in entities if not entity_qid(entity))
    bucket.entity_count_cultural_only += len(cultural_entities)
    bucket.missing_qid_cultural_only += sum(
        1 for entity in cultural_entities if not entity_qid(entity)
    )


def process_row(state: QualityState, row: dict[str, Any]) -> None:
    key = (
        str(row.get("model")),
        str(row.get("topic")),
        str(row.get("language")),
        str(row.get("country_region")),
    )
    state.observed_groups.add(key)

    entities, ok = parse_entities_field(row.get("entities"))
    if not ok:
        entities = []
    cultural_entities, _excluded = filter_entities_for_metrics(entities)

    text = str(row.get("generated_text") or "")
    detected_language = detect_language(text)
    language_checked = detected_language not in {"und", "unknown"}
    language_mismatch = language_checked and not language_matches(
        str(row.get("language")), detected_language
    )

    suspicious_entities = []
    for entity in entities:
        label = normalize_label(entity_label(entity))
        qid = entity_qid(entity)
        entity_type = str(entity.get("entity_type", "")).lower()
        if label and qid:
            state.label_qids[label][qid] += 1
        if entity_type in SUSPICIOUS_TYPES and (
            label in SUSPICIOUS_LABELS or qid in SUSPICIOUS_QIDS
        ):
            suspicious_entities.append(entity)

    row_flags = {
        "repeated_ngram": has_repeated_ngram_block(text),
        "repeated_sentence": has_repeated_sentence(text),
        "empty_entities": len(entities) == 0,
        "language_checked": language_checked,
        "language_mismatch": language_mismatch,
        "suspicious": bool(suspicious_entities),
    }

    update_bucket(state.overall, row_flags, entities, cultural_entities)
    update_bucket(
        state.by_slice[(str(row.get("model")), str(row.get("language")), str(row.get("topic")))],
        row_flags,
        entities,
        cultural_entities,
    )
    update_bucket(state.by_topic[str(row.get("topic"))], row_flags, entities, cultural_entities)

    if row_flags["repeated_ngram"]:
        add_example(state, "repeated_ngram", row)
    if row_flags["repeated_sentence"]:
        add_example(state, "repeated_sentence", row)
    if row_flags["empty_entities"]:
        add_example(state, "empty_entities", row)
    if row_flags["language_mismatch"]:
        add_example(state, "language_mismatch", row, f"detected={detected_language}")
    if suspicious_entities:
        detail = ", ".join(
            f"{entity_label(entity)} ({entity.get('entity_type')}, {entity_qid(entity) or 'NA'})"
            for entity in suspicious_entities[:3]
        )
        add_example(state, "suspicious_entities", row, detail)


def scan_rows(sample: int | None, seed: int, full: bool) -> QualityState:
    rng = random.Random(seed)
    state = QualityState()
    reservoirs: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    seen_by_sample_key: Counter = Counter()
    columns = DEFAULT_COLUMNS

    for shard in tqdm(
        iter_makieval_parquet_frames(columns=columns),
        desc="Reading MAKIEval parquet shards",
    ):
        if shard.empty:
            continue
        for record in shard.to_dict(orient="records"):
            group_key = (
                str(record.get("model")),
                str(record.get("topic")),
                str(record.get("language")),
                str(record.get("country_region")),
            )
            state.observed_groups.add(group_key)

            if full or sample is None:
                process_row(state, record)
                continue

            sample_key = (
                str(record.get("model")),
                str(record.get("language")),
                str(record.get("topic")),
            )
            seen_by_sample_key[sample_key] += 1
            seen = seen_by_sample_key[sample_key]
            bucket = reservoirs[sample_key]
            if len(bucket) < sample:
                bucket.append(record)
            else:
                replace_at = rng.randrange(seen)
                if replace_at < sample:
                    bucket[replace_at] = record

    if not full and sample is not None:
        for bucket in reservoirs.values():
            for record in bucket:
                process_row(state, record)

    return state


def pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.00%"
    return f"{100 * numerator / denominator:.2f}%"


def bucket_row(label: str, stats: BucketStats) -> str:
    cultural_qid_rate = pct(
        stats.missing_qid_cultural_only,
        stats.entity_count_cultural_only,
    )
    all_qid_rate = pct(stats.missing_qid_all_types, stats.entity_count_all_types)
    lang_rate = pct(stats.language_mismatch_rows, stats.language_checked_rows)
    return (
        f"| {label} | {stats.rows} | {pct(stats.repeated_ngram_rows, stats.rows)} | "
        f"{pct(stats.repeated_sentence_rows, stats.rows)} | "
        f"{pct(stats.empty_entity_rows, stats.rows)} | {lang_rate} | "
        f"{cultural_qid_rate} | {all_qid_rate} | {stats.suspicious_count} |"
    )


def top_surface_inconsistencies(state: QualityState, limit: int = 20) -> list[tuple[str, Counter]]:
    rows = [
        (label, counts)
        for label, counts in state.label_qids.items()
        if len(counts) > 1
    ]
    rows.sort(key=lambda item: (len(item[1]), sum(item[1].values())), reverse=True)
    return rows[:limit]


def examples_markdown(state: QualityState, kind: str) -> list[str]:
    rows = state.examples.get(kind, [])
    if not rows:
        return ["No examples captured in this run."]
    lines = []
    for row in rows:
        context = (
            f"{row['model']} / {row['topic']} / {row['language']} / "
            f"{row['country_region']}"
        )
        detail = f" ({row['detail']})" if row.get("detail") else ""
        lines.append(f"- {context}{detail}: {row['generated_text']}")
    return lines


def build_report(state: QualityState, mode_label: str) -> str:
    lines = [
        "# MAKIEval Published Data Quality Report",
        "",
        REPORT_NOTE,
        "",
        f"- Mode: `{mode_label}`",
        f"- Rows analyzed for quality checks: `{state.overall.rows}`",
        f"- Observed `(model, topic, language, country_region)` cells: `{len(state.observed_groups)}`",
        "",
        "## Summary",
        "",
        "| Scope | Rows | Repeated n-gram | Repeated sentence | Empty entities | Language mismatch | missing_qid_cultural_only | missing_qid_all_types | Suspicious rows |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        bucket_row("Overall", state.overall),
        "",
        "## Slice Breakdown",
        "",
        "| Model / Language / Topic | Rows | Repeated n-gram | Repeated sentence | Empty entities | Language mismatch | missing_qid_cultural_only | missing_qid_all_types | Suspicious rows |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    slice_rows = sorted(
        state.by_slice.items(),
        key=lambda item: (
            item[1].language_mismatch_rows / max(1, item[1].language_checked_rows),
            item[1].empty_entity_rows / max(1, item[1].rows),
        ),
        reverse=True,
    )
    for (model, language, topic), stats in slice_rows[:30]:
        lines.append(bucket_row(f"{model} / {language} / {topic}", stats))

    lines.extend(
        [
            "",
            "## Missing QID By Topic",
            "",
            "| Topic | cultural_entities | missing_qid_cultural_only | missing_qid_cultural_only_rate | all_entities | missing_qid_all_types | missing_qid_all_types_rate |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for topic, stats in sorted(state.by_topic.items()):
        lines.append(
            f"| {topic} | {stats.entity_count_cultural_only} | "
            f"{stats.missing_qid_cultural_only} | "
            f"{pct(stats.missing_qid_cultural_only, stats.entity_count_cultural_only)} | "
            f"{stats.entity_count_all_types} | {stats.missing_qid_all_types} | "
            f"{pct(stats.missing_qid_all_types, stats.entity_count_all_types)} |"
        )

    lines.extend(
        [
            "",
            "## Surface Form To QID Inconsistency",
            "",
            "| Normalized label | Distinct QIDs | Top QIDs |",
            "|---|---:|---|",
        ]
    )
    inconsistencies = top_surface_inconsistencies(state)
    if not inconsistencies:
        lines.append("| None captured | 0 |  |")
    for label, counts in inconsistencies:
        top_qids = ", ".join(f"{qid} ({count})" for qid, count in counts.most_common(5))
        lines.append(f"| {label} | {len(counts)} | {top_qids} |")

    example_sections = [
        ("Repeated n-gram examples", "repeated_ngram"),
        ("Repeated sentence examples", "repeated_sentence"),
        ("Empty entity examples", "empty_entities"),
        ("Language mismatch examples", "language_mismatch"),
        ("Suspicious extraction review candidates", "suspicious_entities"),
    ]
    for title, key in example_sections:
        lines.extend(["", f"## {title}", ""])
        lines.extend(examples_markdown(state, key))

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Language detection uses `langid` when installed, with a script-based fallback.",
            "- Suspicious extraction rows are rule-based review candidates, not confirmed false positives.",
            "- `missing_qid_cultural_only` excludes `place`, `person_name`, `listener_name`, and `reader_name` via `data_loading.filter_entities_for_metrics`; this is the Table 10-comparable missing-QID rate.",
            "- `missing_qid_all_types` keeps every extracted entity type for broader extraction/linking completeness diagnostics.",
            "- Missing-QID rates are compared descriptively against the paper's 26-35% range; released data may use a different snapshot.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit published MAKIEval data quality.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--sample", type=int, default=200, help="Reservoir sample rows per model-language-topic slice.")
    mode.add_argument("--full", action="store_true", help="Analyze every row in the published dataset.")
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed")
    parser.add_argument(
        "--output",
        default="docs/DATA_QUALITY_REPORT.md",
        help="Markdown report path",
    )
    args = parser.parse_args()

    sample = None if args.full else args.sample
    state = scan_rows(sample=sample, seed=args.seed, full=args.full)
    mode_label = "full" if args.full else f"sample={sample} per model-language-topic"
    report = build_report(state, mode_label)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")

    print(f"Wrote quality report to {output}")
    print(
        json.dumps(
            {
                "mode": mode_label,
                "rows_analyzed": state.overall.rows,
                "observed_cells": len(state.observed_groups),
                "empty_entity_rate": pct(state.overall.empty_entity_rows, state.overall.rows),
                "language_mismatch_rate": pct(
                    state.overall.language_mismatch_rows,
                    state.overall.language_checked_rows,
                ),
                "missing_qid_cultural_only_rate": pct(
                    state.overall.missing_qid_cultural_only,
                    state.overall.entity_count_cultural_only,
                ),
                "missing_qid_all_types_rate": pct(
                    state.overall.missing_qid_all_types,
                    state.overall.entity_count_all_types,
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
