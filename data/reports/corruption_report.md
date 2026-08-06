# Corruption, Repair & Comparison Report

Generated at: 2026-08-06T09:47:36.619581+00:00

All three states are evaluated on the same frozen evaluation set with the same retriever and top-k, so the dataset is the only variable that changes.

## 1. RAG metrics

| Metric | Baseline | Corrupted | Repaired | Corruption impact | Repair vs baseline |
| --- | ---: | ---: | ---: | ---: | ---: |
| `samples` | 10 | 10 | 10 | +0.0000 | +0.0000 |
| `retrieval_hit_rate` | 0.6000 | 0.3000 | 0.6000 | -0.3000 | +0.0000 |
| `mean_token_f1` | 0.0000 | 0.0000 | 0.0000 | +0.0000 | +0.0000 |
| `judge_accuracy` | 0.0000 | 0.0000 | 0.0000 | +0.0000 | +0.0000 |
| `mean_judge_score` | 1 | 1 | 1 | +0.0000 | +0.0000 |

## 2. Observability signals

| Signal | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Data quality overall | PASS | FAIL | PASS |
| Rows | 24 | 24 | 24 |
| Freshness `is_fresh` | True | False | True |
| Stale rows | 0 | 3 | 0 |
| Oldest published | 2026-02-12 | 2000-01-01 | 2026-02-12 |
| Latest published | 2026-08-01 | 2026-07-01 | 2026-08-01 |

### Data quality checks

| Check | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| `row_count` | PASS — 24 rows | PASS — 24 rows | PASS — 24 rows |
| `paper_id_not_null` | PASS — 0 rows with missing paper_id | PASS — 0 rows with missing paper_id | PASS — 0 rows with missing paper_id |
| `paper_id_unique` | PASS — 0 duplicate paper_id values | FAIL — 2 duplicate paper_id values | PASS — 0 duplicate paper_id values |
| `title_not_null` | PASS — 0 rows with missing title | PASS — 0 rows with missing title | PASS — 0 rows with missing title |
| `summary_length` | PASS — 0 rows with summary shorter than 100 chars | FAIL — 2 rows with summary shorter than 100 chars | PASS — 0 rows with summary shorter than 100 chars |
| `freshness` | PASS — 0 rows older than 180 days | FAIL — 3 rows older than 180 days | PASS — 0 rows older than 180 days |

## 3. Corruption scenarios applied

Targeting strategy: `baseline_retrieval_hits`

Rows: 24 -> 24 (0), unique paper_id: 22

| Scenario | Rows | Evaluated docs hit | Expected quality signal |
| --- | ---: | ---: | --- |
| `drop_records` | 2 | 2 | row count drops and the ground-truth documents become unretrievable |
| `blank_summary` | 2 | 2 | summary length check fails and the embedding loses its main semantic content |
| `truncate_title` | 2 | 2 | exact title lookup breaks and the title contributes far less to the embedding |
| `stale_publication_date` | 3 | 3 | freshness flips to stale because age_days jumps far past the threshold |
| `inject_noise` | 2 | 2 | embedding drifts away from the paper topic while the record still looks complete |
| `duplicate_records` | 2 | 1 | paper_id uniqueness check fails and duplicated documents crowd the top-k results |

- Evaluated documents damaged: **8** of 10
- Documents the baseline actually retrieved: **6** (dropped 2, degraded 2, left untouched as control 2)

The control documents are retrievable at baseline and are deliberately never touched, so if their questions keep hitting while the damaged ones stop hitting, the drop is attributable to the targeted damage rather than to global index noise.

## 4. Reading of the results

- Corruption moved `retrieval_hit_rate` by **-0.3000** against the baseline.
- After repairing from the raw snapshot, `retrieval_hit_rate` sits **+0.0000** from the baseline.
- Data quality went PASS -> FAIL -> PASS; freshness `is_fresh` went True -> False -> True.

Repair replays the saved raw records through the standard cleaning rules instead of re-fetching the API: a fresh fetch would return a different set of papers, and the frozen evaluation set points at paper_ids from the original snapshot, so the comparison would stop being fair.

Only metrics that actually moved support a causal claim. Signals that stayed flat are reported as flat.
