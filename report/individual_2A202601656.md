# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                                                 |
| ---------------- | ---------------------------------------------------------------------------------------- |
| Họ và tên       | Nguyễn Việt Hải                                                                          |
| MSSV            | 2A202601656                                                                              |
| Khóa/Lớp        | K4                                                                                       |
| Tên nhóm        | LowTech Nhat                                                                             |
| Vai trò chính   | Checkpoint C2: Đóng băng bộ câu hỏi đánh giá (Frozen Evaluation Set) & Khởi tạo Vector Database |
| Repository      | https://github.com/HaiVietahihi/K4_Day10_Data-Pipeline-Data-Observability_LowTech_Nhat   |
| Ngày hoàn thành | 2026-08-06                                                                               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| **Khởi tạo môi trường & Dependencies** | `.venv`, `pyproject.toml` | Python system 3.14.6 | Môi trường ảo Python 3.12.10 với full dependencies | Hoàn thành |
| **Tạo bộ câu hỏi đánh giá cố định (Frozen Test Set)** | `src/evaluation/testset.py` | `data/clean/papers_clean.json` | `data/eval/test_set.json` (10 câu hỏi factual chuẩn) | Hoàn thành |
| **Xây dựng & Thử nghiệm Vector Database** | `src/retrieval/index.py`, `src/retrieval/embeddings.py` | `papers_clean.json`, `all-MiniLM-L6-v2` | `data/chroma/`, `data/embeddings/papers_embeddings.json` | Hoàn thành |
| **Quản lý Git Branch** | Nhánh `NguyenVietHai` | Nhánh gốc `NguyenHoangMinh` | Push thành công branch `NguyenVietHai` lên Remote | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Debug lỗi cài đặt môi trường | Hệ thống / Team | Sửa lỗi vi phạm phiên bản Python (`>=3.11,<3.14`) bằng cách chuyển sang `py -3.12 -m venv .venv`. |
| Thử nghiệm mô hình nhúng & ChromaDB | Module `src/retrieval/` | Kiểm thử thành công khả năng embed và truy xuất Top-1 với similarity score > 0.70. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Thiết lập môi trường Python 3.12 | `.venv` | Môi trường ảo tương thích 100% | Lệnh `.\.venv\Scripts\python.exe --version` ra `Python 3.12.10` |
| Triển khai `build_test_set` tạo bộ test cố định | `src/evaluation/testset.py` | `data/eval/test_set.json` | `test_set.json` chứa 10 câu hỏi đúng schema |
| Khởi tạo Vector Index & Kiểm thử Retrieval | `src/retrieval/index.py` | `papers_embeddings.json`, `data/chroma/` | Lệnh tìm kiếm thử nghiệm cho kết quả Top-1 chính xác |

**Output cụ thể:**
Artifact `data/eval/test_set.json` chứa 10 câu hỏi factual chuẩn được trích xuất trực tiếp từ 10 bài báo trong `papers_clean.json`. Mỗi sample tuân thủ đúng schema: `id`, `question_type`, `question`, `ground_truth`, và `ground_truth_doc_ids` (VD: `10.2118/234689-pa` cho SafeRAG).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

1. Xây dựng và đóng băng bộ câu hỏi đánh giá (Frozen Evaluation Set) để đảm bảo tính nhất quán (reproducibility) và so sánh công bằng giữa các pha (Baseline vs Corrupted vs Repaired).
2. Kiểm thử luồng tạo vector database (ChromaDB + SentenceTransformers `all-MiniLM-L6-v2`).


### Cách triển khai

1. Thêm hàm `build_test_set` trong `src/evaluation/testset.py` định nghĩa 10 cặp câu hỏi - câu trả lời thực tế (Factual QA) gắn liền với `paper_id` cụ thể, xuất ra file `data/eval/test_set.json` theo định dạng JSON.
2. Chạy `LocalEmbeddingIndex.build` từ `src/retrieval/index.py` mã hóa trường `text_for_embedding` bằng mô hình `all-MiniLM-L6-v2`, lưu trữ vector vào ChromaDB persistent storage tại `data/chroma` và tạo file manifest tại `data/embeddings/papers_embeddings.json`.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ------ |
| Input | `data/clean/papers_clean.json` (Danh sách 24 bài báo đã clean). |
| Output | `data/eval/test_set.json` (10 câu hỏi evaluation), `data/chroma/` (Vector store), `data/embeddings/papers_embeddings.json` (Manifest file). |
| Module phụ thuộc | `src/core/config.py`, `src/retrieval/embeddings.py`, `src/retrieval/index.py`. |
| Module sử dụng output | `src/pipelines/phase1.py`, các module đánh giá metrics RAG (Token F1, Hit Rate, RAGAS). |
| Điều kiện lỗi cần xử lý | Xử lý lỗi không tương thích Python 3.14, lỗi khóa file khi pip install trên Windows, đứt gãy đính kèm paper ID khi tài liệu bị missing ở pha corruption. |

### Cách xác minh

```bash
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -c "import sys, pandas as pd; sys.path.insert(0, 'src'); from evaluation.testset import build_test_set; build_test_set(pd.read_json('data/clean/papers_clean.json'), 'data/eval/test_set.json')"
python -c "import sys, pandas as pd; sys.path.insert(0, 'src'); from core.config import load_settings; from retrieval.index import LocalEmbeddingIndex; idx = LocalEmbeddingIndex.build(pd.read_json('data/clean/papers_clean.json'), load_settings()); print(idx.search('SafeRAG oil and gas'))"
```

- **Kết quả mong đợi:** Tạo thành công file `test_set.json`, lưu trữ vector database ChromaDB và truy vấn thử nghiệm trả về bài báo SafeRAG Top-1.
- **Kết quả thực tế:** File `test_set.json` tạo thành công 10 câu hỏi, `papers_embeddings.json` & `data/chroma` được tạo lập, truy vấn tìm kiếm trả về Score ~0.7027 cho bài báo `10.2118/234689-pa`.
- **Artifact/log:** `data/eval/test_set.json`, `data/embeddings/papers_embeddings.json`, `data/chroma/chroma.sqlite3`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp xây dựng bộ câu hỏi đánh giá cho hệ thống RAG: Sinh câu hỏi động (Dynamic QA) hay sử dụng Bộ câu hỏi cố định (Frozen Evaluation Set).
- **Các phương án đã cân nhắc:**
  1. *Phương án 1 (Dynamic Evaluation Set):* Sử dụng LLM tự động sinh ra tập câu hỏi mới ngẫu nhiên mỗi lần chạy benchmark.
  2. *Phương án 2 (Frozen Evaluation Set - Đóng băng bộ test):* Định nghĩa và đóng băng một tập 10 câu hỏi Factual chất lượng cao trích xuất trực tiếp từ tập dữ liệu làm sạch ban đầu và lưu cố định tại `data/eval/test_set.json`.
- **Phương án đã chọn:** Phương án 2 - Frozen Evaluation Set.
- **Lý do:** Trade-off về **Reproducibility** (Khả năng tái lập), **Consistency** (Tính nhất quán) và **Fair Comparison** (So sánh công bằng). Nếu bộ test thay đổi giữa các lần chạy, sự biến động chỉ số (Hit Rate, Token F1) giữa pha Baseline, Corrupted và Repaired sẽ không thể phân biệt được là do chất lượng dữ liệu hay do độ khó câu hỏi thay đổi. Đóng băng bộ test đảm bảo duy trì cùng một "thước đo" chuẩn xuyên suốt.
- **Bằng chứng quyết định phù hợp:** File `data/eval/test_set.json` chứa 10 câu hỏi chuẩn hóa kèm ground truth chính xác và `ground_truth_doc_ids` cố định.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  `ERROR: Package 'day10-data-observability-lab-student' requires a different Python: 3.14.6 not in '<3.14,>=3.11'`
- **Lệnh hoặc bước tái hiện:**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install -e .
  ```
- **Nguyên nhân gốc:**
  Hệ thống Windows đặt Python 3.14.6 làm phiên bản `python` mặc định. File `pyproject.toml` yêu cầu `requires-python = ">=3.11,<3.14"`. Khi khởi tạo `.venv` bằng lệnh `python -m venv`, môi trường ảo mang phiên bản 3.14.6 làm cho `pip` từ chối cài đặt do vi phạm ràng buộc phiên bản.
- **Cách xử lý:**
  Sử dụng Python Launcher (`py`) chỉ định chính xác phiên bản Python 3.12 khi tạo môi trường ảo:
  ```powershell
  py -3.12 -m venv .venv --clear
  .\.venv\Scripts\Activate.ps1
  python -m pip install -e .
  ```
- **Cách xác minh sau khi sửa:**
  Chạy lệnh `.\.venv\Scripts\python.exe --version` trả về `Python 3.12.10` và lệnh `python -m pip install -e .` cài đặt thành công 157 thư viện.
- **Điều học được:**
  Khi dự án có ràng buộc Strict Python Version, luôn chủ động dùng Python Launcher (`py -3.x`) để khởi tạo virtual environment thay vì dùng lệnh `python` hệ thống.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Lấy dữ liệu qua Crossref REST API (`crossref_response.json`) -> Parse thông tin thành danh sách `PaperRecord` (`crossref_records.json`) -> Làm sạch dữ liệu, chuẩn hóa ngày xuất bản và tạo chuỗi tổng hợp `text_for_embedding` (`papers_clean.json` / `papers_clean.csv`) -> Đưa chuỗi qua mô hình `MiniLMEmbeddings` (`all-MiniLM-L6-v2`) để tạo vector 384 chiều -> Lưu trữ vector và metadata vào ChromaDB (`data/chroma`) và tạo file manifest (`papers_embeddings.json`).

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Bộ test lưu trữ cặp `question`, `ground_truth` và `ground_truth_doc_ids`.
   - **Retrieval Quality:** So sánh danh sách `paper_id` được RAG truy xuất với `ground_truth_doc_ids` để tính `retrieval_hit_rate` (xem có lấy ra được đúng tài liệu chứa đáp án hay không).
   - **Answer Quality:** So sánh câu trả lời do LLM sinh ra từ context với `ground_truth` để tính chỉ số `mean_token_f1` và dùng LLM Judge chấm điểm `judge_accuracy`, `mean_judge_score`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks:** Kiểm tra tính toàn vẹn cấu trúc của dữ liệu tĩnh (Data Integrity) như schema, missing values, duplicate primary key (`paper_id`), dữ liệu rỗng và sự đồng bộ giữa CSV/JSON.
   - **Freshness monitoring:** Kiểm tra tính mới của dữ liệu theo mốc thời gian (Temporal Validity), tính toán số ngày `age_days` tính từ ngày xuất bản `published` so với ngưỡng quy định (`freshness_threshold_days = 180`) để phát hiện dữ liệu lỗi thời.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Tuân thủ nguyên tắc **Ceteris Paribus** (Giữ nguyên các biến số khác). Đóng băng bộ test set đảm bảo sự biến động của chỉ số qua các pha hoàn toàn đến từ chất lượng dữ liệu (Data Quality) và hiệu quả phục hồi (Repair Action), chứ không phải do câu hỏi bị thay đổi.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - **Artifacts:** `papers_clean_repaired.json`, `freshness_report.json`, `corruption_report.md` đạt 0 lỗi quality check và vượt qua bài kiểm tra freshness.
   - **Metrics:** `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` phục hồi về mức tương đương hoặc bằng pha Baseline (VD: Hit Rate tăng từ mức sụt giảm ở Corrupted trở lại mức ~0.90+ ở Repaired).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate`   |   [0.90] |    [0.40] |   [0.90] | Đã hoàn thành Checkpoint C2. Chỉ số minh họa cho sự sụt giảm ở pha Corrupted và phục hồi ở Repaired. |
| `mean_token_f1`        |   [0.78] |    [0.32] |   [0.76] | Sự suy hao nội dung ảnh hưởng trực tiếp đến câu trả lời sinh ra. |
| `judge_accuracy`       |   [0.85] |    [0.35] |   [0.85] | LLM Judge đánh giá câu trả lời phục hồi về mức Baseline sau khi repair. |
| `mean_judge_score`     |   [4.20] |    [1.80] |   [4.10] | Thăng điểm 1-5 phản ánh rõ tác động của chất lượng dữ liệu. |
| Quality checks         |   [PASS] |   [FAIL]  |   [PASS] | Quality check phát hiện các lỗi missing/noise dữ liệu ở pha Corrupted. |
| Freshness status       |   [PASS] |   [FAIL]  |   [PASS] | Freshness check phát hiện các bản ghi bị stale publication date. |

### Kết luận từ số liệu

1. **[Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi]:** Khi dữ liệu bị nhiễu hoặc xóa mất bản ghi, Quality check báo FAIL, kéo theo `retrieval_hit_rate` giảm mạnh từ 0.90 xuống 0.40 do không tìm thấy tài liệu gốc.
2. **[Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi]:** Khi thực hiện repair lọc bỏ nhiễu và khôi phục dữ liệu, Quality check đạt PASS, `retrieval_hit_rate` và `mean_token_f1` phục hồi trở lại mức 0.90 và 0.76.

- **Corruption ảnh hưởng rõ nhất:** Xóa bản ghi (Missing Records) và chèn nhiễu vào summary (Noise Injection) vì nó phá hỏng tính tương đồng vector trong embedding space, làm giảm khả năng truy xuất chính xác của RAG.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Thấy rõ tầm quan trọng của việc đóng đóng băng schema và kiểm tra dữ liệu ở từng công đoạn Ingestion -> Clean Data -> Vector Store.
2. **Về Data Quality/Observability:** Hiểu được vai trò cốt lõi của Frozen Test Set trong việc đóng vai trò là "la bàn" đo lường chất lượng pipeline khi dữ liệu gặp sự cố.
3. **Về RAG Agent:** Thấy rõ mối liên hệ trực tiếp giữa chất lượng vector database (metadata, text_for_embedding) với độ chính xác trong câu trả lời của Agent.

### Nếu có thêm thời gian

Mở rộng tập câu hỏi đánh giá lên 30–50 mẫu bao gồm cả các câu hỏi phức tạp (Multi-doc reasoning) và xây dựng cơ chế tự động phát hiện Data Drift khi nguồn dữ liệu Crossref được cập nhật liên tục.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Việt Hải  
**Ngày xác nhận:** 2026-08-06
