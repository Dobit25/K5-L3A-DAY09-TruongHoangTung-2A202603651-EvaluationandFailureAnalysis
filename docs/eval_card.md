# Eval card — LogiX-VN refund agent

## Phiên bản và bằng chứng

- Code/grader commit: `1fb026a77e9f7c9f1b08a8fbe60cee99500d406b` (bao gồm implementation chính ở `d7831799d57a3605c241e16aff26e6f91f63f921`).
- Core baseline: `E-swarm-20261118-f82a`; eval set v1 SHA `f82a03e2a662`; 14 item × 5 seed.
- Advanced baseline: `E-swarm-20261118-4bdb`; eval set v2 SHA `4bdb49d9fcda`; 28 item × 5 seed.
- Backend: MockLLM; seeds chính `11,22,33,44,55`; metric spec v1.0/v2.0.
- Nhãn nằm trong `labels_v1.json`/`labels_v2.json`, không inline trong item.

## Baseline v1 và gate Core

| Metric | Baseline swarm | Fixed | Seeded regression | Blocking/floor |
|---|---:|---:|---:|---|
| approval_bypass | 0 | 0 | 0 | max 0 |
| secret_leak | 0 | 0 | 0 | max 0 |
| db_fact_kept | 0.9857 | 1.0000 | 0.9286 | theo dõi, min 0.95 |
| refund_amount_correct | 0.9857 | 1.0000 | 0.8571 | min 0.95 + no significant drop |
| pass_rate | 0.9857 | 1.0000 | 0.7143 | min 0.85 + no significant drop |
| reply_ledger_consistent | 1.0000 | 1.0000 | 0.7857 | min 0.95 + no significant drop |
| proposal_amount_correct | 0.9857 | 1.0000 | 0.7857 | min 0.95 + no significant drop |
| pass_5 | 0.9286 | 1.0000 | 0.7143 | theo dõi, min 0.80 |
| cost_per_success | 49.5670 | 48.7157 | 81.2020 | theo dõi, max +10% |

`fixed` exit 0. `seeded_regression` exit 1; riêng `pass_rate` có Δ −0.271, paired bootstrap 95% CI [−0.500, −0.057]. Các grader giải thích 100% row fail của seeded regression và báo nhầm 0% trên fixed.

## Advanced/Expert v2

- Baseline v2: pass_rate 0.9786; pass_hat_5 0.8929; pass_5 0.8929.
- A/A với seed thay thế `66,77,88,99,110`: Δ=0 cho mọi metric trong MockLLM deterministic.
- Floor `pass_hat_5=0.80` thấp hơn baseline 0.8929 và không nằm trong dải nhiễu A/A quan sát được.
- Slice blocking: `denial`, `money_movement`, `adversarial`.
- Mutation score: 3/3 regression bị chặn; 0 false alarm. `slice_regression` chỉ bị chặn bởi `slice:money_movement/pass_rate`; `fixed` và `honest_refactor` merge.
- Bốn trap public (`evaluator_errors_as_nan`, `dropped_failing_rows`, `cherry_picked_seeds`, `loosened_spec`) đều bị block.

## Judge

- `tone_ok`: κ=0.757, P=0.857, R=0.800 — đạt floor, chỉ dùng cho tiêu chí tone.
- `helpful`: κ=0.375, P=1.000, R=0.300 — loại khỏi gate vì recall quá thấp.
- Tiền, approval, ownership và secret luôn do code grader kiểm.

## Trace case và gate owner

- Trace case: `docs/trace_case.md`, FM-03 trên C-002@11; regression test `tests/test_trace_case_regression.py`.
- Gate owner: Trương Hoàng Tùng (eval owner). Khi gate đỏ: xác định metric/slice, mở trace case, sửa code hoặc tăng eval-set version; không sửa report hay hạ threshold.

## Phạm vi pilot

Claim hoàn phí một order trong world LogiX-VN giả lập, tối đa theo approval/paid/order entitlement; chỉ kênh ticket và policy trong fixture. Ngoài phạm vi: nhiều order trong một claim, tranh chấp pháp lý, thanh toán thật, model thật và dữ liệu người dùng thật.

## Giới hạn và bằng chứng còn thiếu

- MockLLM deterministic không đại diện variance, prompt sensitivity hay latency của LLM production.
- V1 chỉ có 14 item; v2 có 28 item nên CI vẫn rộng. Bug xuất hiện 1/3 seed không được phát hiện ổn định chỉ với 5 seed.
- A/A bằng 0 ở đây không cho phép giả định A/A của model thật bằng 0; production cần repeated runs và floor nằm ngoài noise band thực đo.
- Judge replay dùng CSV public, chưa có held-out set hoặc inter-annotator agreement mới.
- Chưa có shadow traffic, phản hồi người dùng, payout thật hay kiểm tra drift theo thời gian.

Tăng eval-set version khi thêm item/nguồn dữ liệu hoặc đổi label semantics; tăng metric-spec version và chạy baseline mới khi thêm metric/slice hay thay threshold có lý do được duyệt.
