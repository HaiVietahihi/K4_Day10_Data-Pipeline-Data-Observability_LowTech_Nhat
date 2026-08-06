# Phase 1 - Baseline Report

Generated at: 2026-08-06T08:44:46.209494+00:00

## Source summary

- **source_api**: Crossref REST API
- **source_query**: agentic retrieval augmented generation large language model
- **source_filter**: from-pub-date:2026-02-07,has-abstract:true
- **max_results**: 24
- **input_records**: 24
- **dropped_missing_paper_id**: 0
- **dropped_missing_title**: 0
- **dropped_short_summary**: 0
- **dropped_invalid_published**: 0
- **dropped_duplicate_paper_id**: 0
- **dropped_duplicate_title**: 0
- **kept_records**: 24

## Evaluation metrics

- **samples**: 10
- **retrieval_hit_rate**: 0.6000
- **mean_token_f1**: 0.0000
- **judge_accuracy**: 0.0000
- **mean_judge_score**: 1
- **ragas**: {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}

## Data quality

- **passed**: True
- **total_rows**: 24

| Check | Passed | Details |
| --- | --- | --- |
| row_count | True | 24 rows |
| paper_id_not_null | True | 0 rows with missing paper_id |
| paper_id_unique | True | 0 duplicate paper_id values |
| title_not_null | True | 0 rows with missing title |
| summary_length | True | 0 rows with summary shorter than 100 chars |
| freshness | True | 0 rows older than 180 days |

## Freshness

- **generated_at**: 2026-08-06T08:44:46.209494+00:00
- **latest_published**: 2026-08-01
- **oldest_published**: 2026-02-12
- **stale_rows**: 0
- **total_rows**: 24
- **freshness_threshold_days**: 180
- **is_fresh**: True
