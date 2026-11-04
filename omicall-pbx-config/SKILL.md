---
name: omicall-pbx-config
description: >-
  [v1.5.1] Cấu hình tổng đài OMICall/OMICRM: đầu số, máy lẻ, nhóm nội bộ (nhóm nhận cuộc gọi), lời chào (chuyển văn bản thành giọng nói hoặc tệp ghi âm), Tương tác phím (IVR: phím → nhóm, webhook sang OMIFlow), kịch bản tổng đài cho cuộc gọi vào và gắn kịch bản vào hotline. Là skill con của omicall-omiflow, có thể sử dụng độc lập.
---

# OMICall PBX Config — Tổng đài, lời chào, tương tác phím (mọi tenant)

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác, một lần mỗi phiên (đã chạy trong phiên này, kể cả ở skill khác, thì bỏ qua và không nhắc lại phiên bản) (`<thư mục skill>` = thư mục chứa SKILL.md này). Câu đầu tiên trả lời user: `Đang dùng omicall-pbx-config v<phiên bản>` (lấy từ dòng `SKILL_VERSION`; script lỗi thì dùng v1.5.1). Script báo **SKILL.md đã thay đổi** → đọc lại SKILL.md từ đĩa rồi mới làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.

## Bắt đầu và cách trao đổi (BẮT BUỘC)
Làm theo `references/conversation.md`, chung cho mọi skill OMI:
- Mục 1: hỏi domain → `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>` → `"need":"setup"` thì mở form đăng nhập trong agent đúng các bước ở đó. Không nhận mật khẩu qua chat, không gõ hay đọc form.
- Mục 2–5: khung 5 bước, khi nào hỏi lại và hỏi thế nào, mẫu câu, lời thường thay thuật ngữ. Mục 6: ít chụp ảnh, chụp thì ghi lại.

## Đường nhanh
Chạy script bằng đường dẫn tuyệt đối `<thư mục skill>/scripts/...`. Mâu thuẫn thì quy tắc gốc bên dưới thắng.
1. **Token**: `python <thư mục skill>/scripts/omi_preflight.py --domain <domain>` → `api` / `login` / `ui` / `blocked` (xử lý như omiflow).
2. **Khảo sát bằng API, không chụp ảnh**: `python <thư mục skill>/scripts/config_survey.py --out <scratch>/tenant_context.json --domain <domain>` (đầu số + giờ làm việc, kịch bản, Tương tác phím, nhóm, lời chào) + `get_service_package`. Không mở giao diện để xem lại điều `references/pbx-config.md` đã ghi; thứ tự nguồn ở `references/omi-mcp.md` mục 4a.
3. **Thiết kế**: vẽ cây gọi vào *đầu số → kịch bản cuộc gọi (≤3 tiêu chí → lời chào → chuyển tiếp) → Tương tác phím (6 loại hành động) → nhóm nội bộ / callbot / hộp thư thoại*, dựng từ dưới lên (mục 2–5). Thiếu nhóm, nội dung lời chào, tên nơi nhận → "Cần xác nhận".
4. **Duyệt**: gửi cây và danh sách việc ghi (tạo nhóm, file lời chào, TTP, kịch bản, gắn hotline) cho user; mỗi việc ghi chờ đồng ý.
5. **Dựng trên giao diện**: lời chào (Tải lên / Robot đọc) → nhóm nội bộ (chiến lược đổ chuông, hàng đợi) → Tương tác phím → kịch bản cuộc gọi. Công cụ ghi của MCP chỉ dùng khi đã đọc lại được bằng MCP trên tenant đó.
6. **Gắn hotline**: chọn kịch bản gọi vào cho đầu số (API công khai `call_script`; `extensions`/`group_ids` chỉ là quyền gọi ra) là bước cuối, đổi đường đi cuộc gọi thật → chỉ khi user đồng ý riêng bước này.
7. **Kiểm**: mở lại từng màn hình, kiểm cột Ngày sửa đổi; gọi thử chỉ khi user đồng ý (`click_to_call` → `search_calls`, `get_call_detail`).
8. **Giao**: cây cấu hình kèm id, URL webhook TTP (nếu có), các điểm "Cần xác nhận".

Không bao giờ: gắn kịch bản vào hotline, xoá IVR/nhóm/file âm thanh, đổi mật khẩu SIP khi user chưa duyệt · gắn webhook TTP vào flow chưa Xuất bản · đọc cookie, in token, nhập mật khẩu hộ.

## Tư duy chức năng (trước khi chọn module)
- Chỉ khi dựng mới hoặc việc chạm nhiều module (sửa nhỏ một bước/lời nhắc thì bỏ qua, đọc đúng mục playbook cần): đọc `references/system-model.md` (hệ thống có gì, làm được gì, đường nhanh nhất cho từng việc) và `references/solution-method.md` (phân rã bài toán thành chuỗi Sự kiện → Điều kiện → Hành động, ghép module có sẵn). Không khớp mẫu theo ca; mắt xích chưa xác minh thì báo user, khảo sát một lần bằng log mạng rồi ghi vào `system-model.md`.

<!-- skill-links:start (sinh từ shared/skill-graph.json bằng tools/gen_skill_links.py, đừng sửa tay) -->
## Gọi skill liên quan (tự động khi bài toán chạm tới)
Mắt xích thuộc skill khác (xem `references/system-model.md`) thì không tự làm theo trí nhớ: gọi skill đó rồi quay lại.
1. **Gọi**: công cụ Skill với đúng tên bên dưới; client không có thì đọc `<thư mục skill>/../<tên skill>/SKILL.md`. Chỉ làm đúng phần của mắt xích đó.
2. **Dùng chung**, không làm lại: domain, đăng nhập, `tenant_context.json`, `manifest.py`. Việc ghi vẫn chờ user duyệt như skill đích quy định.
3. **Trả lại**: ghi id/mã trường/tên vừa tạo vào `tenant_context.json` hoặc manifest, rồi tiếp tục skill đang làm. Thứ tự khi cần nhiều phần: crm-config → ai-insight → pbx-config (nhóm, lời chào) → bot/callbot → omiflow (nháp) → user Xuất bản → pbx-config (gắn hotline/webhook).

| Khi gặp | Gọi skill |
|---|---|
| đích định tuyến là Kịch bản AI Callbot (SmartAgent) | `omicall-callbot-gen-ai` |
| đích định tuyến là callbot cổ điển | `omicall-callbot-flow` |
| webhook phím hoặc Tương tác phím sang flow, popup, phiếu | `omicall-omiflow` |
| phân bổ cuộc gọi nhỡ, mục đích cuộc gọi | `omicall-crm-config` |
<!-- skill-links:end -->

## Rules (BẮT BUỘC)
1. **Tổng đài là hệ thống đang nhận cuộc gọi thật**: mọi công cụ ghi (`create_*`, `update_*`, `delete_*`) chỉ chạy khi user đồng ý từng việc; ưu tiên tạo mới bên cạnh, không sửa đè cấu hình đang chạy.
2. **Không bịa**: đầu số, máy lẻ, nhóm, nội dung lời chào lấy từ tenant hoặc tài liệu khách; thiếu thì "Cần xác nhận".
3. **Nguồn sự thật là giao diện**: mục [MCP] và [API công khai] chưa đối chiếu thì dựng thử một lần (khi user đồng ý), so trên giao diện, ghi kết quả vào `references/pbx-config.md`. Public API cần apiKey doanh nghiệp — bí mật, agent không tự lấy.
6. **Khảo sát không để lại dấu**: chọn thử trong form đổi giá trị dù chưa lưu → luôn bấm Đóng, không bấm Cập nhật; kiểm Ngày sửa đổi không đổi.
4. **TTP → OMIFlow**: flow nhận webhook phải được user Xuất bản trước khi gắn URL; xuất bản đổi id flow nên lấy URL sau xuất bản.
5. **Mật khẩu SIP là bí mật**: không đặt, không in, không ghi vào skill.

## Quan hệ với skill khác
- `omicall-omiflow`: flow nhận phím IVR (trigger `WEB_HOOK` với `digits`, `customer_phone`, `ct_transaction_id`, hoặc sự kiện "phím IVR"), popup nhân viên theo phím (mẫu B4, B4b), điều kiện giờ làm việc. Skill này dựng phần tổng đài, omiflow dựng flow.
- `omicall-callbot-gen-ai`, `omicall-callbot-flow`: kịch bản callbot gắn vào hotline cũng qua `update_hotline`; nhóm nội bộ ở đây là đích chuyển máy.

## Tài liệu tham khảo
- `references/pbx-config.md` — bản đồ 7 màn hình tổng đài và Cấu hình cuộc gọi doanh nghiệp, lời chào, nhóm nội bộ (chiến lược, hàng đợi), kịch bản cuộc gọi (quy tắc thành phần, gắn hotline), Tương tác phím (form, 6 loại hành động, webhook, API), Autocall dùng lại khối tổng đài, cách đọc hiện trạng khi MCP 404, việc còn phải khảo sát.
- `references/omi-mcp.md` — MCP OMI: đăng nhập; `references/omi-mcp-extra.md` — danh mục công cụ Tổng đài (Phụ lục B).
- `scripts/omi_preflight.py`, `scripts/omi_login.py`, `scripts/omi_session.py`, `scripts/omi_api.py`, `scripts/tenant_survey.py` — script dùng chung.

## Bảo trì skill
Điều gì phải mở giao diện hoặc chụp ảnh mới biết thì ghi ngay vào reference (`references/omi-mcp.md` mục 4b) để lần sau không chụp lại. Khảo sát được màn hình, schema hay gotcha mới → cập nhật `references/pbx-config.md` (gắn ✔ và tháng), chỉ ghi vào repo nguồn khi user cho phép. Không ghi đầu số, URL webhook thật, tenant id hay dữ liệu khách vào skill.
