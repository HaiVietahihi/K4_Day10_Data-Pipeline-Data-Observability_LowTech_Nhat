from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import html
import re

import pandas as pd

from core.utils import compact_join, normalize_whitespace, write_csv, write_json
from ingestion.crossref import PaperRecord

MIN_SUMMARY_CHARS = 100
MARKUP_PATTERN = re.compile(r"<[^>]+>")
ABSTRACT_LABEL_PATTERN = re.compile(r"^(abstract|summary|resumen)\s*[:.\-–—]?\s+", re.IGNORECASE)
DATE_FORMATS = (("%Y-%m-%d", 10), ("%Y/%m/%d", 10), ("%Y-%m", 7), ("%Y", 4))

CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "published",
    "authors_joined",
    "categories_joined",
    "age_days",
    "text_for_embedding",
    "abs_url",
    "pdf_url",
    "primary_category",
    "updated",
    "summary_chars",
    "authors_count",
    "categories_count",
    "comment",
]


def strip_markup(value: str) -> str:
    """Remove XML/HTML markup from a Crossref text field.

    Crossref abstracts are JATS wrapped and frequently double-encoded, e.g.
    `<jats:p>&lt;strong&gt;...` - so entities are decoded before tags are removed,
    otherwise the escaped tags survive into `text_for_embedding` as noise.
    """
    text = str(value or "")
    for _ in range(3):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded
    text = MARKUP_PATTERN.sub(" ", text)
    return normalize_whitespace(html.unescape(text))


def _clean_summary(value: str) -> str:
    return ABSTRACT_LABEL_PATTERN.sub("", strip_markup(value)).strip()


def _clean_values(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        item = strip_markup(str(value))
        if item and item.lower() not in seen:
            seen.add(item.lower())
            cleaned.append(item)
    return cleaned


def _parse_published(value: str) -> date | None:
    """Normalise a publication date to a real `date`, tolerating partial values."""
    text = normalize_whitespace(str(value or ""))
    if not text:
        return None
    for date_format, length in DATE_FORMATS:
        try:
            return datetime.strptime(text[:length], date_format).date()
        except ValueError:
            continue
    return None


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Turn raw `PaperRecord` objects into the embedding-ready clean dataset.

    Cleaning rules: drop records without a title, drop abstracts shorter than
    `MIN_SUMMARY_CHARS`, strip XML/HTML markup, flatten authors/categories into
    comma-joined strings, normalise `published` to YYYY-MM-DD, derive `age_days`
    against `run_date`, and build `text_for_embedding`.

    Every column is a scalar (no list columns): the clean CSV is read back by the
    corruption/repair flow and Chroma metadata only accepts scalar values.

    Drop and dedupe counters are printed and attached to `df.attrs["cleaning_stats"]`
    so no record disappears silently.
    """
    run_day = run_date.date() if isinstance(run_date, datetime) else run_date
    stats = {
        "input_records": len(records),
        "dropped_missing_paper_id": 0,
        "dropped_missing_title": 0,
        "dropped_short_summary": 0,
        "dropped_invalid_published": 0,
        "dropped_duplicate_paper_id": 0,
        "dropped_duplicate_title": 0,
        "kept_records": 0,
    }

    rows: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    seen_titles: set[str] = set()

    for record in records:
        paper_id = normalize_whitespace(str(record.paper_id or "")).lower()
        title = strip_markup(record.title)
        summary = _clean_summary(record.summary)

        if not paper_id:
            stats["dropped_missing_paper_id"] += 1
            continue
        if not title:
            stats["dropped_missing_title"] += 1
            continue
        if len(summary) < MIN_SUMMARY_CHARS:
            stats["dropped_short_summary"] += 1
            continue

        published_date = _parse_published(record.published)
        if published_date is None:
            stats["dropped_invalid_published"] += 1
            continue
        if paper_id in seen_ids:
            stats["dropped_duplicate_paper_id"] += 1
            continue
        if title.lower() in seen_titles:
            stats["dropped_duplicate_title"] += 1
            continue

        seen_ids.add(paper_id)
        seen_titles.add(title.lower())

        authors = _clean_values(record.authors)
        categories = _clean_values(record.categories)
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        updated_date = _parse_published(record.updated)

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "published": published_date.isoformat(),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "age_days": (run_day - published_date).days,
                "text_for_embedding": (
                    f"Title: {title} | Authors: {authors_joined or 'Unknown'} | Summary: {summary}"
                ),
                "abs_url": strip_markup(record.abs_url),
                "pdf_url": strip_markup(record.pdf_url),
                "primary_category": strip_markup(record.primary_category) or (categories[0] if categories else ""),
                "updated": updated_date.isoformat() if updated_date else "",
                "summary_chars": len(summary),
                "authors_count": len(authors),
                "categories_count": len(categories),
                "comment": strip_markup(record.comment),
            }
        )

    df = pd.DataFrame(rows, columns=CLEAN_COLUMNS)
    if not df.empty:
        df = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    stats["kept_records"] = len(df)
    df.attrs["cleaning_stats"] = stats

    dropped = ", ".join(f"{key.removeprefix('dropped_')}={value}" for key, value in stats.items() if key.startswith("dropped_"))
    print(f"[cleaning] kept {stats['kept_records']}/{stats['input_records']} records (dropped: {dropped})")
    return df


def save_clean_dataset(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    """Persist the clean dataset as both CSV and JSON."""
    write_csv(df, Path(csv_path))
    payload = [
        {key: (value.item() if hasattr(value, "item") else value) for key, value in row.items()}
        for row in df.to_dict(orient="records")
    ]
    write_json(Path(json_path), payload)
    print(f"[cleaning] clean dataset -> {csv_path} | {json_path}")
