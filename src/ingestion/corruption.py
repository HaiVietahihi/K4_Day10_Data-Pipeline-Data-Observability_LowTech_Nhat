from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    if len(df) == 0:
        return df
        
    df_corrupt = df.copy()
    log = []
    
    # 1. Xóa 2 bài báo mới nhất (để làm giảm Hit Rate khi tìm các bài này)
    latest_indices = df_corrupt.sort_values(by='published_dt', ascending=False).head(2).index
    df_corrupt = df_corrupt.drop(latest_indices).reset_index(drop=True)
    log.append(f"Dropped 2 latest records.")
    
    # Lấy các index an toàn
    n = len(df_corrupt)
    if n == 0:
        return df_corrupt
        
    # 2. Xóa nội dung tóm tắt ở 2 dòng
    blank_idx = random.sample(range(n), min(2, n))
    for idx in blank_idx:
        df_corrupt.at[idx, 'summary'] = ""
    log.append(f"Blanked summaries at indices {blank_idx}.")
    
    # 3. Chèn nhiễu (noise) vào văn bản
    noise_idx = random.sample(range(n), min(3, n))
    for idx in noise_idx:
        df_corrupt.at[idx, 'summary'] = str(df_corrupt.at[idx, 'summary']) + " X-X-X RAG-NOISE-DATA "
    log.append(f"Injected noise into summaries at indices {noise_idx}.")
    
    # 4. Cắt vụn tiêu đề
    trunc_idx = random.sample(range(n), min(2, n))
    for idx in trunc_idx:
        title = str(df_corrupt.at[idx, 'title'])
        df_corrupt.at[idx, 'title'] = title[:10] + "..." if len(title) > 10 else title
    log.append(f"Truncated titles at indices {trunc_idx}.")
    
    # 5. Làm cho dữ liệu bị cũ (cộng thêm 200 ngày vào age_days)
    stale_idx = random.sample(range(n), min(3, n))
    for idx in stale_idx:
        df_corrupt.at[idx, 'age_days'] = df_corrupt.at[idx, 'age_days'] + 200
    log.append(f"Made dates stale at indices {stale_idx}.")
    
    # 6. Tạo dòng trùng lặp (Duplicate)
    dup_row = df_corrupt.iloc[[0]].copy()
    df_corrupt = pd.concat([df_corrupt, dup_row], ignore_index=True)
    log.append("Added 1 duplicate row.")
    
    # 7. Rebuild text_for_embedding để phản ánh các lỗi trên vào vector
    df_corrupt['text_for_embedding'] = "Title: " + df_corrupt['title'] + "\nAuthors: " + df_corrupt['authors_joined'] + "\nAbstract: " + df_corrupt['summary']
    
    # 8. Ghi log các hành động phá hoại
    out_path = Path(output_log_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
        
    return df_corrupt
