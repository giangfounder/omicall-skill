---
name: omicall-omiflow
description: Shared skill to design and build OMICall/OMICRM OMIFlow automations (workflow /flow/list) for ANY tenant and ANY business problem — triggers (API webhook, call events, IVR keys, tickets, schedule, Excel, partners), conditions, delays, AI classification, external API lookups, ticket/contact/call updates, agent popups, marketing (SMS/ZNS/Callbot), linking with Callbot/Chatbot. The agent reasons from the business problem to a flow using the module catalog; reads/saves flows via campaign-v1 API. Read references/node-catalog.md and references/design-patterns.md before designing.
---

# OMICall OMIFlow — Builder Playbook (mọi tenant, mọi bài toán)

## Overview
**OMIFlow** (menu OMIFlow, path `/flow/list`, editor `/flow/edit/{id}`) là bộ máy tự động hoá của OMICRM, cùng loại N8N, Zapier, Make, nhưng gắn sẵn với tổng đài, Callbot, Chatbot, đa kênh, phiếu ghi, khách hàng. Một flow = **điều kiện bắt đầu** → chuỗi **nút** (điều kiện, trì hoãn, hành động, cửa sổ tương tác, marketing, kênh chat) → kết quả nghiệp vụ.

Các flow mẫu ở tenant demo chỉ là **minh hoạ nhỏ**. Khi nhận bài toán, agent phải **tự suy luận** module nào ghép được thành lời giải từ danh mục đầy đủ (`references/node-catalog.md`), không chép nguyên flow mẫu.

## Rules (BẮT BUỘC)
1. **Suy luận từ bài toán**: chạy khung 8 câu hỏi ở `references/design-patterns.md` mục A, rồi chọn module. Mẫu đã chạy chỉ tham chiếu hình dạng.
2. **Không bịa schema**: module có nhãn [verify JSON] dùng JSON trong catalog; module [enum] phải dựng thử 1 lần trên UI → GET lại để lấy schema → ghi bổ sung vào catalog.
3. **An toàn dữ liệu khách**: chỉ đọc flow đang chạy. Sửa flow đang chạy → lưu nháp hoặc tạo flow mới để **tắt**, chỉ cập nhật hay bật khi user đồng ý. Không xoá, không tắt flow của khách nếu không được yêu cầu. Kiểm tra quota flow ("Thêm mới N/M") và quota nút trước khi tạo.
4. **Không bịa dữ liệu nghiệp vụ**: URL API ngoài, danh mục phiếu, nhân viên nhận, đầu số… lấy từ tài liệu user hoặc từ tenant (GET); thiếu thì ghi "Cần xác nhận".
5. **Verify mọi lần lưu**: GET lại và chạy checklist trong `references/api-reference.md`; test bằng cURL hoặc sự kiện thật, xem tab **Lịch sử**.
6. **Học xong phải ghi lại**: schema mới, module mới, gotcha mới → cập nhật catalog, patterns hoặc mục Gotchas. Không ghi URL, token, tenant id hay dữ liệu khách vào skill (repo dùng chung).

## Input contract (hỏi một lần rồi tự làm)
1. **Domain doanh nghiệp** (`<tên>.omicrm.io`).
2. **Tài khoản đăng nhập**.
3. **Bài toán nghiệp vụ**: file hoặc prompt mô tả (sự kiện gì, cần ra kết quả gì, ai nhận, hệ thống ngoài nào).

**Đăng nhập**: agent không tự gõ mật khẩu vào form hay gọi API đăng nhập bằng mật khẩu. Thứ tự: công cụ MCP đăng nhập (nếu có) → phiên có sẵn → mở trang đăng nhập trong browser pane để user bấm đăng nhập **một lần**. Sau đó agent tự lấy token từ cookie `{domain}_omicrm_io` (JSON, key `"2"`, có thể URL-encode) và làm toàn bộ phần còn lại qua API. Lưu token ở file tạm (scratchpad), không ghi vào skill. Không chuyển trang khi user đang đăng nhập.

## Workflow
### Bước 0 — Khảo sát tenant
- `POST /omi_v2/campaign/search?page=1&size=50` body `{}` → danh sách flow; `GET /omi_v2/campaign/get/{id}` từng flow → hiểu tenant đang tự động hoá gì, biến và danh mục phiếu đang dùng, webhook nào đã có.
- Dữ liệu cấu hình để tham chiếu id (gọi bằng cùng token): danh mục và trạng thái phiếu (`ticket-v2-stg.omicrm.com/ticket/category/get-all`, `/ticket/status-set/get-all`), nhân viên (`agent-v1-stg.omicrm.com/get_all_agent/no_role`), phân bổ (`tenant-v1-stg.omicrm.com/sale_allocation/search`), thuộc tính (`tenant-v1-stg.omicrm.com/attribute/get_all?has_attr=true`), kịch bản callbot (`chatbot-gateway-v1-stg.omicrm.com/callbot/script/list-by-tenant/{tenant_id}`).

### Bước 1 — Phân tích bài toán
Khung 8 câu (design-patterns mục A): sự kiện kích hoạt · đối tượng gốc · dữ liệu còn thiếu · rẽ nhánh · kết quả nghiệp vụ · người tham gia · thời gian chờ · caller cần gì và chống lặp. Ghi ra bảng: câu hỏi → module → cấu hình.

### Bước 2 — Thiết kế flow
- Vẽ luồng dạng text (như mẫu B1–B6): trigger → nút → nhánh, có nhánh lỗi và nhánh mặc định.
- Gom nhánh trùng về một nút chung; dài hoặc dùng lại → tách flow con phụ thuộc (`START_OTHER_CAMPAIGN`).
- Đặt tên: `<số> - [MỤC ĐÍCH]`; thêm nút Ghi chú chứa URL webhook và cURL mẫu.

### Bước 3 — Dựng JSON và lưu
- Lấy một flow cùng tenant làm khung (top-level fields), dựng `nodes` + `edges.connections` theo schema DUAL ở `references/api-reference.md` (nhánh lưu cả trong node lẫn edge).
- Lưu nháp `save_draft_v2` hoặc tạo `add_v2`; sửa `update_v2/{id}`; multipart field `file`, Python `requests` (không dùng curl).
- Nếu API lưu chưa verify cho tenant đó → dựng trên UI (mục *Thao tác UI*), rồi GET để đối chiếu.

### Bước 4 — Verify, test, giao
- Checklist trong api-reference; test webhook bằng cURL; xem tab Lịch sử từng nút.
- Giao: editor URL `https://{domain}.omicrm.io/flow/edit/{id}?lng=vi`, sơ đồ luồng, bảng biến, cURL test, các điểm "Cần xác nhận".

## Danh mục module (tóm tắt — chi tiết và JSON: `references/node-catalog.md`)
- **Trigger** (node CONDITION đầu tiên): API (`WEB_HOOK`), Điều kiện (`GENERAL`: sự kiện cuộc gọi, phím IVR, phiếu mới…), Biểu mẫu, Định kỳ, File Excel, Đối tác (Haravan, Sapo, KiotViet, Shopify, WooCommerce, Pancake, POS Bird, TPOS, Lark Base, Email SMTP), Cuộc gọi đang diễn ra, Khách hàng mới hoặc thoả thuộc tính, Phiếu ghi chuyển trạng thái.
- **Logic**: Điều kiện (nhiều trường hợp + nhánh mặc định; so sánh biến, cuộc gọi, khách, phiếu, khung giờ làm việc), Trì hoãn (sau khoảng, đến thời điểm, trong khung giờ, chờ đến khi thoả điều kiện), Random (A/B), Phân tích thông tin.
- **Hành động** (22): thêm hoặc cập nhật khách, tạo hoặc cập nhật phiếu, thông báo, nhắc nhở, trả kết quả qua Biểu mẫu hoặc API, biến liên kết tùy chỉnh (API, ChatGPT, tính toán, ngẫu nhiên, ảnh thư mời), gán đối tượng liên quan, Google Sheet, cập nhật hội thoại, cuộc gọi, nhân viên, cửa sổ, đánh giá AI Chatbot, gọi API ra ngoài, phân loại, chuyển tiếp cuộc gọi, gọi flow khác, cập nhật đối tác, giữ cuộc gọi.
- **Cửa sổ tương tác** (màn hình nhân viên): thông tin, biểu mẫu (có nhánh hoàn thành), nút bấm, biến, xem chi tiết, tính năng.
- **Marketing** (gửi hàng loạt): SMS, ZNS hoặc ZBS, xin quyền gọi ZCC, Email, AutoCall, AI Callbot, Viber Business.
- **Trò chuyện**: tin nhắn từng kênh (Facebook, Zalo OA, Zalo cá nhân, LiveTalk, Telegram, Viber, TikTok, WhatsApp, Email), gửi tin nhắn chung, giao cho bot AI (ChatGPT, ChatX, AI Chatbot, ProAI, Partner AI).
- **Khác**: Thu thập thông tin (gán biến mặc định), Ghi chú.

## Kết nối với Callbot và Chatbot
- **Callbot → OMIFlow**: callbot gọi URL webhook (khi thu đủ biến, khi bot không xử lý được, khi khách bấm phím chuyển máy) để tạo phiếu, đồng bộ hệ thống ngoài, bật popup cho nhân viên.
- **OMIFlow → Callbot**: nút Marketing `CALLBOT` hoặc `AUTOCALL` tạo phiên gọi cho các khách đi qua flow; kiểm tra trạng thái phiên bằng điều kiện "Kiểm tra trạng thái AI Callbot".
- **Chatbot cần dữ liệu CRM**: chatbot không tự tra khách theo thuộc tính → gọi flow `WEB_HOOK` → `GET_RELATED`/`API_V2` → `SEND_RESPONSE_WEBHOOK_API` trả dữ liệu (thay cho `response_config` cố định).
- Sau cuộc gọi AI: `{{ca_summarize}}` (tóm tắt) và `{{ca_ai_assistant}}` (kết quả phân tích) dùng làm đầu vào cho ChatGPT phân loại hoặc chèn vào mô tả phiếu.

## Thao tác UI (khi phải dựng bằng tay)
- Tab "Thông tin Flow": tên, hoạt động hoặc ngưng, thời gian hiệu lực, mô tả, tag, giới hạn số lần đối tượng đi qua (`iteration_config`), cách bắt đầu: độc lập hoặc phụ thuộc flow khác (`dependent_config`).
- Tab "Kịch bản": chuột phải canvas → bảng chọn nút (Logic, Tương tác, Trò chuyện, Khác). Chọn node (một lần bấm) → thanh công cụ: thêm nút liền kề, sao chép, lưu vào kho nút, xoá (`button[aria-label="Xóa node"]`).
- Nối cạnh bằng chuột hay thất bại vì handle đích không hiện; dùng PointerEvent qua JS (`references/react-flow-selectors.md`).
- Nút **Xuất bản** tạo phiên bản mới và áp dụng ngay; chỉ bấm khi user đồng ý.

## Gotchas
- **Trigger là node CONDITION đầu tiên** (`is_first_node:true`), không phải node riêng; `kick_off.event` phải khớp.
- **Nhánh lưu hai nơi** (node + `edges.connections`); `success_next_nodes`/`fail_next_nodes` là **chuỗi**, `next_nodes` là **mảng**; `sourceHandle`: case id, `"2"` (Bước tiếp theo), `success_action_step`, `fail_action_step`; `targetHandle:"1"`.
- **Mã biến ngẫu nhiên** (`{{MpQxWEiLis}}`): tên hiển thị nằm ở `multi_variables[].field_name` hoặc `custom_variables`. Đổi tên biến không đổi mã; xoá biến làm các tham chiếu hỏng ("N biến liên kết có vấn đề").
- **Bản ghi cuộc gọi sinh trễ**: trước `GET_RELATED CLOSEST_CALL` hoặc gắn cuộc gọi vào phiếu phải `DELAY` 5–10 giây; chờ cuộc gọi kết thúc thì dùng DELAY có điều kiện (tối đa N phút).
- **Trigger API không có đối tượng gốc**: phải `GET_RELATED` hoặc điều kiện xác định khách theo trường **Số điện thoại chuẩn** (không phải thuộc tính tuỳ chỉnh) trước khi cập nhật khách hoặc phiếu.
- **Tra API ngoài có thể rỗng**: luôn có nhánh `CONDITION != ""` và giá trị mặc định (`COLLECT_INFO` "Khách hàng mới") để tên phiếu, popup không bị trống.
- **AI phân loại**: prompt bắt trả DUY NHẤT một mã; điều kiện so đúng mã, không khoảng trắng thừa; luôn có nhánh mặc định cho mã lạ.
- **Phím IVR** có thể ghi `"2"` hoặc `"02"`: so `IN` hoặc `CONTAIN`, hoặc tạo cả hai trường hợp.
- **`response_config` của webhook là cố định**; trả dữ liệu động dùng hành động "Trả kết quả qua API". `status_code` 9999 trong body không phải HTTP status.
- **Gọi flow khác**: flow đích phải là loại phụ thuộc; kết quả của flow đích không quay về webhook của flow gọi.
- **Quota**: số flow theo gói, số nút mỗi flow (ví dụ 16/20) — gom nhánh trùng để tiết kiệm.
- **Ô nhập trong drawer nối thêm thay vì thay thế**: Ctrl+A trước khi gõ; body JSON editor tự bọc `{}`. Không dùng Escape trong drawer.
- **Browser pane không bắt XHR khác domain** trong `read_network_requests`; dùng `performance.getEntriesByType('resource')` để tìm endpoint. Pane hẹp làm canvas tràn ngang → ưu tiên API thay vì bấm UI.

## Tài liệu tham khảo
- `references/node-catalog.md` — mọi trigger, nút, hành động, điều kiện, biến; JSON đã kiểm chứng.
- `references/design-patterns.md` — khung suy luận 8 câu, 6 mẫu đã chạy, mẫu mở rộng theo lĩnh vực, lỗi thiết kế cần tránh.
- `references/api-reference.md` — endpoint, schema flow, DUAL node và edge, khung lưu, checklist.
- `references/webhook-examples.md` — mẫu cURL và response.
- `references/react-flow-selectors.md` — selector DOM để thao tác canvas bằng JS.
