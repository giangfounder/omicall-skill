---
name: omicall-omiflow
description: >-
  [v1.12.0] Thiết kế, dựng và sửa quy trình tự động OMIFlow của OMICall/OMICRM: trigger webhook API, cuộc gọi, phím IVR, phiếu ghi, lịch, Excel, đối tác; điều kiện, trì hoãn, AI phân loại, gọi API ngoài, cập nhật khách/phiếu/cuộc gọi, popup nhân viên, SMS/ZNS, chạy hoặc liên kết Callbot/Chatbot; đọc và lưu qua API campaign-v1.
---

# OMICall OMIFlow — Builder Playbook (mọi tenant, mọi bài toán)

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác (`<thư mục skill>` = thư mục chứa SKILL.md này). Câu đầu tiên trả lời user: `Đang dùng omicall-omiflow v<phiên bản>` (lấy từ dòng `SKILL_VERSION`; script lỗi thì dùng v1.12.0). Script báo **SKILL.md đã thay đổi** → đọc lại SKILL.md từ đĩa rồi mới làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.

## Đường nhanh
Chạy script bằng đường dẫn tuyệt đối `<thư mục skill>/scripts/...`. Khối này chỉ trỏ tới quy tắc gốc bên dưới; mâu thuẫn thì quy tắc gốc thắng.
1. **Token**: `python <thư mục skill>/scripts/omi_preflight.py --domain <domain>` → route `api` / `ui` / `blocked`. `blocked` → đưa user đúng MỘT việc theo `references/omi-mcp.md` (Đọc nhanh); không đọc cookie, không nhập mật khẩu hộ. Trong lúc chờ, làm tiếp bước 3 offline.
2. **Khảo sát (Bước 0, BẮT BUỘC trước thiết kế)**: `<thư mục skill>/scripts/tenant_survey.py --out <scratch>/tenant_context.json` + công cụ MCP → kiểu thuộc tính (`is_list`), danh mục phiếu, tích hợp đã bật, quota flow và nút. Thiếu → "Cần xác nhận".
3. **Thiết kế**: khung 8 câu (`references/design-patterns.md` mục A) → tra `references/node-status.json`: `verified` → đi API; `enum` / `ui_only` / `unverified` → đi UI hoặc ghi "Cần xác nhận".
4. **Dựng — API**: tạo vỏ flow trên UI (có `_id` nháp; cách tối thiểu để lưu được vỏ: Cần xác nhận, `references/api-reference.md` mục Lưu flow) → `flow_outline.py --save <id>` → sửa `nodes` + `edges` + `name_mappings` → `<thư mục skill>/scripts/omi_save.py flow payload.json --domain <domain>` (chỉ `save_draft_v2`, không xuất bản). `name_mappings` (bản editor) chưa `verified`: mỗi phần tử chỉ được **chép nguyên từ bản GET của một nút cùng loại đã dựng trên UI** (`references/node-catalog.md` mục 6, Cách học nhanh) rồi đổi id/giá trị cho khớp `nodes`, không tự viết; chưa có bản GET mẫu cho loại đó → dựng nút đó bằng UI. File `--save` đã che bí mật (`***`): flow có header `Authorization`/token ở nút Gọi API hay webhook thì `omi_save.py` dừng exit 2 (cố ý, tránh ghi đè bí mật thật) → phần đó sửa trên UI, ghi "Cần xác nhận".
5. **Dựng — UI**: mỗi flow một subagent, một tab (mẫu giao việc trong `references/omi-mcp.md`, thao tác ở `references/ui-build-and-test.md`).
6. **Kiểm**: `python <thư mục skill>/scripts/validate_flow.py payload.json --mode pre --context <scratch>/tenant_context.json`; sau lưu GET lại và chạy `--mode post --sent payload.json` (omi_save tự chạy). Có FAIL thì sửa, không lưu tiếp.
7. **Test**: cURL hoặc sự kiện thật chỉ khi user đồng ý; xem tab Lịch sử (Bước 4).
8. **Giao**: flow vẫn là nháp; user tự bấm **Xuất bản** sau khi duyệt (Rule 3).

Không bao giờ: xuất bản, bật, tắt hay xoá flow khi user chưa duyệt · đọc cookie, in token, nhập mật khẩu hộ · bịa schema cho loại chưa `verified` (Rule 2).

## Overview
**OMIFlow** (menu OMIFlow, path `/flow/list`, editor `/flow/edit/{id}`) là bộ máy tự động hoá của OMICRM, cùng loại N8N, Zapier, Make, nhưng gắn sẵn với tổng đài, Callbot, Chatbot, đa kênh, phiếu ghi, khách hàng. Một flow = **điều kiện bắt đầu** → chuỗi **nút** (điều kiện, trì hoãn, hành động, cửa sổ tương tác, marketing, kênh chat) → kết quả nghiệp vụ.

**Module là của nền tảng, dùng chung mọi tenant.** Tenant chỉ khác ở dữ liệu cấu hình (danh mục phiếu, thuộc tính, nhân viên, tag), tích hợp đã bật (OA, SMS, Email, ZNS, đối tác, callbot) và gói (quota flow, nút). Flow có sẵn ở một tenant chỉ là **minh hoạ nhỏ**. Khi nhận bài toán, agent phải **tự suy luận** module nào ghép được thành lời giải từ danh mục đầy đủ (`references/node-catalog.md`) và cơ chế nền tảng (`references/concepts.md`), không chép nguyên flow mẫu.

Tài liệu chính thức: `https://omicrm.io/post/topic/omiflow-7` (tổng quan, trì hoãn, biến, đối tượng, đối tác, Google Sheet, kịch bản mẫu). Gặp module chưa rõ thì đọc ở đây trước.

## Rules (BẮT BUỘC)
1. **Suy luận từ bài toán**: chạy khung 8 câu hỏi ở `references/design-patterns.md` mục A, rồi chọn module. Mẫu đã chạy chỉ tham chiếu hình dạng.
2. **Không bịa schema**: module có nhãn [verify JSON] dùng JSON trong catalog; module [enum] phải dựng thử 1 lần (hoặc Ctrl+C một nút cùng loại trên canvas để đọc định dạng clipboard) → GET lại để lấy schema → ghi bổ sung vào catalog.
3. **An toàn dữ liệu khách**: chỉ đọc flow đang chạy. Sửa flow đang chạy → lưu nháp hoặc tạo flow mới, chỉ cập nhật bản đang chạy hay bật khi user đồng ý. Flow mới: giữ quy ước của user (**Hoạt động**, Không giới hạn lượt, không đặt khoảng hiệu lực — Gotchas "Mặc định mọi flow mới") nhưng **chỉ lưu nháp, chưa xuất bản** tới khi test xong và user duyệt; bản nháp có chạy sự kiện thật hay không: Cần xác nhận. Không xoá, không tắt flow của khách nếu không được yêu cầu. Kiểm tra quota flow ("Thêm mới N/M") và quota nút trước khi tạo.
4. **Không bịa dữ liệu nghiệp vụ**: URL API ngoài, danh mục phiếu, nhân viên nhận, đầu số… lấy từ tài liệu user hoặc từ tenant (GET); thiếu thì ghi "Cần xác nhận".
5. **Verify mọi lần lưu**: GET lại và chạy checklist trong `references/api-reference.md` (tự động bằng `scripts/validate_flow.py --mode post`); test bằng cURL hoặc sự kiện thật, xem tab **Lịch sử**.
6. **Bài học mới** (schema, module, gotcha): ghi theo mục *Bảo trì skill* cuối file.

## Input contract (hỏi một lần rồi tự làm)
1. **Domain doanh nghiệp** (`<tên>.omicrm.io`).
2. **Tài khoản đăng nhập**: user tự đăng nhập (MCP OMI hoặc trang đăng nhập); agent không nhập mật khẩu hộ.
3. **Bài toán nghiệp vụ**: file hoặc prompt mô tả (sự kiện gì, cần ra kết quả gì, ai nhận, hệ thống ngoài nào).

**Đăng nhập — ưu tiên MCP OMI** (chi tiết `references/omi-mcp.md`). Bước đầu luôn là `scripts/omi_preflight.py --domain <domain>` (không in token, không gọi mạng). Áp dụng trên mọi agent/client hỗ trợ MCP chứ không mặc định Codex hay Claude. Không in mật khẩu/token và không ghi bí mật vào repo hoặc file tạm. Thứ tự:
- **(a)** MCP OMI: đã có thì gọi `login_omicall_mcp` (+ `select_tenant`). Chưa có thì agent soạn sẵn lệnh `mcp add` theo `omi-mcp.md` (mật khẩu để placeholder) để **user tự chạy** rồi mở phiên mới; agent không cầm mật khẩu dạng rõ. Token cho API OMIFlow lấy bằng `scripts/omi_session.py` (đọc phiên MCP, không in token).
- **(b)** Phiên có sẵn: `OMI_TOKEN_FILE` do user tự đặt.
- **(c)** Không có (a), (b): dựng và test bằng giao diện (`references/ui-build-and-test.md`). User tự đăng nhập **một lần** trong browser pane; không chuyển trang khi user đang đăng nhập. **Không đọc cookie lấy token** (bằng JS hay CDP): bị bộ lọc an toàn chặn thì dừng, không lách.

Không ghi token hay mật khẩu vào skill.

## Workflow
### Bước 0 — Khảo sát tenant
- **Kiểm TRƯỚC khi thiết kế** (thiết kế sai từ đầu tốn nhiều nhất): kiểu từng thuộc tính khách/phiếu sẽ gán (kiểu *danh sách* không nhận biến → phải rẽ nhánh theo giá trị, xem Gotchas "AI điền CRM" và `references/ui-build-and-test.md` mục 7), danh mục và bộ trạng thái phiếu, tích hợp đã bật (OA, SMS, ZNS, đối tác, callbot), quota flow và nút. Ghi vào `tenant_context.json` (`scripts/tenant_survey.py --out`); thiếu thì "Cần xác nhận".
- **Flow hiện có — đọc bằng bản tóm tắt, không đổ JSON**: `python <thư mục skill>/scripts/flow_outline.py --list`, rồi `python <thư mục skill>/scripts/flow_outline.py <id>` (trigger → nút → nhánh, tên biến thay cho mã; cảnh báo id mồ côi). File có sẵn: `--file <json>` (offline). Chỉ `--save <id>` ra file (vào scratch) khi cần sửa JSON.
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
- Lấy một flow cùng tenant làm khung (top-level fields), dựng `nodes` + `edges.connections` + `name_mappings` theo mô hình DUAL ở `references/api-reference.md` (nhánh lưu cả trong node lẫn edge; bản editor nằm ở `name_mappings`). Loại nút nào dùng JSON được: tra `references/node-status.json`. `name_mappings` đang `unverified`: phần tử editor chỉ chép nguyên từ bản GET của nút cùng loại đã dựng trên UI (`node-catalog.md` mục 6, Cách học nhanh), không tự viết; không có bản GET mẫu → dựng nút đó trên UI.
- Chỉ lưu nháp `save_draft_v2` trên flow nháp có `_id` (✔ 10/2026), multipart field `file`, Python `requests` (không dùng curl) — dùng `scripts/omi_save.py flow`. `add_v2` / `update_v2/{id}` mới thấy trong mã UI, **chưa chạy thật** → không dùng; flow mới thì tạo vỏ trên UI rồi lưu nháp vào `_id` đó.
- Nếu API lưu chưa verify cho tenant đó → dựng bằng **dán JSON nút vào canvas** (định dạng clipboard editor, `concepts.md` mục 7) hoặc thao tác UI, rồi GET để đối chiếu.

### Bước 4 — Verify, test, giao
- Checklist trong api-reference, chạy tự động bằng `scripts/validate_flow.py` (mã C1–C7, X1–X10); test webhook bằng cURL; xem tab Lịch sử từng nút.
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
- Nối cạnh giữa hai nút có sẵn: `left_click_drag` từ chấm nguồn (cuối nút trước) tới chấm đích (đầu nút sau) khi cả hai cùng hiện trên màn hình, rồi Lưu và mở lại để kiểm (`references/ui-build-and-test.md` mục 7). "Bước tiếp theo" trong ngăn chỉ tạo nút mới. Không được thì sửa `next_nodes` + `edges.connections` trong JSON và lưu nháp. Giả lập PointerEvent bằng JS thường không ăn, không dùng làm cách chính.
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
- **`response_config` của webhook là cố định**; trả dữ liệu động dùng hành động "Trả kết quả qua API" (`SEND_RESPONSE_WEBHOOK_API`, schema chưa kiểm chứng). `status_code` 9999 trong body không phải HTTP status.
- **Gọi flow khác**: flow đích phải là loại phụ thuộc; kết quả của flow đích không quay về webhook của flow gọi.
- **Quota**: số flow theo gói, số nút mỗi flow (ví dụ 16/20) — gom nhánh trùng để tiết kiệm.
- **Trigger theo trạng thái chỉ bắt lúc chuyển vào trạng thái**, sửa thuộc tính khác không chạy lại → dùng đổi trạng thái làm mốc nối flow (ví dụ bước "duyệt/verify" do người làm).
- **SLA "không gọi trong N phút"**: điều kiện Mở rộng "Kiểm tra tương tác khách hàng" (Không có tương tác + Cuộc gọi/Ghi chú + N phút), không tự đếm cuộc gọi.
- **Khách đã tồn tại**: "Thêm khách hàng" → `CONTACT_EXIST` (không trùng); "Cập nhật khách hàng" vẫn áp lên khách cũ nhưng chỉ đúng các thuộc tính đã khai báo. Gán phụ trách trùng người hiện tại → `NO_CHANGE`. Cả hai là chấm đỏ vô hại, luồng chạy tiếp.
- **Giới hạn số lần đi qua (mặc định 2)** làm trigger im lặng khi hết lượt, kể cả lúc test.
- **Flow mới trên giao diện**: chưa bấm "Lưu lại" mà đóng hộp thoại trigger hoặc rời trang thì mất cả flow → lưu ngay sau khi chọn trigger. "Lưu lại" hiện hộp thoại "Thông tin về URL" (tick xác nhận rồi Cập nhật). URL webhook của trigger API sinh lại mỗi lần tạo trigger mới và không xem lại được sau khi xuất bản → ghi lại lúc hiện. Xoá khoảng hiệu lực: bấm nút x ở từng ô ngày.
- **Xuất bản đổi id flow** (URL `/flow/edit/{id}` mới): sau xuất bản phải mở lại bằng id mới và kiểm tra lại các nơi đã gắn flow (webhook TTP, bot).
- **Gắn webhook flow vào Tương tác phím (TTP)**: ô "URL nhận kết quả từ hook" của TTP không lưu được (nút Cập nhật không báo lỗi, ngày sửa đổi không đổi) khi flow đích còn là bản nháp; sau khi xuất bản flow thì lưu được → xuất bản trước, gắn sau, rồi tải lại để kiểm chứng. Gõ xong ô nhập phải click ra ngoài rồi mới bấm Cập nhật (click đầu chỉ làm mất focus). Payload TTP gửi: `digits`, `customer_phone`, `ct_transaction_id` (mẫu B4).
- **Cửa sổ thông tin (INFO_DIALOG)**: mục Nhân viên có hai loại — "Nhân viên trong luồng kịch bản" và "Nhân viên" chỉ định (chọn người cụ thể); phải kiểm từng nút vì các nút có thể lệch nhau. Chọn người gồm hai bước: thêm loại Nhân viên rồi chọn người.
- **Học payload từ tenant/flow đã có**: cột "Điều kiện kích hoạt" ở danh sách flow của trigger API liệt kê tên biến → đọc nó thay vì đoán tên trường webhook. Trước khi kết luận "tenant chưa có flow nhận webhook X", phải mở danh sách flow và đọc flow đích; đoán từ cấu hình phía gửi (TTP, callbot) là sai cách.
- **Mặc định mọi flow mới**: Hoạt động, Không giới hạn lượt, không đặt khoảng hiệu lực (trừ khi user nói khác). Vẫn chỉ lưu nháp, chưa xuất bản tới khi test xong và user duyệt (Rule 3).
- **Cấu hình TTP** (Cấu hình > Tổng đài > Tương tác phím, `/config/switchboard/key-interaction/list`): tên, nhạc chờ bắt đầu, số lần cho nhấn sai, thời gian chờ, kịch bản kết thúc, công tắc "Chuyển tiếp… khi nhấn đúng số nội bộ" (đừng bật nhầm), Kích hoạt Webhook + URL, bảng Thao tác phím (phím → kịch bản/nhóm nội bộ). Chỉ tạo/sửa khi user đồng ý; mỗi phím phải có sẵn nhóm nội bộ.
- **Giao việc cho tiến trình nền (fork)**: mỗi flow chỉ một tiến trình ghi tại một thời điểm; sau mỗi tiến trình phải tự mở lại flow kiểm từng nút trước khi báo xong (báo cáo của fork có thể thiếu hoặc lệch).
- **Browser pane dùng chung với user**: user thao tác song song (xuất bản, mở hộp thoại, bật công tắc) làm đổi phiên bản và trạng thái giữa chừng; khung xem co nhỏ làm danh sách chọn bị cắt → đặt lại kích thước (resize preset desktop) và không giao hai việc cùng chạm một flow cho nhiều tiến trình nền.
- **Xuất bản bằng agent có thể bị chặn bởi hệ thống phân quyền** → để user tự bấm Xuất bản, rồi agent làm tiếp phần gắn webhook.

- **LiveTalk**: SĐT khách điền ở form trước chat = biến Đa kênh `{{social_lt_phone_number}}` (email `{{social_lt_email}}`); dùng được trực tiếp trong "Thêm khách hàng" của flow trigger LiveTalk.
- **Bot ↔ flow**: flow phụ thuộc gọi từ bot (`START_OTHER_CAMPAIGN`) không nhận biến hội thoại; cần truyền dữ liệu thì cho bot gọi flow `WEB_HOOK` qua hành động API với body chứa biến. Log flow webhook "2 lượt cùng giây" = bước CONDITION + ACTION của một lượt.
- **Cấu hình phân bổ** (`split_evenly` / `prioritize_employees_with_fewer_customers` / `specific_division` theo %): đổi "Hình thức" của cấu hình đang gắn là đổi cho mọi flow dùng nó; không đưa tài khoản admin (nơi nhận lead thu hồi) vào danh sách chia. Chi tiết `references/crm-config.md`.
- **Biểu mẫu công khai chặn gửi liên tiếp từ cùng trình duyệt** (lần thứ 3 bị từ chối im lặng, trang chỉ tải lại) → test nhiều lead thì xoá dữ liệu trình duyệt của trang form hoặc dùng cửa sổ khác.
- **Bật/tắt flow**: biểu tượng cạnh tên flow → "Thông tin Flow" → Hoạt động / Ngưng hoạt động → Cập nhật (`is_pause`). Xoá flow là xoá vĩnh viễn kèm lịch sử chạy → để user tự xoá.
- **Dựng hoặc test bằng giao diện**: đọc `references/ui-build-and-test.md` (mục 5–6) trước — ô nhập nối thêm, biểu mẫu phải xuất bản, mã biến form, nút kế tiếp, xuất bản đổi id, test trì hoãn, flow bị người khác sửa, browser pane chậm hoặc không bắt XHR.
- **AI điền CRM sau cuộc gọi**: bóc trường bằng nút LLM từ `{{ca_ai_assistant}}`; thuộc tính khách kiểu danh sách không nhận biến → rẽ nhánh theo giá trị, mỗi trường danh sách một flow; mỗi nút Hành động chỉ một Biến liên kết tuỳ chỉnh; biến chỉ hiện sau Lưu (Điều kiện cần tải lại trang); gõ sau khi bấm ô phải chờ ~1s. Chi tiết `references/ui-build-and-test.md` mục 7.

## Tài liệu tham khảo
- `references/concepts.md` — cơ chế nền tảng: đối tượng và vị trí, trigger, biến, cú pháp truy vấn JSON, trì hoãn, AI, marketing, trò chuyện, dán JSON vào canvas, Google Sheet.
- `references/node-catalog.md` — mọi trigger, nút, hành động, điều kiện, biến; JSON đã kiểm chứng.
- `references/design-patterns.md` — khung suy luận 8 câu, 7 mẫu đã chạy (B7: phân lead có duyệt + SLA + thu hồi), mẫu mở rộng theo lĩnh vực, lỗi thiết kế cần tránh.
- `references/crm-config.md` — cấu hình nền tảng: thuộc tính động (kiểu trường, mã), bộ trạng thái khách hàng (WIN/LOST, trình tự), chủ đề và bộ trạng thái phiếu (hạn xử lý, ca làm việc).
- `references/api-reference.md` — endpoint, schema flow, DUAL node và edge, khung lưu, checklist.
- `references/omi-mcp.md` — MCP OMI: cài đặt, đăng nhập, công cụ cho từng bước, cách tiết kiệm token, dựng nhiều artefact, mẫu giao việc cho subagent (bản giống hệt trong 4 skill OMI).
- `references/node-status.json` — trạng thái từng loại nút/hành động (verified / enum / ui_only / unverified), nguồn file:dòng; quyết định đi API hay UI.
- `scripts/omi_session.py` — token từ phiên MCP; `scripts/flow_outline.py` — liệt kê và tóm tắt flow (`--file` offline); `scripts/validate_flow.py` — kiểm JSON flow theo checklist (offline, chỉ đọc). Script dùng chung (`omi_preflight`, `omi_api`, `omi_save`, `tenant_survey`, `manifest`, `extract_text`, `extract_template`): xem `references/omi-mcp.md`.
- `references/webhook-examples.md` — mẫu cURL và response.
- `references/react-flow-selectors.md` — selector DOM để thao tác canvas bằng JS.
- `references/ui-build-and-test.md` — dựng và kiểm thử flow hoàn toàn qua giao diện: biểu mẫu, trigger, cấu hình nút, biến, Lịch sử, chiến lược test trì hoãn.

## Bảo trì skill (sau khi giao)
- Học được schema mới, module mới, gotcha mới → cập nhật catalog (`references/node-catalog.md`, `references/node-status.json`), patterns hoặc mục Gotchas, nhưng **chỉ ghi vào repo nguồn của skill khi user cho phép**; không sửa bản cài (khớp bước *cập nhật skill* ở đầu file).
- Không ghi URL, token, tenant id hay dữ liệu khách vào skill (repo dùng chung). Template nút mới lấy bằng `scripts/extract_template.py` (đã che dữ liệu); nhãn `verified` chỉ do agent chính hoặc user duyệt kèm báo cáo `validate_flow.py --mode post` PASS trên bản GET thật.
