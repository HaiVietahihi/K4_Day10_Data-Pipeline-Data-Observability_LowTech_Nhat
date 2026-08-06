from __future__ import annotations

import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from dataclasses import dataclass
from pathlib import Path

from core.config import Settings


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


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    records = []
    items = payload.get("message", {}).get("items", [])
    
    for item in items:
        # Crossref DOI
        paper_id = item.get("DOI", "")
        if not paper_id:
            continue
            
        # Title array
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""
        if not title:
            continue
            
        summary = item.get("abstract", "")
        
        # Authors
        authors = []
        for a in item.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            authors.append(f"{given} {family}".strip())
            
        # Subject/categories
        categories = item.get("subject", [])
        primary_category = categories[0] if categories else ""
        
        # Dates (created is usually present)
        pub_date = item.get("published-print") or item.get("published-online") or item.get("created")
        published = ""
        if pub_date and pub_date.get("date-parts") and pub_date["date-parts"][0]:
            parts = pub_date["date-parts"][0]
            published = "-".join(f"{p:02d}" for p in parts)
            # Pad with -01-01 if incomplete
            if len(parts) == 1:
                published += "-01-01"
            elif len(parts) == 2:
                published += "-01"
                
        # URLs
        abs_url = item.get("URL", "")
        pdf_url = ""
        links = item.get("link", [])
        if links:
            pdf_url = links[0].get("URL", "")
            
        records.append(PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=published,  # Crossref doesn't always have updated, fallback to published
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=""
        ))
        
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    session = requests.Session()
    # Retry on rate limits (429) and server errors
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    
    url = "https://api.crossref.org/works"
    response = session.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    
    # Save raw API response
    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        
    # Parse records
    records = parse_crossref_payload(payload)
    
    # Save parsed raw records
    records_dict = [vars(r) for r in records]
    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        json.dump(records_dict, f, ensure_ascii=False, indent=2)
        
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [PaperRecord(**item) for item in data]
