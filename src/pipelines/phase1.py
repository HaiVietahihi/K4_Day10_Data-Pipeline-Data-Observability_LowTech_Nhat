from __future__ import annotations

from core.config import load_settings, require_llm_credentials
from core.utils import now_utc
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe, save_clean_dataset
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    settings = load_settings()

    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)

    df = build_clean_dataframe(records, run_date=now_utc())
    save_clean_dataset(df, settings.paths.clean_csv, settings.paths.clean_json)

    index = LocalEmbeddingIndex.build(df, settings)

    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(df, settings.paths.eval_testset)

    require_llm_credentials(settings)
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    quality = run_data_quality_checks(df, settings, report_name="baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "max_results": settings.max_results,
        **df.attrs.get("cleaning_stats", {}),
    }

    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )

    print(
        "[phase1] baseline pipeline complete: "
        f"retrieval_hit_rate={bundle.summary['retrieval_hit_rate']:.3f}, "
        f"mean_token_f1={bundle.summary['mean_token_f1']:.3f}, "
        f"judge_accuracy={bundle.summary['judge_accuracy']:.3f}"
    )
