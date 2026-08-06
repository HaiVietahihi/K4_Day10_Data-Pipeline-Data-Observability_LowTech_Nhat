from __future__ import annotations

import json
from datetime import UTC, datetime

import pandas as pd

from core.config import load_settings, require_llm_credentials
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("--- STARTING PHASE 2: CORRUPTION & REPAIR FLOW ---")
    settings = load_settings()
    require_llm_credentials(settings)
    run_date = datetime.now(UTC)

    # 1. Load baseline metrics & clean data
    print("1. Loading baseline clean data & metrics...")
    df_baseline = pd.read_json(settings.paths.clean_json)
    with open(settings.paths.baseline_metrics, "r", encoding="utf-8") as f:
        baseline_metrics = json.load(f)

    # 2. Làm hỏng dữ liệu (Corrupt)
    print("2. Corrupting data...")
    df_corrupt = corrupt_clean_dataframe(df_baseline, settings.paths.corruption_log)
    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df_corrupt.to_csv(settings.paths.corrupted_clean_csv, index=False)
    df_corrupt.to_json(settings.paths.corrupted_clean_json, orient="records", force_ascii=False)

    # 3. Build Vector & Evaluate trên dữ liệu hỏng
    print("3. Evaluating on CORRUPTED data...")
    index_corrupt = LocalEmbeddingIndex.build(df_corrupt, settings, settings.paths.corrupted_embeddings_json)
    eval_corrupt = evaluate_pipeline(
        settings=settings,
        index=index_corrupt,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    
    # 4. Kiểm tra Data Observability (Dự kiến sẽ báo Fail)
    print("4. Running observability on corrupted data...")
    quality_corrupt = run_data_quality_checks(df_corrupt, settings, "corrupted_quality")
    freshness_corrupt = build_freshness_report(df_corrupt, settings, settings.paths.quality_dir / "corrupted_freshness_report.json")

    # 5. REPAIR: Khôi phục bằng cách lấy lại Raw Data và Clean lại từ đầu
    print("5. REPAIRING: Reloading raw records and cleaning...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, run_date)
    settings.paths.repaired_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df_repaired.to_csv(settings.paths.repaired_clean_csv, index=False)
    df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", force_ascii=False)

    # 6. Build Vector & Evaluate trên dữ liệu đã sửa
    print("6. Evaluating on REPAIRED data...")
    index_repaired = LocalEmbeddingIndex.build(df_repaired, settings, settings.paths.repaired_embeddings_json)
    eval_repaired = evaluate_pipeline(
        settings=settings,
        index=index_repaired,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    
    # 7. Kiểm tra Data Observability (Dự kiến sẽ báo Pass trở lại)
    print("7. Running observability on repaired data...")
    quality_repaired = run_data_quality_checks(df_repaired, settings, "repaired_quality")
    freshness_repaired = build_freshness_report(df_repaired, settings, settings.paths.quality_dir / "repaired_freshness_report.json")

    # 8. Ghi báo cáo so sánh
    print("8. Generating Comparison Report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=eval_corrupt.summary,
        repaired_metrics=eval_repaired.summary,
        corrupted_quality=quality_corrupt,
        repaired_quality=quality_repaired,
        corrupted_freshness=freshness_corrupt,
        repaired_freshness=freshness_repaired,
    )
    
    print("\n[SUCCESS] Phase 2 Corruption & Repair completed!")
    print(f"   - Comparison report saved to: {settings.paths.comparison_report}")

if __name__ == "__main__":
    main()
