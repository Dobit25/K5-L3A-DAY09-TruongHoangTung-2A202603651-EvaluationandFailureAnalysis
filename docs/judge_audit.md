# Judge audit

Lệnh replay:

```text
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 10
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 10
```

| Tiêu chí | n | κ | Precision | Recall | Ma trận (tp/fp/fn/tn) | Đạt FLOORS? | Quyết định |
|---|---:|---:|---:|---:|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | 24 / 4 / 6 / 66 | Có | Dùng cho phân tích tone; không dùng cho tiền/approval |
| helpful | 100 | 0.375 | 1.000 | 0.300 | 9 / 0 / 21 / 70 | Không | Loại khỏi blocking gate vì bỏ sót 70% lỗi helpful |

Tone judge quan sát fail rate 0.28; Rogan–Gladen hiệu chỉnh thành 0.30. Helpful judge quan sát 0.09 nhưng hiệu chỉnh thành 0.30, cho thấy chỉ nhìn observed rate sẽ đánh giá quá lạc quan.

## Audit thủ công các bất đồng

| # | Case | Judge | Human | Ai đúng? | Hành động sửa rubric |
|---:|---|---|---|---|---|
| 1 | H-008: “Em đã hoàn tiền… anh check…” | PASS | FAIL | Human | Ghi rõ cách xưng hô suồng sã và đẩy trách nhiệm kiểm tra cho khách là tone fail. |
| 2 | H-029: “vui lòng chờ… không cần nhắn thêm” | PASS | FAIL | Human | Thêm ví dụ về mệnh lệnh cụt/làm khách im lặng vào negative anchors. |
| 3 | H-042: câu lịch sự, thông báo hoàn và ETA | FAIL | PASS | Human | Judge không được suy diễn số tiền nghiệp vụ thành lỗi tone; tiền do code grader kiểm. |
| 4 | H-070: câu đúng nội dung nhưng có emoji cười | PASS | FAIL | Human | Thêm emoji không phù hợp trong ngữ cảnh khiếu nại vào rubric tone. |
| 5 | H-094: tiếng Việt không dấu nhưng lịch sự và có xin lỗi | PASS | FAIL | Human | Human label coi chất lượng trình bày là tone fail; rubric cần nói rõ chuẩn ngôn ngữ/kênh. |
| 6 | HL-015: chỉ báo đã hoàn tiền, không hướng dẫn bước tiếp theo | PASS | FAIL | Human | Helpful rubric phải yêu cầu hành động/ETA phù hợp, không chỉ xác nhận. |
| 7 | HL-047: “Ok bạn… xử lý rồi nhé” | PASS | FAIL | Human | Thêm anchor cho câu quá mơ hồ: “xử lý” không nói kết quả, số tiền hay thời gian. |
| 8 | HL-043: xin lỗi dài nhưng thiếu thông tin xử lý thiết yếu | PASS | FAIL | Human | Không đồng nhất độ dài/đồng cảm với helpfulness; yêu cầu thông tin có thể hành động. |

## Kết luận

Chỉ `tone_ok` đạt cả ba floor κ≥0.6, P≥0.8, R≥0.7. `helpful` có precision cao nhưng recall 0.3 nên không phù hợp làm blocking gate. Cả hai chỉ là replay public, chưa phải held-out judge calibration; trước production cần nhãn người mới, nhiều annotator và adjudication.
