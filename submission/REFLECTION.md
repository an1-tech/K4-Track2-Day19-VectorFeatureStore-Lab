# Reflection — Lab 19

**Tên:** _<Đỗ Quốc An_
**Cohort:** _<A20-K4>_
**Path đã chạy:** Lite (Windows, CPU, Qdrant local + Feast SQLite)

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Hybrid đạt Precision@10 trung bình 78,6%, cao hơn keyword 77,8% và semantic
73,2%. Với exact, keyword và hybrid cùng 96,7%; semantic 88,7%. Với mixed,
hybrid đạt 100%, semantic 98,5%, keyword 97,0%. Với paraphrase, keyword đạt
33,3%, hybrid 32,0%, semantic 24,0%: kết quả thực tế chưa chứng minh vector
thắng. Model embedding thiên về tiếng Anh có thể là một nguyên nhân; cần
kiểm chứng bằng model đa ngữ và tập query lớn hơn.

BM25 phù hợp khi cần khớp mã, tên riêng hoặc thuật ngữ chính xác và muốn giảm
chi phí embedding. Vector phù hợp khi cách diễn đạt khác nguồn, sau khi đã
đo chất lượng model trên ngôn ngữ sử dụng. Hybrid hữu ích với query pha trộn,
nhưng tăng độ trễ và không luôn thắng mọi slice. NB5–NB8 bổ sung bài học về
lọc, ngân sách truy xuất, ngưỡng cache và leakage. Bonus kết hợp memory,
profile và recent activity; demo in đủ năm context.

---

## Điều ngạc nhiên nhất khi làm lab này

_(Optional, 1–2 câu)_

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/` và `submission/ADVANCED_REPORT.md`)
