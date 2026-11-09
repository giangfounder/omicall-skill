---
name: omicall-crm-config
description: >-
  [v1.7.0] Cấu hình nền của CRM trong OMICall/OMICRM: thuộc tính động của Khách hàng và Phiếu ghi (6 kiểu trường, mã field_code), các trường thông tin mặc định, bộ trạng thái khách hàng (cờ WIN/LOST, trình tự chuyển, phân cấp), chủ đề và bộ trạng thái phiếu ghi (thời hạn xử lý, ca làm việc), cấu hình phân bổ. Là skill con của omicall-omiflow, có thể sử dụng độc lập.
---

# OMICall CRM Config — Thuộc tính, trạng thái, chủ đề phiếu (mọi tenant)

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác, 1 lần/phiên (đã chạy rồi, kể cả ở skill khác, thì bỏ qua). Câu đầu tiên: `Đang dùng omicall-crm-config v<phiên bản>` (dòng `SKILL_VERSION`; script lỗi thì dùng v1.7.0). Script báo **SKILL.md đã thay đổi** → đọc lại từ đĩa rồi làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.
**Chế độ subagent / hỏi đáp**: là subagent hoặc chỉ hỏi tính năng → bỏ qua bước này, hỏi domain, khảo sát (`parallel.md` mục 1).

## Bắt đầu và cách trao đổi (BẮT BUỘC)
Làm theo `references/conversation.md`, chung cho mọi skill OMI:
- Mục 1: hỏi domain → `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>` → `"need":"setup"` thì mở form cục bộ `omi_login.py setup --ui` trong agent (cách duy nhất; dự phòng: `references/omi-mcp.md` mục 2a). Không nhận mật khẩu qua chat, không gõ hay đọc form.
- Mục 2–6: khung 5 bước, cách hỏi lại, mẫu câu, lời thường, ít chụp ảnh.

## Đường nhanh
Chạy script bằng đường dẫn tuyệt đối `<thư mục skill>/scripts/...`. Mâu thuẫn thì quy tắc gốc bên dưới thắng.
1. **Token**: `python <thư mục skill>/scripts/omi_preflight.py --domain <domain>` → `api` / `login` / `ui` / `blocked` (xử lý như omiflow).
2. **Khảo sát bằng API trước, giao diện bằng chữ sau, ảnh chụp sau cùng** (`references/omi-mcp.md` mục 4a): `tenant_survey.py --out <scratch>/tenant_context.json` (thuộc tính Phiếu ghi có `is_list`, bộ trạng thái phiếu, phân bổ) + MCP `get_ticket_categories`. Thuộc tính Khách hàng và bộ trạng thái khách: đọc giao diện `/config/attribute/customer/{status|attribute}` (`references/crm-config.md` mục 1).
3. **Đối chiếu yêu cầu**: lập bảng *trường/trạng thái cần → đã có (mã) / phải tạo (kiểu đề xuất) / Cần xác nhận*. Chọn kiểu theo `references/crm-config.md` mục 3–4 (giá trị cố định → danh sách; giá trị từ hệ thống ngoài → Hộp ký tự).
4. **Duyệt**: gửi bảng cho user (kèm song song/tuần tự: `references/parallel.md`); chỉ tạo hoặc sửa sau khi user đồng ý từng mục.
5. **Tạo trên giao diện**: Cấu hình → Thuộc tính → Khách hàng / Phiếu ghi → mở bộ → Thêm thuộc tính. Chưa có API ghi đã kiểm chứng → không gọi API ghi.
6. **Kiểm**: chạy lại `tenant_survey.py` (Phiếu ghi) hoặc mở lại giao diện (Khách hàng), ghi `field_code` mới vào `tenant_context.json` mục `attributes`.
7. **Giao**: bảng mã trường, kiểu, `is_list`, bộ trạng thái và chủ đề đã dùng; các điểm "Cần xác nhận". Được omiflow gọi thì quay lại bước thiết kế flow.

Không bao giờ: xoá hay đổi tên thuộc tính, trạng thái đang dùng · đổi "Hình thức" của cấu hình phân bổ đang gắn flow khi user chưa duyệt · Xuất bản hay lưu thay đổi chưa được duyệt · đọc cookie, in token, nhập mật khẩu hộ.

## Tư duy chức năng (trước khi chọn module)
- Chỉ khi dựng mới hoặc việc chạm nhiều module (sửa nhỏ một bước/lời nhắc thì bỏ qua, đọc đúng mục playbook cần): đọc `references/system-model.md` (hệ thống có gì, làm được gì, đường nhanh nhất cho từng việc) và `references/solution-method.md` (phân rã bài toán thành chuỗi Sự kiện → Điều kiện → Hành động, ghép module có sẵn). Không khớp mẫu theo ca; mắt xích chưa xác minh thì báo user, khảo sát một lần bằng log mạng rồi ghi vào `system-model.md`.

<!-- skill-links:start (sinh từ shared/skill-graph.json bằng tools/gen_skill_links.py, đừng sửa tay) -->
## Gọi skill liên quan (tự động khi bài toán chạm tới)
Mắt xích thuộc skill khác (xem `references/system-model.md`) thì không tự làm theo trí nhớ: gọi skill đó rồi quay lại.
1. **Gọi**: công cụ Skill với đúng tên bên dưới; client không có thì đọc `<thư mục skill>/../<tên skill>/SKILL.md`. Chỉ làm đúng phần của mắt xích đó.
2. **Dùng chung**, không làm lại: domain, đăng nhập, `tenant_context.json` (chỉ đọc), `manifest.py`. Việc ghi vẫn chờ user duyệt như skill đích quy định.
3. **Trả lại**: ghi id/mã vừa tạo bằng `manifest.py set` (giá trị nền: `ctx-set`), rồi tiếp tục skill đang làm. Thứ tự khi cần nhiều phần: crm-config → ai-insight → pbx-config (nhóm, lời chào) → omiflow (webhook, nháp) → user xuất bản flow → bot/callbot (URL flow, nháp) → user xuất bản bot → pbx-config gắn số → gọi thử (hai cổng user duyệt).

| Khi gặp | Gọi skill |
|---|---|
| flow dùng thuộc tính, trạng thái hoặc chủ đề phiếu vừa cấu hình | `omicall-omiflow` |
| trường AI bóc từ cuộc gọi phải khớp tập giá trị của thuộc tính | `omicall-ai-insight` |
| bot thu thập dữ liệu vào thuộc tính vừa cấu hình | `omicall-chatbot-gen-ai` |
| callbot thu thập dữ liệu vào thuộc tính vừa cấu hình | `omicall-callbot-gen-ai` |
<!-- skill-links:end -->

## Rules (BẮT BUỘC)
1. **Cấu hình dùng chung cả tenant**: thuộc tính, bộ trạng thái, chủ đề phiếu, phân bổ ảnh hưởng mọi nhân viên, flow, bot. Đọc thoải mái; tạo hoặc sửa chỉ khi user đồng ý; không xoá.
2. **Không bịa**: tên trường, danh sách giá trị, trạng thái lấy từ tài liệu user hoặc tenant; thiếu thì ghi "Cần xác nhận".
3. **Kiểu trường quyết định cách flow gán dữ liệu**: Danh sách tùy chọn / Ô chọn không nhận biến (flow phải rẽ nhánh theo từng giá trị); báo rõ hệ quả này cho user trước khi chọn kiểu.
4. **Mã `field_type` của 3 kiểu chọn chưa kiểm chứng**: muốn biết thì tạo một trường thử (khi user đồng ý), đọc lại bằng API, rồi ghi bổ sung vào `references/crm-config.md`.
5. **Không hứa dropdown động từ API** (giao diện chỉ có nguồn "Tùy chỉnh").
6. **Tính năng nền trước flow**: hạn phiếu theo chủ đề + ca làm việc, "Thêm khách hàng tự động qua cuộc gọi", phân bổ cuộc gọi nhỡ, phân loại bắt buộc (`references/crm-config.md` mục 2, 5) — làm được thì không dựng flow.

## Quan hệ với skill khác
- `omicall-omiflow`: flow gán thuộc tính, rẽ nhánh theo trạng thái, tạo phiếu theo chủ đề → cần mã từ skill này. Trigger theo trạng thái chỉ bắt lúc chuyển vào trạng thái.
- `omicall-callbot-gen-ai`, `omicall-chatbot-gen-ai`: biến bot ghi vào thuộc tính khách hoặc phiếu dùng `field_code` ở đây.
- `omicall-ai-insight`: trường AI Assistant bóc ra phải khớp tên và tập giá trị của thuộc tính đích.

## Tài liệu tham khảo
- `references/crm-config.md` — bộ trạng thái khách hàng, bộ thuộc tính (form động), phiếu ghi (chủ đề, 3 loại trạng thái, hạn và đúng/chậm tiến độ, ca làm việc), 6 kiểu trường, API đọc thuộc tính, gợi ý thiết kế, Cấu hình doanh nghiệp → Khác và Phân loại, cấu hình phân bổ.
- `references/omi-mcp.md` — MCP OMI: đăng nhập, công cụ, tiết kiệm token (bản dùng chung).
- `scripts/tenant_survey.py`, `scripts/omi_preflight.py`, `scripts/omi_login.py`, `scripts/omi_session.py`, `scripts/omi_api.py` — script dùng chung.

## Bảo trì skill
Điều gì phải mở giao diện hoặc chụp ảnh mới biết thì ghi ngay vào reference (`references/omi-mcp.md` mục 4b) để lần sau không chụp lại. Học được kiểu trường, mã `field_type`, API ghi mới → cập nhật `references/crm-config.md`, chỉ ghi vào repo nguồn khi user cho phép. Không ghi URL tenant, token hay dữ liệu khách vào skill.
