# OMiCall Callbot Gen AI — API Reference & Schemas

## Base URL & Auth
`https://chatbot-gateway-v1-stg.omicrm.com` (frontend map `chatBot`). Mọi endpoint cần `Authorization: Bearer <accessToken>`. Token: `~/.omicall-mcp/session.json`→`accessToken` hoặc cookie theo `credentials.md`.

> Verify token/cookie per tenant trong `references/credentials.md`.

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/callbot/script/list-by-tenant/{tenant_id}` | List scripts |
| GET | `/callbot/script/get/{id}` | Script detail (nguồn schema chuẩn) |
| GET | `/callbot/script/get_by_uuid/{uuid}` | Detail by uuid |
| POST | `/callbot/script/add_v2` | Create/update — **multipart** field `file` |
| POST | `/callbot/script/save_draft_v2` | Save draft |
| POST | `/callbot/script/delete` | Delete |
| GET | `/callbot/script/template/topics/get?language=vi` | Template topics |

## Save (add_v2) — multipart
```python
import requests, json
tok = json.load(open('<session>'))['accessToken']  # hoặc cookie theo SKILL.md
r = requests.post(base+'/callbot/script/add_v2',
  headers={'Authorization':'Bearer '+tok},
  files={'file':('blob', json.dumps(payload, ensure_ascii=False).encode('utf-8'), 'application/json')}, timeout=120)
new_id = r.json()['payload']['id']  # id MỚI + version tăng mỗi lần lưu
```
Không dùng curl (multipart curl → `invalid_param`). Response payload = script đã lưu.

## Script object (top-level)
```json
{"id","uuid","tenant_id","name",
 "variables":[{"field_name","field_code","field_value":"","field_type":"","type":"COLLECT_INFO","is_dynamic_attribute":true}],
 "collect_info_variables":[{"variable_code","variable_name"}],
 "connections","nodes","org_nodes","is_draft":false,"created_date","last_updated_date",
 "created_by":{"id","name","contact_id"},"public_key","last_updated_by":{"id","name","contact_id"},"is_deleted":false,
 "collect_authentication_data":"NONE","system_intent_ids":[],"system_entity_type_ids":[],
 "version","is_newest_version":true,"layouts":[],"is_publish":true,"custom_variables":[],"classifies":[{"name":""}],
 "variables_with_order":[],"variable_list":{"contact":[],"ticket":[]},
 "speed":1.0,"voice":"northern_female_ngocanh","type":"AI_AGENT","model":"gpt-4o-mini",
 "is_interrupt":false,"parse_datetime":false,
 "ai_assistant_config":{"features":[{"type":"SUMMARY","items":[{"prompt":"","auto_assign":true}]}],"enable":false}}
```

## Node schemas — DUAL-SCHEMA (mỗi node lưu CẢ runtime `nodes` LẪN editor `org_nodes`)

### BEGIN (runtime `nodes`)
```json
{"id":"<node_id>","node_type":"BEGIN","is_collapse":false,
 "ai_agent_config":{"instruction":"<System Prompt>","start_call_instruction":"<câu mở đầu>",
  "knowledge":{"files":[],"apis":[]},"collect_variables":[{collect_variable}],
  "ai_analyze":{"content":null,"context":null,"conditions":[<intents>...,{id:"bot_can_not_answer",...},{id:"customer_not_response",...}],
    "collect_variables":null,"collect_position":null,"customer_response_wrong":null,
    "customer_not_response":{"waiting_time":10,"next_node":null,"id":"customer_not_response","repeat_contents":null,"prompt_end_conv":"","action_steps":null},
    "customer_has_response":null,
    "bot_can_not_answer":{"waiting_time":null,"next_node":null,"id":null,"repeat_contents":null,"prompt_end_conv":null,"action_steps":null},
    ...null/default}}}
```
org BEGIN: `data:{actionType:"CONDITION",startCallInstruction,personality:<instruction>,selectedTraining:[],collectData:[<entry>],type:"BEGIN",conditions:[schema EDITOR],collapseObj:{NEXT_STEP:{isCollapse:false},<mỗi intent>:{isCollapsible:true,isCollapse:false},customer_not_response:{isCollapse:false},bot_can_not_answer:{isCollapse:false}},vision:{enable:false},hearing:{enable:false},queryData:[],collectVariables:{}}`; `width:332, height:535–700`.

### Intent — (A) Runtime `nodes[].ai_agent_config.ai_analyze.conditions[]`
```json
{"id":"<handle>","type":"CUSTOM_INTENT","intent_code":null,"intent_name":null,"name":"<label>","keywords":null,
 "operator":null,"compare_operator":null,"percent":40,"next_node":null,
 "repeat_contents":null,"repeat_time":null,"apply_targets":null,"attachment":null,"limit":null,"limit_ai_config":null,
 "data":[{"id":"<data_id>","type":"OMI_BOT_INTENT","content":"<câu khách nói chính xác>"}],
 "operator_type":"AND","action_steps":null}
```

### Intent — (B) Editor `org_nodes[<BEGIN>].data.conditions[]`
```json
{"actionStep":[],"webhookId":"<tenant_id>-UfofQwd98lNSP14tnPCO","selectedIntent":null,"personality":"",
 "data":[{"isCustomComp":true,"targetType":"OMI_BOT_INTENT","id":"<data_id>","content":"<câu khách nói>","selected":false,"chosen":false}],
 "name":"<label>","id":"<handle>","operatorType":"AND","type":"CUSTOM_INTENT","webhookParam":{"bot_id":"","conv_id":""}}
```
- `data[].type` (runtime) / `isCustomComp:true`+`targetType` (editor) — thiếu → editor hiện ô "Nhận diện ý định" TRỐNG. `content` = câu khách hiển thị (đừng dựa `name`).
- CUSTOM_INTENT đặt TRƯỚC 2 system; min **5 intent**; intent nối node hành động/kết thúc → `next_node` + connection + entry `collapseObj`. Intent được xử lý trong BEGIN dùng `next_node:null` và không có connection. Không bao giờ dùng id BEGIN làm `next_node`.

### System conditions (luôn ở cuối)
Runtime: `{"data":[],"id":"bot_can_not_answer","type":"bot_can_not_answer",...null}` và `{"id":"customer_not_response","type":"customer_not_response",...,"operator_type":null,"action_steps":null}` (full: intent_code/intent_name/name/keywords/operator/compare_operator/percent/next_node/repeat_contents/repeat_time/apply_targets/attachment/limit/limit_ai_config/operator_type/action_steps — hệ thống để null).
Editor: `{"data":[],"id":"bot_can_not_answer","type":"bot_can_not_answer"}` và `{"promptEndConv":"","repeatContent":[],"data":[],"repeat":{"label":"notRepeat","value":"0"},"waitingTime":10,"id":"customer_not_response","type":"customer_not_response","waitingTimeUnit":"second"}`.

### ACTION — TRANSFER_CALL (runtime)
```json
{"id":"<node_id>","node_type":"ACTION",
 "actions":[{"id":"<action_id>","type":"TRANSFER_CALL","data":{"ids":["<agent_id>"],"actionType":"Extension","sip_number":"<ext>","transfer_collected_info":true,"transfer_customize_info":false}}],
 "variables":[{"field_name","field_code","field_value":"","field_type":"","type":"COLLECT_INFO","is_dynamic_attribute":false}],
 "is_collapse":false}
```
org ACTION: `data:{variables:[{"variable":"var_","selected":{}}],count:1,name:"",description:"",type:"ACTION",actions:[{objVariables:{},datas:{selected:<agent_option>,typeOptions:{Extension:[<option>],Ring_group:[],Outer_group:[]},isTransferCustomizeInfo:false,isTransferCollectedInfo:true,customizeInfo:[],type:"TRANSFER_CALL",transferType:"Extension"},id:"<action_id>",type:"TRANSFER_CALL"}],content:"",collapseObj:{NEXT_STEP:{isCollapse:false}}}`; `orgDatas:[{datas:{...không id},"type":"TRANSFER_CALL"}]`; `width:332,height:202`.
`agent_id/contact_id/sip_user`: `omicall_list_agents`/`omicall_list_extensions`. Agent option: `{"contact_id":"","avatar":"","gender":"male","value":"<agent._id>","label":"<ext> - <full_name>","sipNumber":"<ext>","fullName":"<full_name>","email":""}`.
#### Nối `bot_can_not_answer` → TRANSFER_CALL (ba chỗ phải khớp)
- runtime `ai_analyze.conditions[id=bot_can_not_answer].next_node = "<xfer_id>"` **và** `ai_analyze.bot_can_not_answer.next_node = "<xfer_id>"`;
- connection `{"source":"<begin_id>","sourceHandle":"bot_can_not_answer","target":"<xfer_id>","targetHandle":"1","id":"reactflow__edge-<begin_id>bot_can_not_answer-<xfer_id>1","type":"custom"}`;
- node ACTION `TRANSFER_CALL`: runtime `data:{"ids":["<agent_id>"],"actionType":"Extension","sip_number":"<ext>","transfer_collected_info":true,"transfer_customize_info":false}`; org `datas.selected` = `{"sipNumber":"<ext>","gender":"male","fullName":"<tên>","avatar":"","label":"<ext> - <tên>","contact_id":"<contact_id>","value":"<agent_id>","email":""}`, `typeOptions.Extension=[<cùng option>]`, `transferType:"Extension"`, `isTransferCollectedInfo:true`.

Action types AI_AGENT: `TRANSFER_CALL`, `PUSH_NOTIFICATION`, `SEND_WEBHOOK`, `ADD_CLASSIFY`, `START_OTHER_CAMPAIGN`.

### ADD_CLASSIFY — phân loại khách sau intent (runtime key **`data`**, editor key **`datas`**)
```json
{"id":"clf_x","node_type":"ACTION",
 "actions":[{"id":"u_clf_x_1","type":"ADD_CLASSIFY","data":{"ids":["<Nhãn>","<Nhãn có nhu cầu>"],"classifies":[{"name":"<Nhãn>"},{"name":"<Nhãn có nhu cầu>"}]}}],
 "description":"Phân loại khách: ...","variables":[],"is_collapse":false}
```
org: `{"id":"clf_x","type":"ACTION","width":332,"height":205,"position":{"x":400,"y":200},"data":{"type":"ACTION","content":"","actions":[{"id":"o_u_clf_x_1","type":"ADD_CLASSIFY","datas":{"ids":[...],"classifies":[{"name":...}]}}],"handlers":{"SOURCE":{"id":"1","type":"target","position":"left"},"NEXT_STEP":{"id":"2","type":"source","position":"right"}},"count":1,"description":"Phân loại: ...","name":"Phân loại <nhóm>","statusActions":[],"variables":[],"collapseObj":{"NEXT_STEP":{"isCollapse":false}},"pos":{"x":400.0,"y":200.0,"h":205.0}},"orgDatas":[{"datas":{"ids":[...],"classifies":[...]},"type":"ADD_CLASSIFY"}]}`
- Top-level `classifies`: `[{"name":"<Nhãn>"},...]` (server thêm `previous_staff_node_id:null`). Wire: intent → clf node. Nếu cần chuyển/cúp thì nối tiếp clf → TRANSFER/END; nếu xử lý xong và vẫn tiếp tục hội thoại thì clf là node cuối, không có cạnh đi ra. Traps: runtime `datas`/editor `data` → editor không hiện phân loại, runtime `data:null`.

### END_CALL — bắt buộc mô tả cách kết thúc cho agent
Runtime: `{"id":"<end_id>","node_type":"END_CALL","description":"Kết thúc cuộc gọi: bot cảm ơn khách đã gọi, chúc sức khỏe, lịch sự tạm biệt rồi kết thúc cuộc gọi.","actions":[],"variables":[],"is_collapse":false}`
org: `data:{id,type:"END_CALL",content:"<câu TTS chào: Cảm ơn Anh/Chị đã gọi..., chúc sức khỏe, tạm biệt.>",actions:[],handlers:{SOURCE:{id:"1",type:"target",position:"left"},NEXT_STEP:{id:"2",type:"source",position:"right"}},count:1,description:<cùng>,collapseObj:{NEXT_STEP:{isCollapse:false}},pos:{x,y,h:128}}`; `width:332,height:128`. Wire như ACTION.

## Connection
```json
{"sourceHandle":"<intent_handle>","animated":false,"style":{"strokeWidth":3,"stroke":"#00B1FF"},
 "id":"reactflow__edge-<source><intentHandle>-<target><targetHandle>1","source":"<begin_id>","type":"custom","targetHandle":"1","target":"<action_or_end_id>"}
```
targetHandle `"1"` cho cả ACTION và END_CALL.

### Bất biến: không có cạnh ngược về BEGIN
- `connections` chỉ mô tả chiều đi từ intent ở BEGIN sang node xử lý và các bước xử lý tiếp theo. **Cấm mọi connection có `target == <begin_id>`.**
- **Cấm mọi condition có `next_node == <begin_id>`.** Intent xử lý ngay trong BEGIN dùng `next_node:null`; nhánh ACTION xử lý xong dừng ở node cuối, không có connection đi ra.
- Sau node cuối không terminal, hệ thống tự động quay về ngữ cảnh chính BEGIN. Không biểu diễn hành vi tự động này bằng cạnh hoặc `next_node`.
- Trước khi gọi `add_v2`, xác định `begin_id` rồi từ chối payload nếu có `connections.some(c => c.target === begin_id)` hoặc condition có `next_node === begin_id`.

## Thu thập thông tin theo intent (collect-variables) — 1 intent thu NHIỀU biến
- Runtime condition: `"action_steps":[{"action":"collect_variables","prompt":null,"variables_code":["var_a","var_b"]}]`
- Editor condition: `"actionStep":[{"variablesCode":[{"id":"var_a","label":"Tên","labelUnsigned":"ten","value":"var_a","tooltipParent":"Mô tả khi nào thu"},...],"action":"collect_variables","labelUnsigned":"thu thap thong tin","id":"<uuid>","value":"collect_variables"}]`
- ACTION node được nối: runtime `node.variables` = `[{"field_name":"Tên","field_code":"var_a","field_value":"","field_type":"","type":"COLLECT_INFO","is_dynamic_attribute":false}]` (node=false, top-level=true); org `node.data.variables` = `[{"variable":"var_a","selected":{}}]`.
- Intent Từ chối/system: `action_steps:null` (runtime), `actionStep:[]` (editor).
- **Qui trình bắt buộc**: sau intent thu thập → **PHÂN LOẠI khách / xác nhận thông tin / báo giá trị lợi ích** → mới TRANSFER/END. Không nhảy thẳng.

## Cấu hình API cho agent (gọi API / tra cứu) — mẫu verify từ script thật (CSKH điện)
**1) `knowledge.apis[]`**: `{"ref_id":"<mã_biến_action>","name":"<tên>","url":"<endpoint OMi custom: https://customize-v2-stg.omicrm.com/{slug}/...>","method":"POST","headers":[{"id":"<uuid>","key":"Content-Type","value":"application/json"}],"body_type":"raw","body_json":"{\n  \"phone\": \"0913903379\"\n}","variables":null,"prompt":"","query_prompt":"<parse response + luật trả lời>","param_type":"json","time_out":60,"api_response_guide":[],"retrieve_data":null}`. RAG `knowledge.files[]`: `{"url","id","name"}`.
**2) Biến ACTION top-level**: `{"field_name":"<tên hiển thị>","field_code":"<mã_biến_action / ref_id>","field_value":"","field_type":"","type":"ACTION","is_dynamic_attribute":true}` — type `ACTION` = kết quả API, nhúng `{{<ref_id>}}` vào prompt/PUSH_NOTIFICATION; KHÔNG đưa vào `collect_info_variables`.
**3) Intent bước `search_knowledge`**: runtime `action_steps:[{"action":"search_knowledge","prompt":"<dùng {{ref_id}} + biến thu>","variables_code":null}]`; editor `actionStep:[{"action":"search_knowledge","labelUnsigned":"huong dan agent","id":"<uuid>","value":"search_knowledge","prompt":"<cùng prompt>"}]` (editor hiện "huong dan agent").
**query_prompt/prompt phải dạy LLM**: khi nào gọi API; `statusCode==9999` thành công; payload nhiều mã KH (SĐT trùng hợp đồng) → 1 mã đọc luôn, ≥2 mã đọc tên chủ hợp đồng hỏi khách XÁC NHẬN, không tự chọn; dedupe `ID_HDON`; `TONG_TIEN` đọc tiền Việt; `TTRANG_TTOAN` DATT/CHUATT; không đọc field nội bộ (`MA_DVIQLY`...); tham số từ biến đã thu. Endpoint customize OMi: `https://customize-v2-stg.omicrm.com/{slug}/...`.

## collect_data entry (org BEGIN collectData)
```json
{"saveToConv":false,"oldName":"<Name>","name":"<Name>","id":"var_<name>","uuid":"var_<name>","content":"<prompt khi thu>"}
```

## collect_variable entry (ai_agent_config.collect_variables)
```json
{"entity_type_code":null,"variable_code":"var_<name>","variable_name":"<Name>","variable_value":"<prompt>","variable_value_format":null,"entire_user_sentence":null,"node_id":null,"option":"ENTITY","available_variables_detail":null,"collect_info_executed_time":null,"save_to_conv":null,"remember":false,"intent_code":null}
```

## Validation checklist (sau mỗi save — GET /callbot/script/get/{new_id})
Assert TẤT CẢ:
1. `nodes` BEGIN `ai_analyze.conditions` ≥5 `CUSTOM_INTENT`, mỗi `data[].type=="OMI_BOT_INTENT"`.
2. `org_nodes` BEGIN `data.conditions` cùng intent ids như `nodes`, cùng thứ tự, 2 system CUỐI.
3. Mỗi org intent `data[]` có `isCustomComp==true` && `targetType=="OMI_BOT_INTENT"` (không → editor trống).
4. Mỗi runtime intent `data[]` có `content` = câu khách nói.
5. Intent chuyển/cúp: runtime `next_node` = id ACTION/END + `connections` chứa `reactflow__edge-<begin><intent_handle>-<target_id>1` (targetHandle "1").
6. **Không có cạnh ngược**: mọi `connections[].target != begin_id`; mọi condition `next_node != begin_id`; node cuối của nhánh không terminal không có connection đi ra.
7. `collapseObj` BEGIN org có 1 entry mỗi intent id.
8. Intent collect: `action_steps`(runtime) + `actionStep`(editor) ✓; ACTION node `variables`(runtime+org) ✓.
9. ADD_CLASSIFY: runtime `actions[].data.classifies` == editor `actions[].datas.classifies`; top-level `classifies` đủ nhãn.
10. END_CALL: runtime `description` + org `data.description`/`data.content` (cách kết thúc).
11. `is_newest_version:true`, `is_publish:true`, `version` đã tăng.

## Bài học tenant trống (không có script baseline) — đã verify
- `list-by-tenant` trả `payload:[]` vẫn tạo được script mới bằng `add_v2` KHÔNG cần `id`/`uuid`/`public_key`; server sinh `id`, `uuid`, `version:1`. Muốn cập nhật tiếp thì truyền `id` cũ.
- Gửi `is_publish:false` nhưng server trả `is_publish:true` — không dựa vào trường này để biết đã xuất bản.
- Biến đầu vào chiến dịch gọi ra (tên, xe, hạn...) khai báo trong `variables` (type COLLECT_INFO, is_dynamic_attribute true) và nhúng `{{var_x}}` vào prompt; chỉ biến cần thu mới đưa vào BEGIN `collect_variables`. Chưa xác nhận cơ chế nạp giá trị từ chiến dịch.
- Đăng nhập là việc của user (không nhập mật khẩu hộ). Sau khi user đăng nhập trong browser pane, lấy token từ cookie `{domain}_omicrm_io` key "2".
- Ví dụ add_v2 tối thiểu đã chạy: xem payload gồm `nodes`(BEGIN + ACTION ADD_CLASSIFY + END_CALL), `org_nodes`, `connections` (intent→clf; clf là node cuối nếu cuộc gọi tiếp tục), `classifies`.
- **Cập nhật phiên bản mới**: `add_v2` phải gửi CẢ `id` lẫn `uuid` của script cũ. Chỉ gửi `id` → server tạo script trùng (uuid mới, version 1). Gửi cả hai → version tăng và `id` đổi sang id mới (ví dụ v1 `6ad5c47f…` → v2 `6ad5c5b3…`, cùng uuid); luôn lấy `id` mới từ response.
- **Xoá script**: `POST /callbot/script/delete` JSON `{"ids":["<script_id>"]}` (trả `payload:["<id>"]`). Body `{"id":...}` trả 9999 nhưng KHÔNG xoá. Chỉ xoá khi user đồng ý.
