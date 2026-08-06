from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import os
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import compact_join, normalize_whitespace, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"
CONTACT_EMAIL = os.getenv("CROSSREF_MAILTO", "day10-lab@example.com")
USER_AGENT = f"K4-Day10-DataObservabilityLab/1.0 (mailto:{CONTACT_EMAIL})"

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 5
INITIAL_BACKOFF_SECONDS = 2.0
MAX_BACKOFF_SECONDS = 32.0
REQUEST_TIMEOUT_SECONDS = 45


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _first_text(value: Any) -> str:
    """Crossref returns several string fields as single-element lists."""
    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, str) and entry.strip():
                return normalize_whitespace(entry)
        return ""
    if isinstance(value, str):
        return normalize_whitespace(value)
    return ""


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            unique.append(value)
    return unique


def _date_from_parts(node: Any) -> str:
    """Crossref dates look like {"date-parts": [[2026, 6, 15]]} and may be partial."""
    if not isinstance(node, dict):
        return ""
    parts = node.get("date-parts") or []
    if not parts or not isinstance(parts[0], list):
        return ""
    numbers = [int(part) for part in parts[0] if isinstance(part, (int, float))]
    if not numbers:
        return ""
    year = numbers[0]
    month = numbers[1] if len(numbers) > 1 else 1
    day = numbers[2] if len(numbers) > 2 else 1
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""


def _published_date(item: dict) -> str:
    for key in ("published", "issued", "published-online", "published-print", "posted", "created"):
        value = _date_from_parts(item.get(key))
        if value:
            return value
    return ""


def _updated_date(item: dict) -> str:
    for key in ("deposited", "indexed", "created"):
        value = _date_from_parts(item.get(key))
        if value:
            return value
    return ""


def _author_names(item: dict) -> list[str]:
    names: list[str] = []
    for author in item.get("author") or []:
        if not isinstance(author, dict):
            continue
        given = normalize_whitespace(str(author.get("given") or ""))
        family = normalize_whitespace(str(author.get("family") or ""))
        full_name = compact_join([given, family], " ") or normalize_whitespace(str(author.get("name") or ""))
        if full_name:
            names.append(full_name)
    return _dedupe(names)


def _work_type(item: dict) -> str:
    raw_type = normalize_whitespace(str(item.get("type") or ""))
    return raw_type.replace("-", " ").title() if raw_type else ""


def _categories(item: dict) -> list[str]:
    """Crossref has effectively stopped populating `subject`, so fall back to the
    publication venue and work type to keep `categories` non-empty and meaningful."""
    values = [normalize_whitespace(str(entry)) for entry in (item.get("subject") or []) if str(entry).strip()]
    if not values:
        venue = _first_text(item.get("container-title")) or _first_text(item.get("group-title"))
        values = [value for value in (venue, _work_type(item)) if value]
    return _dedupe(values)


def _abs_url(item: dict) -> str:
    url = normalize_whitespace(str(item.get("URL") or ""))
    if url:
        return url
    primary = (item.get("resource") or {}).get("primary") or {}
    return normalize_whitespace(str(primary.get("URL") or ""))


def _pdf_url(item: dict) -> str:
    for link in item.get("link") or []:
        if not isinstance(link, dict):
            continue
        url = normalize_whitespace(str(link.get("URL") or ""))
        content_type = str(link.get("content-type") or "").lower()
        if url and (content_type == "application/pdf" or url.lower().endswith(".pdf")):
            return url
    return ""


def _comment(item: dict) -> str:
    venue = _first_text(item.get("container-title"))
    publisher = normalize_whitespace(str(item.get("publisher") or ""))
    return compact_join([venue, _work_type(item), publisher], " | ")


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref `/works` payload into a list of `PaperRecord`.

    Only records carrying a DOI, a title and an abstract are kept, and DOIs are
    lowercased so `paper_id` stays stable across raw -> clean -> index -> evaluation.
    Markup inside title/abstract is preserved here on purpose: the raw snapshot must
    stay faithful to the source, stripping it is the cleaning stage's job.
    """
    items = ((payload or {}).get("message") or {}).get("items") or []
    records: list[PaperRecord] = []
    seen_ids: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = normalize_whitespace(str(item.get("DOI") or "")).lower()
        title = _first_text(item.get("title"))
        summary = normalize_whitespace(str(item.get("abstract") or ""))
        if not paper_id or not title or not summary or paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        categories = _categories(item)
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=_author_names(item),
                categories=categories,
                primary_category=categories[0] if categories else _work_type(item),
                published=_published_date(item),
                updated=_updated_date(item),
                abs_url=_abs_url(item),
                pdf_url=_pdf_url(item),
                comment=_comment(item),
            )
        )
    return records


def _retry_after_seconds(response: requests.Response) -> float | None:
    header = response.headers.get("Retry-After")
    if not header:
        return None
    try:
        return max(0.0, float(header.strip()))
    except ValueError:
        return None


def _request_with_retry(params: dict[str, Any]) -> requests.Response:
    """GET the Crossref API, retrying transient failures with exponential backoff."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    backoff = INITIAL_BACKOFF_SECONDS
    last_error = "unknown error"

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                CROSSREF_API_URL,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        else:
            if response.status_code == 200:
                return response
            last_error = f"HTTP {response.status_code}"
            if response.status_code not in RETRYABLE_STATUS_CODES:
                raise RuntimeError(f"Crossref request failed ({last_error}): {response.text[:300]}")
            retry_after = _retry_after_seconds(response)
            if retry_after is not None:
                backoff = max(backoff, retry_after)

        if attempt < MAX_ATTEMPTS:
            print(f"[crossref] attempt {attempt}/{MAX_ATTEMPTS} failed ({last_error}); retrying in {backoff:.1f}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)

    raise RuntimeError(f"Crossref request failed after {MAX_ATTEMPTS} attempts. Last error: {last_error}")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch papers from Crossref and persist both raw artifacts.

    Writes the untouched API response to `paths.raw_api_response` (audit trail) and the
    parsed flat records to `paths.raw_records_json` (the repair/replay source of truth).
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "sort": "relevance",
        "order": "desc",
        "mailto": CONTACT_EMAIL,
    }

    response = _request_with_retry(params)
    payload = response.json()
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    if not records:
        raise RuntimeError(
            "Crossref returned no usable record. Check `source_query`/`source_filter` in core/config.py "
            f"(raw response saved at {settings.paths.raw_api_response})."
        )
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])

    total = ((payload.get("message") or {}).get("total-results")) or 0
    print(
        f"[crossref] {settings.source_api}: matched {total} works, "
        f"requested {settings.max_results}, parsed {len(records)} records"
    )
    print(f"[crossref] raw response -> {settings.paths.raw_api_response}")
    print(f"[crossref] raw records  -> {settings.paths.raw_records_json}")
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load the raw record snapshot written by `fetch_source_records`.

    This is the entry point used to replay the pipeline without calling the API again,
    which keeps baseline and repaired runs comparable.
    """
    payload = read_json(Path(path))
    entries = payload.get("records", []) if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise ValueError(f"Unexpected raw records format in {path}: expected a list of records.")

    records: list[PaperRecord] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        paper_id = normalize_whitespace(str(entry.get("paper_id") or "")).lower()
        title = normalize_whitespace(str(entry.get("title") or ""))
        if not paper_id or not title:
            continue
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=str(entry.get("summary") or ""),
                authors=[normalize_whitespace(str(item)) for item in (entry.get("authors") or []) if str(item).strip()],
                categories=[
                    normalize_whitespace(str(item)) for item in (entry.get("categories") or []) if str(item).strip()
                ],
                primary_category=normalize_whitespace(str(entry.get("primary_category") or "")),
                published=normalize_whitespace(str(entry.get("published") or "")),
                updated=normalize_whitespace(str(entry.get("updated") or "")),
                abs_url=normalize_whitespace(str(entry.get("abs_url") or "")),
                pdf_url=normalize_whitespace(str(entry.get("pdf_url") or "")),
                comment=normalize_whitespace(str(entry.get("comment") or "")),
            )
        )
    return records
