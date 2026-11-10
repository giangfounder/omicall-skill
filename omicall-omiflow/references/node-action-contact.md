# OMIFlow — Hành động cập nhật phiếu, thông báo, webhook, biến, đối tượng liên quan (3.2–3.6) và cửa sổ tương tác (mục 4)

Tách nguyên văn từ `node-catalog.md` (mục lục và bảng mã ở đó). Số mục giữ như cũ.

Mục lục: 3.2 Cập nhật phiếu ghi · 3.3 PUSH_NOTIFICATION · 3.4 SEND_WEBHOOK · 3.5 CREATE_CUSTOM_VARIABLE · 3.6 GET_RELATED · 4 Cửa sổ tương tác. Định vị: `grep -n "^##" node-action-contact.md`.

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
