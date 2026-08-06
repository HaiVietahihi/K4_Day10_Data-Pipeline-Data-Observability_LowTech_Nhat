from __future__ import annotations

import json
from typing import Any

import pandas as pd


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    if len(df) == 0:
        return []
        
    # Chọn ngẫu nhiên vài bài báo, hoặc lấy n bài đầu tiên (ví dụ 5 bài)
    # Vì df đã sort theo published_dt, ta lấy 5 bài mới nhất để tạo test set
    sample_df = df.head(5)
    
    test_set = []
    idx = 1
    
    for _, row in sample_df.iterrows():
        # 1. Câu hỏi về tóm tắt (summary)
        test_set.append({
            "id": f"q_{idx}",
            "question_type": "summary",
            "question": f"What is the main topic or abstract of the paper '{row['title']}'?",
            "ground_truth": row['summary'],
            "ground_truth_doc_ids": [row['paper_id']]
        })
        idx += 1
        
        # 2. Câu hỏi về tác giả (authors)
        if row['authors_joined']:
            test_set.append({
                "id": f"q_{idx}",
                "question_type": "authors",
                "question": f"Who are the authors of the paper titled '{row['title']}'?",
                "ground_truth": row['authors_joined'],
                "ground_truth_doc_ids": [row['paper_id']]
            })
            idx += 1
            
        # 3. Câu hỏi về ngày xuất bản (date)
        if row['published']:
            test_set.append({
                "id": f"q_{idx}",
                "question_type": "date",
                "question": f"When was the paper '{row['title']}' published?",
                "ground_truth": str(row['published']),
                "ground_truth_doc_ids": [row['paper_id']]
            })
            idx += 1
            
        # 4. Câu hỏi về categories (nếu có)
        if row['categories_joined']:
            test_set.append({
                "id": f"q_{idx}",
                "question_type": "categories",
                "question": f"What are the subject categories for '{row['title']}'?",
                "ground_truth": row['categories_joined'],
                "ground_truth_doc_ids": [row['paper_id']]
            })
            idx += 1

    # Ghi file JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(test_set, f, ensure_ascii=False, indent=2)
        
    return test_set
