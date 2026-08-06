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


METRIC_KEYS = ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")


def _delta(current: Any, reference: Any) -> str:
    if not isinstance(current, (int, float)) or not isinstance(reference, (int, float)):
        return "n/a"
    return f"{float(current) - float(reference):+.4f}"


def _status(quality: dict[str, Any] | None) -> str:
    if not quality:
        return "n/a"
    return "PASS" if quality.get("passed") else "FAIL"


def _checks_by_name(quality: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    return {check["name"]: check for check in (quality or {}).get("checks", [])}


def _check_cell(quality: dict[str, Any] | None, name: str) -> str:
    check = _checks_by_name(quality).get(name)
    if check is None:
        return "n/a"
    return f"{'PASS' if check.get('passed') else 'FAIL'} — {check.get('details', '')}"


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
    corruption_log: dict[str, Any] | None = None,
) -> None:
    """Write the baseline/corrupted/repaired comparison report.

    The three states are scored on the same frozen evaluation set, so every difference
    in this report is attributable to the dataset rather than to the questions.
    """
    lines: list[str] = [
        "# Corruption, Repair & Comparison Report",
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        "All three states are evaluated on the same frozen evaluation set with the same "
        "retriever and top-k, so the dataset is the only variable that changes.",
        "",
        "## 1. RAG metrics",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Corruption impact | Repair vs baseline |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in METRIC_KEYS:
        if key not in baseline_metrics and key not in corrupted_metrics:
            continue
        baseline_value = baseline_metrics.get(key)
        corrupted_value = corrupted_metrics.get(key)
        repaired_value = repaired_metrics.get(key)
        lines.append(
            f"| `{key}` | {_fmt(baseline_value)} | {_fmt(corrupted_value)} | {_fmt(repaired_value)} "
            f"| {_delta(corrupted_value, baseline_value)} | {_delta(repaired_value, baseline_value)} |"
        )

    lines += [
        "",
        "## 2. Observability signals",
        "",
        "| Signal | Baseline | Corrupted | Repaired |",
        "| --- | --- | --- | --- |",
        f"| Data quality overall | {_status(baseline_quality)} | {_status(corrupted_quality)} "
        f"| {_status(repaired_quality)} |",
        f"| Rows | {_fmt((baseline_quality or {}).get('total_rows'))} "
        f"| {_fmt(corrupted_quality.get('total_rows'))} | {_fmt(repaired_quality.get('total_rows'))} |",
        f"| Freshness `is_fresh` | {_fmt((baseline_freshness or {}).get('is_fresh'))} "
        f"| {_fmt(corrupted_freshness.get('is_fresh'))} | {_fmt(repaired_freshness.get('is_fresh'))} |",
        f"| Stale rows | {_fmt((baseline_freshness or {}).get('stale_rows'))} "
        f"| {_fmt(corrupted_freshness.get('stale_rows'))} | {_fmt(repaired_freshness.get('stale_rows'))} |",
        f"| Oldest published | {_fmt((baseline_freshness or {}).get('oldest_published'))} "
        f"| {_fmt(corrupted_freshness.get('oldest_published'))} "
        f"| {_fmt(repaired_freshness.get('oldest_published'))} |",
        f"| Latest published | {_fmt((baseline_freshness or {}).get('latest_published'))} "
        f"| {_fmt(corrupted_freshness.get('latest_published'))} "
        f"| {_fmt(repaired_freshness.get('latest_published'))} |",
    ]

    check_names = list(
        dict.fromkeys(
            list(_checks_by_name(baseline_quality))
            + list(_checks_by_name(corrupted_quality))
            + list(_checks_by_name(repaired_quality))
        )
    )
    if check_names:
        lines += [
            "",
            "### Data quality checks",
            "",
            "| Check | Baseline | Corrupted | Repaired |",
            "| --- | --- | --- | --- |",
        ]
        for name in check_names:
            lines.append(
                f"| `{name}` | {_check_cell(baseline_quality, name)} "
                f"| {_check_cell(corrupted_quality, name)} | {_check_cell(repaired_quality, name)} |"
            )

    if corruption_log:
        evaluation = corruption_log.get("evaluation_set", {})
        targeting = corruption_log.get("targeting", {})
        lines += [
            "",
            "## 3. Corruption scenarios applied",
            "",
            f"Targeting strategy: `{targeting.get('strategy', 'unknown')}`",
            "",
            f"Rows: {_fmt(corruption_log.get('source_rows'))} -> {_fmt(corruption_log.get('corrupted_rows'))} "
            f"({_fmt(corruption_log.get('row_delta'))}), unique paper_id: "
            f"{_fmt(corruption_log.get('unique_paper_ids'))}",
            "",
            "| Scenario | Rows | Evaluated docs hit | Expected quality signal |",
            "| --- | ---: | ---: | --- |",
        ]
        for scenario in corruption_log.get("scenarios", []):
            lines.append(
                f"| `{scenario['scenario']}` | {scenario['affected_rows']} "
                f"| {len(scenario['evaluation_overlap'])} | {scenario['expected_quality_signal']} |"
            )
        touched = evaluation.get("touched_by_corruption", [])
        control = targeting.get("control_left_untouched", [])
        retrievable = targeting.get("retrievable_at_baseline", [])
        lines += [
            "",
            f"- Evaluated documents damaged: **{len(touched)}** of {len(evaluation.get('doc_ids', []))}",
            f"- Documents the baseline actually retrieved: **{len(retrievable)}** "
            f"(dropped {len(targeting.get('dropped', []))}, "
            f"degraded {len(targeting.get('degraded', []))}, "
            f"left untouched as control {len(control)})",
            "",
            "The control documents are retrievable at baseline and are deliberately never touched, "
            "so if their questions keep hitting while the damaged ones stop hitting, the drop is "
            "attributable to the targeted damage rather than to global index noise.",
        ]

    lines += ["", "## 4. Reading of the results", ""]
    hit_delta = _delta(corrupted_metrics.get("retrieval_hit_rate"), baseline_metrics.get("retrieval_hit_rate"))
    recovery_delta = _delta(repaired_metrics.get("retrieval_hit_rate"), baseline_metrics.get("retrieval_hit_rate"))
    lines += [
        f"- Corruption moved `retrieval_hit_rate` by **{hit_delta}** against the baseline.",
        f"- After repairing from the raw snapshot, `retrieval_hit_rate` sits **{recovery_delta}** "
        "from the baseline.",
        f"- Data quality went {_status(baseline_quality)} -> {_status(corrupted_quality)} -> "
        f"{_status(repaired_quality)}; freshness `is_fresh` went "
        f"{_fmt((baseline_freshness or {}).get('is_fresh'))} -> {_fmt(corrupted_freshness.get('is_fresh'))} -> "
        f"{_fmt(repaired_freshness.get('is_fresh'))}.",
        "",
        "Repair replays the saved raw records through the standard cleaning rules instead of "
        "re-fetching the API: a fresh fetch would return a different set of papers, and the frozen "
        "evaluation set points at paper_ids from the original snapshot, so the comparison would "
        "stop being fair.",
        "",
        "Only metrics that actually moved support a causal claim. Signals that stayed flat are "
        "reported as flat.",
        "",
    ]

    write_text(Path(report_path), "\n".join(lines))
    print(f"[report] corruption comparison report -> {report_path}")
