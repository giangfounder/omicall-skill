# OMiCall Callbot Gen AI — API Reference & Schemas

## Base URL & Auth
`https://chatbot-gateway-v1-stg.omicrm.com` (frontend map `chatBot`). Mọi endpoint cần `Authorization: Bearer <accessToken>`. Token: `scripts/omi_session.py` → `headers()` (đọc phiên do `omi_login.py` ghi; vị trí file phiên: `omi-login.md` mục 2 ý 3); kiểm hạn và domain bằng `omi_preflight.py --domain <domain>`. Đăng nhập: `conversation.md` mục 1. Không đọc cookie bằng JS/CDP.

> **Trạng thái kiểm chứng và việc builder có sinh được hay không: chỉ ghi ở `references/node-status.json`** (cột `status`: verified → sinh JSON được; enum/ui_only/unverified → dựng trên UI hoặc "Cần xác nhận"; cột `builder`: `sinh` | `giu_nguyen` | `khong` = builder dừng exit 2, ghép tay theo mục nguồn). File này chỉ mô tả schema; mục nào ghi khác node-status thì node-status thắng.
> Vì sao nhiều loại là `unverified`: tài liệu không có nhãn kiểm chứng trực tiếp cho loại đó (chỉ suy từ câu tóm tắt add_v2 tối thiểu, chưa có fixture JSON thật) → chỉ nhân bản từ GET baseline; nâng `verified` qua `extract_template.py --mark-verified` kèm validator post PASS trên GET thật, do agent chính hoặc user duyệt.
> Cách học schema mới: dựng 1 nút bằng UI → `GET /callbot/script/get/{id}` → `extract_template.py` → agent chính hoặc user duyệt → mới dùng để sinh hàng loạt. Mẫu node đã làm sạch: `references/templates/`.

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
from omi_session import headers  # scripts/omi_session.py, không in token
r = requests.post(base+'/callbot/script/add_v2',
  headers=headers(),
  files={'file':('blob', json.dumps(payload, ensure_ascii=False).encode('utf-8'), 'application/json')}, timeout=120)
new_id = r.json()['payload']['id']  # id MỚI + version tăng mỗi lần lưu
```
Không dùng curl (multipart curl → `invalid_param`). Response payload = script đã lưu. Có `scripts/omi_save.py` thì dùng `omi_save.py callbot payload.json --domain <domain> --new` (lần lưu đầu của kịch bản mới) hoặc `--update --confirm-update` (lần lưu sau với `id` mới nhất + `uuid` từ response, hoặc script user chỉ định; SKILL.md Rules 4) — tự validate pre, POST, GET lại, validate post.

## Script object (top-level)
```json
{"id","uuid","tenant_id","name",
 "variables":[{"field_name","field_code","field_value":"","field_type":"","type":"COLLECT_INFO","is_dynamic_attribute":true}],
 "collect_info_variables":[{"variable_code","variable_name"}],
 "connections","nodes","org_nodes","is_draft":false,"created_date","last_updated_date",
 "created_by":{"id","name","contact_id"},"public_key","last_updated_by":{"id","name","contact_id"},"is_deleted":false,
 "collect_authentication_data":"NONE","system_intent_ids":[],"system_entity_type_ids":[],
 "version","is_newest_version":true,"layouts":[],"is_publish":false,"custom_variables":[],"classifies":[{"name":""}],
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
Các trường `...null/default`: lấy từ GET baseline của tenant; tenant trống: Cần xác nhận.
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
{"actionStep":[],"webhookId":"<tenant_id>-<random20>","selectedIntent":null,"personality":"",
 "data":[{"isCustomComp":true,"targetType":"OMI_BOT_INTENT","id":"<data_id>","content":"<câu khách nói>","selected":false,"chosen":false}],
 "name":"<label>","id":"<handle>","operatorType":"AND","type":"CUSTOM_INTENT","webhookParam":{"bot_id":"","conv_id":""}}
```
- `webhookId`: tiền tố `<tenant_id>-` + chuỗi ngẫu nhiên khoảng 20 ký tự; cách sinh hậu tố: Cần xác nhận (lấy theo GET thật).
- `data[].type` (runtime) / `isCustomComp:true`+`targetType` (editor) — thiếu → editor hiện ô "Nhận diện ý định" TRỐNG. `content` = câu khách hiển thị (đừng dựa `name`).
- CUSTOM_INTENT đặt TRƯỚC 2 system; quy ước tối thiểu 5 intent (validator C1 chỉ WARN, số thật "Cần xác nhận" theo nghiệp vụ); intent nối node hành động/kết thúc → `next_node` + connection + entry `collapseObj`. Intent được xử lý trong BEGIN dùng `next_node:null` và không có connection. Không bao giờ dùng id BEGIN làm `next_node`.

### System conditions (luôn ở cuối)
Runtime: `{"data":[],"id":"bot_can_not_answer","type":"bot_can_not_answer",...null}` và `{"id":"customer_not_response","type":"customer_not_response",...,"operator_type":null,"action_steps":null}` (full: intent_code/intent_name/name/keywords/operator/compare_operator/percent/next_node/repeat_contents/repeat_time/apply_targets/attachment/limit/limit_ai_config/operator_type/action_steps — hệ thống để null).
Editor: `{"data":[],"id":"bot_can_not_answer","type":"bot_can_not_answer"}` và `{"promptEndConv":"","repeatContent":[],"data":[],"repeat":{"label":"notRepeat","value":"0"},"waitingTime":10,"id":"customer_not_response","type":"customer_not_response","waitingTimeUnit":"second"}`.

### ACTION — TRANSFER_CALL chuyển nhân viên (Extension)
Mục duy nhất về id nhân viên trong TRANSFER_CALL: runtime `data.ids[]`, editor `datas.selected.value` và `typeOptions.Extension[].value` cùng một giá trị. Giá trị đó là `_id` hay `agent_id` của nhân viên: **Cần xác nhận**, chép theo GET thật của tenant. `tenant_survey.py` giữ cả hai, không tự chọn; validator X11 so cả `_id`, `agent_id`, `contact_id`. Các mẫu bên dưới ghi `<agent_id>` chỉ là chỗ điền.
```json
{"id":"<node_id>","node_type":"ACTION",
 "actions":[{"id":"<action_id>","type":"TRANSFER_CALL","data":{"ids":["<agent_id>"],"actionType":"Extension","sip_number":"<ext>","transfer_collected_info":true,"transfer_customize_info":false}}],
 "variables":[{"field_name","field_code","field_value":"","field_type":"","type":"COLLECT_INFO","is_dynamic_attribute":false}],
 "is_collapse":false}
```
org ACTION: `data:{variables:[{"variable":"var_","selected":{}}],count:1,name:"",description:"",type:"ACTION",actions:[{objVariables:{},datas:{selected:<agent_option>,typeOptions:{Extension:[<option>],Ring_group:[],Outer_group:[]},isTransferCustomizeInfo:false,isTransferCollectedInfo:true,customizeInfo:[],type:"TRANSFER_CALL",transferType:"Extension"},id:"<action_id>",type:"TRANSFER_CALL"}],content:"",collapseObj:{NEXT_STEP:{isCollapse:false}}}`; `orgDatas:[{datas:{...không id},"type":"TRANSFER_CALL"}]`; `width:332,height:202`.
Nhân viên và máy lẻ: MCP `list_agents`/`list_extensions` (`agent_id`, `_id`, `contact_id`, `sip_user`). Agent option: `{"contact_id":"<contact_id>","avatar":"","gender":"male","value":"<agent_id>","label":"<ext> - <full_name>","sipNumber":"<ext>","fullName":"<full_name>","email":""}` (`value`: xem đầu mục).
#### Nối `bot_can_not_answer` → TRANSFER_CALL (ba chỗ phải khớp)
- runtime `ai_analyze.conditions[id=bot_can_not_answer].next_node = "<xfer_id>"` **và** `ai_analyze.bot_can_not_answer.next_node = "<xfer_id>"`;
- connection `{"source":"<begin_id>","sourceHandle":"bot_can_not_answer","target":"<xfer_id>","targetHandle":"1","id":"reactflow__edge-<begin_id>bot_can_not_answer-<xfer_id>1","type":"custom"}` (id cạnh theo mục Connection);
- node ACTION `TRANSFER_CALL` như mẫu đầu mục (`transferType:"Extension"`, `isTransferCollectedInfo:true`, option nhân viên giống nhau ở `selected` và `typeOptions.Extension`).

### ACTION — TRANSFER_CALL nhóm nội bộ (Ring_group)
✔ UI 11/2026: trong node TRANSFER_CALL chọn "Nhóm nội bộ" rồi chọn nhóm, GET lại. Mẫu node đầy đủ (runtime, editor, cạnh), đã bỏ giá trị tenant: `references/templates/TRANSFER_CALL_Ring_group.json`. Builder chưa sinh loại này (exit 2, xem node-status): ghép tay node từ mẫu vào payload, giữ cạnh của intent chuyển máy và `bot_can_not_answer`, rồi `omi_save.py --update --confirm-update`.
- runtime `data:{actionType:"Ring_group",sip_number:"<số nhóm>",ids:["<id nhóm pbx>"],transfer_collected_info:true,transfer_customize_info:false}`;
- editor `actions[].datas:{actionType:"Ring_group",selected:"<id nhóm>",isTransferCollectedInfo:true,...}`; `orgDatas[].datas` có `transferType:"Ring_group"`, `selected:{sipNumber,members,label,labelUnsigned,value:"<id nhóm>"}`, `typeOptions.Ring_group:[{sipNumber,members,label,value}]`.
- Validator X3 nhận Ring_group; X11 chỉ WARN vì id nhóm không nằm trong `tenant_context.agents`.
- Cách lấy JSON nhóm khi chưa có mẫu: dựng trên giao diện rồi chỉ lấy node đó (bẫy lưu qua giao diện: playbook Gotchas *Lưu qua giao diện và tab editor cũ*).

### Các loại hành động (AI_AGENT)
`TRANSFER_CALL`, `PUSH_NOTIFICATION`, `SEND_WEBHOOK`, `ADD_CLASSIFY`, `START_OTHER_CAMPAIGN`. Loại nào đã kiểm chứng, builder có sinh hay không: `references/node-status.json`. Loại chưa có JSON: dựng 1 nút trên UI, GET, `extract_template.py`.

### ADD_CLASSIFY — phân loại khách sau intent (runtime key **`data`**, editor key **`datas`**)
```json
{"id":"clf_x","node_type":"ACTION",
 "actions":[{"id":"u_clf_x_1","type":"ADD_CLASSIFY","data":{"ids":["<Nhãn>","<Nhãn có nhu cầu>"],"classifies":[{"name":"<Nhãn>"},{"name":"<Nhãn có nhu cầu>"}]}}],
 "description":"Phân loại khách: ...","variables":[],"is_collapse":false}
```
org: `{"id":"clf_x","type":"ACTION","width":332,"height":205,"position":{"x":400,"y":200},"data":{"type":"ACTION","content":"","actions":[{"id":"o_u_clf_x_1","type":"ADD_CLASSIFY","datas":{"ids":[...],"classifies":[{"name":...}]}}],"handlers":{"SOURCE":{"id":"1","type":"target","position":"left"},"NEXT_STEP":{"id":"2","type":"source","position":"right"}},"count":1,"description":"Phân loại: ...","name":"Phân loại <nhóm>","statusActions":[],"variables":[],"collapseObj":{"NEXT_STEP":{"isCollapse":false}},"pos":{"x":400.0,"y":200.0,"h":205.0}},"orgDatas":[{"datas":{"ids":[...],"classifies":[...]},"type":"ADD_CLASSIFY"}]}`
- Top-level `classifies`: `[{"name":"<Nhãn>"},...]` (server thêm `previous_staff_node_id:null`). Wire: intent → clf node. Nếu cần chuyển/cúp thì nối tiếp clf → TRANSFER/END; nếu xử lý xong và vẫn tiếp tục hội thoại thì clf là node cuối, không có cạnh đi ra. Traps: runtime `datas`/editor `data` → editor không hiện phân loại, runtime `data:null`.

### END_CALL — bắt buộc mô tả cách kết thúc cho agent
Quy tắc nội dung và nối dây (mô tả, chỉ intent Hoàn tất, hỏi còn nhu cầu): playbook mục *Kết thúc và chuyển cuộc gọi*. Mục này chỉ là schema.
Runtime: `{"id":"<end_id>","node_type":"END_CALL","description":"Kết thúc cuộc gọi: bot cảm ơn khách đã gọi, chúc sức khỏe, lịch sự tạm biệt rồi kết thúc cuộc gọi.","actions":[],"variables":[],"is_collapse":false}`
org: `data:{id,type:"END_CALL",content:"<câu TTS chào: Cảm ơn Anh/Chị đã gọi..., chúc sức khỏe, tạm biệt.>",actions:[],handlers:{SOURCE:{id:"1",type:"target",position:"left"},NEXT_STEP:{id:"2",type:"source",position:"right"}},count:1,description:<cùng>,collapseObj:{NEXT_STEP:{isCollapse:false}},pos:{x,y,h:128}}`; `width:332,height:128`. Wire như ACTION.

## Connection (cạnh) và định dạng id cạnh
```json
{"sourceHandle":"<intent_handle>","animated":false,"style":{"strokeWidth":3,"stroke":"#00B1FF"},
 "id":"reactflow__edge-<begin_id><intent_handle>-<action_or_end_id>1","source":"<begin_id>","type":"custom","targetHandle":"1","target":"<action_or_end_id>"}
```
Mục duy nhất về id cạnh. `id = "reactflow__edge-" + source + sourceHandle + "-" + target + targetHandle`, ghép liền không dấu cách. `targetHandle` luôn `"1"` (ACTION và END_CALL) nên id kết thúc bằng `<target>1`. `sourceHandle`: id intent, `bot_can_not_answer`, hoặc `"2"` (NEXT_STEP) khi cạnh đi ra từ node ACTION. ✔ 11/2026: khớp các cạnh do giao diện tạo trong bản GET thật (intent/điều kiện hệ thống → node, ACTION → ACTION). Builder chép định dạng theo cạnh mẫu của base; validator không kiểm id cạnh.

### Bất biến: không có cạnh ngược về BEGIN
- `connections` chỉ mô tả chiều đi từ intent ở BEGIN sang node xử lý và các bước xử lý tiếp theo. **Cấm mọi connection có `target == <begin_id>`.**
- **Cấm mọi condition có `next_node == <begin_id>`.** Intent xử lý ngay trong BEGIN dùng `next_node:null`; nhánh ACTION xử lý xong dừng ở node cuối, không có connection đi ra.
- Sau node cuối không terminal, hệ thống tự động quay về ngữ cảnh chính BEGIN. Không biểu diễn hành vi tự động này bằng cạnh hoặc `next_node`.
- Trước khi gọi `add_v2`, xác định `begin_id` rồi từ chối payload nếu có `connections.some(c => c.target === begin_id)` hoặc condition có `next_node === begin_id` (`validate_smartagent.py`: X1, C6).

## Thu thập thông tin theo intent (collect-variables) — 1 intent thu NHIỀU biến
- Runtime condition: `"action_steps":[{"action":"collect_variables","prompt":null,"variables_code":["var_a","var_b"]}]`
- Editor condition: `"actionStep":[{"variablesCode":[{"id":"var_a","label":"Tên","labelUnsigned":"ten","value":"var_a","tooltipParent":"Mô tả khi nào thu"},...],"action":"collect_variables","labelUnsigned":"thu thap thong tin","id":"<uuid>","value":"collect_variables"}]`
- ACTION node được nối: runtime `node.variables` = `[{"field_name":"Tên","field_code":"var_a","field_value":"","field_type":"","type":"COLLECT_INFO","is_dynamic_attribute":false}]` (node=false, top-level=true); org `node.data.variables` = `[{"variable":"var_a","selected":{}}]`.
- Intent Từ chối/system: `action_steps:null` (runtime), `actionStep:[]` (editor).
- **Qui trình bắt buộc**: intent thu biến để **trống nút kế tiếp** (hệ thống chuyển nút ngay khi đủ biến, bỏ qua câu đọc lại) → intent riêng **"khách xác nhận"** (không thu biến; builder: kind `confirm`) → **PHÂN LOẠI** hoặc **API gửi dữ liệu** → mới TRANSFER/END. Không nhảy thẳng (validator WARN X13, builder WARN X14).

## Cấu hình API cho agent (gọi API / tra cứu) — mẫu verify từ script thật (tra cứu theo số điện thoại)
**1) `knowledge.apis[]`**:
```json
{"ref_id":"<mã_biến_action>","name":"<tên>","url":"<endpoint OMi custom: https://customize-v2-stg.omicrm.com/{slug}/...>","method":"POST","headers":[{"id":"<uuid>","key":"Content-Type","value":"application/json"}],"body_type":"raw","body_json":"{\n  \"phone\": \"<so_dien_thoai>\"\n}","variables":null,"prompt":"","query_prompt":"<parse response + luật trả lời>","param_type":"json","time_out":60,"api_response_guide":[],"retrieve_data":null}
```
RAG `knowledge.files[]`: `{"url","id","name"}`. Tải file: xem mục "RAG — File đào tạo" bên dưới.
**2) Biến ACTION top-level**: `{"field_name":"<tên hiển thị>","field_code":"<mã_biến_action / ref_id>","field_value":"","field_type":"","type":"ACTION","is_dynamic_attribute":true}` — type `ACTION` = kết quả API, nhúng `{{<ref_id>}}` vào prompt/PUSH_NOTIFICATION; KHÔNG đưa vào `collect_info_variables`.
**3) Intent bước `search_knowledge`**: runtime `action_steps:[{"action":"search_knowledge","prompt":"<dùng {{ref_id}} + biến thu>","variables_code":null}]`; editor `actionStep:[{"action":"search_knowledge","labelUnsigned":"huong dan agent","id":"<uuid>","value":"search_knowledge","prompt":"<cùng prompt>"}]` (editor hiện "huong dan agent").
**query_prompt/prompt phải dạy LLM**: khi nào gọi API; `statusCode==9999` thành công; payload có nhiều mã khách (một số điện thoại gắn nhiều hồ sơ/hợp đồng) → 1 mã đọc luôn, ≥2 mã đọc tên chủ hồ sơ rồi hỏi khách XÁC NHẬN, không tự chọn; bỏ bản ghi trùng theo `<ma_hoa_don>`; `<tong_tien>` đọc thành tiền Việt; `<trang_thai>` đổi mã trạng thái sang câu dễ hiểu (ví dụ đã thanh toán / chưa thanh toán); không đọc field nội bộ (mã đơn vị, mã hệ thống...); tham số từ biến đã thu. Tên trường thật lấy theo tài liệu API của khách, không đoán. Endpoint customize OMi: `https://customize-v2-stg.omicrm.com/{slug}/...`.

## RAG — File đào tạo (knowledge.files) — mục duy nhất về RAG callbot; ◐ put_v2 11/2026 (tải lên ✔, truy xuất Cần xác nhận)
UI: Ngữ cảnh bắt đầu → **File đào tạo**. Editor KHÔNG tải file lúc chọn; tải khi bấm **Cập nhật**, với mỗi file chưa có `url`:
1. `POST https://filestore-v1-stg.omicrm.com/file_store/put_v2?business_type=callbot_recording_file&keep_content_type=true`, Bearer, multipart field `file_0=<file>` (một file mỗi request). Phản hồi `payload[0].object_info.name` = `<tenant_id>/callbot_recording_file/<yyyy>/<mm>/<uuid>.<đuôi>`. ◐ 11/2026: tải lên ✔ trên stg; bot truy xuất được nội dung file: Cần xác nhận bằng gọi thử.
   - Đường cũ đọc từ mã editor 10/2026: `/file_store/put?…` cùng query, multipart `image=<file>`, `name=<tên file>` — có thể trả `status_code:-9999`, `payload:{}` với mọi loại file (docx, pdf, txt) trên stg (11/2026). `rag_upload.py` chỉ thử đường này khi `put_v2` lỗi; đừng thử lặp.
2. `url = "https://cdn.omicrm.com/crm/" + object name`; `id` = uuid mới (editor sinh uuid v1); `name` = tên file gốc.
3. Ghi `{"id","name","url"}` vào **cả hai**: `nodes[BEGIN].ai_agent_config.knowledge.files[]` (runtime) và `org_nodes[BEGIN].data.selectedTraining[]` + `data.typeTrainingFile:"file"` (editor hiển thị).
4. Lưu `add_v2` như mọi lần sửa. Không có API "huấn luyện" riêng cho callbot.
Đường nhanh: `scripts/rag_upload.py <file> --base GET.json --out payload.json` (put_v2, lỗi thì thử put) rồi `omi_save.py callbot payload.json --update --confirm-update --base GET.json`. Cần xác nhận lần đầu: gọi thử hỏi câu có trong file mới.

**Dự phòng: chế độ "other"** (chọn bản ghi Dữ liệu khác của kho chung, khi đường file đào tạo không tải được):
- Tạo bản ghi: `scripts/rag_other.py <file.docx> --name <tên> --domain <domain>` (dùng thư viện của skill chatbot-gen-ai: `put_v2` với `business_type=warehouse_of_knowledge_files`, `warehouse_of_knowledge/other/add`, `training`; in `record_id`). Tên bản ghi phải duy nhất (`get_id_by_name` trả trùng → `DUPLICATE_NAME`).
- Gắn vào callbot: `{"id":"<uuid1>","name":"<tên>","other_wok_id":"<record_id>"}` ở `nodes[BEGIN].ai_agent_config.knowledge.files[]` và `org_nodes[BEGIN].data.selectedTraining[]` + `typeTrainingFile:"other"`.
- CHƯA chứng minh: bản ghi vẫn hiện `not_training`, `bots_use_file:0` dù lệnh training trả `true`. Chỉ coi RAG hoạt động sau khi gọi thử một cuộc hỏi câu có trong tài liệu (cần user đồng ý và cho số điện thoại + máy lẻ); tới lúc đó báo "Cần xác nhận".

## collect_data entry (org BEGIN collectData)
```json
{"saveToConv":false,"oldName":"<Name>","name":"<Name>","id":"var_<name>","uuid":"var_<name>","content":"<prompt khi thu>"}
```

## collect_variable entry (ai_agent_config.collect_variables)
```json
{"entity_type_code":null,"variable_code":"var_<name>","variable_name":"<Name>","variable_value":"<prompt>","variable_value_format":null,"entire_user_sentence":null,"node_id":null,"option":"ENTITY","available_variables_detail":null,"collect_info_executed_time":null,"save_to_conv":null,"remember":false,"intent_code":null}
```

## Validation checklist (sau mỗi save — GET /callbot/script/get/{new_id})
Tự động: `validate_smartagent.py <GET.json> --mode post --sent payload.json` (trước khi lưu: `--mode pre`). Mã C1..C11 dưới đây khớp output validator; mục bổ sung X1..X15 ghi ở đầu script (X15: `actionType` của TRANSFER_CALL khớp bản editor và loại id; builder chỉ chép nút mẫu Extension). Assert TẤT CẢ (phần validator không tự kiểm được ghi rõ ở từng mục, agent tự kiểm tay):
1. **C1** `nodes` BEGIN `ai_analyze.conditions` ≥5 `CUSTOM_INTENT` (quy ước, validator chỉ WARN), mỗi `data[].type=="OMI_BOT_INTENT"`.
2. **C2** `org_nodes` BEGIN `data.conditions` cùng intent ids như `nodes`, cùng thứ tự, 2 system CUỐI.
3. **C3** Mỗi org intent `data[]` có `isCustomComp==true` && `targetType=="OMI_BOT_INTENT"` (không → editor trống).
4. **C4** Mỗi runtime intent `data[]` có `content` = câu khách nói.
5. **C5** Intent chuyển/cúp: runtime `next_node` = id ACTION/END + `connections` có cạnh `source=<begin>`, `sourceHandle=<intent_handle>`, `target=<target_id>`, targetHandle "1" (id cạnh: mục Connection).
6. **C6** **Không có cạnh ngược**: mọi `connections[].target != begin_id`; mọi condition `next_node != begin_id`; node cuối của nhánh không terminal không có connection đi ra (validator FAIL khi `END_CALL` có connection đi ra; node ACTION cuối nhánh thì validator không biết nhánh nào là cuối → agent tự kiểm theo thiết kế).
7. **C7** `collapseObj` BEGIN org có 1 entry mỗi intent id.
8. **C8** Intent collect: `action_steps`(runtime) + `actionStep`(editor) ✓; ACTION node được nối `variables`(runtime+org) ✓ (cả hai vế validator đều FAIL khi lệch).
9. **C9** ADD_CLASSIFY: runtime `actions[].data.classifies` == editor `actions[].datas.classifies`; top-level `classifies` đủ nhãn.
10. **C10** END_CALL: runtime `description` + org `data.description`/`data.content` (cách kết thúc).
11. **C11** `is_newest_version:true`, `version` đã tăng. Payload gửi lên luôn `is_publish:false` (chỉ lưu nháp, SKILL.md Rules 4); GET có thể trả `is_publish:true` dù gửi `false` (mục dưới) → ngữ nghĩa `is_publish`: Cần xác nhận, validator chỉ WARN, không dùng để biết đã xuất bản.

## Bài học tenant trống (không có script baseline) — đã verify
- `list-by-tenant` trả `payload:[]` vẫn tạo được script mới bằng `add_v2` KHÔNG cần `id`/`uuid`/`public_key`; server sinh `id`, `uuid`, `version:1`. Muốn cập nhật tiếp thì truyền `id` cũ cùng `uuid` (xem *Cập nhật phiên bản mới*).
- Gửi `is_publish:false` nhưng server trả `is_publish:true` — không dựa vào trường này để biết đã xuất bản.
- Biến đầu vào chiến dịch gọi ra (tên, mã đơn, hạn...) khai báo trong `variables` (type COLLECT_INFO, is_dynamic_attribute true) và nhúng `{{var_x}}` vào prompt; chỉ biến cần thu mới đưa vào BEGIN `collect_variables`. ◐ 11/2026 (tạo phiên và gọi ra được; bot đọc đúng giá trị biến: Cần xác nhận bằng nghe lại): nạp giá trị bằng **phiên gọi ra thủ công** trên UI `…/ai/callbot/callbot-campaign/create` → chọn kịch bản → nguồn **Thủ công** → nhập SĐT và giá trị từng biến đầu vào → *Thêm vào phiên gửi* → *Thêm khách hàng* → *Tạo phiên* → *Xác nhận tạo phiên* (gọi người thật: chỉ khi user đồng ý, dùng số user đưa). Sau cuộc gọi kiểm: chi tiết phiên (kết quả, nhãn phân loại), Lịch sử của flow nhận webhook, phiếu/tin mà flow tạo.
- **Số điện thoại khách trong body SEND_WEBHOOK**: chưa thấy biến hệ thống nào cho SĐT người nghe dùng được trong body → khai báo thêm một biến đầu vào (ví dụ `var_sdt_kh`), truyền đúng SĐT khi tạo phiên và đặt vào body (biến hệ thống tương đương: Cần xác nhận).
- Đăng nhập: một cách duy nhất theo `conversation.md` mục 1 (form cục bộ `omi_login.py setup --ui`, user tự điền; agent không nhập mật khẩu hộ, không đọc cookie hay token bằng JS/CDP).
- Ví dụ add_v2 tối thiểu đã chạy (chưa có fixture JSON thật trong skill; fixture test chỉ ghép từ các khối ở trên): payload gồm `nodes`(BEGIN + ACTION ADD_CLASSIFY + END_CALL), `org_nodes`, `connections` (intent→clf; clf là node cuối nếu cuộc gọi tiếp tục), `classifies`.
- **Cập nhật phiên bản mới**: `add_v2` phải gửi CẢ `id` lẫn `uuid` của script cũ. Chỉ gửi `id` → server tạo script trùng (uuid mới, version 1). Gửi cả hai → version tăng và `id` đổi sang id mới (ví dụ v1 `<id>` → v2 `<id mới>`, cùng uuid); luôn lấy `id` mới từ response.
- ✔ UI 11/2026 (tenant trống, không có mẫu nút thật): Thêm mới → SmartAgent mở `/ai/callbot/script/create?type=AI_AGENT`; nhập tên rồi bấm Lưu lại lần đầu chuyển sang tab Kịch bản, bấm Lưu lại lần nữa mới tạo script (URL đổi sang `/update/{id}`, `is_draft:true`, chỉ BEGIN rỗng, chưa có mẫu CUSTOM_INTENT/TRANSFER_CALL/ADD_CLASSIFY/END_CALL nên builder dừng exit 2). Cách vượt: ghép base = khối node theo api-reference + lớp ngoài (id, uuid, tenant_id, created_by, public_key) từ GET thật, `build_smartagent.py --update`, lưu bằng add_v2 cùng uuid → id mới, editor hiển thị đủ ý định (nhãn "Nhận dạng ý định", tên ý định không hiện). Lưu qua add_v2 trả `is_draft:false`, `version` vẫn 1; danh sách chỉ hiện "Phiên bản 1". Chuyển máy để `ids` rỗng thì validator X3 FAIL, add_v2 vẫn nhận; chuyển cho nhóm: mục *ACTION — TRANSFER_CALL nhóm nội bộ (Ring_group)*.
- ✔ 11/2026 tenant trống, không cần tạo vỏ trên giao diện: lấy một bản GET thật (tenant khác, cùng phiên bản nền tảng) làm khuôn hình dạng cho `build_smartagent.py --new`, rồi trước khi lưu: đổi `tenant_id` và tiền tố `webhookId` sang tenant đích, bỏ `versions`, đặt lại `layouts`, xoá sạch dữ liệu nhân viên/nhóm của tenant nguồn trong node TRANSFER_CALL (`ids`, `sip_number`, `selected`, `typeOptions`), xoá file RAG của kịch bản nguồn (`nodes[BEGIN].ai_agent_config.knowledge.files`, `org_nodes[BEGIN].data.selectedTraining`, `data.typeTrainingFile`; builder `--new` tự xoá trừ khi spec khai báo `knowledge.files`) và grep payload không còn id tenant nguồn. add_v2 không kèm id/uuid tạo script mới `version:1`, `is_draft:false`.
- Builder: luồng cần đọc lại xác nhận dùng cặp intent `collect` (`confirm_by:"<key>"`) + `confirm` (`confirms:"<key ý định collect>"`, `carry_variables` mặc định = biến của intent collect, `classify_labels`): intent thu biến để trống `next_node`, không có node phân loại riêng; intent xác nhận nối node phân loại mang các biến đó. Câu mẫu của intent xác nhận phải gắn với nội dung vừa đọc lại để không trùng câu "đúng rồi" khi xác nhận danh tính đầu cuộc gọi. Spec cũ (collect không có confirm) vẫn nối thẳng node phân loại và in WARN X14. Bước Hướng dẫn Agent (`search_knowledge`, gọi `{{request_api_<tên>}}`) builder chưa sinh: thêm tay vào intent thu biến, SAU bước `collect_variables` (theo agent-config-guide), cả runtime lẫn editor — chỉ cho API tra cứu (chỉ đọc); API ghi dữ liệu (tạo đơn, đặt lịch) nối sau intent xác nhận. Biến đầu vào gọi ra (không thu) thêm tay vào top-level `variables` (COLLECT_INFO, `is_dynamic_attribute:true`), biến kết quả API thêm kiểu `ACTION`.
- Mã giọng đã thấy trong dữ liệu thật: `northern_female_ngocanh` (nữ Bắc), `southern_female_khangan` (nữ Nam), `banmai`.
- Tenant chưa có nhân viên: node TRANSFER_CALL của `bot_can_not_answer` để `ids:[]` → validator X3 FAIL, `omi_save.py` từ chối (pre FAIL) nhưng add_v2 trực tiếp vẫn nhận; ghi Cần xác nhận, chọn nhân viên sau khi tenant có.
- **Xoá script**: `POST /callbot/script/delete` JSON `{"ids":["<script_id>"]}` (trả `payload:["<id>"]`). Body `{"id":...}` trả 9999 nhưng KHÔNG xoá. Chỉ xoá khi user đồng ý.

## Nút gọi API (SEND_WEBHOOK) sau intent — ✔ dựng UI rồi ghép add_v2 (11/2026)
- UI: mở intent trong "Ngữ cảnh bắt đầu" → **Nút kế tiếp** → *Hành động* → ô **API** (công tắc GET/POST, URL, Request Headers có nút `+`, Body raw là editor CodeMirror gõ phím thật được, KHÔNG có đối tượng `ace`). Menu "Thêm hành động" của intent chỉ có *Thu thập thông tin* và *Hướng dẫn Agent*; muốn có nút trên canvas phải đi đường Nút kế tiếp.
- Runtime node: `{"id":"<id>","node_type":"ACTION","actions":[{"id":"<id>","type":"SEND_WEBHOOK","data":{"headers":[{"id","key","value"}],"method":"POST","body_type":"raw","url":"...","body_json":"<chuỗi JSON>","param_type":"json"}}],"is_collapse":false,"variables":[<biến thu của intent, như node ADD_CLASSIFY>]}` (thiếu `variables` thì validator C8 FAIL).
- Editor node: `type:"ACTION"`, `data.actions[0]` = `{type:"SEND_WEBHOOK", id, datas:{paramType:"json", method, url, headers, bodyJson:{"text":"<chuỗi JSON>"}, variables:[...]}}`, `orgDatas[0].datas` thêm `bodyType:"raw"`, `listVariable`; `data.variables=[{"variable":"var_x","selected":{"label","value","desc":"{{var_x}}"}}]`. Body JSON viết nhiều dòng, thụt 2 dấu cách, biến trong nháy kép `"{{var_x}}"`; cả `body_json` runtime lẫn `bodyJson.text` editor phải khớp.
- Dây: **intent "khách xác nhận" → API** (không nối từ intent thu biến: API sẽ chạy ngay khi đủ biến, trước câu đọc lại; validator WARN X13). Intent thu biến để trống `next_node`; intent xác nhận → API là connection thường (`sourceHandle=<id intent xác nhận>`, runtime `next_node=<id API>`). Node API khai `variables` = biến của intent thu biến (body nhận đúng giá trị khi nối sau intent xác nhận hay không: Cần xác nhận bằng gọi thử, xem agent-config-guide mục 4). API → node tiếp theo dùng `sourceHandle:"2"` (NEXT_STEP), `targetHandle:"1"`, id cạnh `reactflow__edge-<api>2-<đích>1`. ACTION→ACTION chỉ cần connection, runtime node không có `next_node`.
- Lấy JSON mẫu bằng giao diện: chỉ lấy node vừa dựng, ghép vào payload gốc rồi lưu add_v2 với id mới nhất + uuid. Bẫy khi bấm **Cập nhật** và tab editor còn mở: playbook Gotchas *Lưu qua giao diện và tab editor cũ*. Nút mới thêm trên UI có thể chồng lên node khác (cùng toạ độ): đặt lại `position` trong org_nodes.
