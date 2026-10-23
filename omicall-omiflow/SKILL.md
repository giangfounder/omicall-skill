---
name: omicall-omiflow
description: >-
  [v1.7.2] Thiết kế, xây dựng và chỉnh sửa quy trình tự động OMIFlow của OMICall/OMICRM cho mọi đơn vị và bài toán nghiệp vụ. Dùng khi quy trình có điểm kích hoạt từ API webhook, cuộc gọi, phím IVR, phiếu ghi, lịch, Excel hoặc đối tác; có điều kiện, trì hoãn, phân loại bằng AI, tra cứu API bên ngoài, cập nhật khách hàng, phiếu ghi hoặc cuộc gọi, bật cửa sổ cho nhân viên, gửi SMS/ZNS, chạy Callbot hoặc liên kết Callbot/Chatbot. Skill phân tích yêu cầu thành luồng theo danh mục mô-đun và đọc hoặc lưu qua API campaign-v1. Đọc references/node-catalog.md, references/design-patterns.md và references/omi-mcp.md khi phù hợp.
---

# OMICall OMIFlow — Builder Playbook (mọi tenant, mọi bài toán)

## Bước bắt buộc khi gọi skill: cập nhật bản mới nhất
Phiên bản skill: **v1.7.2**. Câu đầu tiên trả lời user khi skill được gọi phải là: `Đang dùng omicall-omiflow v<phiên bản>` (lấy từ dòng `SKILL_VERSION` của script dưới; không chạy được script thì dùng v1.7.2).
Trước mọi bước khác, chạy: `python "<thư mục skill>/scripts/self_update.py"` (`<thư mục skill>` = thư mục chứa file SKILL.md này).
- Báo user dòng cuối `SKILL_VERSION=...` (phiên bản đang dùng).
- Script báo **SKILL.md đã thay đổi** → đọc lại SKILL.md (và file tham chiếu được nêu) từ đĩa rồi mới làm tiếp; nội dung đã nạp là bản cũ.
- Không cập nhật được hoặc có bản mới nhưng cài không phải git clone → báo user lý do, làm tiếp với bản hiện có; không tự sửa, xoá hay commit trong thư mục skill.
- Phiên bản ghi ở file `VERSION`, lịch sử thay đổi ở `CHANGELOG.md` gốc repo (https://github.com/giangfounder/omicall-skill).

## Overview
**OMIFlow** (menu OMIFlow, path `/flow/list`, editor `/flow/edit/{id}`) là bộ máy tự động hoá của OMICRM, cùng loại N8N, Zapier, Make, nhưng gắn sẵn với tổng đài, Callbot, Chatbot, đa kênh, phiếu ghi, khách hàng. Một flow = **điều kiện bắt đầu** → chuỗi **nút** (điều kiện, trì hoãn, hành động, cửa sổ tương tác, marketing, kênh chat) → kết quả nghiệp vụ.

**Module là của nền tảng, dùng chung mọi tenant.** Tenant chỉ khác ở dữ liệu cấu hình (danh mục phiếu, thuộc tính, nhân viên, tag), tích hợp đã bật (OA, SMS, Email, ZNS, đối tác, callbot) và gói (quota flow, nút). Flow có sẵn ở một tenant chỉ là **minh hoạ nhỏ**. Khi nhận bài toán, agent phải **tự suy luận** module nào ghép được thành lời giải từ danh mục đầy đủ (`references/node-catalog.md`) và cơ chế nền tảng (`references/concepts.md`), không chép nguyên flow mẫu.

Tài liệu chính thức: `https://omicrm.io/post/topic/omiflow-7` (tổng quan, trì hoãn, biến, đối tượng, đối tác, Google Sheet, kịch bản mẫu). Gặp module chưa rõ thì đọc ở đây trước.

## Rules (BẮT BUỘC)
1. **Suy luận từ bài toán**: chạy khung 8 câu hỏi ở `references/design-patterns.md` mục A, rồi chọn module. Mẫu đã chạy chỉ tham chiếu hình dạng.
2. **Không bịa schema**: module có nhãn [verify JSON] dùng JSON trong catalog; module [enum] phải dựng thử 1 lần (hoặc Ctrl+C một nút cùng loại trên canvas để đọc định dạng clipboard) → GET lại để lấy schema → ghi bổ sung vào catalog.
3. **An toàn dữ liệu khách**: chỉ đọc flow đang chạy. Sửa flow đang chạy → lưu nháp hoặc tạo flow mới để **tắt**, chỉ cập nhật hay bật khi user đồng ý. Không xoá, không tắt flow của khách nếu không được yêu cầu. Kiểm tra quota flow ("Thêm mới N/M") và quota nút trước khi tạo.
4. **Không bịa dữ liệu nghiệp vụ**: URL API ngoài, danh mục phiếu, nhân viên nhận, đầu số… lấy từ tài liệu user hoặc từ tenant (GET); thiếu thì ghi "Cần xác nhận".
5. **Verify mọi lần lưu**: GET lại và chạy checklist trong `references/api-reference.md`; test bằng cURL hoặc sự kiện thật, xem tab **Lịch sử**.
6. **Học xong phải ghi lại**: schema mới, module mới, gotcha mới → cập nhật catalog, patterns hoặc mục Gotchas. Không ghi URL, token, tenant id hay dữ liệu khách vào skill (repo dùng chung).

## Input contract (hỏi một lần rồi tự làm)
1. **Domain doanh nghiệp** (`<tên>.omicrm.io`).
2. **Tài khoản đăng nhập**.
3. **Bài toán nghiệp vụ**: file hoặc prompt mô tả (sự kiện gì, cần ra kết quả gì, ai nhận, hệ thống ngoài nào).

**Đăng nhập — ưu tiên MCP OMI** (chi tiết `references/omi-mcp.md`). Agent tự kiểm tra, tự cài và tự cấu hình MCP OMI ở phạm vi người dùng khi chưa có, trên mọi agent/client hỗ trợ MCP chứ không mặc định Codex hay Claude. Dùng thông tin đăng nhập đã được cung cấp mà không hỏi lại; không in mật khẩu/token và không ghi bí mật vào repo hoặc file tạm. Thứ tự:
- **(a)** Nếu MCP chưa có thì tự cài theo `omi-mcp.md` mục 1; sau đó gọi `login_omicall_mcp` (+ `select_tenant`). Token cho API OMIFlow lấy bằng `scripts/omi_session.py` (đọc phiên MCP, không in token).
- **(b)** Phiên có sẵn (`OMI_TOKEN_FILE`).
- **(c)** Dự phòng: mở trang đăng nhập trong browser pane để user bấm đăng nhập **một lần**, rồi lấy token từ cookie `{domain}_omicrm_io` (JSON, key `"2"`, có thể URL-encode) và lưu vào file scratchpad, đặt `OMI_TOKEN_FILE`. Không chuyển trang khi user đang đăng nhập.

Không ghi token hay mật khẩu vào skill.

## Workflow
### Bước 0 — Khảo sát tenant
- **Flow hiện có — đọc bằng bản tóm tắt, không đổ JSON**: `python scripts/flow_outline.py --list`, rồi `python scripts/flow_outline.py <id>` (trigger → nút → nhánh, tên biến thay cho mã). Chỉ `--save <id>` ra file khi cần sửa JSON.
- **Tra id bằng MCP OMI** (một lần mỗi phiên, lưu `tenant_context.json` ở scratchpad): `get_service_package` (module đã bật), `get_ticket_categories` (danh mục phiếu), `list_agents` (contact_id cho thông báo, người liên quan), `list_hotlines` (đầu số cho trigger cuộc gọi), `get_all_channels` (OA, page, widget cho nút Trò chuyện, Marketing), `list_webhooks`.
- **Chưa có trong MCP → API cùng token**: bộ trạng thái phiếu (`ticket-v2-stg.omicrm.com/ticket/status-set/get-all`), phân bổ (`tenant-v1-stg.omicrm.com/sale_allocation/search`), thuộc tính động (`tenant-v1-stg.omicrm.com/attribute/get_all?has_attr=true`), kịch bản callbot (`chatbot-gateway-v1-stg.omicrm.com/callbot/script/list-by-tenant/{tenant_id}`). Chỉ in các trường id và tên.

### Bước 1 — Phân tích bài toán
Khung 8 câu (design-patterns mục A): sự kiện kích hoạt · đối tượng cần có trong luồng · dữ liệu còn thiếu · rẽ nhánh · kết quả nghiệp vụ · người tham gia · thời gian chờ · caller cần gì và chống lặp. Ghi ra bảng: câu hỏi → module → cấu hình. Kiểm tra tenant đã bật tích hợp mà thiết kế cần chưa (OA, nhà cung cấp SMS, template ZNS, đối tác, kịch bản callbot); thiếu thì ghi "Cần cấu hình".

### Mô hình đối tượng (phải nắm trước khi thiết kế — chi tiết `references/concepts.md`)
- Mỗi lượt chạy mang **đối tượng gốc** từ trigger: khách, phiếu, cuộc gọi, hội thoại, dòng Excel, lượt biểu mẫu, đơn hàng đối tác. Trigger API thì không có đối tượng gốc.
- Một số đối tượng **tự kéo theo**: phiếu kéo khách, cuộc gọi, hội thoại đính kèm; cuộc gọi kéo khách; hội thoại kéo khách; đơn hàng kéo khách đối tác.
- Hành động chỉ chạy khi **đối tượng nó cần đã có trong luồng**: gửi tin Zalo cần hội thoại Zalo, Marketing gửi cho "Khách hàng" cần khách, cập nhật đơn cần ID đơn. Thiếu thì thêm **Gán đối tượng liên quan**; đối tượng cùng loại thứ 2 trở đi có **vị trí** 1–5.
- Biến tuỳ chỉnh và dữ liệu thu thập chỉ sống trong flow hiện tại, không truyền sang flow được gọi.

### Bước 2 — Thiết kế flow
- Vẽ luồng dạng text (như mẫu B1–B6): trigger → nút → nhánh, có nhánh lỗi và nhánh mặc định.
- Gom nhánh trùng về một nút chung; dài hoặc dùng lại → tách flow con phụ thuộc (`START_OTHER_CAMPAIGN`).
- Đặt tên: `<số> - [MỤC ĐÍCH]`; thêm nút Ghi chú chứa URL webhook và cURL mẫu.

### Bước 3 — Dựng JSON và lưu
- Lấy một flow cùng tenant làm khung (top-level fields), dựng `nodes` + `edges.connections` theo schema DUAL ở `references/api-reference.md` (nhánh lưu cả trong node lẫn edge).
- Lưu nháp `save_draft_v2` hoặc tạo `add_v2`; sửa `update_v2/{id}`; multipart field `file`, Python `requests` (không dùng curl).
- Nếu API lưu chưa verify cho tenant đó → dựng bằng **dán JSON nút vào canvas** (định dạng clipboard editor, `concepts.md` mục 7) hoặc thao tác UI, rồi GET để đối chiếu.

### Bước 4 — Verify, test, giao
- Checklist trong api-reference; test webhook bằng cURL; xem tab Lịch sử từng nút.
- Test không chỉ luồng chính: đối tượng đã tồn tại kích hoạt lại, sửa đối tượng đang ở trạng thái trigger, từng nhánh điều kiện, số lượt còn lại theo giới hạn (`references/ui-build-and-test.md` mục 5).
- **Kiểm thử bằng MCP** thay vì mở giao diện:
  - flow tạo phiếu → `search_tickets`, `get_ticket`;
  - flow cập nhật khách → `get_contact_by_phone`;
  - trigger cuộc gọi hoặc phím IVR → `click_to_call` (khi user đồng ý gọi số thật) rồi `search_calls` lấy `transaction_id`.

  Dọn dữ liệu test (`delete_ticket`, `delete_contact`) chỉ khi user đồng ý.
- Giao: editor URL `https://{domain}.omicrm.io/flow/edit/{id}?lng=vi`, sơ đồ luồng, bảng biến, cURL test, các điểm "Cần xác nhận".

## Danh mục module (tóm tắt — chi tiết và JSON: `references/node-catalog.md`)
- **Trigger** (node CONDITION đầu tiên): API (`WEB_HOOK`); Điều kiện (`GENERAL`: đối tượng thêm mới hoặc cập nhật thoả thuộc tính, hoặc sự kiện mở rộng như cuộc gọi kết thúc, phím IVR, phiếu mới, khách quan tâm OA, đánh giá ZNS); Biểu mẫu; Định kỳ (ngày, tuần, tháng, trước hoặc sau một thuộc tính thời gian, thời điểm cụ thể); File Excel; Đối tác (liên kết trực tiếp: Haravan, Sapo, KiotViet, WooCommerce, Pancake…; webhook; đối tác tự định nghĩa); Cuộc gọi đang diễn ra; Phiếu ghi chuyển trạng thái.
- **Logic**: Điều kiện (nhiều trường hợp + nhánh mặc định; so sánh biến, cuộc gọi, khách, phiếu, khung giờ làm việc), Trì hoãn (sau khoảng, thời điểm cụ thể, khung giờ tiếp tục, hoặc điều kiện đến trước), Random (A/B), Phân tích thông tin (AI phân loại theo chủ đề hoặc ý định đã đào tạo, mỗi ý định một nhánh).
- **Hành động** (22): thêm hoặc cập nhật khách, tạo hoặc cập nhật phiếu, thông báo, nhắc nhở, trả kết quả qua Biểu mẫu hoặc API, biến liên kết tùy chỉnh (API, ChatGPT, tính toán, ngẫu nhiên, ảnh thư mời), gán đối tượng liên quan, Google Sheet, cập nhật hội thoại, cuộc gọi, nhân viên, cửa sổ, đánh giá AI Chatbot, gọi API ra ngoài, phân loại, chuyển tiếp cuộc gọi, gọi flow khác, cập nhật đối tác, giữ cuộc gọi.
- **Cửa sổ tương tác** (màn hình nhân viên): thông tin, biểu mẫu (có nhánh hoàn thành), nút bấm, biến, xem chi tiết, tính năng.
- **Marketing** (gửi hàng loạt): SMS, ZNS hoặc ZBS, xin quyền gọi ZCC, Email, AutoCall, AI Callbot, Viber Business.
- **Trò chuyện**: tin nhắn từng kênh (Facebook, Zalo OA, Zalo cá nhân, LiveTalk, Telegram, Viber, TikTok, WhatsApp, Email), gửi tin nhắn chung, giao cho bot AI (ChatGPT, ChatX, AI Chatbot, ProAI, Partner AI).
- **Khác**: Thu thập thông tin (AI bóc thực thể từ nội dung vào biến, hoặc gán giá trị cố định), Ghi chú.

## Kết nối với Callbot và Chatbot
- **Callbot → OMIFlow**: callbot gọi URL webhook (khi thu đủ biến, khi bot không xử lý được, khi khách bấm phím chuyển máy) để tạo phiếu, đồng bộ hệ thống ngoài, bật popup cho nhân viên.
- **OMIFlow → Callbot**: nút Marketing `CALLBOT` hoặc `AUTOCALL` tạo phiên gọi cho các khách đi qua flow; kiểm tra trạng thái phiên bằng điều kiện "Kiểm tra trạng thái AI Callbot".
- **Chatbot cần dữ liệu CRM**: chatbot không tự tra khách theo thuộc tính → gọi flow `WEB_HOOK` → `GET_RELATED`/`API_V2` → `SEND_RESPONSE_WEBHOOK_API` trả dữ liệu (thay cho `response_config` cố định).
- Sau cuộc gọi AI: `{{ca_summarize}}` (tóm tắt) và `{{ca_ai_assistant}}` (kết quả phân tích) dùng làm đầu vào cho ChatGPT phân loại hoặc chèn vào mô tả phiếu.

## Thao tác UI (khi phải dựng bằng tay)
- Playbook đầy đủ, đã làm thật (biểu mẫu, trigger, cấu hình từng nút, Lịch sử, kịch bản test): `references/ui-build-and-test.md`.
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
- **Trigger Biểu mẫu chỉ liệt kê biểu mẫu đã Xuất bản** (xuất bản = link công khai → hỏi user trước).
- **Mã biến form ngẫu nhiên dễ lẫn `I`/`l`**: lấy mã bằng JS hoặc chip biến, không gõ theo ảnh chụp. Biến sai vẫn hiện `{{...}}` thô trên thẻ nút.
- **Nút vừa tạo chưa có "Nút kế tiếp"**: Lưu → mở lại nút (hoặc ←/→ trên ngăn). Điều kiện: "Nút kế tiếp" phải = trường hợp, trái = mặc định.
- **Xuất bản đổi id trong URL editor**: mở flow từ danh sách, đừng giữ URL cũ.
- **Trigger theo trạng thái chỉ bắt lúc chuyển vào trạng thái**, sửa thuộc tính khác không chạy lại → dùng đổi trạng thái làm mốc nối flow (ví dụ bước "duyệt/verify" do người làm).
- **SLA "không gọi trong N phút"**: điều kiện Mở rộng "Kiểm tra tương tác khách hàng" (Không có tương tác + Cuộc gọi/Ghi chú + N phút), không tự đếm cuộc gọi.
- **Khách đã tồn tại**: "Thêm khách hàng" → `CONTACT_EXIST` (không trùng); "Cập nhật khách hàng" vẫn áp lên khách cũ nhưng chỉ đúng các thuộc tính đã khai báo. Gán phụ trách trùng người hiện tại → `NO_CHANGE`. Cả hai là chấm đỏ vô hại, luồng chạy tiếp.
- **Giới hạn số lần đi qua (mặc định 2)** làm trigger im lặng khi hết lượt, kể cả lúc test.
- **Test trì hoãn**: không dùng "Tiếp tục kịch bản" (cảnh báo mơ hồ). Chờ thật bằng `sleep` nền, hoặc tạm đặt 1 phút rồi trả lại giá trị thật và xuất bản.
- **Flow có thể bị người/phiên khác sửa**: đọc Phiên bản và cấu hình trước mỗi lần test.
- **Pane chậm, ảnh chụp trễ 1–2 thao tác**: kiểm tra bằng `get_page_text`/JS, bấm theo `ref` từ `find`.
- **Browser pane không bắt XHR khác domain** trong `read_network_requests`; dùng `performance.getEntriesByType('resource')` để tìm endpoint. Pane hẹp làm canvas tràn ngang → ưu tiên API thay vì bấm UI.

## Tài liệu tham khảo
- `references/concepts.md` — cơ chế nền tảng: đối tượng và vị trí, trigger, biến, cú pháp truy vấn JSON, trì hoãn, AI, marketing, trò chuyện, dán JSON vào canvas, Google Sheet.
- `references/node-catalog.md` — mọi trigger, nút, hành động, điều kiện, biến; JSON đã kiểm chứng.
- `references/design-patterns.md` — khung suy luận 8 câu, 7 mẫu đã chạy (B7: phân lead có duyệt + SLA + thu hồi), mẫu mở rộng theo lĩnh vực, lỗi thiết kế cần tránh.
- `references/crm-config.md` — cấu hình nền tảng: thuộc tính động (kiểu trường, mã), bộ trạng thái khách hàng (WIN/LOST, trình tự), chủ đề và bộ trạng thái phiếu (hạn xử lý, ca làm việc).
- `references/api-reference.md` — endpoint, schema flow, DUAL node và edge, khung lưu, checklist.
- `references/omi-mcp.md` — MCP OMI: cài đặt, đăng nhập, công cụ cho từng bước, cách tiết kiệm token (bản giống hệt trong 3 skill OMI).
- `scripts/omi_session.py` — token từ phiên MCP; `scripts/flow_outline.py` — liệt kê và tóm tắt flow.
- `references/webhook-examples.md` — mẫu cURL và response.
- `references/react-flow-selectors.md` — selector DOM để thao tác canvas bằng JS.
- `references/ui-build-and-test.md` — dựng và kiểm thử flow hoàn toàn qua giao diện: biểu mẫu, trigger, cấu hình nút, biến, Lịch sử, chiến lược test trì hoãn.
