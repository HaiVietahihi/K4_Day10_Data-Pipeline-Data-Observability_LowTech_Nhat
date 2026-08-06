# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Thái Tú          |
| MSSV               | 2A202601504                |
| Khóa/Lớp         | K4                          |
| Tên nhóm         | LowTech Nhất              |
| Vai trò chính    | Observability & Baseline orchestration owner |
| Repository         | https://github.com/HaiVietahihi/K4_Day10_Data-Pipeline-Data-Observability_LowTech_Nhat.git |
| Ngày hoàn thành | 2026-08-06                  |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data quality checks | `src/observability/quality.py::run_data_quality_checks`, `build_freshness_report` | Cleaned `DataFrame`, `Settings` | `data/quality/baseline_quality.json`, `data/quality/freshness_report.json` | Hoàn thành |
| Baseline report      | `src/observability/reporting.py::generate_phase1_report` | source summary, metrics, quality, freshness (dict) | `data/reports/phase1_report.md` | Hoàn thành |
| Baseline orchestration | `src/pipelines/phase1.py::main` | `.env`/`Settings`, raw hoặc cached Crossref records | Toàn bộ artifact Pha 1: raw, clean, embeddings, eval, `baseline_metrics.json`, `baseline_answers.json`, quality/freshness, `phase1_report.md` | Hoàn thành |

Tôi chỉ nhận ownership cho 3 file trên. Các module `core/`, `ingestion/crossref.py`, `ingestion/cleaning.py`, `retrieval/`, `evaluation/` đã có sẵn (fully implemented) trong starter và tôi chỉ gọi lại đúng contract, không chỉnh sửa logic bên trong. `src/ingestion/corruption.py` và `src/pipelines/corruption_flow.py` (Pha 2) chưa được thực hiện trong phạm vi báo cáo này.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Debug môi trường cài đặt | Toàn nhóm (setup chung: `requirements.txt`, `uv sync`) | Phát hiện và xử lý lỗi Windows path-too-long khi cài `torch` qua pip, chuyển sang `uv sync` theo README Cách A (xem mục 6) |
| Review chất lượng câu trả lời | `src/retrieval/qa.py` (không thuộc phần sở hữu) | Phát hiện `_extract_answer` chỉ nhận diện pattern câu hỏi tiếng Anh trong khi test set tiếng Việt, khiến `mean_token_f1`/`judge_accuracy` baseline bằng 0. Đã ghi nhận là lỗi có sẵn trong code tham khảo, chưa sửa vì ngoài phạm vi công việc được giao (xem mục 8) |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Implement 6 data quality checks (row count, paper_id not-null/unique, title not-null, summary length, freshness) | `src/observability/quality.py::run_data_quality_checks` | `data/quality/baseline_quality.json` với `"passed": true` cho cả 6 check | Mở file, kiểm tra từng `checks[i].passed == true` |
| Implement freshness report (latest/oldest published, stale rows) | `src/observability/quality.py::build_freshness_report` | `data/quality/freshness_report.json` với `"is_fresh": true`, `stale_rows: 0` | Mở file, đối chiếu `stale_rows` với `total_rows` |
| Implement markdown report cho Pha 1 | `src/observability/reporting.py::generate_phase1_report` | `data/reports/phase1_report.md` (đủ 4 mục: source summary, evaluation metrics, data quality, freshness) | `cat data/reports/phase1_report.md` |
| Ghép toàn bộ pipeline baseline end-to-end | `src/pipelines/phase1.py::main` | Toàn bộ artifact Pha 1 sinh ra trong `data/` | `uv run python script/run_phase1.py` → exit code 0 |

Output cụ thể: chạy `uv run python script/run_phase1.py` sinh ra `data/results/baseline_metrics.json` với `retrieval_hit_rate=0.6`, `samples=10`, cùng `data/results/baseline_answers.json` (10 câu trả lời chi tiết), `data/quality/baseline_quality.json` (`passed: true`) và `data/reports/phase1_report.md`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trước khi tôi làm, `src/pipelines/phase1.py` chỉ là một hàm `main()` rỗng ném `NotImplementedError`, và hai hàm bắt buộc mà nó cần gọi (`run_data_quality_checks`, `build_freshness_report` trong `quality.py`, và `generate_phase1_report` trong `reporting.py`) cũng là stub. Nhiệm vụ của tôi là (1) viết phần thân của ba stub đó, và (2) nối toàn bộ các module đã có sẵn (config, Crossref ingestion, cleaning, Chroma index, evaluation) cùng ba phần mới viết thành một pipeline baseline chạy được thật, không chỉ biên dịch được.

### Cách triển khai

- **Idempotent fetch**: nếu `settings.refresh_source` là `true` hoặc `data/raw/crossref_records.json` chưa tồn tại thì gọi `fetch_source_records` (gọi API thật); ngược lại dùng `load_raw_records` để replay từ snapshot, tránh gọi lại Crossref không cần thiết mỗi lần chạy.
- **Idempotent test set**: áp dụng logic tương tự cho `settings.refresh_test_set` và `data/eval/test_set.json` trước khi gọi `evaluate_pipeline` (hàm này tự đọc file test set theo đường dẫn được truyền vào).
- **Fail-fast credential check**: gọi `require_llm_credentials(settings)` trước khi evaluate để báo lỗi rõ ràng (`GOOGLE_API_KEY is required...`) ngay từ đầu thay vì để lỗi xảy ra giữa chừng lúc gọi LLM judge.
- **Data quality checks**: viết 6 rule-based check thuần pandas trên `DataFrame` đã clean — đếm dòng, null/duplicate `paper_id`, null `title`, `summary_chars` ngắn hơn `MIN_SUMMARY_CHARS` (tái sử dụng hằng số từ `ingestion/cleaning.py` để không lệch ngưỡng giữa cleaning và quality), và số dòng có `age_days` vượt `freshness_threshold_days`. Gộp thành một JSON có cờ `passed` tổng (`all(check.passed)`), ghi vào `data/quality/{report_name}_quality.json`.
- **Freshness report**: tính `latest_published`/`oldest_published` bằng `min`/`max` trên cột `published` (dạng chuỗi ISO, sort đúng theo thứ tự thời gian), đếm `stale_rows` theo `age_days`, suy ra `is_fresh = stale_rows == 0`.
- **Markdown report**: build danh sách các dòng markdown từ 4 dict đầu vào (source summary, metrics, quality, freshness) rồi ghi một lần bằng `core.utils.write_text`, không phụ thuộc thư viện template ngoài.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `DataFrame` đã clean (từ `ingestion.cleaning.build_clean_dataframe`), `Settings`/`Paths` (`core.config.load_settings`), `LocalEmbeddingIndex` đã build (`retrieval.index`) |
| Output                         | `data/quality/baseline_quality.json`, `data/quality/freshness_report.json`, `data/reports/phase1_report.md`, `data/results/baseline_metrics.json`, `data/results/baseline_answers.json` |
| Module phụ thuộc             | `core.config`, `core.utils`, `ingestion.cleaning` (hằng `MIN_SUMMARY_CHARS`), `ingestion.crossref`, `evaluation.metrics`, `evaluation.testset`, `retrieval.index` |
| Module sử dụng output        | `report/group_report.md` (đọc metrics để phân tích chung); dự kiến `pipelines/corruption_flow.py` (Pha 2) sẽ gọi lại `run_data_quality_checks`/`build_freshness_report` cho corrupted/repaired và so sánh với `baseline_metrics.json` |
| Điều kiện lỗi cần xử lý | Thiếu API key provider → `require_llm_credentials` raise `RuntimeError` rõ nguyên nhân; `DataFrame` rỗng → freshness report trả `latest_published`/`oldest_published` = `None` thay vì crash khi gọi `.max()`/`.min()` trên cột rỗng |

### Cách xác minh

```bash
uv sync
uv run python script/run_phase1.py
```

- **Kết quả mong đợi:** pipeline chạy hết 1 lượt (fetch/load → clean → index → evaluate → quality → freshness → report) không lỗi, sinh đủ artifact trong `data/`.
- **Kết quả thực tế:** chạy thành công, exit code 0. Log cuối: `[phase1] baseline pipeline complete: retrieval_hit_rate=0.600, mean_token_f1=0.000, judge_accuracy=0.000`.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`, `data/quality/baseline_quality.json`, `data/quality/freshness_report.json`, `data/reports/phase1_report.md`. Không có secret trong các file này.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** `run_data_quality_checks` cần ghi report ra file, nhưng Pha 2 (`corruption_flow.py`) sẽ phải gọi lại đúng hàm này cho cả dữ liệu corrupted và repaired để so sánh 3 trạng thái.
- **Các phương án đã cân nhắc:** (a) ghi cố định vào một file duy nhất `data/quality/quality_report.json`; (b) tham số hoá bằng `report_name` (đã có sẵn trong chữ ký hàm) và build đường dẫn động `data/quality/{report_name}_quality.json`.
- **Phương án đã chọn:** (b).
- **Lý do:** nếu dùng chung một tên file cố định, lần chạy corrupted/repaired ở Pha 2 sẽ ghi đè lên báo cáo baseline, làm mất khả năng đối chiếu 3 trạng thái — vốn là yêu cầu cốt lõi của cả bài lab (mục tiêu "so sánh baseline/corrupted/repaired" trong `report/README.md`).
- **Bằng chứng quyết định phù hợp:** `run_data_quality_checks(df, settings, report_name="baseline")` hiện tạo đúng `data/quality/baseline_quality.json`; hàm sẵn sàng nhận `report_name="corrupted"`/`"repaired"` ở Pha 2 mà không cần sửa lại chữ ký hay logic.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ERROR: Could not install packages due to an OSError: [WinError 206] The filename or extension is too long: 'D:\\labAI_vinuni\\Buoi10\\K4_Day10_Data-Pipeline-Data-Observability_LowTech_Nhat\\venv\\Lib\\site-packages\\torch-2.13.0.dist-info\\licenses\\third_party\\kineto\\libkineto\\third_party\\dynolog\\third_party\\prometheus-cpp\\3rdparty\\civetweb\\src\\third_party\\duktape-1.5.2'`
- **Lệnh hoặc bước tái hiện:** tạo `venv` bằng `python -m venv venv` trong thư mục project, sau đó `python -m pip install -r requirements.txt`.
- **Nguyên nhân gốc:** đường dẫn tuyệt đối = thư mục project (tên dài) + `venv\Lib\site-packages\` + đường dẫn file license lồng rất sâu bên trong gói `torch` vượt quá giới hạn `MAX_PATH` (260 ký tự) mặc định của Windows; máy không có quyền admin để bật Long Path Support qua registry (`LongPathsEnabled`).
- **Cách xử lý:** bỏ cách cài bằng `pip` + `venv` thủ công, chuyển sang dùng `uv sync` (đúng Cách A — cách được README khuyến nghị) để tạo `.venv` và cài cả project lẫn dependency; `uv` không gặp lỗi này khi giải nén cùng bộ gói.
- **Cách xác minh sau khi sửa:** `uv sync` chạy xong với exit code 0, thư mục `.venv` xuất hiện đầy đủ trong project; sau đó `uv run python script/run_phase1.py` chạy hết pipeline không phát sinh lỗi cài đặt nào.
- **Điều học được:** giới hạn độ dài path của Windows là rủi ro thực tế khi cài các gói ML nặng (torch, chromadb, onnxruntime...) trong thư mục project có tên dài; nên ưu tiên trình quản lý gói hiện đại (`uv`) hoặc rút ngắn đường dẫn thay vì cố sửa từng gói riêng lẻ.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** `fetch_source_records` gọi Crossref REST API, lưu response thô vào `data/raw/crossref_response.json` và parse thành `PaperRecord` (list) lưu vào `data/raw/crossref_records.json`. `build_clean_dataframe` lọc bản ghi thiếu `paper_id`/`title`, tóm tắt ngắn hơn 100 ký tự, ngày xuất bản không hợp lệ hoặc trùng lặp, rồi chuẩn hoá thành `DataFrame` với cột `text_for_embedding`. `save_clean_dataset` ghi ra `data/clean/`. `LocalEmbeddingIndex.build` dùng MiniLM (`sentence-transformers/all-MiniLM-L6-v2`) để embed `text_for_embedding` của từng dòng, nạp vào một collection ChromaDB tại `data/chroma/`, đồng thời ghi manifest embeddings ra `data/embeddings/papers_embeddings.json`.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** Bộ 10 câu hỏi cố định (`FROZEN_TEST_SET` trong `evaluation/testset.py`) có sẵn `ground_truth` (câu trả lời đúng) và `ground_truth_doc_ids` (DOI của tài liệu chứa câu trả lời). `evaluate_pipeline` với mỗi câu hỏi: gọi `answer_question` để retrieve top-k tài liệu từ Chroma và tạo câu trả lời, so `retrieved_doc_ids` với `ground_truth_doc_ids` để tính `retrieval_hit`, so token giữa câu trả lời và `ground_truth` để tính `token_f1`, và gọi LLM judge để chấm điểm 1-5 cùng cờ `correct`.
3. **Quality checks khác freshness monitoring ở điểm nào?** `run_data_quality_checks` kiểm tra tính toàn vẹn cấu trúc của dữ liệu tại một thời điểm (completeness: không null; uniqueness: không trùng `paper_id`; độ dài hợp lệ của `summary`) — đây là các ràng buộc schema/nội dung. `build_freshness_report` chỉ tập trung vào một chiều duy nhất: độ mới theo thời gian (`age_days` so với `freshness_threshold_days`), tức dữ liệu có thể "đầy đủ và đúng schema" nhưng vẫn "cũ" (stale), hoặc ngược lại.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Vì mục tiêu là đo ảnh hưởng của *chất lượng dữ liệu* lên agent, không phải đo do câu hỏi khác nhau. Nếu đổi test set giữa các lần chạy, chênh lệch metric có thể đến từ việc câu hỏi khó/dễ khác nhau chứ không phản ánh đúng tác động của corruption/repair — làm mất tính so sánh được (`report/README.md` mục 2 nêu rõ yêu cầu này).
5. **Repair được xem là thành công dựa trên artifact và metric nào?** Dựa trên việc metrics (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`) của dataset repaired quay lại gần với baseline (so với dataset corrupted bị giảm rõ rệt), đồng thời `data/quality/repaired_quality.json` và freshness report tương ứng phải PASS trở lại như baseline. Phần này (Pha 2) chưa được chạy trong phạm vi công việc của tôi nên tôi chưa có artifact thực tế để trích dẫn số liệu cụ thể.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      0.6 |  Chưa chạy |  Chưa chạy | Đúng 6/10 câu hỏi retrieve trúng tài liệu ground-truth; Pha 2 (corruption/repair) chưa được thực hiện nên chưa có số liệu để so sánh |
| `mean_token_f1`      |      0.0 |  Chưa chạy |  Chưa chạy | Bằng 0 do lỗi có sẵn trong `retrieval/qa.py::_extract_answer` (chỉ nhận pattern câu hỏi tiếng Anh, test set tiếng Việt) — xem chi tiết bên dưới, không phải lỗi trong phần tôi phụ trách |
| `judge_accuracy`     |      0.0 |  Chưa chạy |  Chưa chạy | Hệ quả trực tiếp của việc `token_f1` thấp; LLM judge chấm câu trả lời không khớp câu hỏi là sai |
| `mean_judge_score`   |        1 |  Chưa chạy |  Chưa chạy | Điểm sàn (1/5) cho toàn bộ 10 câu, nhất quán với `judge_accuracy=0` |
| Quality checks         |     PASS |  Chưa chạy |  Chưa chạy | 6/6 check PASS: row_count, paper_id not-null, paper_id unique, title not-null, summary_length, freshness |
| Freshness status       | is_fresh=true |  Chưa chạy |  Chưa chạy | 0/24 dòng stale so với ngưỡng 180 ngày; dữ liệu Crossref lấy về đều rất mới (12/02/2026 – 01/08/2026) |

### Kết luận từ số liệu

Tôi **chưa thể hoàn thành** hai chuỗi nguyên nhân–bằng chứng đầy đủ (baseline → corrupted → repaired) vì `src/ingestion/corruption.py` và `src/pipelines/corruption_flow.py` (Pha 2) không thuộc phạm vi công việc tôi được giao và chưa được implement trong lần chạy này. Tôi chỉ có số liệu cho baseline.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Chưa xác định được — Pha 2 chưa chạy nên không có số liệu corrupted để phân tích.

Kết quả nào khác với kỳ vọng ban đầu?

Kỳ vọng ban đầu là baseline (dữ liệu sạch) phải cho `mean_token_f1` và `judge_accuracy` cao, làm mốc đối chứng rõ ràng cho Pha 2. Thực tế cả hai đều bằng 0. Tôi đã kiểm tra `data/results/baseline_answers.json` và xác nhận nguyên nhân: `retrieval/qa.py::_extract_answer` chỉ so khớp các cụm tiếng Anh (`"who authored"`, `"when was"`, `"what categories"`) để chọn cách trả lời, còn `evaluation/testset.py::FROZEN_TEST_SET` toàn câu hỏi tiếng Việt — nên hàm luôn rơi vào nhánh mặc định, trả về câu đầu tiên của `summary` tài liệu top-1 thay vì trả lời đúng trọng tâm câu hỏi (ví dụ hỏi tên tác giả nhưng trả lời lại là một câu mô tả nội dung bài báo). Đây là hành vi có sẵn trong `qa.py` (file được đánh dấu "đã có code tham khảo", không phải phần tôi phụ trách), nên tôi chỉ ghi nhận và chưa sửa.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** một pipeline "chạy được" (không lỗi cú pháp) và một pipeline "đúng" là hai việc khác nhau — `phase1.py` có thể chạy hết từ đầu đến cuối và sinh đủ artifact, nhưng số liệu bên trong vẫn có thể sai lệch nghiêm trọng nếu một module phụ thuộc (ở đây là `qa.py`) không tương thích với dữ liệu thực tế (ngôn ngữ câu hỏi).
2. **Về data quality/observability:** tách riêng "completeness/uniqueness" (đúng schema tại một thời điểm) khỏi "freshness" (đúng về mặt thời gian) giúp chẩn đoán chính xác hơn khi có sự cố — một dataset có thể pass hết completeness nhưng vẫn stale, hoặc ngược lại.
3. **Về ảnh hưởng của data đến RAG agent:** metric thấp không nhất thiết do dữ liệu xấu — cần đọc artifact chi tiết (`baseline_answers.json`) thay vì chỉ nhìn con số tổng hợp trong `baseline_metrics.json`, vì nguyên nhân gốc có thể nằm ở tầng xử lý câu hỏi/câu trả lời chứ không phải ở chất lượng dữ liệu nguồn.

### Nếu có thêm thời gian

Tôi sẽ sửa `retrieval/qa.py::_extract_answer` để nhận diện thêm pattern câu hỏi tiếng Việt (ví dụ "tác giả nào", "khi nào", "chủ đề gì") trước khi rơi vào nhánh mặc định, sau đó chạy lại `script/run_phase1.py` để đo lại `mean_token_f1`/`judge_accuracy` trên cùng test set — nếu hai chỉ số này tăng rõ rệt so với 0.0 hiện tại thì xác nhận đúng nguyên nhân gốc đã nêu ở mục 8.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thái Tú
**Ngày xác nhận:** 2026-08-06
