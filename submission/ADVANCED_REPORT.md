# Kết quả NB5–NB8 và Hybrid AI Memory

Môi trường: Windows, Python 3.12, nhánh Lite, FastEmbed BGE-small 384 chiều,
Qdrant local trong RAM, Feast SQLite. Notebook `.py` là nguồn; `.ipynb` là bản
đã chạy có output. Dữ liệu sinh từ các script của lab, không phải dữ liệu thật.

## NB5 — Filtered Search

Pre-filter là cosine chính xác trên subset và làm ground truth. Với filter
`acme AND >=2026`, 38/1000 tài liệu khớp (3,8%): post-filter top-10 toàn corpus
có recall 0,00, trong khi filtered search có recall 1,00. Bảng notebook in
recall và thời gian của cả ba phương pháp.

| `fetch_k` | Recall trung bình trên 3 query | Candidate budget / corpus |
|---:|---:|---:|
| 10 | 0,03 | 1% |
| 50 | 0,27 | 5% |
| 200 | 0,80 | 20% |
| 500 | 1,00 | 50% |
| 1000 | 1,00 | 100% |

Over-fetch phải lên 500 trong phép đo này mới phục hồi toàn bộ ground truth.
Qdrant local không dùng payload index/HNSW như server: 10 hits trả về không
chứng minh engine chỉ duyệt 10 vector. Các số latency chỉ phản ánh lần chạy
Lite trên máy này; recall 1,00 không phải bảo đảm cho mọi cấu hình ANN.

## NB6 — Agentic Retrieval

| Chiến lược | Recall | Balance | Calls trung bình |
|---|---:|---:|---:|
| Single-shot | 0,526 | 0,08 | 1,0 |
| Agentic, không filter | 0,922 | 0,92 | 2,3 |
| Agentic, có filter | 0,839 | 0,75 | 2,3 |

Ba chiến lược đều có đúng 16 candidate slots trong kế hoạch ban đầu. Planner
chia cả phần dư khi có ba câu con (6+5+5), thay vì bỏ mất một slot. Dedup có thể
làm số tài liệu duy nhất nhỏ hơn 16. Reflection tăng số call khi filter làm
thiếu bằng chứng; chi phí được báo cáo, không coi là miễn phí.

Hard topic filter suy từ keyword loại cả tài liệu liên quan ở topic khác.
Ground truth là hợp cosine top-8 của hai câu con trên toàn corpus, vì vậy
agentic có filter thấp hơn no-filter. Planner là rule-based, không gọi LLM.
`build_context()` in được feature Feast của `u_001` (`cloud`, `vi`) và doc IDs.
Demo reflection phục hồi từ 0 thành 8 kết quả sau một lần retry bỏ filter.

## NB7 — Semantic Cache

| Ngưỡng | Positive probes được reuse | Negative probes bị false-hit |
|---:|---:|---:|
| 0,60 | 100% | 97% |
| 0,70 | 100% | 60% |
| 0,75 | 100% | 36% |
| 0,80 | 100% | 5% |
| **0,85** | **100%** | **0%** |
| 0,90 | 96% | 0% |
| 0,95 | 53% | 0% |

Chọn 0,85: ngưỡng nhỏ nhất trong sweep có false-hit bằng 0 và reuse ít nhất
80% trên bộ probe này. Kiểm tra thêm cho thấy positive probes không ghép sai
đáp án (0/75). Đây là bộ thử nhỏ; không suy ra bảo đảm 0% lỗi trong production.
“Tiết kiệm” là tỷ lệ reuse giả định, chưa đo chi phí USD của một LLM thật.

`namespaced=False` làm Globex nhận doanh thu của Acme; bật namespace trả MISS.
TTL demo: HIT tại t=0 và t=600, MISS tại t=4200, một stale eviction.
Namespace là điều kiện cô lập cache, không thay thế xác thực người dùng.

## NB8 — Feature Engineering

| Encoding trên `session_id` | Train AUC | Test AUC | Gap |
|---|---:|---:|---:|
| Target-naive | 0,999 | 0,522 | **0,477** |
| Target-in-fold | 0,519 | 0,522 | **−0,003** |

Target-naive dùng nhãn của chính hàng train trong mã hóa nên train AUC gần 1;
in-fold loại ảnh hưởng đó. Latest join có 98,2% dòng dùng feature từ tương lai:
AUC 0,715 so với PIT 0,595, chênh 0,120. Việc AUC giảm khi bỏ leakage là kết quả
đúng, không phải lý do chọn latest join. Hệ thực cần xét cả thời điểm dữ liệu
được cung cấp, ngoài event timestamp.

Feast ODFV đã apply/materialize và trả ba dòng. Cùng `u_000`, amount 100.000
và 15.000.000 cho `amount_vs_avg` khoảng 0,03 và 4,21; `is_spike` lần lượt 0
và 1. Đã sửa lệnh subprocess dùng Python/Feast của venv và UTC hiện tại để
chạy đúng trên Windows.

## Bonus — Hybrid AI Memory

[ARCHITECTURE.md](../bonus/ARCHITECTURE.md) có sơ đồ, ba quyết định và đánh đổi,
phương án bị bác bỏ, đặc thù tiếng Việt và giới hạn POC.
[agent.py](../bonus/agent.py) triển khai `remember()` và `recall()` bằng
Qdrant có filter `user_id`, BM25 theo user, RRF và profile/activity từ Feast.

[demo.py](../bonus/demo.py) in context cho đủ năm query mẫu. Query activity
được push vào Feast và tăng từ 1 đến 5; sentinel riêng của user thứ hai không
xuất hiện trong context. Demo trả context, không gọi LLM hay tuyên bố đã tạo
recommendation/summary hoàn chỉnh. Registry bonus tách khỏi project NB4.

## Bằng chứng và chạy lại

Lần kiểm chứng trên venv mới và bản sao sạch: **49 tests passed**, smoke test
Lite **All checks passed**, `pip check` không có dependency lỗi, và demo bonus
**exit code 0** với đủ năm context. Log và exit code được lưu bên dưới.

- Notebook có output: `notebooks/05_filtered_search.ipynb` đến
  `notebooks/08_feature_engineering.ipynb`.
- [Output dạng text](evidence/) và các trang HTML lấy trực tiếp từ output đã
  lưu; ảnh JPG trong [screenshots/](screenshots/) chụp các trang bằng chứng đó.
- [validation.json](evidence/validation.json) lưu exit code từng bước kiểm tra.
  Phạm vi là venv mới và bản sao project không có dữ liệu/registry cũ trên cùng
  máy Windows; dùng lại cache embedding. Đây không phải phép thử máy vật lý mới.
- [Lock dependencies](evidence/requirements-windows-py312.lock.txt) ghi phiên bản
  đã kiểm chứng cho Windows/Python 3.12, không phải lock đa nền tảng.

Từ thư mục gốc lab trong PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts\gen_agent_queries.py
.\.venv\Scripts\python.exe scripts\gen_spend.py
.\.venv\Scripts\python.exe scripts\run_advanced.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -X utf8 scripts\verify_lite.py
.\.venv\Scripts\python.exe -X utf8 bonus\demo.py
```

`pytest -q` và `verify_lite.py` là các lệnh tương ứng của `make test` và
`make verify-lite` trên Windows. Số test được thu thập ở phiên bản repo này
là 49 sau khi bổ sung 8 test về ngân sách, isolation và cửa sổ thời gian.

## Điểm cần lưu ý trước khi nộp

Bản NB3 trước đó của người học ghi hybrid P99 111,7 ms, còn WARN so với rubric
50 ms. NB2 của bản đó cho paraphrase: keyword 33,3%, semantic 24,0%, hybrid
32,0%; chưa thể khẳng định vector thắng slice này. Những kết quả NB1–NB4 đã
được giữ nguyên và không được thay bằng số mong muốn. Báo cáo này không bảo
đảm điểm chấm. Điền tên/cohort trong `REFLECTION.md` và kiểm tra repository
trước khi tự push/nộp URL lên LMS.
