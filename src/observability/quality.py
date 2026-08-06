from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json
from ingestion.cleaning import MIN_SUMMARY_CHARS


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run completeness/uniqueness/freshness checks on a clean dataset and persist the report."""
    total_rows = len(df)
    checks: list[dict[str, Any]] = []

    checks.append(
        {
            "name": "row_count",
            "passed": total_rows > 0,
            "details": f"{total_rows} rows",
        }
    )

    if "paper_id" in df.columns:
        missing_ids = int((df["paper_id"].isna() | (df["paper_id"].astype(str).str.strip() == "")).sum())
        duplicate_ids = int(df["paper_id"].duplicated().sum())
    else:
        missing_ids = total_rows
        duplicate_ids = 0
    checks.append(
        {
            "name": "paper_id_not_null",
            "passed": missing_ids == 0,
            "details": f"{missing_ids} rows with missing paper_id",
        }
    )
    checks.append(
        {
            "name": "paper_id_unique",
            "passed": duplicate_ids == 0,
            "details": f"{duplicate_ids} duplicate paper_id values",
        }
    )

    if "title" in df.columns:
        missing_titles = int((df["title"].isna() | (df["title"].astype(str).str.strip() == "")).sum())
    else:
        missing_titles = total_rows
    checks.append(
        {
            "name": "title_not_null",
            "passed": missing_titles == 0,
            "details": f"{missing_titles} rows with missing title",
        }
    )

    if "summary_chars" in df.columns:
        short_summaries = int((df["summary_chars"] < MIN_SUMMARY_CHARS).sum())
    elif "summary" in df.columns:
        short_summaries = int((df["summary"].astype(str).str.len() < MIN_SUMMARY_CHARS).sum())
    else:
        short_summaries = total_rows
    checks.append(
        {
            "name": "summary_length",
            "passed": short_summaries == 0,
            "details": f"{short_summaries} rows with summary shorter than {MIN_SUMMARY_CHARS} chars",
        }
    )

    if "age_days" in df.columns:
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
    else:
        stale_rows = 0
    checks.append(
        {
            "name": "freshness",
            "passed": stale_rows == 0,
            "details": f"{stale_rows} rows older than {settings.freshness_threshold_days} days",
        }
    )

    report = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "total_rows": total_rows,
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
    }

    output_path = settings.paths.quality_dir / f"{report_name}_quality.json"
    write_json(output_path, report)
    print(f"[quality] {report_name} quality report -> {output_path} (passed={report['passed']})")
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize dataset freshness (latest/oldest publication date, stale row count)."""
    total_rows = len(df)
    if total_rows == 0 or "published" not in df.columns or "age_days" not in df.columns:
        latest_published = None
        oldest_published = None
        stale_rows = 0
    else:
        latest_published = str(df["published"].max())
        oldest_published = str(df["published"].min())
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())

    report = {
        "generated_at": now_utc().isoformat(),
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": stale_rows == 0,
    }

    write_json(Path(report_path), report)
    print(f"[quality] freshness report -> {report_path} (is_fresh={report['is_fresh']})")
    return report
