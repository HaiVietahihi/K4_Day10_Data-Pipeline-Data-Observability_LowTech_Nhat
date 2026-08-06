from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe, save_clean_dataset
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _require_baseline(settings: Settings) -> None:
    """Phase 2 is only meaningful once phase 1 has produced its artifacts."""
    required = {
        "baseline metrics": settings.paths.baseline_metrics,
        "clean dataset": settings.paths.clean_csv,
        "frozen evaluation set": settings.paths.eval_testset,
        "raw records snapshot": settings.paths.raw_records_json,
    }
    missing = [f"{label} ({path})" for label, path in required.items() if not path.exists()]
    if missing:
        raise RuntimeError(
            "Cannot run the corruption flow before the baseline is complete. Missing:\n  - "
            + "\n  - ".join(missing)
            + "\nRun `python script/run_phase1.py` first."
        )


def _read_optional(path: Path) -> dict | None:
    """Read a JSON artifact if phase 1 produced it, otherwise report it as absent."""
    return read_json(path) if path.exists() else None


def _read_clean_csv(path: Path) -> pd.DataFrame:
    """Read a clean dataset back from CSV.

    Empty text cells come back as NaN, which would end up as `nan` inside Chroma
    metadata, so string columns are restored to empty strings here.
    """
    df = pd.read_csv(path)
    text_columns = [column for column in df.columns if df[column].dtype == object]
    df[text_columns] = df[text_columns].fillna("")
    return df


def _evaluate_state(
    settings: Settings,
    label: str,
    df: pd.DataFrame,
    embeddings_path: Path,
    metrics_path: Path,
    answers_path: Path,
):
    """Rebuild a dedicated Chroma collection for one state and score the frozen test set."""
    print(f"\n[{label}] building index ({len(df)} rows) ...")
    index = LocalEmbeddingIndex.build(df, settings, embeddings_path)
    print(f"[{label}] collection={index.collection_name} documents={len(index.documents)}")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=metrics_path,
        answers_output_path=answers_path,
    )
    summary = bundle.summary
    print(
        f"[{label}] hit_rate={summary['retrieval_hit_rate']:.3f} "
        f"token_f1={summary['mean_token_f1']:.3f} "
        f"judge_acc={summary['judge_accuracy']:.3f} "
        f"judge_score={summary['mean_judge_score']:.2f}"
    )
    return bundle


def main() -> None:
    settings = load_settings()
    paths = settings.paths
    _require_baseline(settings)

    baseline_metrics = read_json(paths.baseline_metrics)
    clean_df = _read_clean_csv(paths.clean_csv)
    print(f"[baseline] loaded {len(clean_df)} clean rows from {paths.clean_csv}")

    # --- Corruption -------------------------------------------------------------
    corrupted_df = corrupt_clean_dataframe(
        clean_df,
        paths.corruption_log,
        test_set_path=paths.eval_testset,
        baseline_answers_path=paths.baseline_answers,
    )
    save_clean_dataset(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)

    corrupted_eval = _evaluate_state(
        settings,
        "corrupted",
        corrupted_df,
        paths.corrupted_embeddings_json,
        paths.corrupted_metrics,
        paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.quality_dir / "freshness_report_corrupted.json"
    )

    # --- Repair -----------------------------------------------------------------
    # Replay the saved raw snapshot through the standard cleaning rules. Re-fetching the
    # API instead would return a different set of papers, and the frozen test set points
    # at paper_ids from the original snapshot, so the comparison would stop being fair.
    print(f"\n[repaired] replaying cleaning from {paths.raw_records_json}")
    raw_records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    save_clean_dataset(repaired_df, paths.repaired_clean_csv, paths.repaired_clean_json)

    repaired_eval = _evaluate_state(
        settings,
        "repaired",
        repaired_df,
        paths.repaired_embeddings_json,
        paths.repaired_metrics,
        paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.quality_dir / "freshness_report_repaired.json"
    )

    # --- Comparison -------------------------------------------------------------
    # Baseline observability signals come from the artifacts phase 1 already wrote, so the
    # report can show all three states side by side without re-running the baseline.
    generate_corruption_report(
        report_path=paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval.summary,
        repaired_metrics=repaired_eval.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
        baseline_quality=_read_optional(paths.quality_dir / "baseline_quality.json"),
        baseline_freshness=_read_optional(paths.freshness_report),
        corruption_log=_read_optional(paths.corruption_log),
    )

    print("\n=== baseline / corrupted / repaired ===")
    for metric in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        print(
            f"  {metric:<20} "
            f"{baseline_metrics.get(metric, float('nan')):>8.3f} "
            f"{corrupted_eval.summary[metric]:>10.3f} "
            f"{repaired_eval.summary[metric]:>9.3f}"
        )
    print(f"\n[report] {paths.comparison_report}")
