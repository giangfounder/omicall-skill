# OMIFlow — Trigger có JSON đã kiểm chứng (1a–1d)

Tách nguyên văn từ `node-catalog.md` (mục lục và bảng mã ở đó). Số mục giữ như cũ.

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

### 1d. PERIOD — "Trước khi" N ngày so với thuộc tính NGÀY của khách [verify JSON: GET 16/11/2026; flow chưa xuất bản nên giờ kích hoạt thật: Cần xác nhận]
Bản do giao diện lưu (`kick_off` + nút đầu là CONDITION chứa `data[].type = "PERIOD"`):
```json
"kick_off":{"type":null,"event":"PERIOD","id":null,"name":null},
"kick_off_ids":["contact_<field_code trường Ngày>"],
"start_date":null,"end_date":null,
"nodes":[{"is_first_node":true,"node_type":"CONDITION","conditions":[{"id":"<caseId>","type":null,"operator_type":"AND",
  "data":[{"type":"PERIOD","start_type":"BEFORE","start_at":"1","start_unit":"day","fields":["<field_code>"],"field_type":"CONTACT",
           "time_slot":{"from":"08:00","to":"08:30"},
           "apply_days":["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]}],
  "next_nodes":["<nodeId>"]}]}]
```
- Đối tượng (khách) **suy ra từ thuộc tính thời gian**; ngăn PERIOD không có ô chọn đối tượng và **không có điều kiện thuộc tính** → lọc thêm (ví dụ "Trạng thái lịch hẹn = Đã đặt") bằng nút `CONDITION` ngay sau (`target_type:"CONTACT"`, `is_dynamic_field:true`).
- Thuộc tính phải **kiểu Ngày**; trường Ngày tự tạo **có hiện** trong danh sách (đã kiểm 16/11). Trường kiểu chữ chứa "dd/MM/yyyy" không dùng được → `omicall-crm-config` tạo thêm trường Ngày, giữ trường chữ nếu bot cần đọc.
- Giờ là **khung** `time_slot` từ–đến (bật "Đặt khung giờ kích hoạt"), không phải mốc cố định; xuất bản sau khung giờ thì lượt đầu chạy sáng hôm sau.
- `conditions[0].type = null` là bản UI tự lưu; `validate_flow.py` (từ 16/11/2026) lấy loại từ `data[0].type` khi `kick_off.event = "PERIOD"`.
- Form tạo mới mặc định hiệu lực **7 ngày** (vd 16/11→23/11) và nút ✕ khó bấm → sau lần lưu đầu đặt `start_date`/`end_date` = `null` qua `save_draft_v2`.
- Tab "Lặp lại" (Hằng ngày/Tuần/Tháng + "Vào lúc HH:mm") không bắt chọn đối tượng trên UI; lưu và chạy trần: Cần xác nhận. Tab "Sau khi", "Thời gian cụ thể": cùng bố cục, chưa lưu thử.

