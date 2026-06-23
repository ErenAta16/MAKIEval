"""Small faithful/proxy MAKIEval generation smoke test via Together AI."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analysis_beverage
import analysis_book
import analysis_clothing
import analysis_food
import analysis_music
import analysis_transportation
import entity_extraction
import prompt_construct
from data_loading import clean_entities_column, filter_entities_for_metrics, load_makieval_dataset, normalize_filters
from metrics import collect_qids, culture_specificity, diversity, granularity


TOGETHER_BASE_URL = "https://api.together.ai/v1"

FAITHFUL_DECODING = {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 10,
    "max_tokens": 100,
}

PAPER_MODEL_TO_TOGETHER = {
    "Qwen2.5-7B-Instruct": "Qwen/Qwen2.5-7B-Instruct-Turbo",
    "Llama-3.1-8B-Instruct": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    "Llama-3.3-70B-Instruct": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "Mistral-7B-Instruct-v0.1": "mistralai/Mistral-7B-Instruct-v0.1",
    "aya-expanse-8b": "CohereLabs/aya-expanse-8b",
    "DeepSeek-V3": "deepseek-ai/DeepSeek-V3",
    "ChatGPT-4o-mini": "openai/gpt-oss-120b",
}

MODEL_ALIASES = {
    "qwen": "Qwen2.5-7B-Instruct",
    "qwen2.5-7b-instruct": "Qwen2.5-7B-Instruct",
    "llama3": "Llama-3.1-8B-Instruct",
    "llama3_70b": "Llama-3.3-70B-Instruct",
    "mistral": "Mistral-7B-Instruct-v0.1",
    "aya": "aya-expanse-8b",
    "deepseek": "DeepSeek-V3",
    "chatgpt": "ChatGPT-4o-mini",
}

LANGUAGE_INSTRUCTION_MAP = {
    "en": "Please answer in English.",
    "zh": "\u8bf7\u7528\u4e2d\u6587\u4f5c\u7b54\u3002",
    "zh-tw": "\u8acb\u7528\u7e41\u9ad4\u4e2d\u6587\u4f5c\u7b54\u3002",
    "de": "Bitte antworten Sie auf Deutsch.",
    "it": "Si prega di rispondere in italiano.",
    "yo": "J\u1ecdw\u1ecd dahun ni ede Yoruba.",
    "ha": "Don Allah ku amsa da Hausa.",
    "ar": "\u064a\u0631\u062c\u0649 \u0627\u0644\u0631\u062f \u0628\u0627\u0644\u0644\u063a\u0629 \u0627\u0644\u0639\u0631\u0628\u064a\u0629.",
    "tr": "L\u00fctfen T\u00fcrk\u00e7e cevap verin.",
    "fa": "\u0644\u0637\u0641\u0627\u064b \u0628\u0647 \u0632\u0628\u0627\u0646 \u0641\u0627\u0631\u0633\u06cc \u067e\u0627\u0633\u062e \u062f\u0647\u06cc\u062f.",
    "th": "\u0e01\u0e23\u0e38\u0e13\u0e32\u0e15\u0e2d\u0e1a\u0e40\u0e1b\u0e47\u0e19\u0e20\u0e32\u0e29\u0e32\u0e44\u0e17\u0e22",
    "ja": "\u65e5\u672c\u8a9e\u3067\u7b54\u3048\u3066\u304f\u3060\u3055\u3044\u3002",
    "ko": "\ud55c\uad6d\uc5b4\ub85c \ub300\ub2f5\ud574\uc8fc\uc138\uc694.",
    "hi": "\u0915\u0943\u092a\u092f\u093e \u0939\u093f\u0902\u0926\u0940 \u092e\u0947\u0902 \u0909\u0924\u094d\u0924\u0930 \u0926\u0947\u0902\u0964",
}

TOPIC_FETCHERS = {
    "food": analysis_food.fetch_wikidata_food_info,
    "beverage": analysis_beverage.fetch_wikidata_beverage_info,
    "clothing": analysis_clothing.fetch_wikidata_clothing_info,
    "music": analysis_music.fetch_wikidata_music_info,
    "book": analysis_book.fetch_wikidata_book_info,
    "transportation": analysis_transportation.fetch_wikidata_transportation_info,
}


def canonical_model_name(model: str) -> str:
    return MODEL_ALIASES.get(model.strip().lower(), model.strip())


def normalize_topic(topic: str) -> str:
    return "book" if topic.strip().lower() == "books" else topic.strip().lower()


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def require_together_key() -> str:
    key = os.environ.get("TOGETHER_API_KEY")
    if not key:
        key = os.environ.get("TOGETHER_API_KEY".lower())
    if not key:
        raise ValueError("TOGETHER_API_KEY environment variable is required.")
    return key


def together_client() -> OpenAI:
    return OpenAI(api_key=require_together_key(), base_url=TOGETHER_BASE_URL)


def resolve_together_model(model: str) -> tuple[str, list[str]]:
    canonical = canonical_model_name(model)
    if canonical not in PAPER_MODEL_TO_TOGETHER:
        allowed = ", ".join(sorted(PAPER_MODEL_TO_TOGETHER))
        raise ValueError(f"Model '{model}' is outside the paper set. Allowed: {allowed}")

    deviations = []
    together_model = PAPER_MODEL_TO_TOGETHER[canonical]
    if canonical == "ChatGPT-4o-mini":
        deviations.append("PROXY MODEL - ChatGPT-4o-mini is replaced by Together openai/gpt-oss-120b.")
    elif canonical != together_model:
        deviations.append(f"Together serving endpoint used: {together_model}.")
    if together_model.endswith("-Turbo"):
        deviations.append("Provider serving variant uses a Turbo endpoint, not local weights.")
    return together_model, deviations


def add_language_instruction_if_needed(prompt: str, model: str, language: str) -> str:
    canonical = canonical_model_name(model)
    if canonical.startswith("Qwen") or canonical.startswith("Mistral"):
        instruction = LANGUAGE_INSTRUCTION_MAP.get(language, f"Please answer in {language}.")
        return prompt + instruction
    return prompt


def load_prompt(
    model: str,
    topic: str,
    language: str,
    country: str,
    use_published_prompt: bool,
) -> tuple[str, dict[str, Any]]:
    filters = {
        "model": canonical_model_name(model),
        "topic": normalize_topic(topic),
        "language": language,
        "country_region": country,
    }
    if use_published_prompt:
        df, _report = load_makieval_dataset(filters=filters, limit=1)
        if not df.empty:
            row = df.iloc[0].to_dict()
            return str(row["prompt"]), {"source": "published_hf_prompt", "row": row}

    matches = prompt_construct.search_category_bias(
        "meta_info/prompt.json",
        normalize_topic(topic),
        "bias",
        language_filter=language,
    )
    if not matches:
        raise ValueError(f"No prompt template for topic={topic}, language={language}.")
    prompt = matches[0]["text"].replace("{country}", country)
    return prompt, {"source": "meta_info/prompt.json"}


def together_chat(
    client: OpenAI,
    model: str,
    messages: list[dict[str, str]],
    decoding: dict[str, Any],
    *,
    json_mode: bool = False,
    seed: int | None = None,
) -> str:
    extra_body = {"top_k": decoding["top_k"], "reasoning_effort": "low"}
    if seed is not None:
        extra_body["seed"] = seed
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": decoding["temperature"],
        "top_p": decoding["top_p"],
        "max_tokens": decoding["max_tokens"],
        "extra_body": extra_body,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def generate_responses(
    client: OpenAI,
    prompt: str,
    together_model: str,
    num_responses: int,
    decoding: dict[str, Any],
    seed: int,
) -> list[str]:
    rows = []
    for idx in range(num_responses):
        messages = [{"role": "user", "content": prompt}]
        rows.append(
            together_chat(
                client,
                together_model,
                messages,
                decoding,
                seed=seed + idx,
            )
        )
    return rows


def parse_extraction_dict(content: str) -> dict[str, str]:
    text = content.strip()
    if not text:
        return {}
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        text = text[first : last + 1]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(k): str(v) for k, v in parsed.items()}


def extract_entities_with_together(
    client: OpenAI,
    responses: list[str],
    topic: str,
    extraction_model: str,
) -> tuple[list[list[dict[str, Any]]], str]:
    decoding = {"temperature": 0.0, "top_p": 1.0, "top_k": 10, "max_tokens": 180}
    extracted_rows: list[list[dict[str, Any]]] = []
    used_model = extraction_model

    for response in responses:
        prompt = f"""Help me extract the words or phrases in the given text which are {entity_extraction.get_topic_hint(topic)}.
Answer in a dictionary format, with the type of the extracted text labeled.
{entity_extraction.get_example_for_topic(topic)}
Please ensure that you do not extract redundant entities. Do not provide any explanations, only output JSON like:
{{"<extracted_text>": "type", "<extracted_text>": "type"}}
Text: {response}"""
        content = ""
        errors = []
        for candidate in [extraction_model, "Qwen/Qwen2.5-7B-Instruct-Turbo"]:
            try:
                content = together_chat(
                    client,
                    candidate,
                    [
                        {"role": "system", "content": "You extract cultural entities as strict JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    decoding,
                    json_mode=True,
                )
                used_model = candidate
                break
            except Exception as exc:
                errors.append(f"{candidate}: {type(exc).__name__}")
        if not content and errors:
            raise RuntimeError("Together extraction failed: " + "; ".join(errors))
        parsed = parse_extraction_dict(content)
        extracted_rows.append(
            [
                {"entity": label, "entity_type": entity_type, "qid": None}
                for label, entity_type in parsed.items()
            ]
        )
    return extracted_rows, used_model


def link_entities(
    extracted_rows: list[list[dict[str, Any]]],
    topic: str,
    language: str,
) -> tuple[list[list[dict[str, Any]]], dict[str, str]]:
    fetcher = TOPIC_FETCHERS.get(normalize_topic(topic))
    if fetcher is None:
        raise ValueError(f"Unsupported topic for linking: {topic}")

    labels = sorted(
        {
            str(entity["entity"])
            for row in extracted_rows
            for entity in row
            if entity.get("entity")
        }
    )
    if not labels:
        return extracted_rows, {}

    linked_df = fetcher(labels, language)
    label_to_info: dict[str, dict[str, Any]] = {}
    for record in linked_df.to_dict(orient="records"):
        label_to_info[str(record.get("Original Label"))] = record

    country_lookup: dict[str, str] = {}
    linked_rows: list[list[dict[str, Any]]] = []
    for row in extracted_rows:
        linked_row = []
        for entity in row:
            info = label_to_info.get(str(entity.get("entity")), {})
            qid = info.get("Q_ID")
            qid_value = None if qid in (None, "", "NA") else str(qid)
            if qid_value:
                country_lookup[qid_value] = str(info.get("Origin Country", "NA"))
            linked = dict(entity)
            linked["qid"] = qid_value
            linked["origin_country"] = info.get("Origin Country", "NA")
            linked["is_category"] = info.get("is_category", "NA")
            linked_row.append(linked)
        linked_rows.append(linked_row)
    return linked_rows, country_lookup


def aggregate_metrics(rows: list[dict[str, Any]], country: str, country_lookup: dict[str, str]) -> dict[str, Any]:
    all_entities: list[dict[str, Any]] = []
    for row in rows:
        filtered, _excluded = filter_entities_for_metrics(row.get("entities", []))
        all_entities.extend(filtered)
    return {
        "granularity": granularity(all_entities),
        "diversity": diversity(all_entities),
        "culture_specificity": culture_specificity(all_entities, country, country_lookup),
        "entity_count": len(all_entities),
        "unique_qids": len(collect_qids(all_entities)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small MAKIEval generation smoke test.")
    parser.add_argument("--model", default="Qwen2.5-7B-Instruct", help="Paper model name")
    parser.add_argument("--language", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--country", required=True)
    parser.add_argument("--num-responses", type=int, default=5)
    parser.add_argument("--faithful", action="store_true", default=True, help="Lock paper decoding values")
    parser.add_argument("--no-faithful", dest="faithful", action="store_false")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--use-published-prompt", action="store_true", default=True)
    parser.add_argument("--no-use-published-prompt", dest="use_published_prompt", action="store_false")
    parser.add_argument("--device", default="api", choices=["api", "auto", "cuda", "cpu"])
    parser.add_argument("--no-extraction", action="store_true")
    parser.add_argument(
        "--extraction-model",
        default=os.environ.get("TOGETHER_EXTRACTION_MODEL", "openai/gpt-oss-120b"),
        help="Together model for proxy extraction when OPENAI_API_KEY is unavailable",
    )
    parser.add_argument("--output-dir", default="results/smoke")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    canonical = canonical_model_name(args.model)
    topic = normalize_topic(args.topic)
    together_model, deviations = resolve_together_model(canonical)
    decoding = dict(FAITHFUL_DECODING)
    if not args.faithful:
        deviations.append("Non-faithful mode requested; paper decoding lock disabled.")

    prompt, prompt_meta = load_prompt(
        canonical,
        topic,
        args.language,
        args.country,
        args.use_published_prompt,
    )
    model_prompt = add_language_instruction_if_needed(prompt, canonical, args.language)
    client = together_client()
    responses = generate_responses(
        client,
        model_prompt,
        together_model,
        args.num_responses,
        decoding,
        args.seed,
    )

    rows = [{"generated_text": text, "entities": []} for text in responses]
    country_lookup: dict[str, str] = {}
    extraction_status = "skipped"
    extraction_model_used = None
    metrics = None

    if args.no_extraction:
        deviations.append("Extraction disabled with --no-extraction; metrics not computed.")
    else:
        deviations.append(
            "OPENAI_API_KEY not used; GPT-4o-mini extraction replaced by Together proxy extraction."
        )
        extracted_rows, extraction_model_used = extract_entities_with_together(
            client,
            responses,
            topic,
            args.extraction_model,
        )
        linked_rows, country_lookup = link_entities(extracted_rows, topic, args.language)
        for row, entities in zip(rows, linked_rows):
            row["entities"] = entities
        extraction_status = "completed"
        metrics = aggregate_metrics(rows, args.country, country_lookup)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (
        f"{safe_slug(canonical)}_{safe_slug(args.language)}_"
        f"{safe_slug(topic)}_{safe_slug(args.country)}.json"
    )

    payload = {
        "metadata": {
            "model": canonical,
            "together_model": together_model,
            "language": args.language,
            "topic": topic,
            "country": args.country,
            "num_responses": args.num_responses,
            "seed": args.seed,
            "faithful": args.faithful,
            "decoding": decoding,
            "prompt_source": prompt_meta["source"],
            "prompt": prompt,
            "model_prompt": model_prompt,
            "provider": "together",
            "base_url": TOGETHER_BASE_URL,
            "extraction_status": extraction_status,
            "extraction_model": extraction_model_used,
            "deviations": deviations,
        },
        "rows": rows,
        "country_lookup": country_lookup,
        "metrics": metrics,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote smoke results to {output_path}")
    if metrics:
        print(json.dumps(metrics, indent=2))
    else:
        print("Extraction/metrics skipped.")


if __name__ == "__main__":
    main()
