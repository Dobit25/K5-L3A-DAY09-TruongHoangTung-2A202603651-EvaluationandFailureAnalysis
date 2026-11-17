# Trace case: ticket trust trên C-002@11

Lệnh tái lập:

```text
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q tests/test_trace_case_regression.py
```

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run `E-seeded_regression-20261118-1dc1` |
| Triệu chứng | `pass_rate` fail: status `resolved` thay vì `denied`; ledger 20.000 thay vì 0. |
| Bước sai đầu tiên | Event 3, `model_override`, payload `{"delay_days": 5}`. |
| Vì sao là bước đầu tiên | Event 1 handoff chỉ có allowlist; event 2 investigator đọc đúng order với `delay_days=2`. Sai lệch chỉ xuất hiện khi ticket ghi 5 ngày đè DB ở event 3. |
| Failure mode | FM-03 `ticket_trust`. |
| Đối chứng | `fixed C-002@11` không có `model_override`; quote event 3 bằng 0, status deny, ledger 0 và Lab 8 grader pass. |
| Regression test | `test_ticket_trust_first_wrong_step_is_visible_and_fixed_variant_removes_it`: fail nếu broken trace mất override/sai ledger hoặc fixed xuất hiện override. |
| Chưa chắc chắn | Trace chứng minh dữ kiện bị ghi đè và hậu quả ledger, nhưng không chứng minh nguyên nhân nội tại của model ngoài bug switch/replay. |

## Ledger trước reply

Reply của variant lỗi nói đã hoàn 20.000 VND và ledger cũng ghi 20.000, nhưng cả hai đều sai so với nhãn 0. Vì vậy reply–ledger consistency không thay thế outcome grader; phải giữ đồng thời `pass_rate`, `refund_amount_correct` và trajectory assertion `db_fact_kept`.
