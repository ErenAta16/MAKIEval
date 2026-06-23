"""Compare a small smoke-generation result with the published HF slice."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loading import filter_entities_for_metrics, load_makieval_dataset
from metrics import collect_qids, culture_consensus, culture_specificity, diversity, granularity
from quality_report import detect_language, has_repeated_ngram_block, has_repeated_sentence, language_matches
from smoke_generation import aggregate_metrics, canonical_model_name, normalize_topic, safe_slug


def load_smoke(path: str | None, model: str, language: str, topic: str, country: str) -> dict[str, Any]:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    candidate = Path("results/smoke") / (
        f"{safe_slug(canonical_model_name(model))}_{safe_slug(language)}_"
        f"{safe_slug(normalize_topic(topic))}_{safe_slug(country)}.json"
    )
    if not candidate.exists():
        raise FileNotFoundError(f"Smoke result not found: {candidate}")
    return json.loads(candidate.read_text(encoding="utf-8"))


def flatten_entities_from_smoke(smoke: dict[str, Any]) -> list[dict[str, Any]]:
    entities = []
    for row in smoke.get("rows", []):
        filtered, _excluded = filter_entities_for_metrics(row.get("entities", []))
        entities.extend(filtered)
    return entities


def flatten_entities_from_df(df: pd.DataFrame) -> list[dict[str, Any]]:
    entities = []
    for row_entities in df.get("entities_parsed", []):
        entities.extend(row_entities)
    return entities


def dominant_qid(entities: list[dict[str, Any]]) -> tuple[str, int]:
    qids = [str(entity.get("qid")) for entity in entities if entity.get("qid")]
    if not qids:
        return "NA", 0
    qid, count = Counter(qids).most_common(1)[0]
    return qid, count


def quality_rates(rows: list[dict[str, Any]], language: str) -> dict[str, float]:
    if not rows:
        return {"degenerate": 0.0, "language_leakage": 0.0}
    degenerate = 0
    leakage_checked = 0
    leakage = 0
    for row in rows:
        text = str(row.get("generated_text") or "")
        if has_repeated_ngram_block(text) or has_repeated_sentence(text):
            degenerate += 1
        detected = detect_language(text)
        if detected not in {"und", "unknown"}:
            leakage_checked += 1
            leakage += int(not language_matches(language, detected))
    return {
        "degenerate": degenerate / len(rows),
        "language_leakage": leakage / leakage_checked if leakage_checked else 0.0,
    }


def published_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    return df.to_dict(orient="records")


def label(value: float, close_threshold: float = 0.15) -> str:
    if value == 0:
        return "MATCH"
    if abs(value) <= close_threshold:
        return "CLOSE"
    return "DIVERGE"


def build_report(
    smoke: dict[str, Any],
    published_df: pd.DataFrame,
    published_limit: int | None,
) -> str:
    meta = smoke["metadata"]
    smoke_rows = smoke.get("rows", [])
    smoke_entities = flatten_entities_from_smoke(smoke)
    published_entities = flatten_entities_from_df(published_df)
    country = meta["country"]

    smoke_metrics = smoke.get("metrics") or aggregate_metrics(
        smoke_rows,
        country,
        smoke.get("country_lookup", {}),
    )
    published_metrics = {
        "granularity": granularity(published_entities),
        "diversity": diversity(published_entities),
        "culture_specificity": culture_specificity(published_entities, country, {}),
        "entity_count": len(published_entities),
        "unique_qids": len(collect_qids(published_entities)),
    }

    smoke_qids = collect_qids(smoke_entities)
    published_qids = collect_qids(published_entities)
    qid_jaccard = culture_consensus(smoke_qids, published_qids)
    smoke_dom = dominant_qid(smoke_entities)
    published_dom = dominant_qid(published_entities)
    smoke_quality = quality_rates(smoke_rows, meta["language"])
    published_quality = quality_rates(published_rows(published_df), meta["language"])

    lines = [
        "# MAKIEval Smoke Reproduction Comparison",
        "",
        "Scope: small-sample, not paper-scale. Published data may be an older snapshot per the author.",
        "",
        f"- Model: `{meta['model']}`",
        f"- Together endpoint: `{meta.get('together_model')}`",
        f"- Slice: `{meta['language']} / {meta['topic']} / {meta['country']}`",
        f"- Our N: `{len(smoke_rows)}`",
        f"- Published N used: `{len(published_df)}`"
        + (f" (limit={published_limit})" if published_limit else ""),
        f"- Extraction status: `{meta.get('extraction_status')}`",
        "",
        "## Deviations",
        "",
    ]
    deviations = meta.get("deviations") or []
    if deviations:
        lines.extend(f"- {item}" for item in deviations)
    else:
        lines.append("- None recorded.")

    lines.extend(
        [
            "",
            "## Metric Comparison",
            "",
            "| Metric | Ours | Published | Status | Comment |",
            "|---|---:|---:|---|---|",
        ]
    )
    for metric in ("granularity", "diversity", "culture_specificity", "entity_count", "unique_qids"):
        ours = smoke_metrics.get(metric, 0)
        published = published_metrics.get(metric, 0)
        delta = float(ours) - float(published)
        lines.append(
            f"| {metric} | {ours:.4f} | {published:.4f} | {label(delta)} | "
            "Small N; exact match is not expected. |"
        )

    lines.extend(
        [
            f"| qid_set_jaccard | {qid_jaccard:.4f} | n/a | {'CLOSE' if qid_jaccard > 0 else 'DIVERGE'} | Entity-set overlap between our slice and published slice. |",
            f"| dominant_qid | {smoke_dom[0]} ({smoke_dom[1]}) | {published_dom[0]} ({published_dom[1]}) | {'MATCH' if smoke_dom[0] == published_dom[0] else 'DIVERGE'} | Mode QID comparison. |",
            f"| degenerate_rate | {smoke_quality['degenerate']:.4f} | {published_quality['degenerate']:.4f} | {label(smoke_quality['degenerate'] - published_quality['degenerate'])} | Rule-based repeated text check. |",
            f"| language_leakage_rate | {smoke_quality['language_leakage']:.4f} | {published_quality['language_leakage']:.4f} | {label(smoke_quality['language_leakage'] - published_quality['language_leakage'])} | langid/script detector. |",
            "",
            "## Notes",
            "",
            "- Diversity and consensus are N-sensitive; this comparison is directional only.",
            "- Published culture specificity is `0.0` here unless per-QID origin lookup metadata is supplied.",
            "- GPT-4o-mini extraction was not used because OPENAI_API_KEY is intentionally unavailable.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare smoke output to HF published data.")
    parser.add_argument("--smoke-result", default=None)
    parser.add_argument("--model", default="Qwen2.5-7B-Instruct")
    parser.add_argument("--language", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--country", required=True)
    parser.add_argument("--published-limit", type=int, default=None)
    parser.add_argument("--output", default="docs/REPRODUCTION_COMPARISON.md")
    args = parser.parse_args()

    smoke = load_smoke(args.smoke_result, args.model, args.language, args.topic, args.country)
    limit = args.published_limit or int(smoke["metadata"].get("num_responses", 0)) or None
    filters = {
        "model": canonical_model_name(args.model),
        "topic": normalize_topic(args.topic),
        "language": args.language,
        "country_region": args.country,
    }
    published_df, _report = load_makieval_dataset(filters=filters, limit=limit)
    if published_df.empty:
        raise ValueError(f"No published rows matched filters: {filters}")

    report = build_report(smoke, published_df, limit)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Wrote comparison report to {output}")


if __name__ == "__main__":
    main()
