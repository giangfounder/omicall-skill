# OMIFlow — Trigger có JSON đã kiểm chứng (1a–1c)

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
