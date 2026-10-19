# OMiCALL AI Chatbot (OmiBot) — API Reference & Schemas

## Base URL & Auth
`https://chatbot-gateway-v1-stg.omicrm.com` (cùng gateway callbot). Header `Authorization: Bearer <accessToken>`. Token: cookie `{domain}_omicrm_io` → URL-decode → JSON → key `"2"` = JWT (HttpOnly → CDP). Login qua UI: `https://{domain}.omicrm.io` form `input[name=username]`/`input[name=password]`.

> Đã verify tenant `oanhtesting.omicrm.io` — bot "Zalo OA Bot" `_id 6ab9d5fc82ddf2619521d99a`, gpt-4o-mini, SCENARIO_HANDLER.

## Endpoints (prefix `omiai_assistant/` — KHÁC callbot)
| Method | Path | Purpose |
|---|---|---|
| POST | `/omiai_assistant/get/{id}` body `{"_id":id}` | Chi tiết bot (schema chuẩn) |
| POST | `/omiai_assistant/get_list` | Danh sách bot |
| POST | `/omiai_assistant/search` | Tìm bot |
| POST | `/omiai_assistant/save_draft_v2` | Lưu BẢN NHÁP — **multipart** field `file` |
| POST | `/omiai_assistant/publish_v2` | **Xuất bản** — multipart field `file` |
| POST | `/omiai_assistant/update_info` | Cập nhật cấu hình |
| POST | `/omiai_assistant/training_data/add_v2` | (re)load 1 file training/RAG |
| POST | `/omiai_assistant/training_data/remove_v2` | Xoá 1 file training |
| POST | `/omiai_assistant/training` | Train toàn bộ |
| POST | `/omiai_assistant/training_status` | Trạng thái training |
| POST | `/omiai_assistant/bot_testing_v2` | Nhắn thử / kiểm tra bot |
| POST | `/omiai_assistant/message/search` | Lịch sử tin nhắn |
| POST | `/omiai_assistant/generate_sentences_instruction` | Sinh gợi ý câu mẫu |
| POST | `/omiai_assistant/get_evaluation_config` | Config đánh giá |
| POST | `/omiai_assistant/delete/{id}` / `delete_many` | Xoá |
| GET | `/omiai_assistant/get_attrs` | Thuộc tính |
| GET | `/omiai_assistant/get_list_for_role` | Bot theo vai trò |

## Save (save_draft_v2 / publish_v2) — multipart
```python
import requests, json
tok = json.load(open(r"...\oanh_session.json", encoding="utf-8"))["token"]  # cookie key "2"
bot = requests.post(base + "/omiai_assistant/get/{bot_id}", json={"_id": bot_id}, headers={"Authorization": "Bearer "+tok}).json()["payload"]
bot["system_prompt"] = "<nội dung prompt mới>"
r = requests.post(base + "/omiai_assistant/save_draft_v2",
    headers={"Authorization": "Bearer " + tok},
    files={"file": ("blob", json.dumps(bot, ensure_ascii=False).encode("utf-8"), "application/json")}, timeout=120)
# r.json()["payload"]["_id"] — GIỮ NGUYÊN id. is_draft:true, is_newest_version:false.
```
Verifed: gửi lại nguyên payload + sửa `system_prompt` → lưu 200, id không đổi, GET lại thấy prompt mới.

## RAG — "Dữ liệu khác" (warehouse_of_knowledge/other) — VERIFIED end-to-end
UI: **Đào tạo tab → Dữ liệu khác → Quản lý Dữ liệu khác → Thêm mới** (dropzone). Giới hạn: **mỗi file ≤ 15MB**; hỗ trợ `.xls,.xlsx,.doc,.docx,.pdf,.txt,.rtf`. Slot thông tin: Tên (bắt buộc), Mô tả, Ngôn ngữ (vi/en), "BOT được đào tạo" (linked bots).
Auth: các endpoint dưới ở **`external-v1-stg.omicrm.com`** + **`filestore-v1-stg.omicrm.com`** — dùng **`Authorization: Bearer <token>`** (cookie/`x-access-token` → **500 "Error Occurred!!!"**, chỉ Bearer hoạt động).

1) **Upload file → filestore**:
```python
r = requests.post("https://filestore-v1-stg.omicrm.com/file_store/put_v2"
    + "?business_type=warehouse_of_knowledge_files&keep_content_type=true&lng=vi&utm_source=web",
    headers={"Authorization":"Bearer "+tok},
    files={"file_0": ("rag_kienthuc_tonghop.docx", open(p,"rb").read(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
# filename viết THƯỜNG. Response payload[0].object_info:
# {"name":"<tenant_id>/warehouse_of_knowledge_files/<yyyy>/<mm>/<uuid>.docx",
#  "file_name":"rag_kienthuc_tonghop.docx","content_type":"...","length":...,...}
```

2) **Dedup theo tên** (tùy chọn, trùng sẽ hỏi xác nhận/dùng lại):
`POST external/omi_v2/warehouse_of_knowledge/other/get_id_by_name?lng=vi&utm_source=web` body `{"name":"<tên>"}` → `data` non-empty = đã tồn tại.

3) **Tạo record "Dữ liệu khác"**:
`POST external/omi_v2/warehouse_of_knowledge/other/add?lng=vi&utm_source=web`
```json
{"name":"rag_kienthuc_tonghop","language":"vi","description":"...",
 "type":"file","enable_training":true,"url_website":"","url_sitemap":"",
 "object_info":{"file_name":"rag_kienthuc_tonghop.docx",
   "content_type":"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
   "url_file":"<object name bước 1>", "file_type":"docx"},
 "add_bot_uuids":["<bot uuid>"],"remove_bot_uuids":[]}
```
⚠ `object_info.url_file` = object `name` từ bước 1 (KHÔNG phải URL); `file_type` = đuôi file ("docx"). Response payload: `{"_id":"<record_id>","file_id":"file-<uuid>","status":"not_training","bots_use_file":[{"uuid","id":"<bot_id>","name","status"}],"language":"vi",...}`. `add_bot_uuids` dùng **bot `uuid`**; record sẽ hiện `bots_use_file` link bot ngay.

4) **List/Kiểm tra**: `POST external/omi_v2/warehouse_of_knowledge/other/search?page=1&size=10&lng=vi&utm_source=web` (body `{}`) → `payload.items[]`. ⚠ `other/get_list` trả `payload:null` — phải dùng `search`. GET `.../other/total_training/get` → tổng. `delete`/`training`/`reload_file_online` = `other/<type>/<id>`.

5) **Gắn vào Ngữ cảnh bắt đầu (Kho tri thức → Dữ liệu khác)** rồi `save_draft_v2`:
- `bot.vector_store` (đang null → thay bằng):
```json
{"vector_store_id":"vs-<uuid>",
 "vector_store_files":[{"vector_store_file_id":"vs_file-<uuid>","file_id":"file-<uuid>",
   "file_training_status":"completed","ref_id":"<record _id>","language":"vi","total_website":null,"is_post":false}],
 "all_file_ref_ids":["<record _id>"]}
```
- `campaign.nodes[0].ai_analyze.vector_store_ids = ["<record _id>"]`.
- Frontend serializer (chunk 57015): `vector_store_ids = vector_store.vector_store_files.map(e=>e.ref_id)` — **`ref_id` = record `_id` của `other/add`** (KHÔNG phải `file_id`). Sau save, GET lại: `file_training_status:"completed"` = training xong; `vector_store_id`/`vector_store_file_id` server tự sinh.

6) **Prompt trong Ngữ cảnh bắt đầu**: "Hướng dẫn & Tính cách BOT" = `campaign.nodes[0].ai_analyze.content` (verify: set qua API → editor hiển thị trong drawer); "Khách hàng bắt đầu cuộc trò chuyện" dùng luôn `content`. Top-level `system_prompt` bổ sung prompt chung (2 nơi đều được).

7) **Bot `uuid` cần cho `add_bot_uuids`** = top-level `uuid` của bot (vd `87e27f1f-32fa-44aa-aadd-7c3d561a03e8`), khác `_id`.

## Bot object (top-level — 52 keys, từ GET thật)
```json
{"_id","created_date","create_by","last_updated_date","last_updated_by","is_deleted","tenant_id",
 "is_draft":true,"current_version":null,"versions_history":null,"is_newest_version":false,"is_publish":false,
 "last_publish_time":null,"uuid","assistant_id":"assistant-<uuid>_draft","assistant_name","assistant_avatar","assistant_description",
 "assistant_name_unsigned","assistant_description_unsigned","is_control":true,"is_inferences_qa":false,
 "mode_reply":"","content_reply":"","model":"gpt-4o-mini",
 "llm_config":{"enable":null,"presence_penalty":null,"frequency_penalty":null,"temperature":null,"top_p":null,"max_tokens":null},
 "system_prompt":"","is_pause":false,"iteration_config":null,"max_characters_reply":null,
 "context_kick_of_hook_ids":[],"draft_sync_last_version":false,"type":"SCENARIO_HANDLER",
 "question_answer":null,"vector_store":null,"api_knowledge":[],"is_v2":null,
 "topic_originals":null,"file_originals":null,
 "campaign":{"edges":{"connections":[]},"name_mappings":[...],"nodes":[...],"variables":[],"classifies":[]},
 "history_config":{"enable":false,"history_length":null,"conversation_history_length":null},
 "draft_key":"<tenant>_<uuid>_true","name_key":"<tenant>_<assistant_name>",
 "evaluation_configs":[],"natural_language_configs":[],"integrated_scope":{"type":"social","contact_ids":[],"contact_category_ids":[]},
 "is_public":null,"public_key":"<uuid4>"}
```

### campaign.name_mappings (editor view của BEGIN)
```json
[{"id":"<node_id>","type":"BEGIN_CONTEXT",
  "conditions":[
    {"id":"bot_can_not_answer","type":"bot_can_not_answer","intent":null,"data":[]},
    {"id":"customer_not_response","type":"customer_not_response","promptEndConv":"","waitingTime":3,
     "waitingTimeUnit":"minute","repeat":{"value":"0","label":"notRepeat"},"repeatContent":[],"intent":null,"data":[]}
  ]}]
```
CUSTOM_INTENT sẽ chèn vào `conditions[]` cùng vị trí (TRƯỚC 2 system) — schema intent đang xác minh bằng captor (xem cuối).

### campaign.nodes[] — BEGIN_CONTEXT (runtime)
```json
{"id":"<node_id>","is_first_node":true,"description":null,"description_type":null,"color":null,
 "position":{"x":"160","y":"40"},"node_type":"BEGIN_CONTEXT","conditions":null,"actions":null,
 "next_nodes":[],"fail_next_nodes":null,"success_next_nodes":null,"name":null,"is_collapse":false,
 "collapse_obj":{},"collapse_info":null,"width":334.0,"height":287.0,"related_position":null,
 "ai_analyze":{"content":"","context":null,"conditions":[],
   "collect_variables":[],"collect_position":null,"customer_response_wrong":null,
   "customer_not_response":{"waiting_time":180,"next_node":"","id":"customer_not_response","repeat_contents":null,"prompt_end_conv":"","action_steps":null},
   "customer_has_response":null,"bot_can_not_answer":{"waiting_time":null,"next_node":"","id":null,"repeat_contents":null,"prompt_end_conv":null,"action_steps":null},
   "collect_sentence_time":null,"chat_gpt_model":null,"active_time":null,"agent_conditions":null,
   "end_call_config":null,"customize_bot_config":null,"omi_ai_bot_config":null,"partner_ai_config":null,
   "limit_config":null,"question_answer_ids":[],"vector_store_ids":[],"api_knowledge_ids":[],
   "web_hook_id":null,"type":null,"assistant_id":"assistant-<uuid>_<node_id>_draft",
   "action_status":null,"context_map":null,"hearing":null,"vision":null,
   "chatx_api_key":null,"conversation_id":null,"user_id":null,"is_use_prev_convid":null,
   "pro_ai_api_key":null,"llm_config":null},
 "types":null,"waiting_time":null,"variables":[],"single_action":null,"unit_waiting_time":null,
 "value_waiting_time":null,"prioriy_conv_id":null,"prioriy_channel_id":null,"custom_sending":null,
 "sms_number":null,"sending_option":null,"delay_node_config":null}
```

## Kịch bản (scenario) — VERIFIED build nhanh chưa có action

Editor là **React Flow canvas** (như callbot). Palette bot: Ngữ cảnh (BEGIN_CONTEXT) / Kích hoạt ngữ cảnh (KICK_OFF_CONTEXT) / Điều kiện (CONDITION) / Hành động (ACTION) / Gửi tin nhắn chung (SEND_MESSAGE) / Thu thập thông tin (`$Pl.OMI_BOT_COLLECT_INFO`) / Kết thúc trò chuyện (`$Pl.END`). Node BEGIN ("Ngữ cảnh bắt đầu") có 2 khu: **Khách hàng bắt đầu cuộc trò chuyện** (= `ai_analyze.content`) và **Các trường hợp BOT nhận dạng** (= intents). Tab này = "Kịch bản".

### Intent custom — DUAL-SCHEMA (đã verify render + runtime accept)
- **Editor** `campaign.name_mappings[0].conditions` (CUSTOM_INTENT, 2 system CUỐI cùng):
```json
{"id":"<hid>","type":"CUSTOM_INTENT","name":"<Tên ý định>","personality":"","actionStep":[],
 "selectedIntent":null,"webhookId":"<tenant_id>-<uuid4>","webhookParam":{"bot_id":"<bot_id>","conv_id":""},
 "data":[{"isCustomComp":true,"targetType":"OMI_BOT_INTENT","id":"<uuid4>","content":"<câu khách nói>","selected":false,"chosen":false},
         {"isCustomComp":true,"targetType":"OMI_BOT_INTENT","id":"<uuid4>","content":"<câu khác>",...}]}
```
- **Runtime** `campaign.nodes[0].ai_analyze.conditions[]`:
```json
{"id":"<hid>","type":"CUSTOM_INTENT","name":"<Tên ý định>","next_node":"",
 "data":[{"id":"<uuid4>","type":"OMI_BOT_INTENT","content":"<câu khách nói>"}]}
```
- `hid` dùng CHUNG id cho cặp editor+runtime (trong quá trình làm: mỗi cái dùng uuid riêng vẫn render OK; dùng chung = sạch hơn).
- `name_mappings[0].conditions` phải kết thúc bằng đúng 2 system: `bot_can_not_answer` rồi `customer_not_response` (đừng chèn sau).
- Editor pre-fill: `"data":[{"isCustomComp":true,"targetType":"OMI_BOT_INTENT","id":...,"content":...}]` → hiển thị nhận diện; thiếu isCustomComp/targetType → hàng intent TRỐNG.
- Frontend serializer (chunk 57015, hàm G): runtime C-entry custom = `{id,type,next_node:"",name}` — không kèm data; data ở editor (`k.conditions`). Camera: rảnh data runtime vẫn OK.
- save_draft_v2 round-trip GIỮ NGUYÊN; `bot_testing_v2` trả `{"payload":true}` cho cấu hình hợp lệ (chỉ ACK, text thật chạy qua LiveTalk realtime).

### Quy trình build Kịch bản bằng API
1. GET bot → sửa `campaign.name_mappings[0].conditions` (custom + 2 system cuối) và `campaign.nodes[0].ai_analyze.conditions` (custom).
2. `save_draft_v2` (multipart file) → GET lại → reload editor page (CDP `Page.navigate` + sleep 4s) → đọc node text `.react-flow__node` để xác nhận.
3. Người dùng sau đó wire hành động/action trong UI (schema ACTION/Gửi tin nhắn/Kết thúc đang xác minh qua captor).

## UI mapping (đã thấy trên editor Zalo OA Bot)
- **Kịch bản tab**: "Ngữ cảnh bắt đầu" (= `system_prompt`), "Khách hàng bắt đầu cuộc trò chuyện", "Các trường hợp BOT nhận dạng" (= intents: bot_can_not_answer + customer_not_response + custom intent), nút **Xuất bản** / **Lưu lại**.
- **Đào tạo tab**: upload RAG file (docx/txt), trạng thái training.
- **Trò chuyện thử**: cửa sổ LiveTalk test (có nút "Tham gia", "Chuyển nhân viên phụ trách").
- Đường dẫn: `/ai/bot/edit/{bot_id}?lng=vi` (sửa bot), `/ai/bot/create` (tạo mới), `/ai/bot` (danh sách).

## Validation checklist (sau mỗi save — GET lại)
1. `system_prompt` = nội dung mới (đã ghi).
2. `is_draft:true`, `_id` giữ nguyên.
3. Intents (khi cấu hình): đủ ở `campaign.name_mappings[0].conditions` LẪN `campaign.nodes[0].ai_analyze.conditions`; 2 system CUỐI.
4. `history_config`, `max_characters_reply`, `mode_reply` đúng yêu cầu.
5. `assistant_name`/`assistant_description` hiển thị trong editor.
6. Nếu dùng RAG: `vector_store`/`question_answer`/`file_originals` có dữ liệu + training OK, test tin nhắn trả lời bằng kiến thức.
7. Không sửa `is_publish` trừ khi user yêu cầu xuất bản.

## Học schema intent/action từ UI (captor)
Inject script sau vào trang editor (CDP `Runtime.evaluate`), user thao tác trong Chrome, rồi đọc `window.__omiCaps`:
```python
sniff = r"""(() => { if (window.__omiCapsInjected) return {already:true}; window.__omiCaps=[];
 const want = u => (/omiai_assistant|omiai_v2|chatbot-gateway/i.test(u) && !/\.png|\.svg|\.js|\.css/.test(u));
 const push=(kind,url,body,resp)=>{ try{ if(window.__omiCaps.length>200) window.__omiCaps.shift();
   window.__omiCaps.push({t:Date.now(),kind,url:String(url).slice(0,300),body:String(body||'').slice(0,300000),resp:String(resp||'').slice(0,300000)});}catch(e){} };
 const of=window.fetch; window.fetch=function(u,o){ try{ const url=typeof u==='string'?u:(u&&u.url)||'';
   if(want(url)){ let b=''; if(o&&o.body){ b=typeof o.body==='string'?o.body:'';
     try{ if(o.body instanceof FormData){ b='[FormData]'; for(const kv of o.body.entries()) b+='\n'+kv[0]+': '+(typeof kv[1]==='string'?kv[1].slice(0,300):'['+kv[1].constructor.name+']');}}catch(e){} }
     push('fetch',url,b); }
   return of.apply(this,arguments).then(r=>{ const c=r.clone(); c.text().then(t=>{try{push('fetch-resp',url,null,t);}catch(e){}}).catch(()=>{}); return r; }); }catch(e){ return of.apply(this,arguments); } };
 const ox=window.XMLHttpRequest.prototype.open; window.XMLHttpRequest.prototype.open=function(m,url){ this.__u=url; return ox.apply(this,arguments); };
 const os=window.XMLHttpRequest.prototype.send; window.XMLHttpRequest.prototype.send=function(body){ try{ const url=this.__u||'';
   if(want(url)){ let b=body; try{ if(body instanceof FormData){ b='[FormData]'; for(const kv of body.entries()) b+='\n'+kv[0]+': '+(typeof kv[1]==='string'?kv[1].slice(0,300):'['+kv[1].constructor.name+']'); } }catch(e){}
     push('xhr',url,typeof b==='string'?b:String(b)); this.addEventListener('load',()=>{try{push('xhr-resp',url,null,this.responseText);}catch(e){}}); } }catch(e){}
    return os.apply(this,arguments); };
 window.__omiCapsInjected=true; return {ok:true}; })()"""
```
Rồi: `c.eval_js("JSON.stringify(window.__omiCaps.filter(x=>x.kind!=='fetch-resp'&&x.kind!=='xhr-resp').slice(-15))")`. Ghi schema học được vào đây.
## API Knowledge ("Truy vấn" trong Kho tri thức) — VERIFIED (save_draft_v2 round-trip OK)
- Khai ở top-level `bot.api_knowledge[]` + bật cho Ngữ cảnh bắt đầu bằng `campaign.nodes[0].ai_analyze.api_knowledge_ids` (list `ref_id`). Entry không nằm trong `api_knowledge_ids` = có trong kho nhưng node không dùng.
- Biến đa kênh có sẵn ở `campaign.variables` (type `SOCIAL`): `social_phone_number_linked` (SĐT khách liên kết Zalo OA/FB), `social_customer_name_linked`. Dùng trong body dạng `{{social_phone_number_linked}}`.
```json
{"ref_id":"request_lay_thong_tin_chi_tiet_khach_hang","name":"Lấy thông tin chi tiết khách hàng từ CRM",
 "url":"https://public-v1-stg.omicall.com/api/v2/contact/search?page=1&size=1","method":"POST",
 "headers":[{"id":"<10 ký tự ngẫu nhiên>","key":"Content-Type","value":"application/json"},
            {"id":"<10 ký tự>","key":"Authorization","value":"Bearer <access_token>"}],
 "body_type":"raw","body_json":"{\n  \"keyword\": \"{{social_phone_number_linked}}\"\n}",
 "variables":null,"prompt":"<Hướng dẫn BOT: khi nào gọi>","query_prompt":"<Hướng dẫn BOT đọc kết quả>",
 "param_type":"json","time_out":60,"api_response_guide":[],"retrieve_data":null}
```
- `ref_id` = `request_` + slug tên (không dấu, `_`). Header rỗng mặc định: `[{"id":..,"key":"","value":""}]`.
- Gọi API từ trang editor đã đăng nhập (CDP `Runtime.evaluate` + `fetch` với token cookie) — không cần lưu token ra file.
- Public API OMICall (contact search…): xem `omicall-public-api.md` (token hết hạn 24h → header Authorization phải thay định kỳ).

## Diagnostic checks for customer API and LiveTalk tester — verified 2026-10-01

- When the user directly supplies an OMICall Public API Key for a customer API test, exchange it via GET `/api/auth?apiKey=<user-supplied-key>` and use `Authorization: Bearer <payload.access_token>`. Do not use a bare API Key as the Authorization value for `/api/v2/contact/search`: the verified negative test returned HTTP 401. Do not extract session cookies or JWTs.
- Invoke the active query exactly as saved and verify both HTTP status and application status. Non-sensitive excerpt of the verified search response: `{"status_code":9999,"payload":{"total_items":1}}`. Confirm the returned phone equals the requested phone. This proves the request works; it does not prove the chatbot executed it during a conversation.
- In the tested staging tenant, the user-key-derived Public API access token also authorized `omiai_assistant/get/{id}` and `save_draft_v2`. Verify authorization per tenant and operation; do not assume this works in every deployment.
- The SCENARIO_HANDLER tester wrapper in public frontend module 92318 embeds `/omi-bot-chat-live-talk` with `domain`, `botId` (bot UUID, not Mongo `_id`), `botName`, `tenantId`, `contactId`, `name`, `email`, and `phone`. The default identity comes from the signed-in profile; closing/reopening the popup only changes visibility.
- The iframe route waits for `ready`, then calls `omiLiveTalk.createConvs()`. Rooms are reused by bot UUID + contactId when active, so reloading alone does not guarantee a new conversation.
- LiveTalk sends test messages to `POST https://livetalk-v2-stg.omicrm.com/widget/message/omibot/test` as multipart fields `uuid`, `content` (URL-encoded), `room_id`, `bot_id`, `user_name`, `user_id`, `tenant_id`, and optional `quote_id`. This is separate from the gateway helper named `bot_testing_v2`.
- The inspected wrapper/iframe/widget scripts did not send `is_draft`, `is_test`, or a version number. Whether the backend selects draft or published remains unverified. Do not claim a draft test passed merely because a saved query works in a direct API call, and do not publish without a user request.
- After temporarily fixing a phone for a test, restore the exact pre-test variable and re-read the saved draft. Preserve unrelated intents, query references, and publish state.

Public implementation evidence: `_app-577b9e01f73ca56b.js` (module 92318), `pages/omi-bot-chat-live-talk-ec86399a5e373422.js`, and `https://cdn.omicrm.com/script/livetalk/main.js`. No credential values or private customer data are included here.
