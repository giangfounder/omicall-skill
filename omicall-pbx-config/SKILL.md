---
name: omicall-pbx-config
description: >-
  [v1.2.0] Cấu hình tổng đài OMICall/OMICRM: đầu số, máy lẻ, nhóm nội bộ (nhóm đổ chuông), lời chào (TTS hoặc file ghi âm), Tương tác phím (IVR, phím → nhóm, webhook sang OMIFlow), kịch bản tổng đài gọi vào và gắn vào hotline. Skill con của omicall-omiflow; gọi riêng được.
---

# OMICall PBX Config — Tổng đài, lời chào, tương tác phím (mọi tenant)

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác (`<thư mục skill>` = thư mục chứa SKILL.md này). Câu đầu tiên trả lời user: `Đang dùng omicall-pbx-config v<phiên bản>` (lấy từ dòng `SKILL_VERSION`; script lỗi thì dùng v1.2.0). Script báo **SKILL.md đã thay đổi** → đọc lại SKILL.md từ đĩa rồi mới làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.

## Bắt đầu: domain và đăng nhập
Được `omicall-omiflow` gọi trong cùng phiên thì dùng lại domain, đăng nhập và `tenant_context.json` đã có, bỏ qua mục này. Gọi riêng: làm đúng mục "Bắt đầu" của `omicall-omiflow/SKILL.md` — hỏi domain, `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>`, `"need":"setup"` thì mở trang đăng nhập OMI thật để user tự nhập mật khẩu. Agent không gõ mật khẩu, không đọc cookie hay token.

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
- `references/omi-mcp.md` — MCP OMI: đăng nhập, danh mục công cụ Tổng đài (Phụ lục B).
- `scripts/omi_preflight.py`, `scripts/omi_login.py`, `scripts/omi_session.py`, `scripts/omi_api.py`, `scripts/tenant_survey.py` — script dùng chung.

## Bảo trì skill
Điều gì phải mở giao diện hoặc chụp ảnh mới biết thì ghi ngay vào reference (`references/omi-mcp.md` mục 4b) để lần sau không chụp lại. Khảo sát được màn hình, schema hay gotcha mới → cập nhật `references/pbx-config.md` (gắn ✔ và tháng), chỉ ghi vào repo nguồn khi user cho phép. Không ghi đầu số, URL webhook thật, tenant id hay dữ liệu khách vào skill.
