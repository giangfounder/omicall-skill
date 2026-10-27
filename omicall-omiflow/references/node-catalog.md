# OMIFlow — Danh mục module (trigger, nút, hành động, điều kiện)

Danh mục này là của **nền tảng**, áp dụng cho mọi tenant (xem `concepts.md` để hiểu cơ chế đối tượng, biến, trigger). Nguồn: (1) enum và nhãn tiếng Việt trích từ mã giao diện OMICRM (bản stg, 10/2026); (2) tài liệu chính thức `omicrm.io/post/topic/omiflow-7`; (3) JSON thật của các flow đang chạy, đọc qua `GET /omi_v2/campaign/get/{id}`. Mục có nhãn **[verify JSON]** đã thấy JSON thật; **[UI đã dựng]** đã cấu hình và chạy thật qua editor (chưa có JSON mẫu, cách làm ở `ui-build-and-test.md`); mục **[enum]** đã biết công dụng nhưng chưa có JSON mẫu: khi dùng thì dựng thử một lần (hoặc Ctrl+C một nút cùng loại trên canvas để xem định dạng clipboard), GET lại để lấy schema rồi bổ sung vào đây.

Id trong ví dụ đã thay bằng `<...>`. Mã biến thật là chuỗi ngẫu nhiên 10 ký tự (ví dụ `{{MpQxWEiLis}}`).

---

## 1. Điều kiện bắt đầu (trigger)

Trigger KHÔNG phải node riêng: nó là **node `CONDITION` đầu tiên** (`is_first_node:true`), `conditions[0].type` = loại trigger. `kick_off.event` của flow lặp lại loại này, `kick_off_ids` chứa id webhook (nếu có).

| Mã (`conditions[0].type`) | Nhãn UI | Khi nào dùng | Trạng thái |
|---|---|---|---|
| `WEB_HOOK` | API | Hệ thống ngoài, Callbot, Chatbot gọi vào URL để chạy flow, truyền biến qua body | [verify JSON] |
| `GENERAL` | Điều kiện | Đối tượng (khách, phiếu, cuộc gọi, cuộc gọi AI phân tích, hội thoại) được thêm mới hoặc cập nhật và thoả thuộc tính; hoặc **sự kiện mở rộng** (cuộc gọi kết thúc, phím IVR, phiếu mới, khách quan tâm OA, đánh giá ZNS…) kèm điều kiện thuộc tính | [verify JSON] |
| `FORM` | Biểu mẫu | Khách hoàn thành hoặc sửa Biểu mẫu. Chỉ liệt kê biểu mẫu đã xuất bản | [UI đã dựng] |
| `PERIOD` | Xảy ra định kỳ | Hằng ngày, tuần, tháng; **trước hoặc sau** một thuộc tính thời gian (sinh nhật, hạn phiếu, ngày hẹn); thời điểm cụ thể | [enum] |
| `EXCEL` | Kích hoạt bằng File Excel | Chạy hàng loạt, mỗi dòng Excel là một đối tượng, định nghĩa giá trị biến | [enum] |
| `THIRD_PARTY` | Đối tác | Nhận sự kiện hoặc webhook từ đối tác tích hợp | [enum] |
| `DIRECT_CALL` | Cuộc gọi đang diễn ra | Chạy ngay trong lúc cuộc gọi diễn ra (kết hợp `HOLDING_CALL`, `TRANSFER_CALL`) | [enum] |
| `HARAVAN`, `SAPO`, `KIOTVIET`, `WOOCOMMERCE`, `SHOPIFY`, `PANCAKEPOS`, `POSBIRD`, `TPOS`, `LARK_BASE`, `EMAIL_SMTP` | Đối tác cụ thể | Sự kiện đơn hàng, khách hàng, hoá đơn: tạo mới, cập nhật, thanh toán, huỷ, giao hàng; sự kiện email | [enum] |
| `SEARCHOPT` | (nội bộ) | Dùng làm `sub_condition` khi tra đối tượng, không phải trigger | [verify JSON] |

Mô tả chính thức của các trigger (nhãn UI): ADD_CONTACT "khi có 1 khách hàng được thêm mới và thoả 1 trong các điều kiện"; CONTACT "khi khách hàng thoả các điều kiện thuộc tính"; TICKET "khi phiếu ghi được chuyển đến trạng thái nhất định"; FORM; PERIOD; EXCEL; THIRD_PARTY; WEB_HOOK; DIRECT_CALL.

### 1a. WEB_HOOK [verify JSON]
```json
{"id":"<caseId>","type":"WEB_HOOK","operator_type":"AND",
 "data":[{"type":"WEB_HOOK","method":"POST","web_hook_id":"<tenant_id>-<token20>",
   "multi_variables":[
     {"field_code":"<code10>","field_name":"phone_number","shorthand_query":"phone_number","query":[{"key":"phone_number","filter":"="}]},
     {"field_code":"<code10>","field_name":"status","shorthand_query":"status","query":[{"key":"status","filter":"="}]}],
   "response_config":"{\n  \"message\": \"success\",\n  \"status_code\": 9999\n}",
   "time_out":5000,"skip_time_out":true}],
 "next_nodes":["<nodeId>"],"iteration_config":{"is_limit":false,"number_of_times":0,"time_range":"none","apply_for_branch":false}}
```
- URL: `https://external-v1-stg.omicrm.com/api/campaign/webhook/<web_hook_id>`.
- Mỗi biến trong `multi_variables` lấy `body.<key>`; truy vấn lồng dùng `query` nhiều bậc như API_V2 (xem 3.9).
- `response_config` là body trả về cố định. Muốn trả **dữ liệu động** (sau khi tra cứu) thì dùng hành động `SEND_RESPONSE_WEBHOOK_API` ("Trả kết quả qua API") trong luồng.
- `skip_time_out:true` + `time_out` (ms): caller không phải chờ hết flow.

### 1b. GENERAL — sự kiện cuộc gọi [verify JSON]
```json
{"id":"<caseId>","type":"GENERAL","operator_type":"AND","data":[
  {"type":"CALL","attributes":[
     {"field_code":"ct_call_status","values":["answered","noanswered"],"operator_type":"OR"},
     {"field_code":"ct_call_type","values":["inbound"],"operator_type":"OR"},
     {"field_code":"ct_sip_number","values":["<đầu số>"],"operator_type":"OR"}]},
  {"type":"COMPARE","compare_conditions":[
     {"operator":"CONTAIN","operator_type":"OR","values":[{"start_value":"1"},{"start_value":"2"}],"target_type":"CALL","field_code":"ct_key_action"}]}],
 "next_nodes":["<nodeId>"],"allocation":{},"iteration_config":{"time_range":"none"}}
```
Thuộc tính cuộc gọi hay dùng: `ct_call_status` (answered, noanswered…), `ct_call_type` (inbound, outbound, local), `ct_sip_number` (đầu số), `ct_key_action` (phím IVR khách bấm, có thể là "2" hoặc "02"), `ct_phone_number`, `ct_transaction_id`.

### 1c. GENERAL — phiếu ghi mới [verify JSON]
```json
{"type":"GENERAL","data":[{"type":"CUSTOM","custom_data":[{"target_type":"NEW_TICKET","category":{"id":"<ticket_category_id>"}}]}]}
```

---

## 2. Loại nút (`node_type`)

Mọi node có chung khung: `id, is_first_node, description, description_type, color, position{x,y}, node_type, conditions, actions, next_nodes, fail_next_nodes, success_next_nodes, collapse_obj, width, height`.

| `node_type` | Nhóm / nhãn UI | Vai trò | Trạng thái |
|---|---|---|---|
| `CONDITION` | Logic → Điều kiện | Rẽ nhánh theo nhiều *trường hợp*; `next_nodes` của node = nhánh "Bước tiếp theo" (else) | [verify JSON] |
| `DELAY` | Logic → Trì hoãn (Delay) | Chờ khoảng thời gian, chờ đến khung giờ, hoặc chờ đến khi thoả điều kiện | [verify JSON] |
| `RANDOM` | Logic → Random | Chia nhánh ngẫu nhiên theo tỉ lệ (A/B test kịch bản, phân tải) | [enum] |
| `AI_ANALYZE` | Logic → Phân tích thông tin | AI phân loại một đoạn nội dung theo Chủ đề hoặc Ý định đã đào tạo ở mô-đun AI, mỗi ý định một nhánh | [enum] |
| `ACTION` | Tương tác → Hành động | Chuỗi nhiều hành động chạy tuần tự (mục 3) | [verify JSON] |
| `MARKETING` | Tương tác → Marketing | Tạo phiên gửi hàng loạt: SMS, ZNS hoặc ZBS, ZCC (xin quyền gọi Zalo), Email, AutoCall, AI Callbot, Viber Business | [enum] |
| `INFO_DIALOG` / `FORM_DIALOG` / `BUTTON_DIALOG` / `VARIABLE_DIALOG` / `VIEW_DETAIL_DIALOG` / `FEATURE_DIALOG` | Tương tác → Cửa sổ tương tác | Bật cửa sổ trên màn hình nhân viên (mục 4) | INFO, FORM [verify JSON]; còn lại [enum] |
| `ZALO_PERSONAL_MESSAGE`, `ZALO_MESSAGE`, `FACEBOOK_CHAT_MESSAGE`, `FACEBOOK_POST_MESSAGE`, `LIVE_TALK_MESSAGE`, `TELEGRAM_MESSAGE`, `VIBER_MESSAGE`, `TIKTOK_BUSINESS_MESSAGE`, `WHATSAPP_BUSINESS_MESSAGE`, `EMAIL_SMTP_MESSAGE`, `MULTI_CHANNEL_MESSAGE` | Trò chuyện → từng kênh / Gửi tin nhắn chung | Gửi tin hoặc thao tác trên kênh (ví dụ Zalo cá nhân: `REQUEST_FRIEND`) | Zalo cá nhân [verify JSON] |
| `CHAT_GPT`, `CHATX_AI`, `OMI_BOT_AI`, `PRO_AI`, `PARTNER_AI`, `CUSTOMIZE_BOT_AI` | Trò chuyện → ChatGPT / ChatX / AI Chatbot / ProAI / Partner AI | Giao cuộc trò chuyện cho bot AI xử lý | [enum] |
| `COLLECT_INFO` | Khác → Thu thập thông tin | AI bóc Đối tượng hoặc Thực thể (SĐT, email, ngày, thực thể tự đào tạo) từ nội dung, lưu vào biến; tuỳ chọn `FROM_DEFINED_VARIABLE` gán giá trị cố định | [verify JSON] (kiểu giá trị cố định) |
| `DESCRIPTION` | Khác → Ghi chú | Ghi chú trên canvas (URL webhook, cURL mẫu, giải thích) | [verify JSON] |
| `MENU`, `CUSTOM_UI`, `DIRECT_CALL*`, `END_CALL`, `BEGIN` | (luồng gọi / bot) | Dùng trong flow cuộc gọi trực tiếp hoặc giao diện tuỳ biến | [enum] |

### 2.1 CONDITION — nhiều trường hợp [verify JSON]
```json
{"id":"<nodeId>","node_type":"CONDITION","description":"Kiểm tra giờ làm việc",
 "conditions":[
   {"id":"<caseA>","operator_type":"AND","data":[{"type":"COMPARE","compare_conditions":[
      {"operator":"EQUAL","operator_type":"AND","values":[{"start_value":"new"}],"target_type":"CUSTOM_VARIABLE","is_dynamic_field":true,"field_code":"<code10>","field_name":"status"}]}],
    "next_nodes":["<nodeNew>"]},
   {"id":"<caseB>", "...": "...", "next_nodes":["<nodeUpdate>"]}],
 "next_nodes":["<nodeElse>"],
 "collapse_obj":{"<caseA>":false,"<caseB>":false,"NEXT_STEP":false}}
```
**Mở rộng → "Kiểm tra tương tác khách hàng"** [UI đã dựng]: chọn *Tương tác mới* hoặc *Không có tương tác*; loại tương tác (Cuộc gọi, SMS, ZBS, Email Marketing, Ghi chú, Chuyển trạng thái, Log, Phiếu ghi, Đánh giá); người tương tác (bắt buộc: Nhân viên cụ thể, Nhóm, Nhân viên phụ trách KH, Nhân viên liên quan, Hệ thống — chip "Nhân viên phụ trách KH" để trống bị báo thiếu, dùng chip Nhân viên + chọn người); "Thời điểm tương tác gần nhất" N phút/giờ. Cửa sổ tính lùi từ lúc nút chạy. Dùng cho mọi SLA "không gọi / không ghi chú trong N phút": DELAY N → điều kiện này → cảnh báo/thu hồi; không cần biến tự đếm cuộc gọi.

Các mục Mở rộng khác (35): Kiểm tra khách hàng tồn tại, Khách hàng được thêm mới, Khung giờ, Kiểm tra biến liên kết đã tồn tại, trạng thái SMS/ZBS/Email/AutoCall/AI Callbot/ZCC, Khách hàng được cập nhật, Khách hàng/Phiếu ghi thay đổi người phụ trách, Kiểm tra tương tác Phiếu ghi, Nhân viên rời/tham gia hội thoại, Kiểm tra khung giờ làm việc, đánh giá ZBS, Kiểm tra trạng thái nhân viên.

Kiểu `data[].type` trong một trường hợp: `COMPARE` (so sánh), `CALL` (thuộc tính cuộc gọi), `CUSTOM` (`TIME_FRAME`, `NEW_TICKET`…), `TICKET` (trạng thái phiếu), `CONTACT`, `SOCIAL`, `FORM`, `COLLECT_INFO`, `AGENT`, `VOUCHER`, `VOICE_VERIFICATION`, `AI_CALL_TRANSACTION`, `CALL_ASSISTANT`, `AI_ASSISTANT_MULTI_CHANNEL`, `CHAT_INSIGHT`.

`target_type` của `COMPARE`: `CUSTOM_VARIABLE` (biến liên kết), `CALL`, `CONTACT`, `TICKET`, `COLLECT_INFO`, …

Phép toán (UI → API): `=`→`EQUAL`, `!=`→`NOT_EQUAL`, `>`→`GT`, `<`→`LT`, `>=`→`GTE`, `<=`→`LTE`, `IN`/`NOT IN` (dùng `ml_values`), `BETWEEN` (`start_value` + `end_value`), `CONTAIN`, `NOT_CONTAIN`, `START_WITH`, `NOT_START_WITH`, `END_WITH`, `NOT_END_WITH`. "Rỗng" = `NOT_EQUAL` với `values:[{}]` hoặc `[{"start_value":""}]`.

**Khung giờ làm việc** (`CUSTOM` → `TIME_FRAME`): `working_days` theo thứ `"1"`…`"7"`, mỗi ngày `{"type":"time_frame","time_frames":[{"from":<epoch ms>,"to":<epoch ms>}]}` (chỉ lấy giờ:phút) hoặc `{"type":"not_apply"}`. Trường hợp thoả = **trong giờ**; nhánh "Bước tiếp theo" = **ngoài giờ**.

### 2.2 DELAY [verify JSON]
```json
{"id":"<a>","type":"DELAY","data":{"type":"after","value_string":"10","unit":"second","use_time_slot":false,"days_in_week":null}}
```
Thời gian cụ thể [verify JSON]: `{"type":"DELAY","data":{"type":"specific","value_string":"{{<bien>}}"}}` + `variables:[{"name":"<bien>","type":"CUSTOM",...}]` ở node. Ô UI có mặt nạ `HH:mm dd/MM/yyyy` nhưng nhận gõ tay `{{mã biến}}`, nên mốc chờ lấy được từ webhook hoặc biến tính toán (biến phải đúng định dạng đó).
- 4 tuỳ chọn: **sau khoảng thời gian** (`type:"after"`, giây, phút, giờ, ngày); **thời gian cụ thể** (mốc trong quá khứ thì bỏ qua nút); **khung giờ tiếp tục** (`use_time_slot` + `days_in_week`, ví dụ 08:00–17:30 thứ 2–6 trước khi gọi hoặc gửi ZNS); **hoặc điều kiện đến trước** (`conditions`).
- Lượt chạy đang trì hoãn vẫn chờ kể cả khi flow bị ngưng; trong Lịch sử có thể Tiếp tục hoặc Huỷ hàng loạt.
- **Chờ có điều kiện**: thêm `conditions` (cùng schema CONDITION). Ví dụ: chờ tối đa 30 phút cho đến khi cuộc gọi có `ct_transaction_id` = biến và đã kết thúc:
```json
{"conditions":[{"id":"<c>","operator_type":"AND","data":[
   {"type":"COMPARE","compare_conditions":[{"operator":"EQUAL","values":[{"start_value":"{{<callIdVar>}}"}],"target_type":"CALL","field_code":"ct_transaction_id"}]},
   {"type":"CALL","attributes":[{"field_code":"ct_call_status","values":["answered","noanswered"],"operator_type":"OR"}]}]}],
 "type":"after","value_string":"30","unit":"minute","use_time_slot":false}
```

### 2.3 COLLECT_INFO [verify JSON — kiểu giá trị cố định]
Kiểu AI bóc thực thể (chọn nội dung cần phân tích + Đối tượng hoặc Thực thể) chưa có JSON mẫu. Kiểu gán cố định, dùng làm giá trị mặc định khi tra cứu không ra:
```json
{"type":"COLLECT_INFO","data":{"content":"Khách hàng mới","variables":[
  {"variable_code":"<code10>","variable_name":"Tên khách","variable_value":"Khách hàng mới","option":"FROM_DEFINED_VARIABLE"}]}}
```

### 2.4 DESCRIPTION [verify JSON]
`{"node_type":"DESCRIPTION","description":"<text, URL webhook, cURL mẫu>","description_type":"TEXT","color":"#56CC6E"}` — không nối cạnh.

### 2.5 ZALO_PERSONAL_MESSAGE → REQUEST_FRIEND [verify JSON]
`{"type":"REQUEST_FRIEND","data":{"message_type":"REQUEST_FRIEND","message":"<lời mời kết bạn>","target":"","quick_reply":[]}}`

### 2.6 MARKETING → AUTOCALL (Gọi tự động, đọc TTS) [verify JSON]
```json
{"node_type":"MARKETING","actions":[{"id":"<a>","type":"AUTOCALL","data":{"name":"<tên phiên>",
  "autocall_detail":{"phone_number":"<đầu số>","public_number_of_tenant_id":"<id đầu số>","num_per_call":10,"distance_per_call":30,
    "num_retry":0,"distance_retry":0,"timeSlots":[],"ringTimeoutSeconds":30,"allocation_type":"fixed",
    "templateDialplans":[{"target":"Nội dung có {{<mã biến>}}","target_type":"Text_variable","voice":"banmai","speed":0}]},
  "sending_option":{"contact":false,"other":true,"phone_numbers":["{{<mã biến SĐT>}}"],"send_to_agent_contact":false,"agent_contact_ids":null}}}]}
```
- **Đầu số** liệt kê cả hotline lẫn **đầu số Zalo** (logo Zalo, mã ~19 số): chọn đầu số Zalo = gọi qua Zalo OA (ZCC), người nhận phải đã đồng ý yêu cầu gọi (Marketing → "Yêu cầu cuộc gọi ZCC": đồng ý trong 24h, gọi được 30 ngày).
- Thành phần cuộc gọi: Lời chào, **Robot đọc** (TTS, chèn biến; nút "Biến liên kết (ký tự)" đọc từng ký tự, "(chữ)" đọc thành từ), AI Callbot, Tương tác nhấn phím, Nhóm nội bộ.
- Người nhận: Khách hàng (cần khách trong luồng) / **Số điện thoại tuỳ chỉnh** (biến) / nhân viên. Tuỳ chọn gọi lại khi không nghe máy, phân bổ N cuộc mỗi 30s.

---

## 3. Hành động trong nút ACTION (`actions[].type`)

Ngăn "Hành động" trên UI có 22 mục (nhãn và mô tả chính thức):

| Mã | Nhãn UI | Mô tả chính thức | Trạng thái |
|---|---|---|---|
| `ADD_NEW_CONTACT` | Thêm khách hàng | Gán cho nhân viên cụ thể hoặc cấu hình Phân Sale. SĐT đã có → `CONTACT_EXIST`, không tạo trùng | [UI đã dựng]; runtime verify (mục 6, dòng 329-334), editor một phần |
| `UPDATE_INFO_CONTACT` | Cập nhật khách hàng | Cập nhật thuộc tính khách hàng nếu đã tồn tại (phụ trách + ghi chú log, trạng thái pipeline + ghi chú…; chỉ đổi đúng thuộc tính đã khai báo). Giá trị trùng hiện tại → `NO_CHANGE` | [UI đã dựng]; runtime verify (mục 6, dòng 329-334), editor một phần |
| `ADD_TICKET` | Tạo phiếu ghi | Dùng thuộc tính từ biểu mẫu hoặc tự định nghĩa | [verify JSON] |
| `UPDATE_INFO_TICKET` | Cập nhật phiếu ghi | Cập nhật thuộc tính phiếu ghi đã tồn tại (lưu thành các `ASSIGN_TICKET_*`) | [verify JSON] |
| `PUSH_NOTIFICATION` | Tạo thông báo | Gửi thông báo đẩy đến nhân viên hoặc nhóm | [verify JSON] |
| `PUSH_REMINDER` | Tạo nhắc nhở | Tạo lời nhắc cho nhân viên hoặc nhóm | [enum] |
| `SEND_DATA_TO_FORM` | Trả kết quả qua Biểu mẫu | Trả thông tin sau khi khách hoàn thành hoặc sửa biểu mẫu | [enum] |
| `SEND_RESPONSE_WEBHOOK_API` | Trả kết quả qua API | Trả thông tin sau khi bên thứ 3 gọi API (trả dữ liệu động cho caller) | [enum] |
| `CREATE_CUSTOM_VARIABLE` | Biến liên kết tùy chỉnh | Khai báo biến và quy định giá trị: API, ChatGPT, tính toán, ngẫu nhiên, ảnh thư mời | [verify JSON] |
| `GET_RELATED` | Gán đối tượng liên quan | Đưa đối tượng liên quan (phiếu, cuộc gọi, khách, nhân viên, hội thoại…) vào luồng | [verify JSON] |
| `UPLOAD_GOOGLE_SHEET` | Google Sheet | Ghi bảng tính với tài khoản Google đã liên kết | [enum] |
| `UPDATE_CONVERSATION` | Cập nhật cuộc trò chuyện | Cập nhật thuộc tính hội thoại đi qua flow | [enum] |
| `UPDATE_CALL_TRANSACTION` | Cập nhật lịch sử cuộc gọi | Cập nhật thuộc tính cuộc gọi đi qua flow | [enum] |
| `UPDATE_INFO_EMPLOYEE` | Cập nhật nhân viên | Cập nhật thuộc tính nhân viên | [enum] |
| `UPDATE_CUSTOM_DIALOG` | Cập nhật cửa sổ tương tác | Cập nhật thuộc tính ở Cửa sổ thông tin, Cửa sổ biểu mẫu | [enum] |
| `OMI_BOT_EVALUATION` | Cập nhật đánh giá AI Chatbot | Ghi đánh giá chất lượng AI Chatbot | [enum] |
| `SEND_WEBHOOK` | API | Gửi thông tin cho đối tác theo phương thức tự định nghĩa | [verify JSON] |
| `ADD_CLASSIFY` | Phân loại | Đánh dấu, phân loại lịch sử chiến dịch để báo cáo | [enum] |
| `TRANSFER_CALL` | Chuyển tiếp cuộc gọi | Chuyển đến nhân viên, nhóm nội bộ, nhóm bên ngoài | [enum] |
| `START_OTHER_CAMPAIGN` | Gọi đến kịch bản khác | Kích hoạt flow khác; flow đích phải là loại *phụ thuộc* | [enum] |
| `ORDER_*_ACTION` (Haravan, KiotViet, Sapo, Shopify, WooCommerce, POS Bird, TPos), `PANCAKEPOS_ACTION`, `UPDATE_LARK_BASE`, `CREATE_RECORD_LARK_BASE` | Cập nhật đối tác | Cập nhật đơn hàng, khách hàng ở đối tác | [enum] |
| `HOLDING_CALL` | Giữ cuộc gọi | Tạm giữ cuộc gọi để chờ điều kiện, hành động hoặc thông tin bên thứ 3 | [enum] |

Mã chi tiết hơn (lưu bên trong khi chọn trường trong "Cập nhật …"): `ASSIGN_TICKET_TYPE/STATUS/PRIORITY/DUE_DATE/NAME/DESCRIPTION/TAG/REPORTER/ASSIGNEE/ASSIGNEE_ALLOCATION/PIN_OBJECT/ATTRIBUTE_STRUCTURE/NOTIFY_*`, `ADD_TICKET_NOTE`, `ADD_TICKET_EVALUATION`, `ASSIGN_TAG`, `REMOVE_TAG`, `ASSIGN_ATTRIBUTE_STRUCTURE`, `REMOVE_ATTRIBUTE_STRUCTURE`, `ASSIGN_GROUP`, `ASSIGN_BUSINESS`, `ASSIGN_SALE_ALLOCATION`, `ASSIGN_USER_OWNER_ID/ALLOCATION`, `ASSIGN_RELATED_EMPLOYEE`, `ADD_CONTACT_NOTE`, `ADD_CONTACT_EVALUATION`, `ASSIGN_CALL_TRANSACTION_TAG/CALL_PURPOSE/ASSGNEE`, `ADD_CALL_TRANSACTION_NOTE`, `ASSIGN_CONVERSATION_TAG/MEMBER/ATTRIBUTE_STRUCTURE`, `ADD_CONVERSATION_NOTE`, `UPDATE_SOCIAL_CHATBOT_STATUS`, `UPDATE_SOCIAL_IS_SOLVED`, `BLOCK_CONVERSATION`, `LINK_CONTACT_CONVERSATION`, `AGENT_ASSIGN_*`, `UPDATE_VOUCHER_*`, `ASSIGN_VOUCHER_LINK_*`, `ACCEPT/REJECT_REQUEST_JOIN_GROUP(_ZLP)`, `ACTION_MINI_APP`, `ASSIGN_CUSTOM_DIALOG`, `REMOVE_CUSTOM_DIALOG`, `RE_DISTRIBUTE`.

### 3.1 ADD_TICKET [verify JSON]
```json
{"type":"ADD_TICKET","data":{
  "ticket_detail":{"name":"ĐĂNG KÝ MỚI - {{<tenVar>}} - {{<sdtVar>}}",
    "ticket_category_id":"<categoryId>","priority":"from_topic","tags":["<tagId>"],
    "description":"<HTML được phép>","is_not_draft":true,"source":"crud",
    "assignee_config":{"sale_allocation_type":"allocate_according_to_configuration","sale_allocation_ids":["<allocId>"],
       "priority_option":{"agent_join_conv":true,"agent_of_call":true},"assign_criteria":{}}},
  "created_by":{"option":"SYSTEM"}}}
```
- `created_by.option`: `SYSTEM` hoặc `CAMPAIGN_CALLBOT_CREATOR` (người tạo = người phụ trách chiến dịch callbot).
- `priority_option`: ưu tiên nhân viên đã nghe cuộc gọi hoặc đang ở hội thoại, rồi mới đến cấu hình phân bổ.
- Phiếu vừa tạo trở thành **đối tượng phiếu ghi** của luồng: các hành động `ASSIGN_TICKET_*` sau đó áp lên phiếu này.

### 3.2 Cập nhật phiếu ghi (`ASSIGN_TICKET_*`) [verify JSON]
```json
{"type":"ASSIGN_TICKET_REPORTER","data":{"fix_attribute":{"ids":["<agentContactId>"]},"update_types":[{"field_code":"ticket_reporter","field_type":"single_text","type":"INSERT"}]}}
{"type":"ASSIGN_TICKET_PIN_OBJECT","data":{"fix_attribute":{"pin_info":[{"action":"add","ref_type":"call_transaction","ref_id":"{{ct_transaction_id}}"}],"pin_all":{"call_transaction":true}}}}
{"type":"ASSIGN_TICKET_TYPE","data":{"fix_attribute":{"ticket_category_id":"<categoryId>","current_type":2}}}
{"type":"ASSIGN_TICKET_DESCRIPTION","data":{"fix_attribute":{"description":" {{ca_ai_assistant}} "},
  "update_types":[{"field_code":"ticket_description","field_type":"multi_text","type":"INSERT","position":"END"}]}}
{"type":"ASSIGN_TICKET_ATTRIBUTE_STRUCTURE","data":{"attribute_structures":[{"field_code":"<attr>","field_type":"single_text","value":[{"display_value":"{{<var>}}"}]}],
  "update_types":[{"field_code":"<attr>","field_type":"single_text","type":"OVERWRITE"}]}}
```
`update_types[].type`: `INSERT` (chèn thêm), `OVERWRITE` (ghi đè), gỡ giá trị (nhóm "Gỡ giá trị" trên UI). `current_type` của `ASSIGN_TICKET_TYPE` chọn trạng thái trong bộ trạng thái của danh mục (theo thứ tự).

### 3.3 PUSH_NOTIFICATION [verify JSON]
```json
{"type":"PUSH_NOTIFICATION","data":{"title":"CÓ LỖI VỚI LỊCH HẸN CỦA {{<tenVar>}}","content":"<HTML>",
  "send_to_agent_contact":true,"agent_contact_ids":["<agentContactId>"],"enable_platforms":["web"]}}
```

### 3.4 SEND_WEBHOOK (gọi API ra ngoài) [verify JSON]
```json
{"type":"SEND_WEBHOOK","data":{"url":"https://<he-thong-ngoai>/api/<tao_ban_ghi>","method":"POST",
  "headers":[{"id":"<id>","key":"Content-Type","value":"application/json"}],
  "param_type":"json","body_type":"raw",
  "body_json":"{\n  \"fullname\": \"{{<tenVar>}}\",\n  \"phonenumber\": \"{{<sdtVar>}}\"\n}"}}
```
Chỉ **gửi** dữ liệu. Muốn **đọc kết quả trả về vào biến** thì dùng `CREATE_CUSTOM_VARIABLE` kiểu API (3.5).

### 3.5 CREATE_CUSTOM_VARIABLE — 5 kiểu
| UI (`typeVar`) | `data.type` lưu | Dùng để |
|---|---|---|
| `api` | `API_V2` | Gọi API ngoài và bóc kết quả vào biến (tra cứu khách hàng, hồ sơ, đơn hàng, lịch hẹn…) [verify JSON] |
| `gpt` | `CHAT_GPT` | Cho mô hình ngôn ngữ phân loại, tóm tắt hoặc trích xuất từ văn bản; kết quả là một biến [verify JSON] |
| `math` | `CALCULATION` | Tính toán từ biến (cộng ngày, điểm, tiền) [enum] |
| `random` | `RANDOM` | Sinh giá trị ngẫu nhiên (mã, nội dung gợi ý) [enum] |
| `invitation` | `COMBINE_IMAGE` | Ghép 2 ảnh thành ảnh thư mời, dùng như URL [enum] |

API_V2 [verify JSON]:
```json
{"type":"CREATE_CUSTOM_VARIABLE","data":{"type":"API_V2","config":{
  "url":"https://<he-thong-ngoai>/api/<tra_cuu_khach>","method":"POST","time_out":10,
  "headers":[{"id":"<id>","key":"Content-Type","value":"application/json"}],
  "variables":[{"id":"<id>","key":"phoneNumber","value":"{{ct_phone_number}}","type":"text"}],
  "multi_variables":[
    {"field_code":"<code10>","field_name":"Mã khách","whole_response":false,"shorthand_query":"data|1.ma_khach",
     "query":[{"type":"array","key":"data","pos":1},{"key":"ma_khach","filter":"="}]},
    {"field_code":"<code10>","field_name":"Toàn bộ kết quả","whole_response":true,"shorthand_query":"ten_khach","query":[{"key":"ten_khach","filter":"="}]}],
  "param_type":"array","body_type":"raw"}}}
```
- GET: tham số đặt thẳng vào URL (`...?phoneNumber={{<sdtVar>}}`); POST: `variables` là cặp key, value của body (`param_type:"array"`), hoặc `param_type:"json"` + `body_json`.
- `shorthand_query` `data|1.ten` = phần tử thứ nhất của mảng `data`, lấy trường `ten`. `whole_response:true` = lấy cả response.

CHAT_GPT [verify JSON]:
```json
{"type":"CREATE_CUSTOM_VARIABLE","data":{"type":"CHAT_GPT","config_variables":[{"type":"CHAT_GPT","config":{"multi_variables":[
  {"field_code":"<code10>","field_name":"intent","chat_gpt_model":"gpt-4o-mini","llm_config":{},
   "content":"Bạn là chuyên gia phân loại ý định...\nTÓM TẮT: {{ca_summarize}}\n...Trả về DUY NHẤT mã ý định."}]}}]}}
```
Mô hình chọn được: `gpt-3.5-turbo`, `gpt-4`, `gpt-4o-mini`.

- Tab UI (10/2026): **API · Random · Phép toán · Thư mời · LLM** (LLM = `CHAT_GPT`). **Phép toán chỉ + - * / trên số**, không cộng trừ ngày giờ.
- **Mỗi nút ACTION chỉ chứa một hành động "Biến liên kết tuỳ chỉnh"** (danh sách "Thêm hành động" ẩn mục này khi đã có): cần 2 biến tính toán → 2 nút.
- **Tính mốc giờ** (ví dụ ETA − 10 phút cho Trì hoãn "thời gian cụ thể"): LLM với `{{current_date_time}}` (HH:mm dd/MM/yyyy) + biến giờ, prompt bắt trả DUY NHẤT chuỗi `HH:mm dd/MM/yyyy`. Biến hệ thống nhóm *Khác*: `{{current_date}}`, `{{current_date_time}}`, `{{current_day_of_week}}`, `{{current_time}}`.

### 3.6 GET_RELATED (Gán đối tượng liên quan) [verify JSON]
```json
{"type":"GET_RELATED","data":{"options":["CLOSEST_CALL"],"sort_by_created_date":true,
  "condition":{"id":"<c>","type":"GENERAL","operator_type":"AND","data":[{"type":"COMPARE","compare_conditions":[
     {"operator":"EQUAL","operator_type":"AND","values":[{"start_value":"{{<callIdVar>}}"}],"target_type":"CALL","field_code":"ct_transaction_id"}]}],
     "iteration_config":{"time_range":"none"},"allocation":{}},
  "search_with_other_object":true,"sub_options":["CLOSEST_CONTACT"],"sub_sort_by_created_date":true,
  "sub_condition":{"type":"SEARCHOPT","data":[{"type":"COMPARE","compare_conditions":[
     {"operator":"EQUAL","values":[{"start_value":"{{<sdtVar>}}"}],"target_type":"CONTACT","field_code":"phone_number","field_type":"phone"}]}]}}}
```
- `options`: `CLOSEST_TICKET`, `CLOSEST_CONTACT`, `CLOSEST_AGENT`, `CLOSEST_CALL`, `CLOSEST_CONV`, voucher, `CLOSEST_LARK_BASE`, `OTHER` (đối tác). Ưu tiên theo `created_date` hoặc `last_updated_date`.
- Điều kiện tra theo trạng thái phiếu: `{"type":"TICKET","ticket_status":[{"id":"<statusSetId>","indexes":[0],"not_contain":false}]}`.
- `sub_options` + `sub_condition`: tra đối tượng thứ hai (ví dụ phiếu gần nhất **của khách có SĐT = biến**).
- Có nhánh `success_next_nodes` (tìm thấy) và "Bước tiếp theo".

---

## 4. Cửa sổ tương tác (hiện trên màn hình nhân viên)
| Mã | Mô tả chính thức |
|---|---|
| `INFO_DIALOG` | Cửa sổ thông tin: văn bản, hình ảnh, checklist [verify JSON] |
| `FORM_DIALOG` | Hiển thị biểu mẫu; nhân viên hoàn thành thì luồng đi tiếp nhánh `success_action_step` [verify JSON] |
| `BUTTON_DIALOG` | Các nút đã gắn sẵn kịch bản, hành động hoặc marketing, chạy khi nhân viên bấm [enum] |
| `VARIABLE_DIALOG` | Hiển thị các biến liên kết của luồng [enum] |
| `VIEW_DETAIL_DIALOG` | Tự mở cửa sổ chi tiết đối tượng hoặc thêm mới [enum] |
| `FEATURE_DIALOG` | Mở chi tiết Khách hàng, Phiếu ghi, Đa kênh, Lịch sử cuộc gọi [enum] |

```json
{"type":"FORM_DIALOG","data":{"title":"KHÁCH BẤM PHÍM 1 - PHIẾU ĐĂNG KÝ",
  "sending_option":{"send_to_agent_contact":true,"agent_contact_ids":["<agentContactId>"],"send_to_agent_in_session":true},
  "ui_config":{"bg_color":"#00B1FF","audio":{}},"auto_close":{"unit":"minute","value":5},"dialog_id":"<uuid>",
  "variables":[{"name":"<code10>","type":"CUSTOM"},{"name":"<code10>","type":"COLLECT_INFO"}],
  "attribute_structures":[{"field_code":"<f>","field_name":"Họ và tên","field_type":"single_text","default_value":"{{<tenVar>}}","values":[{"default_value":"{{<tenVar>}}"}]},
                          {"field_code":"<f>","field_name":"Ngày hẹn","field_type":"date"}]}}
```
Giá trị nhân viên nhập vào biểu mẫu thành biến `{{<field_code>}}` dùng ở các nút sau (ví dụ tạo phiếu ghi). `INFO_DIALOG` dùng `info_dialog_data:[{"type":"multiText","text":"<HTML có {{biến}}>"}]`. `send_to_agent_in_session:true` = gửi cho nhân viên đang nghe máy hoặc đang ở hội thoại.

---

## 5. Biến dùng được trong flow
1. **Biến trigger**: `multi_variables` của WEB_HOOK, tham chiếu `{{<field_code>}}`.
2. **Biến liên kết tùy chỉnh**: từ `CREATE_CUSTOM_VARIABLE`, khai báo ở top-level `custom_variables:[{"name","field_code"}]`.
3. **Dữ liệu thu thập** (`COLLECT_INFO` hoặc phần thu thập trong nút gửi tin): AI bóc thực thể từ nội dung hoặc câu trả lời; hoặc gán giá trị cố định (mẫu: tra API không ra tên thì gán "Khách hàng mới", rồi nhập lại nhánh chính). Biến tuỳ chỉnh và dữ liệu thu thập chỉ sống trong flow hiện tại.
4. **Biến hệ thống cuộc gọi**: `{{ct_phone_number}}`, `{{ct_transaction_id}}`, `ct_key_action`, `ct_call_status`, `ct_call_type`, `ct_sip_number`.
5. **AI Assistant**: `{{ca_summarize}}` (tóm tắt cuộc gọi), `{{ca_ai_assistant}}` (kết quả phân tích, hay chèn vào mô tả phiếu).
6. **Đa kênh**: `social_*` (ví dụ `social_phone_number_linked`, `social_customer_name`, `social_zalo_shared_info_phone`…).
7. **Biến từ biểu mẫu trong cửa sổ**: `{{<field_code>}}` của `FORM_DIALOG`.

Top-level `variables` liệt kê mọi biến đã dùng (`{"name":"<code10>","type":"CUSTOM"|"COLLECT_INFO"|...}`). UI báo "N biến liên kết có vấn đề" khi văn bản tham chiếu một mã không còn được khai báo.

---

## 6. Cấu trúc đã kiểm chứng bằng GET sau khi dựng trên editor (10/2026) — trigger theo trạng thái khách, SLA, thu hồi

Cách học nhanh: dựng **một** flow mẫu trên editor (mỗi loại nút một lần), lưu, `GET /omi_v2/campaign/get/{id}`, rồi sinh các flow còn lại bằng script từ chính JSON đó và lưu bằng `save_draft_v2` (multipart `file`; flow mới thì bỏ `_id`, `uuid`, `created_date`, `last_updated_date` — Cần xác nhận: `omi_save.py` chỉ lưu nháp vào flow có `_id`, nên tạo vỏ flow trên UI trước, `api-reference.md` mục Lưu flow). Mỗi flow lưu **hai bản**: `nodes[]` (runtime, snake_case) và `name_mappings[]` (editor, camelCase, nút đầu loại `BEGIN`). Sửa nút phải sửa cả hai, nếu không editor hiển thị "Chưa có dữ liệu".

**Trigger Điều kiện theo trạng thái khách** (node đầu, `kick_off.event:"GENERAL"`; mỗi trường hợp một nhánh, có thể chọn nhiều trạng thái):
```json
{"id":"<case>","type":"GENERAL","operator_type":"AND","data":[{"type":"CONTACT","filter_contacts":[
  {"pos":null,"not_contain":false,"id":"<statusSetId>","index":[{"first_index":2,"second_index":[]},{"first_index":3,"second_index":[]}],"operator_type":"OR"}]}],
 "next_nodes":["<nodeId>"],"execute_for_exist":false,"iteration_config":{"is_limit":false,"number_of_times":0,"time_range":"none","apply_for_branch":false}}
```
`first_index` = số thứ tự trạng thái (bắt đầu từ 1) trong bộ trạng thái (`POST contact-v1-stg…/filter_contacts/get_list` trả `values[].index`, `values[].name`). Nút Điều kiện giữa luồng dùng cùng khối `data` (không có `iteration_config`).

**Điều kiện "Không có tương tác"** (Mở rộng → Kiểm tra tương tác khách hàng), một trường hợp có thể ghép nhiều mục `data` (AND), ví dụ "vẫn đang ở trạng thái X" + "không có tương tác":
```json
{"type":"CUSTOM","custom_data":[{"target_type":"NOT_HAVE_CONTACT_INTERACTIVE",
  "agent_option":{"assignee":true,"related":false,"system":false,"customer":false,"anonymous":false,"agent_ids":[],"agent_groups":[],"internal_groups":[],"agent_emails":[]},
  "time_range":{"value":"718","unit":"minute"},"sources":["note","call"]}]}
```
`sources`: `note`, `call`, `change_status` (bản editor ghi `call_interactive` thay cho `call`). `assignee:true` = nhân viên phụ trách khách. Cửa sổ tính lùi từ lúc nút chạy: để cửa sổ ngắn hơn trì hoãn 1–2 phút để log ghi lúc vào trạng thái không bị tính.

**Delay** (nút `DELAY`): `actions:[{"id":"<id>","type":"DELAY","data":{"type":"after","value_string":"12","unit":"hour","use_time_slot":false,"days_in_week":null}}]`, `unit`: `minute|hour|day`.

**Hành động khách hàng** (nút `ACTION`, runtime) [verify JSON — runtime; bản editor một phần]:
- `ADD_CONTACT` `{phone,email,full_name,country_code:"+84"}` (UI "Thêm khách hàng" tách thành 2 hành động) + `ASSIGN_SALE_ALLOCATION` `{ids:["<allocId>"],assign_priority:{agent_of_call:false,agent_join_conv:false},assign_criteria:{use_criteria:false,re_assign_when_match_previous:false,match_all:false,criteria:[]}}`.
- Đổi người phụ trách: `ASSIGN_USER_OWNER_ID` `{ids:["<agentContactId>"],swap_owner_to_related:false,transfer_agent_note:"<ghi chú>",assign_criteria:{...}}`.
- Đổi trạng thái: `ASSIGN_FILTER_CONTACT` `{filter_contacts:[{id:"<statusSetId>",index:1,note:"<ghi chú log>",opportunity_expired:{type:"SPECIFIC",time:""},total_deals_string:"",products:null}]}`.
- Ghi vào Mô tả khách: `ASSIGN_ATTRIBUTE_STRUCTURE` với `field_code:"note"`, `field_type:"multi_text"`, `update_types[0].type:"INSERT"`, `position:"START"`.
- Bản editor tương ứng: `UPDATE_INFO_CONTACT` `{assign:[{name:"assignUserOwner",...},{name:"assignStatus",value:"fc-<statusSetId>",targetType:"filter_contacts",values:{selectOpt:{label,value:<index>},content:"<ghi chú>",...}}]}` và `ADD_NEW_CONTACT` `{type:"ASSIGN_SALE_ALLOCATION",fullName,phone,email,selected:{value:"<allocId>"}}`.

**Cạnh (edges)**: trường hợp của CONDITION/trigger dùng `sourceHandle:<case id>`; nhánh còn lại và nút tuần tự dùng `"2"`; `targetHandle:"1"`; id cạnh `reactflow__edge-<src><handle>-<tgt>1`.

**Bẫy khi dựng bằng giao diện** (đã gặp):
- Trigger thật là thẻ trong màn "Điều kiện bắt đầu OMIFlow này" (nút đầu có tiêu đề "Điều kiện" + mô tả "Kịch bản bắt đầu khi thỏa…"). Bấm nhầm chữ "Điều kiện" bằng JS chỉ thêm một nút Điều kiện giữa luồng và trigger vẫn trống → "Kịch bản không hợp lệ".
- Nút Delay/Điều kiện cuối chuỗi không có nút kế tiếp cũng làm lưu thất bại: kết thúc bằng nút Hành động. Nút mới chưa có mục "Nút kế tiếp" trong ngăn → dùng nút "Thêm nút liền kề" trên thanh công cụ của nút (gọi bằng `.click()` JS được).
- Lưu thất bại thì editor tự mở ngăn của nút đầu tiên bị lỗi.
- Chip chọn trạng thái trong trigger là hộp tick; tick bằng `click` chuột theo `ref` (JS `click` không tick được).
- Hệ thống chặn "Xuất bản" flow (triển khai chạy thật) khi chưa được người dùng xác nhận trực tiếp trong chat.

**LiveTalk → tạo khách từ form trước chat (đã chạy thật 10/2026)**: trigger Điều kiện LiveTalk (`social_channel=widget_v2`, `social_send_by=customer`, `social_content` != "", `social_chatbot_waiting=available`, giới hạn 1 lần/đối tượng) → ACTION `ADD_CONTACT` `{phone:"{{social_lt_phone_number}}", full_name:"{{social_customer_name}}"}` + `ASSIGN_SALE_ALLOCATION` + ghi Mô tả + `ASSIGN_FILTER_CONTACT` → `OMI_BOT_AI`. Một nhánh điều kiện nối được nhiều nút (`next_nodes` mảng + nhiều edge cùng `sourceHandle`) để chạy song song.
