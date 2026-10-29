---
name: omicall-crm-config
description: >-
  [v1.0.0] Cấu hình nền CRM của OMICall/OMICRM: thuộc tính động Khách hàng và Phiếu ghi (6 kiểu trường, mã field_code), các trường thông tin mặc định, bộ trạng thái khách hàng (WIN/LOST, trình tự), chủ đề và bộ trạng thái phiếu (hạn xử lý, ca làm việc), cấu hình phân bổ. Skill con của omicall-omiflow; gọi riêng được.
---

# OMICall CRM Config — Thuộc tính, trạng thái, chủ đề phiếu (mọi tenant)

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác (`<thư mục skill>` = thư mục chứa SKILL.md này). Câu đầu tiên trả lời user: `Đang dùng omicall-crm-config v<phiên bản>` (lấy từ dòng `SKILL_VERSION`; script lỗi thì dùng v1.0.0). Script báo **SKILL.md đã thay đổi** → đọc lại SKILL.md từ đĩa rồi mới làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.

## Bắt đầu: domain và đăng nhập
Được `omicall-omiflow` gọi trong cùng phiên thì dùng lại domain, đăng nhập và `tenant_context.json` đã có, bỏ qua mục này. Gọi riêng: làm đúng mục "Bắt đầu" của `omicall-omiflow/SKILL.md` — hỏi domain, `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>`, `"need":"setup"` thì mở trang đăng nhập OMI thật để user tự nhập mật khẩu. Agent không gõ mật khẩu, không đọc cookie hay token.

## Đường nhanh
Chạy script bằng đường dẫn tuyệt đối `<thư mục skill>/scripts/...`. Mâu thuẫn thì quy tắc gốc bên dưới thắng.
1. **Token**: `python <thư mục skill>/scripts/omi_preflight.py --domain <domain>` → `api` / `login` / `ui` / `blocked` (xử lý như omiflow).
2. **Khảo sát**: `tenant_survey.py --out <scratch>/tenant_context.json` (thuộc tính Phiếu ghi có `is_list`, bộ trạng thái phiếu, phân bổ) + MCP `get_ticket_categories`. Thuộc tính Khách hàng và bộ trạng thái khách: đọc giao diện `/config/attribute/customer/{status|attribute}` (`references/crm-config.md` mục 1).
3. **Đối chiếu yêu cầu**: lập bảng *trường/trạng thái cần → đã có (mã) / phải tạo (kiểu đề xuất) / Cần xác nhận*. Chọn kiểu theo `references/crm-config.md` mục 3–4 (giá trị cố định → danh sách; giá trị từ hệ thống ngoài → Hộp ký tự).
4. **Duyệt**: gửi bảng cho user; chỉ tạo hoặc sửa sau khi user đồng ý từng mục.
5. **Tạo trên giao diện**: Cấu hình → Thuộc tính → Khách hàng / Phiếu ghi → mở bộ → Thêm thuộc tính. Chưa có API ghi đã kiểm chứng → không gọi API ghi.
6. **Kiểm**: chạy lại `tenant_survey.py` (Phiếu ghi) hoặc mở lại giao diện (Khách hàng), ghi `field_code` mới vào `tenant_context.json` mục `attributes`.
7. **Giao**: bảng mã trường, kiểu, `is_list`, bộ trạng thái và chủ đề đã dùng; các điểm "Cần xác nhận". Được omiflow gọi thì quay lại bước thiết kế flow.

Không bao giờ: xoá hay đổi tên thuộc tính, trạng thái đang dùng · đổi "Hình thức" của cấu hình phân bổ đang gắn flow khi user chưa duyệt · Xuất bản hay lưu thay đổi chưa được duyệt · đọc cookie, in token, nhập mật khẩu hộ.

## Rules (BẮT BUỘC)
1. **Cấu hình dùng chung cả tenant**: thuộc tính, bộ trạng thái, chủ đề phiếu, phân bổ ảnh hưởng mọi nhân viên, flow, bot. Đọc thoải mái; tạo hoặc sửa chỉ khi user đồng ý; không xoá.
2. **Không bịa**: tên trường, danh sách giá trị, trạng thái lấy từ tài liệu user hoặc tenant; thiếu thì ghi "Cần xác nhận".
3. **Kiểu trường quyết định cách flow gán dữ liệu**: Danh sách tùy chọn / Ô chọn không nhận biến (flow phải rẽ nhánh theo từng giá trị); báo rõ hệ quả này cho user trước khi chọn kiểu.
4. **Mã `field_type` của 3 kiểu chọn chưa kiểm chứng**: muốn biết thì tạo một trường thử (khi user đồng ý), đọc lại bằng API, rồi ghi bổ sung vào `references/crm-config.md`.
5. **Không hứa dropdown động từ API** (giao diện chỉ có nguồn "Tùy chỉnh").

## Quan hệ với skill khác
- `omicall-omiflow`: flow gán thuộc tính, rẽ nhánh theo trạng thái, tạo phiếu theo chủ đề → cần mã từ skill này. Trigger theo trạng thái chỉ bắt lúc chuyển vào trạng thái.
- `omicall-callbot-gen-ai`, `omicall-chatbot-gen-ai`: biến bot ghi vào thuộc tính khách hoặc phiếu dùng `field_code` ở đây.
- `omicall-ai-insight`: trường AI Assistant bóc ra phải khớp tên và tập giá trị của thuộc tính đích.

## Tài liệu tham khảo
- `references/crm-config.md` — bộ trạng thái khách hàng, bộ thuộc tính (form động), phiếu ghi (chủ đề, trạng thái, hạn, ca làm việc), 6 kiểu trường, API đọc thuộc tính, gợi ý thiết kế, cấu hình phân bổ.
- `references/omi-mcp.md` — MCP OMI: đăng nhập, công cụ, tiết kiệm token (bản dùng chung).
- `scripts/tenant_survey.py`, `scripts/omi_preflight.py`, `scripts/omi_login.py`, `scripts/omi_session.py`, `scripts/omi_api.py` — script dùng chung.

## Bảo trì skill
Học được kiểu trường, mã `field_type`, API ghi mới → cập nhật `references/crm-config.md`, chỉ ghi vào repo nguồn khi user cho phép. Không ghi URL tenant, token hay dữ liệu khách vào skill.
