# MAKIEval Smoke Reproduction Comparison

Scope: small-sample, not paper-scale. Published data may be an older snapshot per the author.

- Model: `Qwen2.5-7B-Instruct`
- Together endpoint: `Qwen/Qwen2.5-7B-Instruct-Turbo`
- Slice: `en / book / United States`
- Our N: `3`
- Published N used: `3` (limit=3)
- Extraction status: `completed`

## Deviations

- Together serving endpoint used: Qwen/Qwen2.5-7B-Instruct-Turbo.
- Provider serving variant uses a Turbo endpoint, not local weights.
- OPENAI_API_KEY not used; GPT-4o-mini extraction replaced by Together proxy extraction.

## Metric Comparison

| Metric | Ours | Published | Status | Comment |
|---|---:|---:|---|---|
| granularity | 0.8333 | 1.0000 | DIVERGE | Small N; exact match is not expected. |
| diversity | 1.0000 | 2.0000 | DIVERGE | Small N; exact match is not expected. |
| culture_specificity | 0.0000 | 0.0000 | N/A (origin lookup not supplied) | Needs --country-origin-map; not evaluated here. |
| entity_count | 6.0000 | 9.0000 | DIVERGE | Small N; exact match is not expected. |
| unique_qids | 1.0000 | 2.0000 | DIVERGE | Small N; exact match is not expected. |
| qid_set_jaccard | 0.0000 | n/a | DIVERGE | Entity-set overlap between our slice and published slice. |
| dominant_qid | Q508865 (2) | Q212340 (2) | DIVERGE | Mode QID comparison. |
| degenerate_rate | 0.0000 | 0.0000 | MATCH | Rule-based repeated text check. |
| language_leakage_rate | 0.0000 | 0.0000 | MATCH | langid/script detector. |

## Notes

- Diversity and consensus are N-sensitive; this comparison is directional only.
- Published culture specificity is `0.0` here unless per-QID origin lookup metadata is supplied.
- GPT-4o-mini extraction was not used because OPENAI_API_KEY is intentionally unavailable.
