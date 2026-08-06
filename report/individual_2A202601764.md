# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Hoàng Minh |
| MSSV               | 2A202601764 |
| Khóa/Lớp         | K4 |
| Tên nhóm         | LowTech |
| Vai trò chính    | Source Ingestion & Cleaning Owner (phần 3) |
| Repository         | https://github.com/HaiVietahihi/K4_Day10_Data-Pipeline-Data-Observability_LowTech_Nhat |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Raw ingestion từ Crossref | `src/ingestion/crossref.py`: `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | `Settings.source_query`, `source_filter`, `max_results` từ `src/core/config.py` | `data/raw/crossref_response.json` (response thô), `data/raw/crossref_records.json` (24 record phẳng theo schema `PaperRecord`) | Hoàn thành |
| Cleaning & data modeling | `src/ingestion/cleaning.py`: `build_clean_dataframe`, `save_clean_dataset`, `strip_markup` | `list[PaperRecord]` + `run_date` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` (24 dòng × 16 cột) | Hoàn thành |

Phần việc của tôi là hai mắt xích đầu tiên của pipeline. Đầu ra của tôi là đầu vào bắt buộc của ba người còn lại: `papers_clean.csv` được `src/retrieval/index.py` dùng để build embedding, được `src/evaluation/testset.py` dùng để sinh câu hỏi và ground truth, được `src/observability/quality.py` dùng để chạy quality/freshness checks. Riêng `data/raw/crossref_records.json` là **nguồn repair** của `src/pipelines/corruption_flow.py` — nếu file này không đủ tin cậy thì bước repair của cả nhóm không có gì để phục hồi.

Tôi không nhận ownership cho `testset.py`, `quality.py`, `reporting.py`, `corruption.py`, `phase1.py` và `corruption_flow.py`.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Setup môi trường và smoke test toàn bộ dependency | Cả nhóm | Xác nhận Python 3.13.0, `pip install -e .` thành công, MiniLM tải được (384 chiều), ChromaDB 1.5.9 chạy đúng API `create_collection(configuration={"hnsw": {"space": "cosine"}})` mà `index.py` đang gọi. Phân biệt được lỗi môi trường với `NotImplementedError` cố ý. |
| Khảo sát contract của code có sẵn | Người viết `testset.py` và `phase1.py` | Cảnh báo `src/retrieval/qa.py:20-29` khớp câu hỏi bằng từ khóa cứng (`who authored`, `when was`, `what categories`) và chỉ nhận exact lookup khi title nằm trong dấu nháy đơn — test set phải viết đúng khuôn này, nếu không baseline `mean_token_f1` sẽ thấp giả tạo. |
| Ghi chú version drift | Cả nhóm | Máy chưa có `uv` nên `pip install -e .` resolve về bản mới nhất thay vì pin trong `uv.lock`: pandas 3.0.5 (major version), chromadb 1.5.9, langchain 1.3.14. Code cleaning được viết theo API pandas 3.x. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Gọi Crossref `/works` với retry/backoff, lưu hai dạng raw artifact | `src/ingestion/crossref.py`, `data/raw/` | Response thô 234 KB giữ nguyên 24 items và markup JATS; 24 record phẳng đúng 11 field của `PaperRecord` | Lệnh và output ở cuối mục 4 |
| Parse payload, lọc record không đủ điều kiện, tạo `paper_id` ổn định | `parse_crossref_payload` | Chỉ giữ record có đủ DOI + title + abstract; DOI lowercase thành `paper_id`; dedupe theo DOI | Test tổng hợp: payload 5 item có 1 item hợp lệ → parse trả đúng 1 record |
| Replay pipeline không gọi lại API | `load_raw_records` | Round-trip `fetch → load` khớp `paper_id` từng phần tử | Lệnh xác minh ở mục 4 (đọc từ snapshot, không chạm mạng) |
| Làm sạch và mô hình hóa dữ liệu cho retrieval | `build_clean_dataframe` | 24 dòng × 16 cột, 0 null, `paper_id` unique, không còn markup, `age_days` 5–175 | Lệnh xác minh ở mục 4 |
| Ghi artifact clean | `save_clean_dataset` | `papers_clean.csv` (97 KB), `papers_clean.json` (111 KB) | `pd.read_csv` round-trip giữ đúng 16 cột và `age_days` kiểu int |

Một output cụ thể do phần việc của tôi tạo ra:

`data/clean/papers_clean.csv` — corpus 24 paper với `age_days` trải từ **5 đến 175 ngày**, toàn bộ nằm dưới ngưỡng freshness 180 ngày của `Settings.freshness_threshold_days`. Đây không phải con số ngẫu nhiên: `source_filter` trong `config.py` đặt `from-pub-date` đúng bằng hôm nay trừ 180 ngày, nên **baseline được đảm bảo 100% fresh theo thiết kế**. Nhờ vậy khi thành viên corruption làm stale publication date, tín hiệu freshness sẽ chuyển từ Fresh sang Stale một cách dứt khoát thay vì mập mờ — tức là phần việc của tôi tạo ra điều kiện để chuỗi nhân quả của cả bài lab đo được.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Crossref là API công khai và dữ liệu trả về không sạch: abstract bọc trong thẻ JATS và bị double-encode, tác giả nằm trong dict lồng nhau `{given, family}`, ngày tháng ở dạng mảng `date-parts` có thể thiếu tháng hoặc ngày, `subject` gần như luôn null, và API có thể trả 429/503 tạm thời. Nếu đưa thẳng dữ liệu này vào embedding thì vector sẽ học cả rác markup, và toàn bộ metric phía sau mất ý nghĩa. Phần của tôi phải biến dữ liệu đó thành một dataset phẳng, ổn định, có thể tái lập — đồng thời giữ lại bản gốc để nhóm có thể audit và repair.

### Cách triển khai

**Tách bạch raw và clean.** `fetch_source_records` ghi hai artifact với hai mục đích khác nhau: `crossref_response.json` là body API nguyên bản (còn nguyên `<jats:p>`) để audit nguồn, `crossref_records.json` là bản phẳng đã parse để pipeline dùng lại. Parse **không** strip markup — việc đó thuộc về cleaning.

**Retry có kiểm soát.** Backoff mũ 2s → 4s → 8s → 16s (cap 32s), tối đa 5 lần, chỉ retry `{429, 500, 502, 503, 504}` và lỗi mạng, tôn trọng header `Retry-After` nếu server gửi. Lỗi 4xx khác (ví dụ 404 do sai endpoint) raise ngay thay vì thử lại vô ích.

**`paper_id` ổn định.** Lấy DOI, lowercase, dùng làm khóa duy nhất xuyên suốt raw → clean → index → evaluation. Đây là quyết định có hệ quả xa: `src/evaluation/metrics.py:116` so khớp `ground_truth_doc_ids` với `retrieved_doc_ids` bằng so sánh chuỗi chính xác, mà DOI vốn không phân biệt hoa thường — nếu không chuẩn hóa một lần ở đây thì `retrieval_hit_rate` sẽ miss oan.

**Sáu quy tắc cleaning**, mỗi quy tắc đều có counter: drop record thiếu `paper_id`, thiếu title, abstract dưới 100 ký tự, ngày không parse được, trùng `paper_id`, trùng title (cả hai dedupe đều case-insensitive). Sau đó strip markup, gộp `authors_joined`/`categories_joined` bằng dấu phẩy, chuẩn hóa `published` về `YYYY-MM-DD` (tự pad khi chỉ có năm hoặc năm-tháng), tính `age_days` so với `run_date`, và ghép `text_for_embedding` theo đúng format `Title: … | Authors: … | Summary: …`.

**Không mất record âm thầm.** Toàn bộ counter được in ra stdout và gắn vào `df.attrs["cleaning_stats"]` để người viết `quality.py` và `phase1.py` dùng lại thay vì đếm lại từ đầu.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | `Settings` (query, filter, max_results) cho fetch; `list[PaperRecord]` + `run_date: datetime` cho cleaning |
| Output | 4 artifact: 2 file raw trong `data/raw/`, 2 file clean trong `data/clean/`. DataFrame 16 cột, tất cả đều là scalar |
| Module phụ thuộc | `src/core/config.py` (paths, settings), `src/core/utils.py` (`write_json`, `write_csv`, `normalize_whitespace`, `compact_join`) |
| Module sử dụng output | `src/retrieval/index.py` (cần `paper_id`, `title`, `text_for_embedding`, `published`, `authors_joined`, `categories_joined`, `summary`, `abs_url`, `pdf_url`), `src/evaluation/testset.py`, `src/observability/quality.py`, `src/pipelines/corruption_flow.py` (repair từ raw records) |
| Điều kiện lỗi cần xử lý | HTTP 429/503 tạm thời; lỗi mạng; `date-parts` thiếu tháng/ngày; `subject` null; abstract double-encode; record thiếu DOI/title/abstract; DOI trùng khác hoa thường; Crossref trả 0 record hợp lệ (raise kèm đường dẫn raw response để debug) |

### Cách xác minh

```bash
python -c "
import pandas as pd
from core.config import load_settings
from core.utils import now_utc
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records

s = load_settings()
records = load_raw_records(s.paths.raw_records_json)
df = build_clean_dataframe(records, now_utc())
print('raw records      :', len(records))
print('clean rows x cols:', df.shape)
print('paper_id unique  :', df['paper_id'].is_unique)
print('nulls            :', int(df.isna().sum().sum()))
print('min summary_chars:', int(df['summary_chars'].min()))
print('age_days         :', int(df['age_days'].min()), '->', int(df['age_days'].max()), '| threshold', s.freshness_threshold_days)
print('markup con sot   :', bool(df['summary'].str.contains('<|&lt;').any()))
"
```

- **Kết quả mong đợi:** 24 raw record vào, 24 dòng ra, `paper_id` unique, 0 null, summary tối thiểu vượt ngưỡng 100 ký tự, `age_days` nằm dưới 180, không còn markup.
- **Kết quả thực tế:**

```text
[cleaning] kept 24/24 records (dropped: missing_paper_id=0, missing_title=0, short_summary=0,
           invalid_published=0, duplicate_paper_id=0, duplicate_title=0)
raw records      : 24
clean rows x cols: (24, 16)
paper_id unique  : True
nulls            : 0
min summary_chars: 826
age_days         : 5 -> 175 | threshold 180
markup con sot   : False
```

Lệnh này đọc từ raw snapshot nên **không gọi lại API** — tái lập được offline và không làm thay đổi baseline.

Kiểm tra riêng rằng raw response được lưu đúng dạng body nguyên bản của API:

```bash
python -c "
from pathlib import Path
from core.utils import read_json
p = read_json(Path('data/raw/crossref_response.json'))
print(sorted(p), len(p['message']['items']))
"
# ['message', 'message-type', 'message-version', 'status'] 24
```

Ngoài ra tôi chạy hai bộ kiểm thử riêng:

- **34/34 check tích hợp** với API thật: raw response giữ đúng cấu trúc `status`/`message-type`/`message` và markup JATS; round-trip `fetch → load_raw_records` khớp `paper_id` từng phần tử; CSV round-trip giữ `age_days` kiểu int; đủ 9 cột mà `index.py` yêu cầu và tất cả đều là `str` (hợp lệ làm metadata Chroma).
- **26 check edge case** với dữ liệu tổng hợp, **25 pass**. Check fail duy nhất là do tôi ghi sai giá trị kỳ vọng trong chính file test (582 ngày viết nhầm thành 583) — code tính đúng, đã đối chiếu lại bằng `datetime.date`. Tôi ghi lại đây thay vì bỏ qua vì báo cáo phải khớp với log thật.

- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`. Không file nào chứa secret; `.env` và `.venv/` đã nằm trong `.gitignore` và được xác nhận bằng `git check-ignore -v .env .venv`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Abstract của Crossref chứa markup JATS. Câu hỏi là strip markup ở đâu — lúc parse (trước khi ghi raw) hay lúc cleaning.

- **Các phương án đã cân nhắc:**
  1. Strip ngay trong `parse_crossref_payload`, để raw records đã sạch sẵn. Cleaning nhẹ đi.
  2. Strip trong `build_clean_dataframe`, raw giữ nguyên markup gốc.
  3. Strip ở cả hai chỗ cho chắc.

- **Phương án đã chọn:** Phương án 2 — raw giữ nguyên vẹn, cleaning là nơi duy nhất strip.

- **Lý do:** Ba lý do, xếp theo mức quan trọng. Thứ nhất, **audit**: đề bài yêu cầu raw artifact để "tái hiện và sửa lỗi mà không cần gọi lại API", mà một bản đã bị biến đổi thì không còn là bằng chứng về nguồn nữa. Thứ hai, **repair**: `corruption_flow.py` phục hồi bằng cách chạy lại cleaning từ raw records; nếu raw đã sạch sẵn thì bước repair chỉ là copy file, không chứng minh được rằng quy tắc ETL mới là thứ khôi phục dữ liệu. Thứ ba, **một nguồn sự thật duy nhất**: strip ở hai chỗ (phương án 3) tạo ra hai đoạn code có thể lệch nhau sau này. Cái giá phải trả là raw records nặng hơn và cleaning phải làm nhiều việc hơn — tôi chấp nhận vì đây chỉ là 24 record.

- **Bằng chứng quyết định phù hợp:** Hai check chạy đối nghịch nhau và cùng pass: `raw response keeps JATS markup (auditable)` khẳng định `data/raw/` còn nguyên `<jats:p>`, còn `no XML/HTML markup left in title/summary` khẳng định `data/clean/` đã sạch hoàn toàn. Hai artifact cùng tồn tại chứng minh ranh giới raw/clean được giữ đúng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Trước khi viết code, tôi probe API bằng chính `source_query` trong `config.py` và đếm độ phủ của từng field. Kết quả: `subject` **null ở 24/24 record**, trong khi `type` có ở 24/24 và `container-title` ở 15/24.

```text
Field coverage (n=24):
   24/24  type
   24/24  publisher
   15/24  container-title
    7/24  group-title
   (subject: không xuất hiện ở bất kỳ record nào)

subject: null
```

- **Lệnh tái hiện:**

```bash
python -c "
import requests, collections
from core.config import load_settings
s = load_settings()
r = requests.get('https://api.crossref.org/works',
                 params={'query': s.source_query, 'filter': s.source_filter, 'rows': s.max_results},
                 headers={'User-Agent': 'Day10Lab/0.1 (mailto:day10-lab@example.com)'}, timeout=40)
items = r.json()['message']['items']
print('co subject:', sum(1 for i in items if i.get('subject')), '/', len(items))
"
```

- **Nguyên nhân gốc:** Không phải lỗi code của tôi mà là thay đổi ở phía nguồn dữ liệu — Crossref trên thực tế đã ngừng populate trường `subject`. Nếu map thẳng `subject` sang `categories` theo cách hiển nhiên nhất thì `categories_joined` sẽ rỗng ở toàn bộ 24 dòng. Hệ quả dây chuyền: `testset.py` cần sinh câu hỏi loại `categories`, và `qa.py:28` trả lời câu hỏi `what categories` bằng `metadata["categories_joined"]` — một chuỗi rỗng sẽ khiến `token_f1` của cả nhóm câu hỏi đó bằng 0 ở **mọi** trạng thái. Corruption có làm hỏng thêm cũng không đo được gì, vì metric đã chạm đáy sẵn từ baseline.

- **Cách xử lý:** Thêm fallback trong `_categories()`: dùng `subject` nếu có, nếu không thì lấy `container-title` (hoặc `group-title`) làm venue cộng với `type` đã chuẩn hóa thành Title Case. Ví dụ record đầu tiên cho ra `"SPE Journal, Journal Article"` thay vì chuỗi rỗng. `primary_category` lấy phần tử đầu của danh sách này.

- **Cách xác minh sau khi sửa:** Check `categories_joined non-empty (subject fallback works)` pass trên toàn bộ 24 dòng thật, cộng một test tổng hợp khẳng định payload không có `subject` cho ra đúng `['J', 'Journal Article']`.

- **Điều học được:** Đọc schema tài liệu là chưa đủ, phải đo độ phủ thực tế của từng field trên chính query mình sẽ dùng. Quan trọng hơn: một trường rỗng ở bước ingestion không dừng pipeline lại — nó đi âm thầm tới tận evaluation rồi mới biểu hiện thành metric xấu, và lúc đó rất khó truy ngược. Đây chính là lý do bài lab tồn tại: lỗi dữ liệu không gây crash, nó gây kết quả sai.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**

`fetch_source_records` gọi `https://api.crossref.org/works` với query, filter và số dòng lấy từ `Settings`, ghi response thô xuống `data/raw/crossref_response.json`. `parse_crossref_payload` rút từ `message.items` ra các trường cần thiết, tạo `PaperRecord` với `paper_id` là DOI đã lowercase, ghi xuống `data/raw/crossref_records.json`. `build_clean_dataframe` strip markup, lọc record xấu, tính `age_days`, ghép `text_for_embedding` rồi ghi `data/clean/papers_clean.csv`. Từ đó `LocalEmbeddingIndex.build` biến mỗi dòng thành một document có `record_id = paper_id::index`, encode `text_for_embedding` bằng `all-MiniLM-L6-v2` thành vector 384 chiều, và nạp vào collection Chroma `papers-baseline` với cosine distance, kèm metadata (title, published, authors_joined, categories_joined, summary, URLs). Manifest được ghi ra `data/embeddings/papers_embeddings.json`.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**

Test set được sinh **từ chính cleaned dataset**, nên mỗi câu hỏi biết trước tài liệu nào chứa câu trả lời — đó là `ground_truth_doc_ids`. Khi đánh giá, `answer_question` truy vấn index và trả về `retrieved_doc_ids` (top-k, mặc định 4). `metrics.py` đo hai thứ khác nhau: **retrieval** đúng hay sai (`retrieval_hit_rate` = có ít nhất một doc trong top-k thuộc ground truth hay không) và **câu trả lời** đúng hay sai (`token_f1` so trùng token với `ground_truth`, cộng LLM judge cho điểm 1–5). Tách hai tầng này là cần thiết: hệ thống có thể tìm đúng tài liệu nhưng trả lời sai, hoặc tìm sai mà vẫn đoán trúng — chỉ nhìn một metric sẽ quy sai nguyên nhân.

**3. Quality checks khác freshness monitoring ở điểm nào?**

Quality checks trả lời "dữ liệu có **đúng và đầy đủ** không": đủ số dòng không, `paper_id` có null hay trùng không, title có rỗng không, summary có quá ngắn không. Freshness trả lời một câu hoàn toàn khác: "dữ liệu có **còn mới** không" — dựa trên `published` và `age_days` so với ngưỡng 180 ngày. Một dataset có thể pass sạch mọi quality check mà vẫn stale: đủ 24 dòng, không null, không trùng, nhưng toàn bộ là bài báo từ năm 2019. Với hệ RAG thì đó vẫn là hỏng, vì agent sẽ trả lời tự tin bằng thông tin lỗi thời. Hai loại tín hiệu này bắt được hai họ sự cố khác nhau, nên bài lab yêu cầu cả hai.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**

Vì mục tiêu là đo **tác động của corruption**, không phải đo độ khó của câu hỏi. Nếu mỗi trạng thái sinh test set riêng thì khi `mean_token_f1` tụt, không thể biết là do dữ liệu hỏng hay do bộ câu hỏi mới khó hơn — biến số bị lẫn và kết luận nhân quả sụp đổ. Giữ nguyên test set, ground truth, evaluator và `top_k` khiến dữ liệu trở thành **biến duy nhất thay đổi**, nên mọi chênh lệch metric đều quy được về corruption. Đây cũng là lý do repair phải chạy lại từ raw snapshot cũ chứ không fetch mới: dữ liệu mới sẽ mang theo paper khác, và test set cũ trỏ tới `ground_truth_doc_ids` không còn tồn tại trong index.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**

Không chỉ dựa vào việc script chạy xong. Cần đối chiếu đồng thời: (a) `data/clean/papers_clean_repaired.csv` khôi phục đúng số dòng và `paper_id` như baseline; (b) quality checks trong `data/quality/` chuyển từ Fail về Pass và freshness về lại Fresh; (c) `data/results/repaired_metrics.json` có `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score` quay lại xấp xỉ `baseline_metrics.json`; (d) `data/reports/corruption_report.md` trình bày cả ba trạng thái cạnh nhau kèm delta. Và điều kiện tiên quyết: repair phải sinh ra từ việc **chạy lại cleaning trên raw records**, không phải copy đè file baseline — nếu chỉ copy thì con số đẹp nhưng không chứng minh được pipeline có khả năng phục hồi.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | Chưa có | Chưa có | Chưa có | Cần `phase1.py` và `corruption_flow.py` chạy xong |
| `mean_token_f1`      | Chưa có | Chưa có | Chưa có | Như trên |
| `judge_accuracy`     | Chưa có | Chưa có | Chưa có | Như trên; ngoài ra cần `GOOGLE_API_KEY` để có số thật |
| `mean_judge_score`   | Chưa có | Chưa có | Chưa có | Như trên |
| Quality checks         | Chưa có | Chưa có | Chưa có | Cần `quality.py` |
| Freshness status       | Chưa có | Chưa có | Chưa có | Dữ liệu đầu vào đã sẵn sàng: `age_days` 5–175, dưới ngưỡng 180 |

**Tại thời điểm nộp bản báo cáo này, tôi không điền số vào bảng trên vì `data/results/baseline_metrics.json`, `corrupted_metrics.json` và `repaired_metrics.json` chưa tồn tại.** Các module sinh ra chúng (`testset.py`, `quality.py`, `reporting.py`, `phase1.py`, `corruption.py`, `corruption_flow.py`) thuộc phần việc của thành viên khác và chưa hoàn thành. Tôi không suy đoán số liệu cho phần mình không chạy được — đó là điều kiện trong mục 10 và cũng là yêu cầu của rubric về việc báo cáo phải khớp artifact thật.

Bảng này sẽ được điền sau khi hai entrypoint chạy end-to-end.

### Kết luận từ số liệu

Chưa đủ dữ liệu để khẳng định quan hệ nhân quả. Dưới đây là **dự đoán có cơ sở** từ phần việc của tôi, ghi rõ là dự đoán để đối chiếu về sau chứ không phải kết quả:

1. *(Dự đoán)* Corruption làm stale publication date → `age_days` vượt 180 → freshness chuyển Stale. Cơ sở: baseline hiện có `age_days` cao nhất là 175, chỉ cách ngưỡng 5 ngày, nên chỉ cần đẩy lùi ngày xuất bản một lượng nhỏ là tín hiệu đảo chiều. Tác động lên metric trả lời thì chưa chắc: `qa.py` trả `metadata["published"]` cho câu hỏi loại date, nên nhóm câu hỏi đó sẽ sai, còn nhóm summary có thể không đổi.
2. *(Dự đoán)* Corruption blank summary → `summary_chars` tụt dưới ngưỡng quality check → `text_for_embedding` mất phần nội dung chính → vector mất tín hiệu ngữ nghĩa → `retrieval_hit_rate` giảm. Tôi cho rằng đây sẽ là corruption ảnh hưởng mạnh nhất, vì summary là thành phần dài nhất trong `text_for_embedding` (tối thiểu 826 ký tự so với title chỉ vài chục), nên xóa nó gần như phá hủy toàn bộ vector.

Tôi sẽ kiểm chứng hai dự đoán này bằng `corruption_log.json` và bảng so sánh trong `corruption_report.md` khi nhóm chạy xong, và sẽ ghi lại nếu kết quả trái với dự đoán.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Ranh giới raw/clean không phải chuyện gọn gàng thư mục mà là điều kiện để phục hồi được. Vì giữ raw nguyên vẹn nên nhóm có thể replay toàn bộ pipeline offline, sửa quy tắc ETL rồi chạy lại mà không tốn thêm một lần gọi API — và quan trọng hơn, baseline với repaired vẫn so sánh được công bằng vì cùng xuất phát từ một snapshot.

2. **Về data quality/observability:** Lỗi dữ liệu không làm chương trình crash. `subject` null trả về danh sách rỗng một cách hoàn toàn hợp lệ, pipeline chạy tới cuối, chỉ có metric là xấu — và lúc đó rất khó truy ngược từ một con số `token_f1` thấp về đúng cái trường bị thiếu. Vì thế counter cho từng quy tắc drop và tín hiệu quality phải được đặt **ngay tại điểm dữ liệu bị biến đổi**, không phải đợi tới cuối đường ống.

3. **Về ảnh hưởng của data đến RAG agent:** `text_for_embedding` là nơi chất lượng dữ liệu chuyển hóa thành chất lượng retrieval. Vector chỉ biết những gì có trong chuỗi đó — markup rác vào thì vector học rác, summary bị xóa thì vector mất gần hết tín hiệu. Toàn bộ tầng agent, prompt và LLM phía sau không cứu được một embedding đã hỏng từ đầu vào.

### Nếu có thêm thời gian

Tôi sẽ viết một **schema contract test** chạy độc lập cho `data/clean/papers_clean.csv`: kiểm 16 cột đúng tên và đúng kiểu, `paper_id` unique và non-null, không ô nào là list/dict, `published` khớp regex `YYYY-MM-DD`, `text_for_embedding` khớp đúng format ba phần. Hiện tại các check này nằm trong script kiểm thử tạm của riêng tôi; đưa chúng thành `pytest` trong repo sẽ biến contract giữa tôi và ba thành viên còn lại thành thứ chạy được thay vì thứ thỏa thuận miệng. Cách đo cải thiện: cố tình đổi một tên cột trong `CLEAN_COLUMNS` rồi chạy `pytest` — test phải fail ngay tại tầng cleaning, thay vì để lỗi trôi xuống `index.py` và biểu hiện thành `KeyError` khó đọc.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Hoàng Minh
**Ngày xác nhận:** 2026-08-06
