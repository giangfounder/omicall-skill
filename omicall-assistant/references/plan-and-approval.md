# Hiện từng bước và duyệt (cả chế độ Hỏi đáp và dựng)

Ngay sau khi hiểu việc, hiện bảng kế hoạch rồi mới làm:

| Đợt | Phần việc / câu hỏi | Skill gọi | Chạy | Cần anh/chị duyệt |
|---|---|---|---|---|
| 1 | <phần> | `omicall-<skill>` | song song / tuần tự | Không (chỉ đọc) / Có: <ghi gì, ở đâu> / Cổng: <tên cổng> |

<!-- gen:gates (sinh từ shared/skill-graph.json bằng tools/gen_skill_links.py, đừng sửa tay) -->
**Quy tắc duyệt** (một nguồn: `shared/skill-graph.json`):
- **Đọc** (tài liệu skill; API/MCP chỉ đọc trên domain user đã cho, kể cả lần đầu trong phiên): không cần duyệt.
- **Bản nháp mới** (không ghi đè bản đang chạy): nằm trong lượt duyệt kế hoạch, không xin thêm từng file trung gian.
- **Ghi cấu hình sống** (không có bản nháp): duyệt từng mục, nói rõ ghi gì, ở đâu.
- **Cổng** (bảng dưới): dừng nhánh đó, nói rõ sẽ làm gì, chờ user; mỗi cổng duyệt riêng, không gộp vào lượt duyệt kế hoạch.
- **Subagent** không qua cổng nào; gặp cổng thì trả "blocked".

| Cổng | Tên | Phạm vi |
|---|---|---|
| `duyet_ke_hoach` | Duyệt kế hoạch | một lượt cho bảng đợt (đợt 0); cho phép tạo bản nháp mới, không ghi đè bản đang chạy |
| `ghi_cau_hinh_song` | Ghi cấu hình sống | thuộc tính, trạng thái, chủ đề phiếu, phân bổ, AI Assistant, nhóm, lời chào, Tương tác phím, kịch bản tổng đài: không có bản nháp → duyệt từng mục (ghi gì, ở đâu) |
| `callbot_flow_y_dinh` | callbot-flow: bảng ý định/thực thể | duyệt riêng, không gộp với cổng khác |
| `callbot_flow_huan_luyen` | callbot-flow: file huấn luyện | duyệt file trước khi đẩy Kho tri thức (dùng chung cả tài khoản) |
| `training_reset` | callbot-flow: `training/reset` | nạp dữ liệu mẫu hệ thống vào Kho tri thức trống; hỏi riêng trước khi chạy |
| `xuat_ban_flow` | User xuất bản flow | xuất bản đổi id flow → `manifest.py stale <flow>`, GET lại id/URL mới |
| `xuat_ban_bot` | User xuất bản bot/callbot | xuất bản đổi id bot (uuid giữ nguyên) → `manifest.py stale <bot>`, GET lại id mới |
| `gan_so` | Gắn số | gắn kịch bản gọi vào cho hotline, phím/webhook Tương tác phím, chọn lại Callbot trong kịch bản cuộc gọi, map lại khi `check_callin.py` báo STALE/MISSING: đổi đường đi cuộc gọi thật |
| `goi_thu` | Gọi thử, nhắn thật | gọi hoặc nhắn cho người thật, kể cả số của user |
| `xoa_bat_tat` | Xoá, bật/tắt, ghi đè bản đang chạy | từng việc một |
<!-- /gen:gates -->

- Cách chia đợt, vị trí từng cổng và giới hạn song song: `orchestration.md` mục 2–3.
- Trong lúc làm: mỗi đợt một dòng đầu ("Đợt 2/4: chạy song song callbot và chatbot") và một dòng sau khi xong; đến cổng thì dừng, nói rõ sẽ làm gì rồi chờ.
- Kết thúc: liệt kê skill đã gọi, việc chờ user và các ý chưa có thông tin.
