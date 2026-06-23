# 🌍 MAKIEval

**MAKIEval: A Multilingual Automatic Wikidata-based Framework for Cultural Awareness Evaluation for LLMs**

## 📖 Overview

MAKIEval is a multilingual framework for evaluating cultural awareness in Large Language Models (LLMs). The framework leverages Wikidata to automatically construct culturally grounded prompts, extract entities from model generations, and perform large-scale cultural awareness analysis across languages, countries, and domains.

---

## 🤗 Dataset Release

We have released the MAKIEval dataset on Hugging Face:

👉 **Dataset:** https://huggingface.co/datasets/Raoyuan/MAKIEval

The released dataset currently contains:

* 🤖 **7 LLMs** (see paper Table 1)
* 🌐 13 Languages
* 🗺️ 19 Countries and Regions
* 🎭 6 Cultural Domains

> **Note on scale:** The Hugging Face release contains approximately **5.25M rows**. The paper reports 85.8 million generated texts; at the response level the expected order of magnitude is ≈6M (1,716 prompts × 500 responses × 7 models). The difference may reflect aggregation, filtering, or release packaging — we report HF counts here rather than restating the paper figure.

### Cultural Domains

* 🍽️ Food
* 🥤 Beverage
* 👕 Clothing
* 🎵 Music
* 📚 Books
* 🚆 Transportation / Going to Work

Each sample contains:

* 📝 Prompt
* 💬 Generated Text
* 🏷️ Extracted Entities
* 🔗 Wikidata QIDs (when available)

Example schema:

```text
model
topic
language
country_region
prompt
generated_text
entities
```

---

## 📂 Repository Structure

```text
code/
    analysis_*.py            # topic-specific Wikidata linking
    data_loading.py          # Hugging Face dataset loader
    entity_extraction.py
    lm_utils.py
    metrics.py               # granularity, diversity, specificity, consensus
    prompt_construct.py
    run_experiment.py
    run_metrics.py           # CLI for metric computation
    validate_fidelity.py      # paper-facing fidelity checks

meta_info/
    country.json
    name.json
    prompt.json

tests/
    test_data_loading.py
    test_metrics.py

docs/
    DEVIATIONS.md
    FIDELITY_REPORT.md
```

---

## 🔁 Reproduce (metrics)

> ⚠️ **Use `--full` for paper-comparable numbers. The default 5,000-row limit is only a quick smoke test; Diversity and Consensus in this mode are not comparable to the paper values.**

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Compute metrics from the public dataset

No API key is required for `run_metrics.py`; API-backed generation and entity
extraction still require `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` in the
environment.

```bash
python code/run_metrics.py --model Qwen2.5-7B-Instruct --topic beverage --language ar --seed 42 --limit 5000
```

Outputs are written to `results/metrics/`:

* `group_metrics.csv` — granularity, diversity, culture specificity per (model, topic, language, country)
* `culture_consensus.csv` — pairwise Jaccard scores across languages
* `parse_report.json` — entity JSON parse statistics

`run_metrics.py` defaults to a 5,000-row limit for quick checks. Add `--full` to process all rows matching the selected filters.

### 3. Run tests

```bash
pytest -q tests/
```

---

## ⚙️ Pipeline

```text
Prompt Templates
        ↓
Country-Specific Prompt Generation
        ↓
LLM Generation
        ↓
Entity Extraction
        ↓
Wikidata Entity Linking
        ↓
Cultural Awareness Analysis
```

---

## 🚀 Features

* 🌍 Multilingual evaluation
* 🗺️ Country-aware prompt generation
* 🔗 Wikidata-based entity linking
* 📊 Quantitative cultural awareness analysis
* 🤖 Compatible with both open-source and proprietary LLMs

---

## 📚 Citation

If you use this repository or dataset, please cite:

```bibtex
@inproceedings{zhao-etal-2025-makieval,
    title = "{MAKIE}val: A Multilingual Automatic {W}i{K}idata-based Framework for Cultural Awareness Evaluation for {LLM}s",
    author = "Zhao, Raoyuan  and
      Chen, Beiduo  and
      Plank, Barbara  and
      Hedderich, Michael A.",
    editor = "Christodoulopoulos, Christos  and
      Chakraborty, Tanmoy  and
      Rose, Carolyn  and
      Peng, Violet",
    booktitle = "Findings of the Association for Computational Linguistics: EMNLP 2025",
    month = nov,
    year = "2025",
    address = "Suzhou, China",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2025.findings-emnlp.1256/",
    doi = "10.18653/v1/2025.findings-emnlp.1256",
    pages = "23104--23136",
    ISBN = "979-8-89176-335-7",
    abstract = "Large language models (LLMs) are used globally across many languages, but their English-centric pretraining raises concerns about cross-lingual disparities for cultural awareness, often resulting in biased outputs. However, comprehensive multilingual evaluation remains challenging due to limited benchmarks and questionable translation quality. To better assess these disparities, we introduce MAKIEval, an automatic multilingual framework for evaluating cultural awareness in LLMs across languages, regions, and topics. MAKIEval evaluates open-ended text generation, capturing how models express culturally grounded knowledge in natural language. Leveraging Wikidata{'}s multilingual structure as a cross-lingual anchor, it automatically identifies cultural entities in model outputs and links them to structured knowledge, enabling scalable, language-agnostic evaluation without manual annotation or translation. We then introduce four metrics that capture complementary dimensions of cultural awareness: granularity, diversity, cultural specificity, and consensus across languages. We assess 7 LLMs developed from different parts of the world, encompassing both open-source and proprietary systems, across 13 languages, 19 countries and regions, and 6 culturally salient topics (e.g., food, clothing). Notably, we find that models tend to exhibit stronger cultural awareness in English, suggesting that English prompts more effectively activate culturally grounded knowledge. We publicly release our code and data."
}

```

---

## ⭐ Acknowledgements

This project builds upon Wikidata and multilingual LLM ecosystems to facilitate reproducible cultural-awareness evaluation research.
