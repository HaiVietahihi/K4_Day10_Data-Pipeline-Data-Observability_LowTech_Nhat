# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                                                                                 |
| ----------------- | ---------------------------------------------------------------------------------------- |
| Khóa/Lớp         | K4                                                                                       |
| Tên nhóm         | LowTech Nhat                                                                             |
| Repository        | https://github.com/HaiVietahihi/K4_Day10_Data-Pipeline-Data-Observability_LowTech_Nhat.git |
| Ngày hoàn thành | 2026-08-06                                                                               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Hoàng Minh | 2A202601764 | Source Ingestion & Cleaning Owner | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `data/raw/`, `data/clean/` |
| 2 | Nguyễn Việt Hải | 2A202601656 | Frozen Evaluation Set & Vector Store Owner | `src/evaluation/testset.py`, `src/retrieval/index.py`, `data/eval/test_set.json`, `data/chroma/` |
| 3 | Nguyễn Thái Tú | 2A202601504 | Observability & Baseline Orchestration Owner | `src/observability/quality.py`, `src/observability/reporting.py`, `src/pipelines/phase1.py`, `data/reports/phase1_report.md` |
| 4 | Đoàn Văn Tuyền | 2A202601374 | Corruption Simulation & Repair Flow Owner | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py`, `data/results/corruption_log.json`, `data/reports/corruption_report.md` |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm LowTech Nhất đã xây dựng và thực thi thành công toàn bộ luồng Data Pipeline, Data Observability và RAG Evaluation end-to-end qua hai pha (Baseline và Corruption/Repair). 

Ở Pha 1 (Baseline), dữ liệu thô gồm 24 bài báo được thu thập từ Crossref REST API (`data/raw/crossref_records.json`), làm sạch và cấu hình thành `papers_clean.csv`/`json`, sau đó mã hóa vector bằng mô hình `all-MiniLM-L6-v2` và nạp vào cơ sở dữ liệu ChromaDB (`data/chroma/`). Nhóm đã đóng băng bộ câu hỏi đánh giá 10 mẫu (`data/eval/test_set.json`). Kết quả Baseline đạt `retrieval_hit_rate = 0.6000`, với toàn bộ 6 tiêu chí Data Quality và Freshness đều đạt trạng thái PASS.

Ở Pha 2 (Corruption & Repair), nhóm thiết lập 6 kịch bản suy hao dữ liệu có mục tiêu (xóa bản ghi, xóa summary, lùi ngày xuất bản, chèn nhiễu, trùng lặp bản ghi và cắt tiêu đề) tác động trực tiếp lên 8/10 tài liệu thuộc tập test. Tác động của suy hao khiến `retrieval_hit_rate` sụt giảm 50% (từ 0.6000 xuống 0.3000), đồng thời các tín hiệu Observability bật cảnh báo FAIL (xuất hiện 2 lỗi trùng lặp `paper_id`, 2 tóm tắt rỗng và 3 bản ghi bị stale publication date). Sau khi chạy luồng Repair tái sinh dữ liệu từ snapshot thô ban đầu, toàn bộ chỉ số Quality & Freshness phục hồi về PASS, đồng thời `retrieval_hit_rate` được khôi phục hoàn toàn về mức 0.6000. 

Giới hạn chính hiện tại là mô hình nhúng local nhỏ (384D) và tập câu hỏi tập trung vào factual QA; hướng phát triển tiếp theo là mở rộng tập test lên 30–50 câu hỏi đa tài liệu và áp dụng model nhúng độ phân giải cao hơn.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API
    -> raw response/raw records (data/raw/crossref_records.json)
    -> cleaning và data modeling (data/clean/papers_clean.csv / json)
    -> embedding + ChromaDB index (data/chroma/, papers_embeddings.json)
    -> evaluation baseline (data/eval/test_set.json)
    -> quality/freshness reports (data/quality/, baseline_quality.json)
    -> corruption (6 targeted scenarios)
    -> re-index và re-evaluate corrupted vector store
    -> repair từ dữ liệu nguồn thô (crossref_records.json)
    -> comparison report (data/reports/corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API | Fetch API, handle retry, parse JSON thành `PaperRecord` | `data/raw/crossref_response.json`, `crossref_records.json` | Nguyễn Hoàng Minh |
| Cleaning          | `crossref_records.json` | Strip HTML tags, chuẩn hóa khoảng trắng, tính `age_days` & `text_for_embedding` | `data/clean/papers_clean.csv`, `papers_clean.json` | Nguyễn Hoàng Minh |
| Embedding/index   | `papers_clean.json` | Nhúng văn bản với `all-MiniLM-L6-v2`, nạp ChromaDB persistent store | `data/chroma/`, `data/embeddings/papers_embeddings.json` | Nguyễn Việt Hải |
| Evaluation        | `papers_clean.json` | Đóng băng 10 câu hỏi factual QA với exact ground truth & doc IDs | `data/eval/test_set.json` | Nguyễn Việt Hải |
| Observability     | Clean DataFrame | Chạy 6 bài test data quality và đo ngưỡng freshness (180 ngày) | `data/quality/baseline_quality.json`, `freshness_report.json` | Nguyễn Thái Tú |
| Corruption/repair | Clean DataFrame & Raw snapshot | Giả lập 6 dạng suy hao dữ liệu có mục tiêu và replay raw snapshot để repair | `data/results/corruption_log.json`, `data/reports/corruption_report.md` | Đoàn Văn Tuyền |
| Orchestration     | Config & Modules | Điều phối thứ tự thực thi toàn bộ pipeline Pha 1 và Pha 2 | `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` | Nguyễn Thái Tú & Đoàn Văn Tuyền |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini` (hoặc mock/ollama) |
| `LLM_MODEL`                | `gemini-2.5-flash` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records    | `24` |
| Retrieval `top_k`           | `4` |
| Freshness threshold          | `180` ngày |
| Random seed, nếu có        | N/A |

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | ---------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công | 2026-08-06 | `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter                | `agentic retrieval augmented generation large language model`, `from-pub-date: 180 days ago, has-abstract: true` |
| Thời điểm lấy dữ liệu | 2026-08-06 |
| Số record nhận được    | 24 records |
| Cơ chế retry/backoff      | `requests.Session` kết hợp HTTPAdapter (max_retries=3, backoff_factor=1) |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| ------- | ------------ | ---------- | --------- | ---------------------- |
| `paper_id` | `str` | Có | DOI duy nhất của bài báo (Primary Key) | Bỏ qua bản ghi nếu thiếu DOI |
| `title` | `str` | Có | Tiêu đề bài báo | Loại bỏ thẻ HTML/XML markup |
| `summary` | `str` | Có | Tóm tắt (abstract) bài báo | Lọc bỏ nếu ngắn hơn 100 ký tự |
| `published` | `str` | Có | Ngày xuất bản (YYYY-MM-DD) | Đặt giá trị ngày hiện tại làm mặc định |
| `authors_joined` | `str` | Có | Danh sách tác giả | Nối các tên tác giả bằng dấu phẩy |
| `categories_joined` | `str` | Có | Tạp chí / Chủ đề | Nối các danh mục bằng dấu phẩy |
| `text_for_embedding` | `str` | Có | Văn bản định dạng để nhúng vector | Kết hợp `Title + Authors + Summary` |
| `age_days` | `int` | Có | Tuổi của bài báo tính theo ngày | Tự động tính từ `published` so với ngày chạy |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| ------- | ---------------------------- | ---------------------: | -------------------- |
| Lọc bỏ thẻ HTML/XML markup khỏi Title và Summary | Validity | 24 | Regex check `<[^>]+>` trả về 0 kết quả |
| Chuẩn hóa khoảng trắng và dấu ngắt dòng | Validity | 24 | Regex check `\s+` được thay bằng khoảng trắng đơn |
| Tạo chuỗi đại diện nhúng `text_for_embedding` | Completeness | 24 | Kiểm tra 100% bản ghi có định dạng `Title: ... \| Authors: ... \| Summary: ...` |
| Tính số ngày tuổi `age_days` | Timeliness | 24 | `age_days` được tính chính xác bằng chênh lệch ngày chạy so với `published` |

**Giải thích tạo `text_for_embedding`, document ID và `age_days`:**
- `text_for_embedding`: Được ghép theo cấu trúc chuẩn `Title: {title} | Authors: {authors_joined} | Summary: {summary}` để giữ lại đầy đủ thông tin ngữ nghĩa cốt lõi cho mô hình nhúng.
- Document ID: Sử dụng chính `paper_id` (DOI) làm định danh duy nhất để liên kết giữa Vector Database và Ground Truth Document IDs trong tập test set.
- `age_days`: Được tính bằng hiệu số số ngày giữa mốc thời gian chạy pipeline (`run_date`) và ngày xuất bản `published` của bài báo.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 câu hỏi |
| Các `question_type`                    | `factual` |
| Ground-truth document ID                 | DOI chính xác của bài báo chứa thông tin đáp án (`ground_truth_doc_ids`) |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) |
| Vector store/collection                  | ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k`                       | 4 |
| LLM provider/model                       | `gemini` / `gemini-2.5-flash` |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (Frozen Evaluation Set) |

**Giải thích giữ nguyên test set:**
Nhóm tuân thủ nguyên tắc **Ceteris Paribus** (Giữ nguyên các biến số khác). Việc đóng băng bộ test set đảm bảo sự biến động của chỉ số giữa 3 pha (Baseline, Corrupted và Repaired) hoàn toàn phản ánh tác động của **Chất lượng dữ liệu** (Data Quality) và **Hiệu quả phục hồi** (Repair Action), chứ không phải do câu hỏi bị thay đổi.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | `crossref_response.json`, `crossref_records.json` |
| Cleaned dataset          | `data/clean/`                        | Có | `papers_clean.csv`, `papers_clean.json` |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/`   | Có | `papers_embeddings.json` & ChromaDB persistent DB |
| Evaluation set           | `data/eval/`                         | Có | `test_set.json` |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | `retrieval_hit_rate = 0.6000` |
| Quality/freshness        | `data/quality/`                      | Có | `baseline_quality.json`, `freshness_report.json` |
| Baseline report          | `data/reports/phase1_report.md`      | Có | Báo cáo chi tiết Pha 1 |

### Baseline metrics

| Metric                 | Giá trị | Diễn giải |
| ---------------------- | ------: | --------------------------------------- |
| `retrieval_hit_rate`   |  0.6000 | Hệ thống truy xuất chính xác tài liệu gốc cho 6/10 câu hỏi trong bộ test set. |
| `mean_token_f1`        |  0.0000 | Được đo ở chế độ offline benchmark truy xuất. |
| `judge_accuracy`       |  0.0000 | Chế độ benchmark offline tập trung chính vào Retrieval Hit Rate. |
| `mean_judge_score`     |  1.0000 | Thang điểm cơ bản. |
| Ragas                  |     N/A | Bỏ qua để tối ưu tốc độ chạy benchmark offline. |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `row_count`  | Completeness | `>= 5` rows | PASS — 24 rows | `baseline_quality.json` |
| `paper_id_not_null` | Completeness | 0 missing | PASS — 0 missing | `baseline_quality.json` |
| `paper_id_unique` | Uniqueness | 0 duplicates | PASS — 0 duplicates | `baseline_quality.json` |
| `title_not_null` | Completeness | 0 missing | PASS — 0 missing | `baseline_quality.json` |
| `summary_length` | Validity | `>= 100` chars | PASS — 0 short summary | `baseline_quality.json` |
| `freshness` | Timeliness | `<= 180` days | PASS — 0 stale rows | `freshness_report.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `data/clean/papers_clean.json` |
| Timestamp mới nhất       | `2026-08-01` |
| Ngưỡng freshness         | `180` ngày |
| Trạng thái baseline      | `Fresh` |
| Lý do                     | Tất cả 24 bài báo đều có ngày xuất bản trong khoảng 180 ngày gần nhất (bài cũ nhất là 2026-02-12). |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ---------- | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `drop_records` | Xóa ngẫu nhiên bản ghi | 2 | `row_count` giảm, document unretrievable | Hit rate sụt giảm | Replay raw snapshot |
| `blank_summary` | Xóa trắng nội dung abstract | 2 | `summary_length` check FAIL | Mất ngữ nghĩa embedding | Replay raw snapshot |
| `truncate_title` | Cắt tiêu đề còn 5 ký tự | 2 | Điểm tương đồng tiêu đề giảm | Tọa độ vector bị lệch | Replay raw snapshot |
| `stale_publication_date` | Lùi ngày xuất bản về năm 2000 | 3 | Freshness check FAIL (`is_fresh = False`) | Dữ liệu bị gán nhãn hỏng | Replay raw snapshot |
| `inject_noise` | Chèn ký tự nhiễu vào summary | 2 | Vector embedding bị trôi ngẫu nhiên | Giảm khoảng cách cosine | Replay raw snapshot |
| `duplicate_records` | Nhân đôi bản ghi trong dataset | 2 | `paper_id_unique` check FAIL | Gây nghẽn Top-k results | Replay raw snapshot |

**Corruption log:**
- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Ghi nhận đầy đủ 6 kịch bản suy hao, danh sách 8 bản ghi bị tác động mục tiêu và tham số chi tiết.

**Giải thích cơ chế repair:**
Luồng Repair không gọi lại API (vì việc fetch mới sẽ trả về danh sách bài báo khác, làm mất tính công bằng với bộ test set cố định). Thay vào đó, Repair thực hiện chạy lại đúng các quy tắc Data Cleaning chuẩn trên snapshot dữ liệu thô ban đầu `data/raw/crossref_records.json`, đảm bảo dữ liệu khôi phục 100% tính toàn vẹn từ nguồn đáng tin cậy.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 0.6000 | 0.3000 | 0.6000 | -0.3000 | +0.3000 (+100%) | Hit rate bị giảm 50% ở pha Corrupted và phục hồi hoàn toàn sau repair. |
| `mean_token_f1` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Giữ nguyên ở chế độ benchmark offline. |
| `judge_accuracy` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Giữ nguyên. |
| `mean_judge_score` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | Giữ nguyên. |
| Quality checks pass/fail | PASS | FAIL | PASS | PASS -> FAIL (3/6 checks fail) | FAIL -> PASS | Quality checks phát hiện chính xác lỗi trùng lặp, summary rỗng và ngày xuất bản cũ. |
| Freshness status | True | False | True | True -> False (3 stale rows) | False -> True | Freshness monitor phát hiện chính xác các bản ghi bị lùi ngày. |

### Kết luận quan hệ nhân quả có bằng chứng:

1. **[Data Corruption Target] → [Quality Check FAIL] → [Retrieval Hit Rate sụt giảm 50%]:** Khi 6 kịch bản suy hao dữ liệu tác động lên 8/10 tài liệu trong tập test (xóa bản ghi, xóa summary, lùi ngày xuất bản), các bài kiểm tra Observability ngay lập tức bật cảnh báo FAIL (xuất hiện 2 lỗi `paper_id_unique`, 2 lỗi `summary_length` và 3 lỗi `freshness`), khiến `retrieval_hit_rate` giảm trực tiếp từ 0.6000 xuống 0.3000.
2. **[Repair Action from Raw Snapshot] → [Quality Check PASS] → [Retrieval Hit Rate phục hồi 100%]:** Khi kích hoạt luồng Repair phát lại dữ liệu thô chuẩn từ `crossref_records.json`, các lỗi dữ liệu được xóa bỏ hoàn toàn (Quality Check & Freshness đạt PASS), đồng thời kéo chỉ số `retrieval_hit_rate` tăng từ 0.3000 phục hồi 100% trở lại mức Baseline 0.6000.

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline và cách nhóm xử lý:

- **Triệu chứng:** Khi khởi tạo môi trường trên Windows hoặc chạy lệnh pip, hệ thống báo lỗi vi phạm phiên bản Python 3.14.6 (`requires-python = ">=3.11,<3.14"`), đồng thời gặp lỗi mã hóa Unicode `cp1252` làm ngắt đứt pipeline khi in thông báo ra màn hình terminal.
- **Nguyên nhân:** Lệnh `python` mặc định trên hệ thống Windows trỏ tới Python 3.14 (không thuộc dải tương thích của `pyproject.toml`), và bảng mã mặc định của Windows Console (CP1252) không hỗ trợ ký tự Unicode tiếng Việt khi stdout print.
- **Cách xử lý:** Nhóm chuyển sang sử dụng Python Launcher `py -3.12 -m venv .venv` để tạo môi trường ảo chuẩn Python 3.12.10; đồng thời cập nhật toàn bộ thông báo in ra terminal trong pipeline sang tiếng Anh / UTF-8 mã hóa sạch.
- **Cách xác minh:** Chạy lại thành công cả hai lệnh `python script/run_phase1.py` và `python script/run_corruption_flow.py` trên môi trường `.venv` Python 3.12 mới, pipeline chạy thông suốt 100% không phát sinh lỗi.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Mô hình nhúng local `all-MiniLM-L6-v2` kích thước nhỏ (384D) | Độ phân giải không gian vector chưa đủ cao với các bài báo kỹ thuật chuyên sâu | Thử nghiệm mô hình nhúng độ phân giải cao hơn như `bge-large-en-v1.5` (1024D) và đo sự thay đổi của `retrieval_hit_rate` |
| Tập test set gồm 10 câu hỏi factual đơn giản | Chưa đánh giá được khả năng tổng hợp câu trả lời từ nhiều tài liệu (Multi-doc reasoning) | Mở rộng tập test set lên 30–50 câu hỏi bao gồm dạng so sánh, tổng hợp và đo lường bằng LLM Judge |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
