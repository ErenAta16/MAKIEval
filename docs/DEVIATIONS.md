# Deviations from upstream / paper

This fork documents reproducibility additions for the public
`mainlp/MAKIEval` release and notes where the released Hugging Face data cannot
be compared directly to paper-level numbers.

## Metrics layer

| Item | Status | Notes |
|------|--------|-------|
| Metric computation | **Added** | Upstream did not include a runnable implementation for granularity, diversity, culture specificity, or culture consensus. This branch adds `code/metrics.py`, `code/data_loading.py`, and `code/run_metrics.py`. |
| Fidelity validation | **Added** | `code/validate_fidelity.py` scans Hugging Face parquet shards and writes `docs/FIDELITY_REPORT.md` with paper-facing sanity checks. MISMATCH rows are reported rather than hidden because released linking can differ from paper-side attribution. |
| Published-data quality audit | **Added** | `code/quality_report.py` audits the released Hugging Face rows without generation, GPU, or API keys and writes `docs/DATA_QUALITY_REPORT.md`. Language detection is approximate and rule-based checks are review candidates, not manual labels. |
| Smoke reproduction comparison | **Added** | `code/smoke_generation.py` and `code/compare_to_published.py` run a small Together-backed generation/extraction/linking path and compare it with the matching published HF slice. This is intentionally small-sample and not paper-scale. |

## Repository hygiene

| Item | Status | Notes |
|------|--------|-------|
| API keys | **Changed** | Hardcoded placeholder/default API keys are removed from `code/lm_utils.py`. OpenAI and DeepSeek clients now read `OPENAI_API_KEY` and `DEEPSEEK_API_KEY` from the environment. |
| `entity_extraction.py` syntax | **Fixed** | Restores importability by replacing the invalid `OpenAI(api_key )=` line with an environment-backed client initialization. |
| Together API | **Added** | Small smoke generation can use `TOGETHER_API_KEY` through an OpenAI-compatible client. Keys stay in the environment and are not committed. |

## Metric specifics

- **Null QIDs:** Excluded from diversity, consensus QID sets, and
  culture-specificity denominators.
- **Culture specificity without lookup:** `run_metrics.py` reports `0.0`
  unless a `--country-lookup` JSON is supplied; the Hugging Face rows do not
  include origin-country metadata per entity.
- **Excluded entity types:** `place`, `person_name`, `listener_name`,
  `reader_name`.
- **Metric CLI default:** `run_metrics.py` defaults to a deterministic
  `head(5000)` limit for quick smoke tests. This is biased toward early Hugging
  Face rows and is **not comparable to paper diversity/consensus values**; pass
  `--full` for all matching rows. Partial outputs include `is_partial_sample`,
  `n_rows_used`, and warning metadata.
- **Partial group completeness:** `run_metrics.py` scans filtered parquet group
  columns to compare actually present Hugging Face
  `(model, topic, language, country_region)` groups against computed groups and
  warns when partial sampling drops complete groups.
- **Figure 2 ZH/consensus note:** The EN and DE Figure 2 book columns are
  reproducible from stated QIDs and origin attributions in
  `tests/test_metrics.py`. The ZH column / consensus=0.5 value could not be
  reproduced from the stated EN/DE entity attributions alone; the corresponding
  test is marked `xfail` rather than inventing an expected value.
- **Together serving variants:** When smoke reproduction uses Together-hosted
  endpoints such as `Qwen/Qwen2.5-7B-Instruct-Turbo`, the run is provider-backed
  and not a local-weight execution. Reports record the Together endpoint.
- **Proxy extraction without OpenAI:** The paper uses GPT-4o-mini for
  extraction. If `OPENAI_API_KEY` is intentionally unavailable, this branch can
  use a Together extraction model and records the run as proxy extraction. Those
  metrics are not exact paper-faithful extraction results.
- **Live Wikidata rate limits:** Smoke linking uses the existing live SPARQL
  analysis modules. Wikidata 429/rate-limit responses can reduce linked QIDs or
  origin-country metadata in small smoke runs; this is reported rather than
  hidden.

## README corrections

- Dataset lists **7 LLMs** (not 13).
- Hugging Face release has **approximately 5.25M rows**; the paper mentions
  85.8M generated texts. At the response level, the expected order of magnitude
  is about 6M rows (1,716 prompts x 500 responses x 7 models).
