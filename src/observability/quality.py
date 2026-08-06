from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    total_rows = len(df)
    
    # Check paper_id null and uniqueness
    null_ids = df['paper_id'].isnull().sum()
    duplicate_ids = df.duplicated(subset=['paper_id']).sum()
    
    # Check title null
    null_titles = df['title'].isnull().sum() + (df['title'] == "").sum()
    
    # Check summary length (dưới 50 ký tự coi như lỗi)
    short_summaries = (df['summary'].str.len() < 50).sum()
    
    # Check freshness
    stale_rows = (df['age_days'] > settings.freshness_threshold_days).sum()
    
    # Passed nếu không vi phạm nào
    success = (
        total_rows > 0 and 
        null_ids == 0 and 
        duplicate_ids == 0 and 
        null_titles == 0 and 
        short_summaries == 0 and
        stale_rows == 0
    )
    
    report = {
        "report_name": report_name,
        "total_rows": int(total_rows),
        "null_ids": int(null_ids),
        "duplicate_ids": int(duplicate_ids),
        "null_titles": int(null_titles),
        "short_summaries": int(short_summaries),
        "stale_rows": int(stale_rows),
        "success": bool(success)
    }
    
    out_path = settings.paths.quality_dir / f"{report_name}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    if len(df) == 0:
        return {"error": "Empty dataframe"}
        
    latest_published = df['published'].max()
    oldest_published = df['published'].min()
    stale_rows = (df['age_days'] > settings.freshness_threshold_days).sum()
    
    is_fresh = stale_rows == 0
    
    report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": int(stale_rows),
        "total_rows": len(df),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": bool(is_fresh)
    }
    
    out_path = Path(report_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    return report
