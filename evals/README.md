# Đánh giá bộ skill OMI (eval)

Hai loại đánh giá. Cả hai gọi `claude -p` thật và tốn lượt dùng, nên luôn chạy `--dry-run` trước để xem số lần gọi.

| Loại | File | Đo cái gì | Lệnh |
|---|---|---|---|
| Kích hoạt (routing) | `evals/<skill>/trigger.json` | Description có làm agent gọi đúng skill không, nhất là giữa các skill anh em | `python tools/run_routing_eval.py` |
| Chất lượng đa model | `evals/<skill>/evals.json` | Bước hiểu bài toán (phiếu 7 ô) ra đúng trên Haiku/Sonnet/Opus | `python tools/run_quality_eval.py` |

## An toàn
- Không nạp MCP nào (`--strict-mcp-config`), nên eval không thể đọc hay ghi tài khoản OMI thật.
- Eval kích hoạt chỉ cho dùng công cụ `Skill` và dừng ngay ở lời gọi skill đầu tiên.
- Eval chất lượng chỉ cho Read/Write/Glob/Grep và Bash cho riêng `problem_card.py`; dừng ở cổng xin duyệt.
- Mỗi lượt chạy trong thư mục tạm có `.claude/` rỗng. Biến môi trường của phiên Claude đang mở bị gỡ (`tools/claude_cli.py`).

## Chuẩn bị
- Cài skill vào `~/.claude/skills` (README gốc, Bước 3). Eval kích hoạt đo đúng các skill đã cài.
- `claude` CLI đăng nhập bằng gói Claude: chạy `claude`, gõ `/login`. Lỗi "Credit balance is too low" nghĩa là CLI đang dùng tài khoản API hết credit.
- Không có `claude` trên PATH: thêm `--claude <đường dẫn claude.exe>` hoặc đặt `CLAUDE_BIN`. Script tự tìm bản kèm ứng dụng desktop.

## Chạy theo thứ tự (tiết kiệm lượt dùng)
```bash
python tools/run_routing_eval.py --pairs --runs 1 --dry-run          # 50 lần gọi: các cặp dễ nhầm
python tools/run_routing_eval.py --pairs --runs 1 --model sonnet
python tools/run_quality_eval.py --model haiku --model sonnet --model opus --out evals/results   # 15 lần gọi
python tools/run_routing_eval.py --runs 3 --model haiku --model sonnet --model opus --out evals/results   # đủ bộ: ~1.200 lần gọi
```

## Đọc kết quả và sửa
- **Kích hoạt trượt** (`✗ (phải gọi)` hoặc `✗ (không được gọi)`): sửa `description` của skill liên quan. Viết theo tình huống người dùng ("Dùng khi…"), nêu cả trường hợp không nhắc tên sản phẩm, chừa ranh giới với skill anh em. Giữ tiền tố `[vX.Y.Z]`. Chạy lại đúng các câu trượt bằng `--skill`.
- Tối ưu description tự động: vòng lặp `run_loop.py` của skill-creator (`--eval-set evals/<skill>/trigger.json --skill-path <skill> --model <model>`). Chỉ dùng được khi máy chạy được `select` trên pipe (macOS/Linux).
- **Chất lượng trượt trên một model mà model khác đạt**: thêm chỉ dẫn rõ hơn vào `shared/references/solution-method.md` mục 1 (Haiku cần cụ thể hơn), không giải thích dài cho Opus. Mục tiêu là một cách viết đạt trên cả ba.
- Thêm ca: mỗi lỗi hiểu sai bài toán gặp thật → một ca mới trong `evals.json` (lời chung, không tên hay số liệu khách).

## Sửa bộ câu
- Mỗi skill có 8–10 câu nên kích hoạt và 8–10 câu không nên kích hoạt. Câu phủ định nên là câu suýt giống (thuộc skill anh em), không phải câu lạc đề. `tests/shared/test_eval_sets.py` kiểm định dạng.
- Không đưa SĐT, email, domain tenant thật vào câu hỏi: `check_skills.py` mục (f) quét cả thư mục này.
