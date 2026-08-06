from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import now_utc, read_json, write_json

# Mirrors the string built by ingestion.cleaning.build_clean_dataframe so corrupted rows
# keep exactly the same schema as the baseline dataset.
EMBEDDING_TEXT_TEMPLATE = "Title: {title} | Authors: {authors} | Summary: {summary}"

STALE_PUBLISHED_DATE = "2000-01-01"
TITLE_TRUNCATE_CHARS = 18
NOISE_TEXT = (
    "!!!### lorem ipsum dolor sit amet consectetur adipiscing elit zzz qqq xyzzy "
    "000111222 @@@ unrelated boilerplate cookie policy advertisement placeholder "
    "terms and conditions apply see footer for details ###!!!"
)

DROP_COUNT = 2
DEGRADE_COUNT = 2
STALE_DATE_COUNT = 3
DUPLICATE_COUNT = 2
CONTROL_MIN = 2


def _evaluation_doc_ids(test_set_path: Path | str | None) -> list[str]:
    """Read the frozen evaluation set to learn which documents are actually asked about."""
    if test_set_path is None:
        return []
    path = Path(test_set_path)
    if not path.exists():
        return []
    doc_ids: list[str] = []
    for sample in read_json(path):
        for doc_id in sample.get("ground_truth_doc_ids") or []:
            normalised = str(doc_id).strip().lower()
            if normalised and normalised not in doc_ids:
                doc_ids.append(normalised)
    return doc_ids


def _retrieved_doc_ids(baseline_answers_path: Path | str | None) -> list[str]:
    """Read which ground-truth documents the baseline run actually retrieved.

    Damaging a document that the baseline already fails to retrieve cannot move
    `retrieval_hit_rate` - the question was a miss before and stays a miss. Only the
    documents behind a baseline hit carry measurable signal, so they are corrupted first.
    """
    if baseline_answers_path is None:
        return []
    path = Path(baseline_answers_path)
    if not path.exists():
        return []
    doc_ids: list[str] = []
    for answer in read_json(path):
        if not answer.get("retrieval_hit"):
            continue
        for doc_id in answer.get("ground_truth_doc_ids") or []:
            normalised = str(doc_id).strip().lower()
            if normalised and normalised not in doc_ids:
                doc_ids.append(normalised)
    return doc_ids


def _reference_date(df: pd.DataFrame) -> date:
    """Recover the run date used at cleaning time from `published` + `age_days`.

    Deriving it keeps recomputed `age_days` on the same clock as the baseline dataset
    instead of silently drifting when the corruption flow runs on a later day.
    """
    for _, row in df.iterrows():
        try:
            published = date.fromisoformat(str(row["published"]))
            return published + timedelta(days=int(row["age_days"]))
        except (ValueError, TypeError):
            continue
    return now_utc().date()


def _embedding_text(row: pd.Series) -> str:
    return EMBEDDING_TEXT_TEMPLATE.format(
        title=str(row["title"] or ""),
        authors=str(row["authors_joined"] or "") or "Unknown",
        summary=str(row["summary"] or ""),
    )


def _pick_targets(df: pd.DataFrame, count: int, preferred: list[str], used: set[str]) -> list[str]:
    """Choose paper_ids to damage, preferring documents the evaluation set asks about.

    Corrupting documents that no question ever retrieves would leave every metric flat,
    so evaluated documents are always consumed first.
    """
    present = set(df["paper_id"])
    chosen = [paper_id for paper_id in preferred if paper_id in present and paper_id not in used][:count]
    if len(chosen) < count:
        remaining = [
            paper_id for paper_id in df["paper_id"] if paper_id not in used and paper_id not in chosen
        ]
        chosen += remaining[: count - len(chosen)]
    used.update(chosen)
    return chosen


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path: Path | str,
    test_set_path: Path | str | None = None,
    baseline_answers_path: Path | str | None = None,
) -> pd.DataFrame:
    """Apply six controlled corruption scenarios to the clean dataset.

    Scenarios: drop records, blank summaries, truncate titles, inject unrelated noise
    into `text_for_embedding`, backdate publication dates, and duplicate rows while
    keeping the original `paper_id`.

    Targeting is deliberate rather than random. Documents behind a baseline retrieval
    hit are corrupted first, because damaging a document the baseline already fails to
    retrieve cannot move `retrieval_hit_rate`. The three text-destroying scenarios are
    stacked on the same documents so their embeddings are genuinely destroyed instead of
    merely nudged - with a 24 document corpus and top_k=4, a lightly damaged record is
    still comfortably inside the top-k. At least `CONTROL_MIN` retrievable documents are
    left untouched as a control group.

    The full change list is written to `output_log_path`.
    """
    work = df.copy().reset_index(drop=True)
    original_rows = len(work)
    reference_date = _reference_date(work)
    evaluated_ids = _evaluation_doc_ids(test_set_path)
    retrievable_ids = [
        paper_id for paper_id in _retrieved_doc_ids(baseline_answers_path) if paper_id in set(work["paper_id"])
    ]
    scenarios: list[dict[str, Any]] = []

    # Plan the targets up front so the destructive scenarios can stack on purpose.
    published_rank = {row["paper_id"]: row["published"] for _, row in work.iterrows()}
    measurable = sorted(retrievable_ids, key=lambda pid: published_rank.get(pid, ""), reverse=True)
    budget = max(0, len(measurable) - CONTROL_MIN)
    dropped = measurable[: min(DROP_COUNT, budget)]
    degraded = measurable[len(dropped) : min(len(dropped) + DEGRADE_COUNT, budget)]
    control = [paper_id for paper_id in measurable if paper_id not in dropped and paper_id not in degraded]

    # Fall back to evaluation-set order when no baseline answers are available.
    if not measurable:
        fallback = [paper_id for paper_id in evaluated_ids if paper_id in set(work["paper_id"])]
        dropped = fallback[:DROP_COUNT]
        degraded = fallback[DROP_COUNT : DROP_COUNT + DEGRADE_COUNT]
        control = fallback[DROP_COUNT + DEGRADE_COUNT :]

    used: set[str] = set(dropped) | set(degraded) | set(control)

    def log(scenario: str, description: str, parameters: dict[str, Any], paper_ids: list[str], signal: str) -> None:
        scenarios.append(
            {
                "scenario": scenario,
                "description": description,
                "parameters": parameters,
                "affected_paper_ids": paper_ids,
                "affected_rows": len(paper_ids),
                "evaluation_overlap": [paper_id for paper_id in paper_ids if paper_id in evaluated_ids],
                "expected_quality_signal": signal,
            }
        )

    # 1. Delete records outright: the only scenario that removes a document from the index.
    work = work[~work["paper_id"].isin(dropped)].reset_index(drop=True)
    log(
        "drop_records",
        "Delete retrievable records to simulate an ingestion window that silently lost data.",
        {"count": len(dropped)},
        dropped,
        "row count drops and the ground-truth documents become unretrievable",
    )

    # 2. Blank the summary, the longest and most informative part of text_for_embedding.
    mask = work["paper_id"].isin(degraded)
    work.loc[mask, "summary"] = ""
    work.loc[mask, "summary_chars"] = 0
    log(
        "blank_summary",
        "Replace the abstract with an empty string to simulate a failed field mapping upstream.",
        {"count": len(degraded)},
        degraded,
        "summary length check fails and the embedding loses its main semantic content",
    )

    # 3. Truncate the titles of the same records, stripping the little text they have left.
    work.loc[mask, "title"] = work.loc[mask, "title"].str.slice(0, TITLE_TRUNCATE_CHARS)
    log(
        "truncate_title",
        "Cut titles to a fixed prefix to simulate a column width limit in an upstream store.",
        {"count": len(degraded), "max_chars": TITLE_TRUNCATE_CHARS},
        degraded,
        "exact title lookup breaks and the title contributes far less to the embedding",
    )

    # 4. Backdate publication dates so freshness monitoring has something to catch.
    staled = _pick_targets(work, STALE_DATE_COUNT, evaluated_ids, used)
    mask = work["paper_id"].isin(staled)
    stale_date = date.fromisoformat(STALE_PUBLISHED_DATE)
    work.loc[mask, "published"] = STALE_PUBLISHED_DATE
    work.loc[mask, "age_days"] = (reference_date - stale_date).days
    log(
        "stale_publication_date",
        f"Rewrite the publication date to {STALE_PUBLISHED_DATE} to simulate a broken date parser.",
        {"count": STALE_DATE_COUNT, "published": STALE_PUBLISHED_DATE},
        staled,
        "freshness flips to stale because age_days jumps far past the threshold",
    )

    # Rebuild text_for_embedding for the blanked/truncated records, then inject noise on top.
    rebuild_mask = work["paper_id"].isin(degraded)
    if rebuild_mask.any():
        work.loc[rebuild_mask, "text_for_embedding"] = work.loc[rebuild_mask].apply(_embedding_text, axis=1)

    # 5. Inject unrelated content into what is left of the embedding text.
    work.loc[rebuild_mask, "text_for_embedding"] = work.loc[rebuild_mask, "text_for_embedding"] + " " + NOISE_TEXT
    log(
        "inject_noise",
        "Append unrelated boilerplate to text_for_embedding to simulate template or footer leakage.",
        {"count": len(degraded), "noise_chars": len(NOISE_TEXT)},
        degraded,
        "embedding drifts away from the paper topic while the record still looks complete",
    )

    # 6. Duplicate rows while keeping the original paper_id.
    duplicate_ids = _pick_targets(work, DUPLICATE_COUNT, evaluated_ids, used)
    duplicates = work[work["paper_id"].isin(duplicate_ids)].copy()
    work = pd.concat([work, duplicates], ignore_index=True)
    log(
        "duplicate_records",
        "Append copies of existing rows keeping the same paper_id to simulate a re-run that double-loaded.",
        {"count": DUPLICATE_COUNT},
        duplicate_ids,
        "paper_id uniqueness check fails and duplicated documents crowd the top-k results",
    )

    work = work.reset_index(drop=True)
    touched = sorted({paper_id for event in scenarios for paper_id in event["affected_paper_ids"]})
    payload = {
        "generated_at": now_utc().isoformat(),
        "reference_date": reference_date.isoformat(),
        "source_rows": original_rows,
        "corrupted_rows": len(work),
        "row_delta": len(work) - original_rows,
        "unique_paper_ids": int(work["paper_id"].nunique()),
        "targeting": {
            "strategy": "baseline_retrieval_hits" if retrievable_ids else "evaluation_set_order",
            "test_set_path": str(test_set_path) if test_set_path else None,
            "baseline_answers_path": str(baseline_answers_path) if baseline_answers_path else None,
            "retrievable_at_baseline": retrievable_ids,
            "dropped": dropped,
            "degraded": degraded,
            "control_left_untouched": control,
        },
        "evaluation_set": {
            "doc_ids": evaluated_ids,
            "touched_by_corruption": sorted(set(touched) & set(evaluated_ids)),
            "untouched": sorted(set(evaluated_ids) - set(touched)),
        },
        "scenarios": scenarios,
    }
    write_json(Path(output_log_path), payload)

    print(f"[corruption] {original_rows} -> {len(work)} rows across {len(scenarios)} scenarios")
    for event in scenarios:
        overlap = len(event["evaluation_overlap"])
        print(
            f"[corruption]   {event['scenario']:<24} rows={event['affected_rows']} "
            f"evaluated_docs_hit={overlap}"
        )
    print(f"[corruption] log -> {output_log_path}")
    return work
