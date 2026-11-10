# Subagent OMI: đọc file này, không đọc parallel.md

Dành cho subagent và chế độ hỏi đáp. Người điều phối (chia việc, mẫu giao việc, sổ chung): `parallel.md`.

<!-- gen:brief (sinh từ shared/skill-graph.json bằng tools/gen_skill_links.py, đừng sửa tay) -->
## 1. Chế độ subagent / hỏi đáp
- **Subagent** (được `omicall-assistant` hoặc agent khác giao việc): bỏ qua `self_update.py` (hoặc chạy với `--subagent`), câu phiên bản, hỏi domain, khảo sát tenant; dùng domain, phiên đăng nhập sẵn có, `tenant_context.json` (chỉ đọc) và manifest ghi trong lời giao việc; không chia tiếp. **Không đọc**: `conversation.md` mục 2–6, `system-model.md`, `solution-method.md`, `parallel.md` (file này thay thế).
- **Hỏi đáp** (user chỉ hỏi tính năng, mức đáp ứng (không đọc hay ghi tenant)): bỏ qua `self_update.py`, hỏi domain, đăng nhập, khảo sát tenant; dùng tài liệu của skill; thiếu nguồn thì ghi "Chưa có thông tin".

## 2. Giới hạn và quy tắc
- Tối đa **3 subagent giao diện** và **8 subagent chỉ API/MCP** cùng lúc; mỗi subagent giao diện một tab riêng (`tabs_create`, truyền `tabId` ở mọi lệnh), khung trình duyệt dùng chung với user.
- Chỉ làm đúng danh sách được giao. Gặp việc cần chia, thuộc skill khác, chạm cổng của user hoặc cần đăng nhập giao diện: dừng nhánh đó, trả "blocked" kèm đề xuất (không tự đoán).
- Một artefact = một subagent = một tiến trình ghi. Không truyền, không in token, cookie, mật khẩu (kể cả trong sổ chung, file tạm); dùng phiên sẵn có.

## 3. CẤM cho subagent (danh sách duy nhất; mọi chỗ khác trỏ về đây)
xuất bản, bật/tắt, xoá, gắn hotline/kênh/phím thật, gọi hoặc nhắn người thật, nhập mật khẩu, in hay chuyển token/cookie, đụng artefact không phải của mình, ghi `tenant_context.json` (ghi qua `manifest.py`), tự đánh dấu verified cho template (`extract_template --mark-verified`), chia tiếp cho subagent khác.

## 4. Mẫu trả về
Trả về tối đa 10 dòng: key | trạng thái done/partial/blocked | id/uuid đã GET | verify_report (PASS/FAIL) | Cần xác nhận | chưa làm được + lý do | cổng chờ user | số ảnh đã chụp. Không dán JSON hay log dài.
<!-- /gen:brief -->
