from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import now_utc, write_text


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline phase markdown report (source, metrics, quality, freshness)."""
    lines: list[str] = [
        "# Phase 1 - Baseline Report",
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        "## Source summary",
        "",
    ]
    for key, value in source_summary.items():
        lines.append(f"- **{key}**: {_fmt(value)}")

    lines += ["", "## Evaluation metrics", ""]
    for key in ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        if key in metrics:
            lines.append(f"- **{key}**: {_fmt(metrics[key])}")
    if "ragas" in metrics:
        lines.append(f"- **ragas**: {metrics['ragas']}")

    lines += [
        "",
        "## Data quality",
        "",
        f"- **passed**: {quality.get('passed')}",
        f"- **total_rows**: {quality.get('total_rows')}",
        "",
        "| Check | Passed | Details |",
        "| --- | --- | --- |",
    ]
    for check in quality.get("checks", []):
        lines.append(f"| {check['name']} | {check['passed']} | {check['details']} |")

    lines += ["", "## Freshness", ""]
    for key, value in freshness.items():
        lines.append(f"- **{key}**: {_fmt(value)}")
    lines.append("")

    write_text(Path(report_path), "\n".join(lines))
    print(f"[report] phase1 report -> {report_path}")


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
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
