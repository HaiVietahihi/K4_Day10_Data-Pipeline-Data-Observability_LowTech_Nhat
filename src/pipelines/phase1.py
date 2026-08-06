from __future__ import annotations

import json
from datetime import UTC, datetime

import pandas as pd

from core.config import load_settings, require_llm_credentials
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("--- STARTING PHASE 1: BASELINE PIPELINE ---")
    settings = load_settings()
    require_llm_credentials(settings)
    run_date = datetime.now(UTC)

    # 1. Fetch or Load Raw Data
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print("1. Fetching source records...")
        raw_records = fetch_source_records(settings)
    else:
        print("1. Loading existing raw records...")
        raw_records = load_raw_records(settings.paths.raw_records_json)

    # 2. Clean Data
    print(f"2. Cleaning {len(raw_records)} records...")
    df_clean = build_clean_dataframe(raw_records, run_date)
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(settings.paths.clean_csv, index=False)
    df_clean.to_json(settings.paths.clean_json, orient="records", force_ascii=False)

    # 3. Create Vector Index
    print("3. Building local vector index (embeddings & ChromaDB)...")
    index = LocalEmbeddingIndex.build(df_clean, settings, settings.paths.embeddings_json)

    # 4. Generate Testset
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        print("4. Building test set...")
        test_set = build_test_set(df_clean, settings.paths.eval_testset)
    else:
        print("4. Loading existing test set...")
        with open(settings.paths.eval_testset, "r", encoding="utf-8") as f:
            test_set = json.load(f)

    # 5. Evaluate RAG Agent
    print(f"5. Evaluating RAG agent on {len(test_set)} questions... (this may take a few minutes)")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = eval_bundle.summary
    answers = eval_bundle.answers
        
    # 6. Data Observability
    print("6. Running data observability checks...")
    quality = run_data_quality_checks(df_clean, settings, "phase1_quality")
    freshness = build_freshness_report(df_clean, settings, settings.paths.freshness_report)

    # 7. Generate Final Report
    print("7. Generating Phase 1 Report...")
    source_summary = {
        "query": settings.source_query,
        "raw_count": len(raw_records),
        "clean_count": len(df_clean)
    }
    generate_phase1_report(settings.paths.baseline_report, source_summary, metrics, quality, freshness)

    print("\n[SUCCESS] Phase 1 Baseline completed!")
    print(f"   - Retrieval Hit Rate: {metrics.get('retrieval_hit_rate', 0):.2f}")
    print(f"   - Judge Accuracy:   {metrics.get('judge_accuracy', 0):.2f}")
    print(f"   - Report available at: {settings.paths.baseline_report}")

if __name__ == "__main__":
    main()
