from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
        
    df = pd.DataFrame([vars(r) for r in records])
    
    # 1. Normalize
    def clean_text(text: str) -> str:
        if not isinstance(text, str):
            return ""
        # Xóa các thẻ HTML dư thừa (vd: <jats:title>)
        text = re.sub(r'<[^>]+>', '', text)
        return " ".join(text.split())
        
    df['title'] = df['title'].apply(clean_text)
    df['summary'] = df['summary'].apply(clean_text)
    df['title'] = df['title'].fillna("")
    df['summary'] = df['summary'].fillna("")
    
    # 2. Parse dates & 3. Tính age_days
    df['published_dt'] = pd.to_datetime(df['published'], errors='coerce', utc=True)
    if run_date.tzinfo is None:
        import datetime as dt
        run_date = run_date.replace(tzinfo=dt.timezone.utc)
    
    df['age_days'] = (run_date - df['published_dt']).dt.days
    df['age_days'] = df['age_days'].fillna(0).astype(int)
    
    # 4. Tạo helper columns
    df['authors_joined'] = df['authors'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
    df['categories_joined'] = df['categories'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
    df['summary_chars'] = df['summary'].str.len()
    
    df['text_for_embedding'] = "Title: " + df['title'] + "\nAuthors: " + df['authors_joined'] + "\nAbstract: " + df['summary']
    
    # 5. Drop duplicates và filter rows lỗi
    df = df.drop_duplicates(subset=['paper_id'], keep='first')
    df = df[df['title'].str.len() > 0]
    df = df[df['summary_chars'] > 50]  # Phải có abstract độ dài tương đối
    
    # 6. Sort
    df = df.sort_values(by='published_dt', ascending=False)
    
    return df
