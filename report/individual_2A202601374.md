# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đoàn Văn Tuyền             |
| MSSV               | 2A202601374                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | LowTech Nhất     |
| Vai trò chính    | AI Engineer                 |
| Repository         | https://github.com/HaiVietahihi/K4_Day10_Data-Pipeline-Data-Observability_LowTech_Nhat.git |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Ingestion & Cleaning | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py` | Query API từ Crossref | JSON/CSV dữ liệu bài báo sạch | Hoàn thành |
| Data Observability | `src/observability/quality.py`, `src/observability/reporting.py` | DataFrame dữ liệu sạch/bẩn | Báo cáo Markdown và JSON Quality/Freshness | Hoàn thành |
| Pipeline Orchestration | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | Các scripts nhỏ lẻ | Luồng chạy End-to-End Pipeline Pha 1 & 2 | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Xử lý lỗi Encoding (Unicode) | Windows Terminal | Đổi các thông báo in ra màn hình sang tiếng Anh để tránh lỗi `cp1252` làm sập Pipeline. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Xây dựng Baseline RAG Pipeline | `src/pipelines/phase1.py` | `data/reports/phase1_report.md` | Chạy `python script/run_phase1.py` |
| Mô phỏng lỗi dữ liệu và phục hồi | `src/pipelines/corruption_flow.py` | `data/reports/corruption_report.md` | Chạy `python src/pipelines/corruption_flow.py` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Đảm bảo dữ liệu từ nguồn Crossref được tự động lấy về, làm sạch để tạo Vector cho mô hình RAG; đồng thời phải có cơ chế cảnh báo (Observability) để biết được khi nào dữ liệu bị hỏng làm giảm chất lượng trả lời của RAG.

### Cách triển khai

- Sử dụng thư viện `requests` để kéo dữ liệu từ API Crossref, có kết hợp Retry cơ bản để chống lỗi mạng.
- Dùng `pandas` để làm sạch (loại bỏ Null, nối mảng Tác giả, chuẩn hóa định dạng Ngày tháng).
- Thiết lập hệ thống kiểm tra chất lượng (Data Quality) bằng cách đếm số dòng lỗi, độ dài tóm tắt, và tính độ trễ ngày tháng (`age_days`).
- Xây dựng file luồng chạy (Orchestration) để chạy tự động qua tất cả các bước thay vì chạy tay từng file.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Dữ liệu JSON thô từ REST API của Crossref |
| Output                         | Báo cáo so sánh Markdown (`corruption_report.md`) |
| Module phụ thuộc             | `core/config.py` (cung cấp đường dẫn và cấu hình) |
| Module sử dụng output        | Không có (đây là output cuối cùng báo cáo cho người dùng) |
| Điều kiện lỗi cần xử lý | Mất mạng, Lỗi Unicode trên Windows, Quên cấu hình API Key LLM |

### Cách xác minh

```bash
python src/pipelines/corruption_flow.py
```

- **Kết quả mong đợi:** Pipeline chạy mượt mà qua các khâu Corrupt -> Repair -> Compare mà không bị crash.
- **Kết quả thực tế:** Hệ thống chạy thành công và xuất ra báo cáo chứng minh AI bị giảm điểm khi dữ liệu bẩn và phục hồi khi dữ liệu sạch.
- **Artifact/log:** `data/reports/corruption_report.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Phát hiện lỗi UnicodeEncodeError khi in chữ tiếng Việt ra màn hình Windows Terminal làm crash Pipeline ở pha cuối cùng.
- **Các phương án đã cân nhắc:** (1) Bắt người dùng đổi biến môi trường `PYTHONIOENCODING=utf-8` hoặc (2) Đổi toàn bộ các lệnh in ra màn hình sang tiếng Anh.
- **Phương án đã chọn:** Phương án 2 (Đổi ngôn ngữ in ra màn hình trong các file pipeline).
- **Lý do:** Giảm thiểu sự phức tạp trong quá trình setup môi trường cho các thành viên khác khi họ kéo code về máy chạy (đặc biệt là môi trường Windows).
- **Bằng chứng quyết định phù hợp:** Pipeline chạy trơn tru đến cuối sau khi áp dụng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `RuntimeError: GOOGLE_API_KEY is required when LLM_PROVIDER=gemini.`
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_phase1.py` khi chưa cấu hình file `.env`.
- **Nguyên nhân gốc:** Module RAG Agent và LLM Judge cần khóa API để gọi lên Gemini. Hệ thống có cơ chế kiểm tra (Guard) và văng lỗi ngay khi file `.env` chứa khóa này bị thiếu.
- **Cách xử lý:** Mở file `.env`, điền API Key thật của Google vào, lưu lại.
- **Cách xác minh sau khi sửa:** Chạy lại Pipeline và nó không còn báo lỗi nữa.
- **Điều học được:** Cần kiểm tra kỹ các biến môi trường cấu hình trước khi chạy bất kỳ ứng dụng nào sử dụng API bên thứ ba.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu JSON kéo về từ API -> Lọc thành mảng Dictionary (Ingestion) -> Đưa vào DataFrame của Pandas để làm sạch (Cleaning) tạo ra cột `text_for_embedding` -> Trích xuất cột này đẩy vào ChromaDB và dùng mô hình MiniLM để tạo Vector (Embedding).
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Ground-truth Document IDs dùng để kiểm tra xem thuật toán tìm kiếm Vector có moi lên đúng bài báo gốc không (Hit Rate). Evaluation set (Ground truth) dùng làm đáp án mẫu để Giám khảo LLM hoặc hàm Token F1 đem so sánh với câu trả lời thực tế của Agent (Judge Accuracy).
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks quan tâm tới độ hoàn thiện của dữ liệu (không trùng lặp, không rỗng tiêu đề, tóm tắt đủ dài). Còn Freshness monitoring tập trung duy nhất vào tuổi đời của dữ liệu (`age_days` > 180 thì coi là đồ ôi thiu).
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính công bằng (cố định hằng số). Việc này giúp khẳng định nguyên nhân duy nhất làm biến động điểm số đánh giá là do chất lượng dữ liệu bị thay đổi, chứ không phải do câu hỏi khó hay dễ.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Khi điểm số Quality Passed & Freshness Passed chuyển từ ❌ No thành ✅ Yes, đồng thời Retrieval Hit Rate và Judge Accuracy phục hồi lại về đúng bằng mức của Baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |     1.00 |      0.60 |     1.00 | Dữ liệu hỏng làm AI không tìm thấy bài báo (tụt 40%). |
| `mean_token_f1`      |     0.43 |      0.26 |     0.43 | Phục hồi hoàn hảo. |
| `judge_accuracy`     |     0.33 |      0.20 |     0.33 | Khả năng trả lời đúng của AI tụt mạnh khi mất thông tin. |
| `mean_judge_score`   |     2.33 |      1.80 |     2.33 | Phục hồi hoàn hảo sau khi Clean lại từ RAW. |
| Quality checks         |   ✅ Yes |     ❌ No |   ✅ Yes | Hoạt động cực kỳ nhạy bén để phát hiện lỗi. |
| Freshness status       |   ✅ Yes |     ❌ No |   ✅ Yes | Báo động đúng các bài báo cũ kỹ. |

### Kết luận từ số liệu

1. **Data corruption** → **quality/freshness signal thay đổi (từ Yes sang No)** → **agent metric thay đổi (tụt dốc thê thảm từ 1.00 Hit Rate xuống 0.60)**.
2. **Repair action (chạy lại luồng clean từ nguồn thô)** → **quality/freshness signal phục hồi (trở lại Yes)** → **agent metric phục hồi (trở lại 1.00 như Baseline)**.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
Việc cắt vụn tiêu đề (truncate) và xóa trống Tóm tắt (blank summary) ảnh hưởng trực tiếp đến khả năng truy xuất (Retrieval) của hệ thống. Vì nội dung của cột `text_for_embedding` hoàn toàn phụ thuộc vào chúng. Khi chúng bị rỗng hoặc thiếu từ khóa, Vector được tạo ra không mang thông tin ngữ nghĩa đúng, dẫn đến hệ thống tìm không ra bài báo liên quan, kéo theo mọi câu trả lời của RAG LLM đều sai lệch đi.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Hệ thống RAG không chỉ phụ thuộc vào Prompt hay LLM xịn, mà chất lượng dữ liệu đầu vào (Garbage In - Garbage Out) đóng vai trò sống còn.
2. Data Observability là hệ thống bắt buộc phải có để phát hiện sự hỏng hóc một cách chủ động thay vì chờ khách hàng phàn nàn AI trả lời sai sự thật.
3. Việc phân chia module hóa các hàm nhỏ giúp quá trình phục hồi (Repair) cực kỳ dễ dàng (chỉ cần gọi lại hàm Clean với file Raw ban đầu).

### Nếu có thêm thời gian
Em sẽ bổ sung thêm một lớp Filter (Lọc) tự động trong Pipeline. Lớp lọc này sẽ cô lập (Quarantine) các dòng dữ liệu bị báo lỗi (Corrupted/Stale) bởi Observability không cho đưa vào Vector thay vì dừng lại toàn bộ hoặc nạp tuốt vào Vector. Cách đo lường là tính xem lượng dữ liệu "rác" không lọt được vào ChromaDB là bao nhiêu %.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đoàn Văn Tuyền
**Ngày xác nhận:** 2026-08-06
