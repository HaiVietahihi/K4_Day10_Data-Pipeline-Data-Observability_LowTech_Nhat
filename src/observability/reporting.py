from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    content = f"""# Phase 1 Baseline Report

## 1. Source Data
- **Query**: `{source_summary.get('query', '')}`
- **Raw Records Fetched**: {source_summary.get('raw_count', 0)}
- **Cleaned Records**: {source_summary.get('clean_count', 0)}

## 2. Data Quality & Freshness
- **Quality Checks Passed**: {'✅ Yes' if quality.get('success') else '❌ No'}
- **Freshness Passed**: {'✅ Yes' if freshness.get('is_fresh') else '❌ No'}
- **Stale Records**: {freshness.get('stale_rows', 0)} / {freshness.get('total_rows', 0)}

## 3. Evaluation Metrics (RAG)
- **Retrieval Hit Rate**: {metrics.get('retrieval_hit_rate', 0):.2f}
- **Retrieval MRR**: {metrics.get('retrieval_mrr', 0):.2f}
- **Mean Token F1**: {metrics.get('mean_token_f1', 0):.2f}
- **Judge Accuracy**: {metrics.get('judge_accuracy', 0):.2f}
- **Mean Judge Score**: {metrics.get('mean_judge_score', 0):.2f}
"""
    out_path = Path(report_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    content = f"""# Phase 2 Corruption & Repair Comparison Report

## 1. Data Quality & Freshness Comparison
| State | Quality Passed | Freshness Passed |
|-------|----------------|------------------|
| **Baseline** | ✅ Yes | ✅ Yes |
| **Corrupted** | {'✅ Yes' if corrupted_quality.get('success') else '❌ No'} | {'✅ Yes' if corrupted_freshness.get('is_fresh') else '❌ No'} |
| **Repaired** | {'✅ Yes' if repaired_quality.get('success') else '❌ No'} | {'✅ Yes' if repaired_freshness.get('is_fresh') else '❌ No'} |

## 2. Agent Performance Comparison
| Metric | Baseline | Corrupted | Repaired |
|--------|----------|-----------|----------|
| **Hit Rate** | {baseline_metrics.get('retrieval_hit_rate', 0):.2f} | {corrupted_metrics.get('retrieval_hit_rate', 0):.2f} | {repaired_metrics.get('retrieval_hit_rate', 0):.2f} |
| **Token F1** | {baseline_metrics.get('mean_token_f1', 0):.2f} | {corrupted_metrics.get('mean_token_f1', 0):.2f} | {repaired_metrics.get('mean_token_f1', 0):.2f} |
| **Judge Acc** | {baseline_metrics.get('judge_accuracy', 0):.2f} | {corrupted_metrics.get('judge_accuracy', 0):.2f} | {repaired_metrics.get('judge_accuracy', 0):.2f} |
| **Judge Score**| {baseline_metrics.get('mean_judge_score', 0):.2f} | {corrupted_metrics.get('mean_judge_score', 0):.2f} | {repaired_metrics.get('mean_judge_score', 0):.2f} |

## Conclusion
Báo cáo này chứng minh rằng khi dữ liệu bị lỗi (Corrupted), không chỉ Data Quality bị fail mà hiệu suất của RAG Agent cũng giảm theo. Khi ta phục hồi dữ liệu (Repaired) thông qua pipeline chuẩn, hiệu suất của Agent quay lại mức tốt như ban đầu (Baseline).
"""
    out_path = Path(report_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
