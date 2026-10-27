# Callbot NORMAL + Kho tri thức — API Reference

Base: `https://chatbot-gateway-v1-stg.omicrm.com/` — header `Authorization: Bearer <token>` (+ `Content-Type: application/json` cho body JSON). Tham số `?lng=vi&utm_source=web` tuỳ chọn.
Nguồn: bắt request trang Kho tri thức/editor, đọc bundle web, dữ liệu kịch bản thật; các mục ghi "đã kiểm chứng" đã chạy thật trên tenant (2026-10-22). Id trong ví dụ là giả lập.

## 1. Kho tri thức — đọc
| Method | Path | Body / ghi chú |
|---|---|---|
| GET | `callbot/intent/list-by-tenant/{tenant_id}` | toàn bộ intent (`id, code, name, is_system, system_intent_id`) |
| POST | `callbot/intent/search_v2` | `{"page":1,"size":10,"keyword":"","tenantId":"<tenant_id>"}` |
| POST | `callbot/entity-type/search` | `{"page":1,"size":100,"keyword":"","tenantId":"<tenant_id>","isSearch":true,"with_entity_data_type":true}` |
| GET | `callbot/entity-type/list-by-tenant/{tenant_id}` | entity type kèm roles |
| GET | `callbot/entity-type/system/list-all?new_prefix=false` | entity hệ thống (id hệ thống dùng cho editor COLLECT_INFO) |
| GET | `callbot/training/get/intents/entities/{tenant_id}?new_prefix=false` | intent kèm `entities[]` đã gắn trong câu huấn luyện |
| POST | `callbot/training/search_v3?page=<p>&size=100` | `{"keyword":"","tenantId":"<tenant_id>"}` — câu huấn luyện; **server trả tối đa 50/trang**, `total_items` = tổng; đếm theo intent phải duyệt hết trang |
| GET | `callbot/training/get_v2/{training_id}` | chi tiết 1 câu: `intent`, `entities[]` (`start_char`, `end_char`, `content`) |
| GET | `callbot/training/history/search?page=1&size=3` | các lần huấn luyện: `status` (`TRAINING`/`SUCCESS`), `total_trainings`, `created_date`, `last_updated_date` |
| GET | `callbot/training/history/status/{session_id}` | trạng thái 1 lần huấn luyện |

Intent hệ thống thường có (sau `training/reset`): `omi_intent_agree`, `omi_intent_deny`, `omi_intent_disagree_service`, `omi_intent_confirm_right`, `omi_intent_confirm_wrong`, `omi_intent_promise`, `omi_intent_recall`, `omi_intent_repeat`, `omi_intent_question`, `omi_intent_angry`, `omi_intent_ask_fee`, `omi_intent_name`, `omi_intent_phone`, `omi_intent_address`, `omi_intent_number`, `omi_intent_email`, `omi_intent_age`, `omi_intent_good_rating`, `omi_intent_bad_rating`, `khach_can_gap/{nhan_vien_kinh_doanh|ky_thuat_vien|ke_toan|hr}`... Entity hệ thống: `omi_entity_datetime` (id hệ thống `634d6c3042d14f7ec2df05e4`), `omi_entity_number`, `omi_entity_money`, `omi_entity_name`, `omi_entity_phone`, `omi_entity_address`, `omi_entity_email`, `omi_entity_duration`, `omi_entity_age`... Trình biên tập hiển thị mã với tiền tố `ai_` (chỉ hiển thị).

```json
{"id":"<intent_id>","tenant_id":"<tenant_id>","code":"omi_intent_question","name":"Khách đặt câu hỏi","is_system":true,"system_intent_id":"634d6c0142d14f7ec2df0073"}
{"id":"<entity_type_id>","code":"hoi_gia","name":"Hỏi giá","is_system":false,"entity_data_types":["STRING"],"system_entity_type_id":null}
```

## 2. Kho tri thức — ghi
| Method | Path | Ghi chú |
|---|---|---|
| GET | `callbot/training/reset` | **Đã kiểm chứng**: = nút "Đào tạo dữ liệu mẫu của hệ thống" (trang Kho tri thức trống). Nạp 29 intent + 13 entity hệ thống + roles + ~4.800 câu có gắn thực thể, tự huấn luyện (~10 phút). Web gọi tiếp `callbot/model/load-model`. Trên tenant đã có dữ liệu: Cần xác nhận (có thể xoá dữ liệu cũ) — chỉ dùng khi tenant trống và user đồng ý |
| POST | `callbot/training/upload_excel` | **Đã kiểm chứng** (qua UI): multipart field `excel` (.xlsx/.xls/.csv ≤5MB) → `payload.import_training_session_id`. Tạo intent/entity mới theo mã, dùng lại cái trùng mã, tính `start_char/end_char`, rồi **tự huấn luyện lại toàn bộ** |
| GET | `callbot/training/upload_excel/status/{session}` | `{"completed":true,"total":N,"successTotalRecord":N,"errorTotalRecord":0,"errCode":null}` |
| POST | `callbot/training/download_excel_template` | body `{}` → `payload.value.object_info.name` = `/callbot/Import_training_data_template.xlsx`; tải công khai `https://cdn.omicrm.com/callbot/Import_training_data_template.xlsx` |
| GET | `callbot/training/retraining` | huấn luyện lại thủ công |
| POST | `callbot/intent/store_v2` | `{"call_bot_intents":[{"tenant_id":"<tenant_id>","code":"<code>","name":"<tên>","ordering":0}]}` |
| POST | `/callbot/entity-type/store_v2` | `{"entity_types":[{"code":"<code>","name":"<tên>","tenant_id":"<tenant_id>","ordering":0}]}` |
| POST | `callbot/entity-type/role/add` | `{"entity_type_id":"<id>","code":"<role>","name":"<tên>","ordering":0}` |
| POST | `callbot/training/store_v2` | 1 câu: `{"trainings":[{"tenant_id","ordering":0,"content","intent_id","removed_entity_ids":[],"entities":[{"role_id":null,"entity_type_id","tenant_id","start_char","end_char","variable_type":"STRING","content","ordering":0}]}]}` |
| POST | `callbot/{intent,entity-type,training}/delete_v2` | body: Cần xác nhận. Xoá dữ liệu dùng chung — chỉ khi user yêu cầu; thao tác có thể bị chặn quyền |
| POST | `callbot/training/export_excel` | không dùng được qua API (file gửi qua thông báo) |
| — | `callbot/training/intent_entity/clone_system` | chưa rõ khác `reset` — không gọi |

Ưu tiên nhập Excel một lần thay vì `store_v2` từng câu (mỗi thay đổi đều cần huấn luyện lại).

## 3. Kịch bản — endpoint
| Method | Path | Ghi chú |
|---|---|---|
| GET | `callbot/script/list-by-tenant/{tenant_id}` | mọi kịch bản kèm `nodes/org_nodes/connections`, `version`, `is_newest_version` |
| GET | `callbot/script/get/{id}` | chi tiết |
| POST | `callbot/script/add_v2` | multipart field `file` = JSON blob. Mới: không gửi `id/uuid`. Cập nhật: gửi **cả** `id` + `uuid` của bản mới nhất (chỉ `id` → sinh kịch bản trùng). Trả `payload.id` mới, `version` tăng. Server tạo thêm 1 id kế tiếp cùng uuid cho editor |
| POST | `callbot/script/delete` | `{"ids":["<id>"]}` — chỉ khi user đồng ý |

## 4. Kịch bản NORMAL — runtime `nodes`
Top-level: `tenant_id, name, type:"NORMAL", variables, collect_info_variables, classifies:[{"name"}], layouts, nodes, org_nodes, connections, voice, speed, is_interrupt, parse_datetime, collect_authentication_data:"NONE", system_intent_ids:[], system_entity_type_ids:[], custom_variables:[], variables_with_order:[], variable_list:{"contact":[],"ticket":[]}` (+ `id, uuid` khi cập nhật).

Biến top-level: chiến dịch `{"field_name":"<mã>","field_code":"<mã>","type":"","is_dynamic_attribute":true,...}`; thu thập `type:"COLLECT_INFO"`; xưng hô `{"field_name":"Anh/Chị","field_code":"gender1_ai","type":"CONTACT","is_dynamic_attribute":true}`. Biến trong node: `{"field_name":"","field_code":"<mã>","field_value":"","field_type":"","type":"OTHER","is_dynamic_attribute":false}`.

- BEGIN: `{"id":"<b>","node_type":"BEGIN","next_nodes":["<staff đầu>"],"is_collapse":false}`
- STAFF: `{"id","node_type":"STAFF","template_content":"<lời>","return_template_content":"","wrong_response_content":"","customer_response_delay":10000,"variables":[...],"next_nodes":[<id các CONDITION>],"actions":[COLLECT_INFO?],"is_collapse":false,"speed":1}`. STAFF kết thúc: không `next_nodes`. STAFF nối thẳng ACTION (không chờ khách): `next_nodes:["<action>"]` (đã kiểm chứng: báo chuyển máy → TRANSFER).
- COLLECT_INFO trong STAFF: `{"id","type":"COLLECT_INFO","data":{"variables":[{"entity_type_code":"omi_entity_datetime","variable_code":"var_ngay","variable_name":"Ngày hẹn"},{"variable_code":"var_cau","variable_name":"Câu khách nói","option":"ENTIRE_USER_SENTENCE"}]}}`
- CONDITION `INTENT`: `{"id","node_type":"CONDITION","condition_type":"INTENT","intent_code":"<mã>","entity_code":"<mã>?","return_contents":[{"type":"TEXT","content":"<câu>"}],"next_nodes":["<đích>"],"variables":[...],"return_template_contents":[],"is_collapse":false}`
- `CUSTOMER_NOT_RESPONSE` (+ `customer_not_response_delay`), `CUSTOMER_RESPONSE_WRONG`, `CUSTOMER_RESPONSE`: cùng dạng, không `intent_code`.
- `KEYWORD`: `conditions[].data[].compare_conditions[{"ml_values":[[{"start_value":"<từ>","end_value":""}]],"operator":"CONTAIN","operator_type":"OR","is_dynamic_field":true}]` — chạy không cần huấn luyện.
- `FROM_SYSTEM` (node riêng, rẽ theo biến): `{"node_type":"CONDITION","condition_type":"FROM_SYSTEM","next_nodes":["<nhánh còn lại>"],"conditions":[{"id","name","operator_type":"AND","next_nodes":["<đích>"],"data":[{"type":"COMPARE","compare_conditions":[{"target_type":"CUSTOM_COMPARE","field_code":"<id ngẫu nhiên>","content":"{{var_x}}","operator":"EQUAL","values":[{"start_value":"1","end_value":""},{"start_value":"một","end_value":""}],"operator_type":"OR","is_dynamic_field":false,"pos":null}]}],"data_random":null,"allocation":null,"iteration_config":null,"execute_for_exist":false}]}` — operator khác: `GT`, `LTE`, `NOT_EQUAL`...; với biến ngày thu được có biến tính sẵn `{{diff_days_<mã biến>}}`.
- ACTION: `{"id","node_type":"ACTION","actions":[...],"next_nodes":["<tiếp>"]?,"variables":[],"is_collapse":false}`; action:
  - `ADD_CLASSIFY` `{"data":{"ids":["<nhãn>"]}}` (nhãn khai báo top-level `classifies`)
  - `TRANSFER_CALL` `{"data":{"actionType":"Extension","ids":["<agent_id>"],"sip_number":"<máy lẻ>","transfer_collected_info":true,"transfer_customize_info":false}}` (nhóm: `actionType:"Ring_group"`)
  - `PUSH_NOTIFICATION`: runtime `data` như nhánh `PUSH_NOTIFICATION` trong `scripts/build_callflow.py` (`title`, `content`, `agent_contact_ids`, `enable_platforms:["web"]`, các cờ `send_to_*`); bản editor (org) chưa kiểm chứng → GET lại và soát trên editor.
  - `ADD_TICKET`, `ADD_CONTACT` + `ASSIGN_AGENT_CONTACT`, `HOLDING_CALL`: chưa có JSON đã kiểm chứng ở skill nào → dựng trên UI rồi GET lại (Cần xác nhận cấu trúc trước khi sinh bằng script).

### Số lần trả lời/nhắc của nhánh (đã đối chiếu kịch bản thật)
Runtime không có trường lặp: **số câu trong `return_contents` = số lần bot trả lời/nhắc**; dùng hết thì lần sau đi `next_nodes`. Nhánh có câu trả lời **luôn có `next_nodes`** (kịch bản thật không có ngoại lệ). Editor ghi kèm: INTENT có N câu → `"repeat":{"label":["times",{"t":"l","n":N-1}],"value":"N"}`; INTENT không câu → `{"label":"notRepeat","value":"0"}`; NOT_RESPONSE → `{"label":["times",{"t":"l","n":0}],"value":"1"}`; RESPONSE_WRONG → `"repeat":0` (số).

## 5. Kịch bản NORMAL — editor `org_nodes` + `connections`
`scripts/build_callflow.py` sinh toàn bộ mục này; dùng builder thì không cần đọc. Chỉ đọc khi sửa tay hoặc dựng loại chưa có trong builder (`references/node-status.json`).
- org types: `BEGIN`, `STAFF`, `ACTION`, `CONDITION` (chỉ node FROM_SYSTEM riêng), `COLLECT_INFO`. Nhánh INTENT/hệ thống của STAFF **nằm trong** `org_nodes[STAFF].data.conditions[]` (id = id node CONDITION runtime) → số org ít hơn nhiều so với nodes.
- org STAFF: `{"id","type":"STAFF","width":332,"height","position":{"x":"<str>","y":"<str>"},"data":{"type":"STAFF","id","name","content","subContent","typeSay":"text","audio_file":null,"speed":{"label":"speedRead.normal","value":1},"notResponseTime":10000,"responseTime":10000,"count":1,"variables":[{"variable":"<mã>","selected":{}}],"objVariables":{"<mã>":""},"collectionInfo":[...],"conditions":[...],"collapseObj":{"NEXT_STEP":{"isCollapse":false},"<cond id>":{"isCollapsible":true,"isCollapse":false},"CUSTOMER_NOT_RESPONSE":{"isCollapse":false},"CUSTOMER_RESPONSE_WRONG":{"isCollapse":false},"COLLECT_INFO":{"isCollapsible":true,"isCollapse":false}},"pos":{"x","y","h"},"oldIdIem":{},"activeIdx":0,"isCallBot":true,"dataRpNumStep":[]}}`
- Biến xưng hô trong org: `{"variable":"gender1_ai","selected":{"attributeType":"CONTACT","showTooltip":"c_config/ai.genderAiTip","label":[["gender1"]," (?)"],"value":"gender1_ai","desc":"{{gender1_ai}}"}}`, `objVariables.gender1_ai=[["gender1"]," (?)"]`. Editor hiển thị thành thẻ "Anh/Chị".
- `data.conditions[]`:
  - COLLECT_INFO `{"conditionId":"<id>","id":"COLLECT_INFO","type":"COLLECT_INFO"}`
  - INTENT `{"id":"<cond id>","type":"INTENT","intent":{"id":"<intent_id>","value":"<intent_id>","code","label","name","isTenantIntent":true,"isSystem":true,"systemIntentId","tenantId"},"returnContents":[{"type":"text","content"}],"repeat":{...},"entities":[],"keywords":[],"isErrorAudio":false}`; có thực thể thêm `"applyEntity":true,"responseWrongCollectionInfo":{"code","entityCode","id":"<entity_type_id>","value":"<entity_type_id>","label":"<tên>","isTenantEntity":true,"isSystem":false,"desc":"{{<mã>}}"}` (editor hiển thị "Khách đặt câu hỏi, <tên thực thể>")
  - NOT_RESPONSE `{"id":"CUSTOMER_NOT_RESPONSE","type":"CUSTOMER_NOT_RESPONSE","conditionId":"<id runtime>","returnContents":[...],"repeat":{...},"customerNotResponseDelay":10000,"isErrorAudio":false}`
  - RESPONSE_WRONG `{"id":"CUSTOMER_RESPONSE_WRONG","type":"CUSTOMER_RESPONSE_WRONG","conditionId":"<id runtime>","returnContents":[...],"repeat":0,"textSayRespWrong":"","isErrorAudio":false}`
- `collectionInfo[]`: thực thể `{"entityCode":"omi_entity_datetime","variableName","variableCode","label":"Thời gian ngày tháng","value":"<system_entity_type_id>"}`; nguyên câu `{"variableName","variableCode","keyIcon":"communicate","label":"c_config/ai.allCustomersSay","value":"ENTIRE_USER_SENTENCE"}`.
- org COLLECT_INFO: node riêng id `<staff_id>COLLECT_INFO`, `data:{"type":"COLLECT_INFO","collectionInfo":[...],"objVariables":{...},"variables":[],"count":1,"collapseObj":{"NEXT_STEP":{"isCollapse":false}}}`.
- org ACTION: `data:{"type":"ACTION","name","actions":[{"datas":{...},"id","type"}],...}` + `orgDatas:[{"datas","id","type"}]` (ADD_CLASSIFY `datas:{"ids":[nhãn]}`; TRANSFER `datas:{"actionType":"Extension","selected":"<agent_id>","isTransferCollectedInfo":true,...}`, `orgDatas[].datas.selected` = object nhân viên `{"sipNumber","fullName","label":"<ext> - <tên>","contact_id","value":"<agent_id>","email","gender","avatar"}`).
- org CONDITION (FROM_SYSTEM): `data:{"type":"CONDITION","actionType":"CONDITION","name","description","conditions":[{"id","name","operator_type","next_nodes","data":[...]}]}` + `orgDatas:[{"id","operatorType":"AND","datas":[{"isComparison":true,"fieldCode","values","targetType":"CUSTOM_COMPARE","label":"custom","value":"custom","content":"{{var_x}}","operator":"=","operator_type":"OR"}]}]`.
- Connections `{"source","sourceHandle","target","targetHandle":"1","type":"custom","animated":false,"style":{"strokeWidth":3,"stroke":"#1e3150"},"id":"reactflow__edge-<source><handle>-<target>1"}`:
  - BEGIN → bước đầu: handle `"1"`. STAFF nhánh INTENT: handle = id điều kiện. Hệ thống: handle `CUSTOMER_NOT_RESPONSE`/`CUSTOMER_RESPONSE_WRONG` + `"conditionId"`. ACTION/STAFF→ACTION/FROM_SYSTEM còn lại: handle `"2"`. FROM_SYSTEM nhánh: handle = id điều kiện. STAFF → COLLECT_INFO: handle `COLLECT_INFO`, `"animated":true`, + `conditionId`.

## 6. Checklist sau mỗi lần lưu (GET lại)
Tự động: `scripts/verify_callflow.py <bản GET>.json --sent payload.json --context tenant_context.json --mode post --base <bản mới nhất trước khi sửa>.json` (mã C1..C7 dưới đây; X<n> là mục bổ sung: X3 còn placeholder `<...>`, X4 chỉ có một trong id/uuid, X5 số node/dây lệch payload đã gửi). `omi_save.py` tự chạy sau khi lưu nhưng chưa truyền `--context`/`--base` → C4 và version tăng chỉ ra WARN; chạy lại tay đủ tham số trên bản GET đã lưu. Dự phòng khi chỉ kiểm được trong trang: `references/browser-snippets.md` §6.
1. **C1** `next_nodes` mọi node trỏ tới node tồn tại; mỗi CONDITION của STAFF có trong `org_nodes[STAFF].data.conditions`.
2. **C2** Nhánh có `return_contents` đều có `next_nodes`; hỏi đáp/lặp lại/phản hồi sai trỏ bước báo chuyển (script in WARN, soát theo spec); repeat editor khớp số câu.
3. **C3** Mỗi STAFF chờ khách có NOT_RESPONSE + RESPONSE_WRONG; STAFF kết thúc không `next_nodes`.
4. **C4** Mọi `intent_code`/`entity_code` có trong Kho tri thức; huấn luyện mới nhất `SUCCESS`.
5. **C5** TRANSFER có `ids` nhân viên khác rỗng; `transfer_collected_info:true`.
6. **C6** Biến `{{...}}` khai báo ở node và top-level; không còn "anh/chị" trong lời (dùng `{{gender1_ai}}`).
7. **C7** `connections` khớp `next_nodes`; `version` tăng, `is_newest_version:true`.
