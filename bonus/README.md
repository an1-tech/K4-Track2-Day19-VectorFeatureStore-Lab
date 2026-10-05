# Bonus — Hybrid AI Memory

Ba sản phẩm chính: [thiết kế](ARCHITECTURE.md), [agent](agent.py),
[demo năm query](demo.py). POC dùng Qdrant trong RAM, BM25 và Feast SQLite;
không cần API key. `recall()` trả context cho LLM, chưa gọi LLM.

Từ thư mục gốc repository, với môi trường Lite đã cài:

```powershell
.\.venv\Scripts\python.exe -X utf8 bonus\demo.py
```

Demo tự tạo profile, đăng ký hai feature view và materialize trong project
`lab19_bonus`. Profile lấy từ dữ liệu NB4 nếu có, hoặc từ hai user tổng hợp
khi chạy trên thư mục sạch. Mỗi query push recent activity vào Feast trước
khi lookup. Dòng cuối phải là:

```text
PASS: 5 contexts, fresh Feast activity and no cross-user memories
```

Năm query in cả memory, profile và số query tăng từ 1 đến 5. Một memory riêng
của `u_002` được dùng để kiểm tra isolation. Vector và lịch sử hoạt động trong
RAM mất khi process kết thúc; SQLite nằm trong `bonus/feast_repo/` và được
bỏ qua bởi Git. Phân tích đánh đổi, tiếng Việt và giới hạn ở `ARCHITECTURE.md`.

Chạy test:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_bonus.py
```
