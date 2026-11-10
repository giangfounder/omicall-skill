# OMIFlow — Nút điều kiện, trì hoãn, thu thập, mô tả, Zalo cá nhân, gọi tự động (2.1–2.6)

Tách nguyên văn từ `node-catalog.md` (mục lục và bảng mã ở đó). Số mục giữ như cũ.

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

**Khung giờ làm việc** (`CUSTOM` → `TIME_FRAME`): `working_days` theo thứ `"1"`…`"7"`, mỗi ngày `{"type":"time_frame","time_frames":[{"from":<epoch ms>,"to":<epoch ms>}]}` (chỉ lấy giờ:phút) hoặc `{"type":"not_apply"}`. Trường hợp thoả = **trong giờ**; nhánh "Bước tiếp theo" = **ngoài giờ**. `"1"` = Chủ nhật, `"2"`…`"7"` = T2…T7 (✔ GET 10/2026, giờ lưu theo epoch của ngày tạo, múi +7). **Bắt buộc đi kèm ít nhất 1 điều kiện khác trong cùng trường hợp** — thiếu thì UI báo "Điều kiện Khung giờ chỉ hoạt động khi sử dụng chung ít nhất 1 điều kiện khác" và lặng lẽ xoá dữ liệu trường hợp khi đóng ngăn (✔ UI 10/2026); thêm điều kiện luôn đúng, ví dụ `SOCIAL` `social_channel` = `widget_v2` (Kênh = LiveTalk). Mục "Kiểm tra khung giờ làm việc" thì cần Ca làm việc khai sẵn (tenant chưa có ca → "Không có dữ liệu").
Ví dụ GET thật (trường hợp trong giờ T2–T6 07:00–16:30, kênh LiveTalk):
```json
{"id":"<case>","operator_type":"AND","data":[
  {"type":"CUSTOM","custom_data":[{"target_type":"TIME_FRAME","working_days":{
     "1":{"type":"not_apply"},"2":{"type":"time_frame","time_frames":[{"from":<epoch 07:00>,"to":<epoch 16:30>}]},
     "3":{...},"4":{...},"5":{...},"6":{...},"7":{"type":"not_apply"}}}]},
  {"type":"SOCIAL","attributes":[{"field_code":"social_channel","values":["widget_v2"],"operator_type":"OR","not_contain":false,"is_dynamic_field":false}]}],
 "next_nodes":["<nút trong giờ>"]}
```
**Chuyển hội thoại cho nhân viên** (Hành động → Cập nhật cuộc trò chuyện → "Phân bổ cuộc trò chuyện"; tuỳ chọn Phân bổ mới / Phân bổ thêm / Huỷ phân bổ, Nhóm tiếp nhận) → `{"type":"RE_DISTRIBUTE","data":{"ids":["<id nhóm tiếp nhận>"],"redistribute_option":{"redistribute_type":"new","skip_exist":false,"session_criterias":[]}}}` (✔ GET 10/2026). Cùng danh sách còn "Trạng thái Chatbot", "Chặn / Bỏ chặn", "Nhân viên phụ trách", Tag…
**Gửi tin LiveTalk** (`LIVE_TALK_MESSAGE`, người nhận mặc định "Cuộc trò chuyện liên quan"): `actions:[{"type":"TEXT","data":{"message_type":"TEXT","message":"<nội dung>","payload":[],"quick_reply":[]}}]` (✔ GET 10/2026).
**Nút `OMI_BOT_AI` → nhánh "BOT chủ động kết thúc"** (bot đi tới nút Kết thúc trò chuyện): `next_nodes` của nút + edge `sourceHandle` = id của trường hợp kết thúc (trùng `ai_analyze.customer_not_response.id`), không phải `"2"` (✔ UI 10/2026). `validate_flow.py` X1 nhận nhánh này khi thấy `customer_not_response.id` trong node; không thấy thì chỉ WARN "Cần xác nhận". Vị trí khoá `ai_analyze` trong node: chưa có JSON mẫu.

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

Bổ sung đã kiểm chứng bằng GET (✔ UI 11/2026, flow trigger API):
- **Một nút làm được cả hai việc**: ngăn "Nội dung" của nút Zalo cá nhân nhận nhiều mục (Thêm nội dung → Văn bản, Hình ảnh, …, Gửi lời mời kết bạn, mời/xoá khỏi nhóm…), chạy tuần tự, cách nhau "Thời gian chờ giữa các tin" (mặc định 0,5 giây). Không cần nút Zalo thứ hai hay DELAY để gửi lời mời rồi gửi tin.
- Tin văn bản runtime: `{"type":"TEXT","data":{"message_type":"TEXT","message":"<nội dung, xuống dòng \n>","payload":[],"zlp_urgency":0,"quick_reply":[]}}` (state editor gọi là `REPLY`, GET lưu `TEXT`).
- **Người nhận** lưu ở cấp nút: `prioriy_conv_id:"{{<mã biến SĐT>}}"` (Người nhận → Tùy chỉnh), `prioriy_channel_id:"-1"` = "Gửi từ: Tài khoản Zalo cá nhân trong luồng kịch bản"; mọi mã biến dùng trong nút liệt kê ở `variables[]` của nút.
- "Gửi từ: Tài khoản Zalo cá nhân tùy chỉnh" bắt buộc ô "Số điện thoại tài khoản Zalo cá nhân dùng để gửi"; đóng ngăn khi ô trống → báo lỗi và **mất toàn bộ cấu hình nút**. Tenant chưa kết nối Zalo cá nhân vẫn lưu/xuất bản được nếu để "trong luồng kịch bản"; flow trigger API không có hội thoại nên trước khi chạy thật nên đổi sang "tùy chỉnh" + SĐT tài khoản (cách chạy khi để "trong luồng": Cần xác nhận).
- Ô lời mời kết bạn không có `maxlength` trên UI; giới hạn ký tự phía Zalo: Cần xác nhận.
- `name_mappings`: nút `{"id","type":"ZALO_PERSONAL_MESSAGE","intentsOptNode":[],"collectionInfo":[]}`; trigger API `{"id","type":"BEGIN","isFirstNode":true,"actionType":"WEB_HOOK"}`.
- Bẫy UI: ngăn mở từ "Bước tiếp theo" của nút khác có danh sách "Biến liên kết tuỳ chỉnh" rỗng → gõ tay `{{mã}}` hoặc mở nút từ canvas. Lần "Lưu lại" đầu có thể làm editor chỉ còn "Xuất bản" (khi nào: Cần xác nhận) → `api-reference.md` mục *Vỏ flow tối thiểu và lần "Lưu lại" đầu*. URL webhook → `api-reference.md` mục *Ba loại id và URL webhook* (ghi chú chứa URL cập nhật theo GET cuối). Nút ✕ đóng ngăn nằm đè logo trang chủ: bấm 2 lần là rời trang, mất flow chưa lưu. Agent bấm "Xuất bản" hoặc "Cập nhật" trong hộp URL có thể bị hệ thống phân quyền chặn → để user tự bấm.

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
