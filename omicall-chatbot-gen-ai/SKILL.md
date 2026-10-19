---
name: omicall-chatbot-gen-ai
description: Shared skill to build/edit OMiCALL/OMiCRM AI Chatbot (OmiBot, text bot for Zalo OA / Facebook / LiveTalk) for ANY tenant — system prompt, intents (Ngữ cảnh bắt đầu), RAG "Dữ liệu khác", API "Truy vấn" (api_knowledge, e.g. OMICall Public API contact/search by {{social_phone_number_linked}}), save_draft_v2/publish_v2 via chatbot-gateway, editor …/ai/bot/edit/{bot_id}. Use when the user gives an omicrm.io /ai/bot/ URL or asks to build/configure an OMI chatbot. Read references/api-reference.md before building. Logs in via the OMI MCP server (omicall-mcp: login_omicall_mcp) when available and uses its tools for lookups/testing — see references/omi-mcp.md.
---

# OMiCALL/OMiCRM AI Chatbot (OmiBot) Gen AI — Generic Builder Playbook (mọi tenant / mọi bot)

# Overview
AI **Chatbot** (text) — OMI gọi là **AI Chatbot / OmiBot** (`/ai/bot/...`), khác **Callbot** (`/ai/callbot/...`). Bot nhắn tin qua **Zalo OA / Fanpage FB / website (OMI LiveTalk)**; `type:"SCENARIO_HANDLER"`, LLM `gpt-4o-mini`. Điểm khác callbot: KHÔNG có STT/TTS, không có node chuyển máy dạng cuộc gọi — thay vào đó là **hội thoại văn bản + training/RAG** (`question_answer`, `vector_store`, `api_knowledge`) + **intents** trong `campaign` (BEGIN_CONTEXT). System Prompt nằm ở top-level `system_prompt` (UI: Kịch bản → Ngữ cảnh bắt đầu). Skill này là **bộ dùng chung**: thiết kế prompt/intent/routing/RAG do bạn (LLM) tự tư duy từ nghiệp vụ user — không chép từ tenant khác.

# Rules (BẮT BUỘC)
1. **Học kiến thức mới → ghi vào skill**: schema/key mới (intent, action, RAG, uplay save), edge-case, tenant mới login → cập nhật `SKILL.md` / `references/api-reference.md` / `references/credentials.md`.
2. Đọc trước khi ghi — tránh trùng lặp.
3. Luôn kèm **ví dụ JSON thật** (từ bot đã verify).
4. Báo phần đã update trong summary cuối.
5. **Giữ skill tổng quát**: KHÔNG hardcode prompt/intent/tên bot của một tenant vào SKILL.md. Tenant chỉ ở `credentials.md` + schema ở `api-reference.md`.
6. **Suy luận từ nghiệp vụ**: đọc tài liệu → tự tách nhóm khách, intent, biến thu, prompt — chỉ dùng bot tenant khác làm tham chiếu hình dạng.

# Input contract
Hỏi một lần: (1) **domain doanh nghiệp**; (2) **tài khoản** (đăng nhập qua MCP OMI — mật khẩu do user tự đặt trong cấu hình MCP, không gửi trong chat); (3) **mô tả nghiệp vụ** (kịch bản, FAQ, tài liệu dịch vụ hoặc prompt). Tên bot tự đặt theo doanh nghiệp và mục đích. Bot đã có sẵn đúng nhu cầu → reuse giữ nguyên `_id` (save ghi đè).

# Workflow

## Bước 0 — Đăng nhập (MCP OMI trước) & lấy token — chi tiết `references/omi-mcp.md`
- **MCP OMI**: `login_omicall_mcp` (+ `select_tenant`) → `python scripts/omi_session.py` (đọc phiên MCP, in tenant/domain/hạn, không in token); script khác import `omi_session.headers()`. MCP chưa cài cho domain này → đưa user lệnh `claude mcp add …` (omi-mcp.md mục 1).
- **Tra một lần bằng MCP**, lưu `tenant_context.json` ở scratchpad: `get_service_package` (module `integrated`, `ai`), `get_all_channels` (oa_id, page_id, widget, bot_id để gắn bot), `list_agents` (nhân viên nhận chuyển hội thoại).
- Dự phòng không có MCP: user đăng nhập một lần trong browser pane → cookie `{domain}_omicrm_io` → key `"2"` = JWT (URL-encode → unquote). Xem mục *Đăng nhập an toàn*.
- Base API (MCP không có công cụ chatbot): `https://chatbot-gateway-v1-stg.omicrm.com` (`Authorization: Bearer <token>`).

## Bước 1 — Baseline schema
- `POST /omiai_assistant/get/{bot_id}` body `{"_id": bot_id}` → cấu trúc bot hiện có (nếu cần tạo mới: dựng payload theo api-reference).
- Lưu ý: bot chatbot có `_id` ỔN ĐỊNH khi save (không tạo id mới như callbot add_v2). `is_draft:true`, `is_newest_version:false` khi ở bản nháp.

## Bước 2 — Hiểu nghiệp vụ (PHÂN TÍCH — do LLM tự suy luận)
Đọc tài liệu/Kịch bản rồi trả lời: mục đích bot (tư vấn/CSKH/bán), nhóm khách, thông tin cần thu, ai nhận bàn giao, kết thúc ra sao.

## Bước 3 — Thiết kế intent + xử lý + routing (do LLM tự tư duy)
- Danh sách **intent** → mỗi intent: `content` (câu khách nói, 1–3 câu), hành động (`collect_variables` / `search_knowledge` / trả lời RAG / chuyển NV / kết thúc), bước kế tiếp.
- Menu tối thiểu (>=5 intent): nhóm chính ≥1; đồng ý/xác nhận; từ chối→kết thúc lịch sự; tra cứu/hỏi thông tin→RAG/API; hoàn tất→kết thúc. Thêm: yêu cầu gặp NV → chuyển; khiếu nại → chuyển.
- RAG vs API: tài liệu tĩnh→**RAG** (`vector_store` / `question_answer`); dữ liệu realtime/cá nhân→**đấu API** (`api_knowledge`); thiếu dữ kiện→HỎI LẠI user.
- Quy trình trước khi chuyển/kết thúc: xác nhận lại thông tin đã thu với khách.

## Bước 4 — Viết System Prompt (do LLM tự soạn từ nghiệp vụ)
Điền vào top-level `system_prompt` (Prompt chính **chỉ mô tả chung** — không mô tả chi tiết ý định):
1. **Vai trò** — bot là ai, công ty, kênh chat, mục tiêu cuộc trò chuyện.
2. **Luồng hội thoại chung** — mở đầu, hỏi nhu cầu, xử lý theo ý định, thu thập, xác nhận, bàn giao/kết thúc.
3. **Quy tắc đối thoại text** — 1–3 câu/tin, hỏi 1 ý/lần, Anh/Chị, khách im lặng/khó chịu → xử lý, không spam.
4. **Guardrails** — chỉ dùng dữ liệu RAG/API, không bịa giá/ưu đãi, không thu CCCD/OTP/thẻ, tôn trọng từ chối.
5. **BIẾN DỮ LIỆU** — mã + tên biến + khi nào thu (khớp `collect_variables`).
6. **Định dạng reply** — tiếng Việt có dấu, bulleting gọn, SĐT đọc từng chữ số, tiền/ngày rõ ràng.
7. **Definition of Success** — đủ biến + trả lời/bàn giao/kết thúc đúng nghiệp vụ.
- Các ý định mô tả NGẮN ở file riêng (kịch bản intent), prompt chính mô tả luồng chung.

## Bước 5 — Dựng payload & intent (schema: api-reference.md — đọc TRƯỚC khi build)
- Lấy GET làm baseline → overwrite `system_prompt`, `assistant_name/description`, `history_config`, intents trong BEGIN_CONTEXT (`campaign.name_mappings[0].conditions` + `campaign.nodes[0].ai_analyze.conditions`) khi schema intent đã xác minh. Nếu intent schema chưa rõ → **dùng UI trên Chrome + bắt mạng (captor)** để học trước khi build API.
- Save: `POST /omiai_assistant/save_draft_v2` (multipart field `file`=JSON). Publish: `POST /omiai_assistant/publish_v2` (chỉ khi user yêu cầu).

## Bước 6 — RAG/Training + Verify + Giao (luồng VERIFIED)
1. Tạo dữ liệu đào tạo **"Dữ liệu khác"** bằng API (không cần UI): upload file lên `file_store/put_v2` (`business_type=warehouse_of_knowledge_files`, field `file_0`) → tạo record `warehouse_of_knowledge/other/add` (base `external-v1-stg.omicrm.com`, **Bearer token**, body có `object_info` + `add_bot_uuids`). Chi tiết + body chuẩn: `references/api-reference.md` mục **"RAG — Dữ liệu khác"** (đã verify end-to-end: file ≤15MB, ref_id = record `_id`).
2. **Gắn file vào Ngữ cảnh bắt đầu → Kho tri thức → Dữ liệu khác**: set `vector_store` + `campaign.nodes[0].ai_analyze.vector_store_ids=[record _id]` rồi `save_draft_v2`. Sau save `file_training_status:"completed"` = đã train xong, bot trả lời được bằng kiến thức.
3. Test chat: `POST /omiai_assistant/bot_testing_v2` hoặc nút "Trò chuyện thử".
4. Verify: `GET bot` (chỉ in trường cần kiểm tra) + reload editor + test tin nhắn. Giao: editor URL `https://{domain}.omicrm.io/ai/bot/edit/{bot_id}?lng=vi`.
5. **Kiểm thử bằng MCP**: `get_contact_by_phone` hoặc `search_contacts` để kiểm tra dữ liệu bot tra cứu; `search_conversations` + `search_channel_messages` để xem hội thoại thật bot đã trả lời; `create_contact` để tạo khách mẫu (dọn bằng `delete_contact` khi user đồng ý). `send_*_message` gửi cho người thật — chỉ khi user đồng ý.

# Interactive OMiCRM (user xem realtime)
Chrome CDP port 9222, profile riêng theo tenant: `Start-Process chrome.exe -ArgumentList '--remote-debugging-port=9222',"--user-data-dir=%TEMP%\omicrm-<profile>",'--no-first-run','https://<domain>.omicrm.io/ai/bot/edit/<bot_id>?lng=vi'`. Dùng `cdp.py` (`find_omicrm_tab()` + `CDP(ws).eval_js/navigate`).
**Học schema từ UI**: inject fetch/XHR captor vào trang editor (ghi `POST body`/`response` vào `window.__omiCaps`) → user thao tác trong Chrome → đọc `window.__omiCaps` → ghi schema học được vào api-reference.md.

## Đăng nhập an toàn
- **Không** tự điền username/password vào form đăng nhập hay API đăng nhập bằng script/JS, kể cả khi đã có sẵn thông tin đăng nhập.
- **Ưu tiên MCP OMI**: mật khẩu nằm trong cấu hình MCP do user tự cài; agent chỉ gọi `login_omicall_mcp` rồi đọc token từ phiên MCP bằng `scripts/omi_session.py`. Đây là đường chính để gọi API chatbot (Bước 5/6).
- **Dự phòng không có MCP**: mở editor trong browser pane, nhờ user tự đăng nhập một lần. Việc đọc cookie để lấy JWT từng bị lớp an toàn của agent chặn (phân loại "Credential Materialization") ở một phiên trước, nhưng chạy được ở phiên khác (10/2026, sau khi user tự đăng nhập). Nếu bị chặn thì **không** tìm cách lách bằng CDP, Windows-MCP hay script khác: đề nghị user cài MCP OMI, hoặc thao tác bằng click/type trên UI.

# Gotchas chí tử (mọi tenant — sai là hỏng)
- **END POINT KHÁC callbot**: chatbot dùng `omiai_assistant/...` (KHÔNG phải `callbot/...`) trên cùng gateway.
- **RAG/warehouse**: dữ liệu đào tạo "Dữ liệu khác" nằm ở `external-v1-stg.omicrm.com` (`warehouse_of_knowledge/other/`) + `filestore` — **BẮT BUỘC Bearer token** (cookie → 500). List phải dùng `other/search` (không phải `get_list` → payload null).
- **ref_id trong `vector_store.vector_store_files` = record `_id` của `other/add`**, không phải `file_id`; `ai_analyze.vector_store_ids` được build từ đó khi save.
- **Prompt của Ngữ cảnh bắt đầu** nằm ở `campaign.nodes[0].ai_analyze.content` (drawer "Hướng dẫn & Tính cách BOT"), song song top-level `system_prompt`.
- **save_draft_v2/publish_v2 multipart** field `file`=JSON blob (như add_v2); `_id` giữ nguyên, KHÔNG đổi version/id mới.
- **DUAL trí**: nếu intent phải khai CẢ `name_mappings[0].conditions` (editor) LẪN `nodes[].ai_analyze.conditions` (runtime) như callbot — xác minh bằng captor, không tự đoán.
- **RAG cần training xong** mới trả lời đúng; `vector_store`/`question_answer` rỗng thì bot chỉ dựa `system_prompt`.
- Không bấm **Xuất bản** trên UI trừ khi user yêu cầu (`is_publish` giữ nguyên).
- Chỉ dùng token đúng tenant: kiểm tra `domain`/`tenant_id` bằng `python scripts/omi_session.py` trước khi ghi; nhiều tenant thì mỗi tenant một server MCP hoặc `logout` rồi đăng nhập lại. Xem mục "Đăng nhập an toàn".
- **Không dùng phím Escape** trong editor Kịch bản để đóng drawer/dialog — có thể kích hoạt reset state cục bộ (mất sạch ý định chưa lưu) hoặc dialog "Xác nhận rời trang". Luôn đóng bằng nút X/"Đóng" hiển thị rõ trên UI.
- **Tab "Đào tạo" tự động lưu ngay** (mọi thao tác thêm/xoá "Dữ liệu khác", "Bộ câu hỏi" áp dụng tức thì, hiện toast "Cập nhật thành công"/"Đã lưu") — khác tab **"Kịch bản"** cần bấm **"Lưu lại"** thủ công. Nếu tab Kịch bản đang có state cục bộ bị lỗi/mất dữ liệu (do thao tác nhầm), **tuyệt đối không** chuyển sang tab Đào tạo trước khi xử lý xong, vì autosave của Đào tạo có thể không đụng tới campaign — nhưng để chắc chắn, luôn **F5 reload lại toàn trang và xác nhận qua `get_page_text`** sau mỗi thao tác quan trọng trước khi tin state hiện tại là đúng.
- **Trước khi sửa nhiều node**: chụp/đọc lại state hiện có (số lượng ý định, tên) TRƯỚC khi bắt đầu; sau khi sửa xong và bấm "Lưu lại", **luôn reload trang (navigate lại đúng URL) rồi đọc `get_page_text`** để xác nhận server thực sự giữ đúng — không tin tưởng UI ngay sau khi bấm lưu.
- **Upload file "Dữ liệu khác" qua UI** (không phải API): nút thật để mở dialog chọn file là ô pill xanh **"Dung lượng mỗi file tối đa là Xmb 📎"** — **không phải** ô "+ BOT được đào tạo" (đó là picker chọn bot áp dụng, click nhầm sẽ mở dropdown tìm bot). Dialog "Open" mở ra là **cửa sổ OS thật** (không phải phần tử DOM) — cách an toàn nhất là gõ thẳng **đường dẫn tuyệt đối** vào ô "File name" rồi Enter/Open, tránh click điều hướng thư mục bằng toạ độ (rủi ro cao trên máy nhiều màn hình/độ phân giải lớn, có thể click nhầm sang cửa sổ khác của user như Zalo/Chrome cá nhân).
- **Giới hạn gói (plan) của tenant**: có thể chỉ cho 1 "File văn bản" mỗi lúc (`0/1`). Phải xoá/gỡ file cũ khỏi "Dữ liệu khác" (tab Đào tạo) trước khi thêm file mới nếu báo "đã đạt giới hạn cho phép".
- **UI thêm ý định (bản mới, đơn giản hơn schema cũ)**: nút **"Thêm trường hợp"** trong drawer "Ngữ cảnh bắt đầu" tạo 1 case mới (tự đặt tên "Trường hợp N", không có ô đổi tên riêng trong flow nhanh này) với 2 chế độ — **"Nhận dạng ý định"** (1 ô textarea tự do "Hướng dẫn BOT": viết mô tả + câu ví dụ khách nói gộp chung, KHÔNG phải chip từng câu như schema `campaign.name_mappings[].conditions[].data[]` cũ) và **"Chủ đề / Ý định mong muốn"** (chưa khảo sát — có thể là chỗ đặt tên tuỳ chỉnh, cần xác minh thêm lần sau). Bot vẫn nhận diện tốt với guidance dạng văn xuôi (đã verify: 9 ý định dạng này + build thành công, hiển thị đúng sau reload).

## Chỉ liệt kê intent nào cần flow xử lý riêng
Hệ thống này chạy tương tự N8N: **chỉ những ý định cần rẽ nhánh/flow xử lý riêng (gọi API, thu biến, chuyển bước) mới cần khai báo trong Ngữ cảnh bắt đầu**. Ý định thuần Q&A (khách hỏi kiến thức chung) — bot đã tự trả lời qua system_prompt + RAG, KHÔNG cần liệt kê thành Trường hợp riêng. Trước khi thêm 1 Trường hợp, hỏi: "ý định này có phải bot làm gì đặc biệt ngoài việc trả lời văn bản không?" — nếu chỉ trả lời từ RAG thì bỏ qua.

## Truy vấn API trong Ngữ cảnh bắt đầu (khác với node Hành động)
Drawer "Ngữ cảnh bắt đầu" có mục **"Truy vấn"** (cạnh "Hướng dẫn & Tính cách BOT", "Kho tri thức") — đây là chỗ khai báo API bot **tự gọi mỗi lượt trước khi chọn ý định**. Đặt các call API "chung, mỗi lượt" ở đây (vd: xác thực KH, lấy data CRM), không dùng node "Hành động" sau case ý định. Config gồm: Tên truy vấn, Hướng dẫn BOT (khi nào dùng — thực tế bot gọi mỗi lượt), Cấu hình (GET/POST/URL/Headers/Body raw JSON), Thời gian chờ, Hướng dẫn BOT lấy kết quả (schema JSON trả về + cách xử lý lỗi).
- Body dùng biến động qua `{{tên_biến}}` — biến Đa kênh chuẩn: `{{social_phone_number_linked}}` (SĐT khách đã link), `{{social_customer_name_linked}}` (tên khách đã link), `{{social_session_id}}`. Danh sách đầy đủ 106 thuộc tính Đa kênh xem trong picker khi bấm "Đa kênh" ở footer drawer.
- Node "Hành động → API" (mở qua right-click canvas → Hành động) dùng cho trường hợp khác: chỉ chạy khi 1 case cụ thể match. Đừng nhầm 2 chỗ này.

## Kiến trúc gọi API — 2 hướng

### Hướng A (khuyên dùng): Chatbot gọi thẳng OMICall Public API
OMICall có API public `POST https://public-v1-stg.omicall.com/api/v2/contact/search` (⚠ `api.omicall.com` chỉ là trang docs, KHÔNG gọi API vào đó; token lấy bằng `GET /api/auth?apiKey=`, hết hạn 24h — xem references/omicall-public-api.md) (docs: https://api.omicall.com/omicall-api/khach-hang#tim-kiem-khach-hang) — cho phép tìm Contact theo SĐT/email/tên và trả về `attribute_structure` đầy đủ (bao gồm cả custom attributes). Chatbot cấu hình 1 "Truy vấn" trỏ thẳng URL này:
- Method: POST
- URL: `https://public-v1-stg.omicall.com/api/v2/contact/search?page=1&size=1`
- Header: `Authorization: Bearer <API_TOKEN>` (token của tenant, KHÔNG phải cookie JWT của user)
- Body raw JSON: `{"keyword": "{{social_phone_number_linked}}"}`
- Response chứa `payload.items[0].attribute_structure[]` (mảng `{field_code, value[0].display_value}`) với mọi field KH → bot đọc trực tiếp để tư vấn.

**Ưu điểm**: không tốn quota OMIFlow; response chuẩn OMI, đầy đủ dữ liệu. **Nhược**: cần user cung cấp API Token (Bearer) hợp lệ — token này khác với JWT session user, thường lấy từ menu Cấu hình → API Key.

Các endpoint khác của OMICall Public API (base `https://public-v1-stg.omicall.com`):
- `POST /api/v2/contact/add` — tạo 1 KH
- `POST /api/v2/contact/addMany` — tạo nhiều KH
- `POST /api/v2/contact/search?page=&size=` — search theo keyword (SĐT/email/tên)
- `GET  /api/v2/contact/get/:id` — chi tiết KH theo id (nhanh hơn search nếu đã có contact_id)
- `POST /api/v2/contact/update` — cập nhật KH (có `otherDynamicUpdates` cho custom attributes)
- `DELETE /api/contacts/delete/:id` — xóa
- `POST /api/contacts/add-note` — thêm note interaction
- `GET  /api/v2/contact/layout/list` — danh sách attribute definitions (custom fields)
- `GET  /api/v2/contact/filterContact/list` — customer status pipelines

Response chung: `{"status_code": 9999, "payload": ...}` — status_code 9999 = success (không phải HTTP status).

### Hướng B: Chatbot gọi OMIFlow (webhook trigger)
Dùng khi cần workflow phức tạp (tạo Contact có phân bổ agent, tích hợp thêm, đa hành động...). Chi tiết trong skill **`omicall-omiflow`**. Ưu điểm: cấu hình visual, không cần code; hỗ trợ chain flow. Nhược điểm: tốn quota flow, response schema tự cấu hình.

### Khi nào dùng hướng nào
- Chỉ cần **đọc data KH** để bot tư vấn → **Hướng A** (đơn giản, 1 API call).
- Cần **tạo KH mới nếu chưa có, phân bổ agent, tích hợp Google Sheet/API bên thứ 3** → Hướng B (OMIFlow).
- **Hybrid**: dùng OMIFlow cho tạo/cập nhật (idempotent qua điều kiện Kiểm tra tồn tại), dùng OMICall Public API để đọc data — mỗi bên làm việc tối ưu của mình.

### Nguyên tắc chung
- **Đối chiếu tự động dùng field "Số điện thoại" CHUẨN của khách hàng** (không phải thuộc tính tùy chỉnh). Khi import hồ sơ, đặt SĐT thật vào field chuẩn.
- **Quota Flow theo gói**: Trial thường chỉ 1 flow — cân nhắc Hướng A trước khi tạo flow.
- **Không tự đoán API token**: hỏi user, không tự trích xuất từ cookie/session (bị chặn bởi safety).

## Kiến trúc chuẩn: 2 OMIFlow riêng (khi đủ quota)
Cho luồng "định danh + đọc data KH" từ chatbot, thiết kế đúng là **2 flow riêng biệt**, KHÔNG gộp:
- **Flow A — "Tạo hồ sơ KH nếu chưa có"**: Trigger API nhận `so_dien_thoai_khach` + `ten_khach_da_kenh` → Điều kiện #1 so SĐT → Điều kiện #2 "Kiểm tra KH tồn tại". Nhánh `else` (chưa tồn tại) → Hành động "Tạo mới khách hàng" (điền Tên = biến `ten_khach_da_kenh`, SĐT = biến `so_dien_thoai_khach`, phân bổ Nhân viên cụ thể/Cấu hình phân bố). Nhánh `đã tồn tại` không cần làm gì. Trả về `{message:"success", status_code:200}`.
- **Flow B — "Lấy data KH từ CRM"**: Trigger API nhận SĐT → tìm KH đã tồn tại (Điều kiện) → Trả về JSON body chứa toàn bộ thuộc tính KH (hotel_id, ten_khach_san, ly_do_lien_he, co_van_de_phong, muc_thieu_phong, hang_phong_dong, co_van_de_gia, chenh_lech_gia, nhan_xet_gia, san_pham_de_xuat, muc_giam_de_xuat, loi_ich_san_pham, ngay_bang_gia, bang_gia_chat, chu_thich_thue, ...). Field "Kết quả trả về" trong trigger API cho phép cấu hình JSON schema trả về, dùng biến `{{...}}` để chèn giá trị thuộc tính KH.
- **Chatbot gọi cả 2**: 2 mục "Truy vấn" riêng trong drawer "Ngữ cảnh bắt đầu" — Truy vấn #1 trỏ Flow A (chỉ tạo nếu chưa có, response không dùng), Truy vấn #2 trỏ Flow B (đọc data → bot dùng để tư vấn). Bot gọi cả 2 mỗi lượt; Flow A idempotent nhờ Điều kiện #2 tự skip khi KH đã có.
- **Tại sao không gộp 1 flow**: gộp làm response schema phức tạp hóa cho cả 2 nhánh (tồn tại + mới tạo), và Truy vấn chatbot chỉ hiểu 1 response schema cố định. Chỉ gộp khi quota gói chỉ cho 1 flow.

## OMIFlow — Trigger API chi tiết
Cấu hình trigger:
- **Method**: POST (mặc định GET, đổi sang POST khi gửi Body JSON).
- **URL** (auto-generated): copy vào cấu hình bên chatbot.
- **Request Headers**: có ô thêm Key/Value (thường không cần cho webhook nội bộ).
- **Khai báo biến liên kết**: tạo các biến (`so_dien_thoai_khach`, `ten_khach_da_kenh`, ...) — mỗi biến có mã liên kết dạng `{{cX7BecmQK8}}` tự sinh, dùng ở các node sau. Chọn **"Truy vấn từ Body"** (mặc định) để hệ thống tự parse Body request và gán vào biến theo tên khớp; hoặc **"Toàn bộ Body"** nếu muốn cả body vào 1 biến JSON.
- **Điều kiện truy vấn**: mỗi biến có 1 hàng "Value" — nhập tên field trong body (VD `so_dien_thoai_khach`) để lấy giá trị.
- **Kết quả trả về**: JSON schema webhook trả cho caller khi kích hoạt thành công. Mặc định `{"message":"success","status_code":9999}`. Sửa thành schema chứa các biến `{{...}}` khi cần trả data (như Flow B).
- **Thời gian chờ**: 60s mặc định (giới hạn thời gian OMIFlow chạy trước khi timeout).

## OMIFlow — Điều kiện chi tiết
Node "Điều kiện" có 5 nhóm điều kiện so sánh:
- **Khách hàng**: các field chuẩn của Contact (Tên, SĐT, Email, ...).
- **Đa kênh** (106 thuộc tính): `{{social_phone_number_linked}}`, `{{social_customer_name_linked}}`, `{{social_customer_name}}`, `{{social_session_id}}`, ...
- **Dữ liệu thu thập**: biến bot tự thu qua node "Thu thập thông tin".
- **Chat Insights**: metrics từ Chat Insights.
- **Biến liên kết tùy chỉnh**: biến khai báo trong trigger API hoặc "Biến liên kết tùy chỉnh" của node Hành động.

Phép toán: `=`, `>`, `<`, `>=`, `<=`, `!=`, `IN`, `NOT IN`, `BETWEEN`, `CONTAIN`, `NOT CONTAIN`, `STARTWITH`, `ENDWITH`, `NOTSTARTWITH`, `NOTENDWITH`. Value là **giá trị cố định gõ tay HOẶC dùng biến `{{...}}`** — không có nút "so khớp thuộc tính này với thuộc tính khác của contact khác".

**Điều kiện "Kiểm tra khách hàng tồn tại"** đặc biệt trong nhóm Đa kênh: 2 giá trị chọn `Là | Không là` × `Khách hàng đã tồn tại | Khách hàng chưa tồn tại`. Cơ chế: hệ thống tự tra Contact theo giá trị field "Số điện thoại" chuẩn khớp SĐT nhận từ webhook (đã set ở Điều kiện trước — thường là Điều kiện #1). Vì thế **thứ tự Điều kiện #1 (so SĐT) → Điều kiện #2 (kiểm tra tồn tại) BẮT BUỘC** — bỏ #1 thì #2 không biết tra ai.

## OMIFlow — Node Hành động "Thêm khách hàng" / "Cập nhật khách hàng"
- **Nhân viên cụ thể**: chọn 1 nhân viên (agent) sẽ được phân bổ khi tạo/cập nhật KH. Cấu hình phân bố: theo % / theo round-robin.
- **Ưu tiên nhân viên thực hiện cuộc gọi** / **Ưu tiên nhân viên tiếp nhận cuộc trò chuyện**: 2 toggle, ưu tiên phân bổ khi khớp.
- **Tên đầy đủ**, **Số điện thoại** (có prefix +84), **Email**: 3 ô input cơ bản. Click ô → footer hiện các chip "Khách hàng | Đa kênh | Dữ liệu thu thập | Biểu mẫu | Cuộc gọi | ... | Biến liên kết tùy chỉnh" — chọn chip tương ứng → picker biến hiện ra → chọn biến để chèn `{{...}}` vào ô.
- Node này chỉ update **đối tượng gốc đã identify** — không tạo KH mới nếu đã identify được KH khác (dùng "Thêm khách hàng" thay vì "Cập nhật khách hàng" khi cần tạo).

## OMIFlow — Trạng thái hành động (nhánh success/fail)
Node Hành động có mục "**Trạng thái hành động**" bên dưới "Danh sách hành động" — có thể thêm nhánh xử lý riêng cho `success` và `fail` của hành động đó. Nếu bỏ qua, mặc định đi tiếp qua "Bước tiếp theo".

## Cấu hình Truy vấn chatbot trỏ OMIFlow
Trong drawer Ngữ cảnh bắt đầu → tab "Truy vấn" → nút "+" → điền:
- **Tên truy vấn** (bắt buộc): tên ngắn để LLM hiểu mục đích.
- **Hướng dẫn BOT** (bắt buộc): mô tả khi nào bot cần gọi. Trên bản UI hiện tại bot gọi mỗi lượt bất kể mô tả — nhưng vẫn viết rõ để mai này thay đổi/audit.
- **Cấu hình truy vấn**: bấm mở drawer con → chọn GET/POST → điền URL webhook OMIFlow → Body Type = `raw` → Body JSON dùng biến `{{social_phone_number_linked}}`, `{{social_customer_name_linked}}`. **Chú ý**: editor JSON tự động thêm `{}` bao ngoài — không paste thêm `{}` gây nested. Xoá sạch trước khi type (Ctrl+A → Delete).
- **Thời gian chờ**: 60s mặc định.
- **Hướng dẫn BOT lấy kết quả về từ API** (bắt buộc): schema JSON trả về (liệt kê từng field) + cách bot xử lý khi các field trống hoặc status_code != 200.

## Test webhook OMIFlow bằng cURL trước khi nối vào chatbot
Trên trang cấu hình trigger API có nút "Test API" — nhưng cách chắc chắn là dùng cURL/Postman gửi POST tới webhook URL với body mẫu, xác nhận:
1. Response về đúng schema.
2. KH mới thực sự được tạo trong CRM (nếu Flow A) hoặc data KH trả đúng (nếu Flow B).
3. Log flow trong tab "Lịch sử" của flow hiển thị đã chạy qua các bước đúng.
Sau khi cURL pass mới nối vào chatbot — tránh debug lồng nhau.

## Kết nối edge / xóa node trong React Flow
UI OMIFlow và một số phần của Chatbot editor dựng bằng React Flow. Kéo edge từ output handle bên phải → input handle bên trái KHÔNG luôn hoạt động qua chuột (do target handle không hover-visible cho tới khi source active). Cách chắc chắn: dispatch `PointerEvent` qua JS. Nút "Xóa node" (`button[aria-label="Xóa node"]`) chỉ hiện khi node được select. Chi tiết code + selectors → xem skill **`omicall-omiflow`** (`references/react-flow-selectors.md`).

## OMIFlow — skill riêng
Các nội dung sau đã tách sang skill **`omicall-omiflow`**: trigger types (API/Biểu mẫu/Định kỳ/...), Điều kiện chi tiết (5 nhóm, phép toán, Kiểm tra tồn tại), node Hành động (Thêm/Cập nhật KH, API, Gọi flow khác), test webhook cURL, gotchas. Khi làm luồng chatbot ↔ CRM, gọi skill đó song song.

# Quy ước biên soạn
- Prompt chính (`system_prompt`) viết bằng tiếng Việt tự nhiên, KHÔNG chứa mô tả ý định chi tiết; ý định liệt kê riêng (file kịch bản intent) để user tự mô tả ngữ cảnh.
- Lời chào/kết thúc lịch sự: cảm ơn → chúc → tạm biệt. Kết thúc khi khách từ chối: cảm ơn + chúc sức khỏe + kết thúc, không ép.
- Mô tả intent dùng từ đầy đủ để mô hình nhận dạng ổn định + người quản trị đọc dễ.
- Khi user chỉ sửa prompt/description/mô tả intent → giữ nguyên `campaign`, `classifies`, `plantigrate`, routing — chỉ cập nhật đúng trường được yêu cầu.

## Suy luận nghiệp vụ TỪ tài liệu, không tự vẽ lại
Khi user gửi tài liệu nghiệp vụ (docx, xlsx, txt) có sẵn cấu trúc chi tiết (bảng ý định + biến + rẽ nhánh + kết quả mong muốn) — nghĩa là **đã có spec hoàn chỉnh**. Nhiệm vụ chỉ là chuyển thể sang định dạng prompt/intent/RAG chuẩn theo hình dạng builder, KHÔNG tự sáng tác lại. Dấu hiệu tài liệu đã có spec:
- File `.xlsx` sheet "Thuộc tính miniCRM" liệt kê từng trường: mã, tên, loại, tùy chọn, giá trị mặc định, bot dùng ở bước nào.
- File `.xlsx` sheet "Mẫu yêu cầu" liệt kê từng chức năng: Nhu cầu / Thông tin cần thu / Bot cần làm gì / Điều kiện / Kết quả mong muốn.
- File `.txt` "tính cách bot": prompt tổng thể ngắn gọn về xưng hô, giới hạn tin, guardrail — copy nguyên vào system_prompt.
- File `.docx` kiến thức phân theo chủ đề — gộp thành 1 file RAG duy nhất, giữ **nguyên văn**.

## CRM cho phép thuộc tính động — không lăn tăn nếu chưa có sẵn
Bộ thuộc tính miniCRM CRM của OMICall cho phép cấu hình động. Khi thiết kế bot cần thuộc tính mới (VD `hotel_id`, `bang_gia_chat`), tự đặt mã trường theo spec — không cần chờ tenant có sẵn thuộc tính đó rồi mới viết flow. User sẽ tự tạo/import thuộc tính theo spec đã cho.

## Không thu SĐT từ khách chat — lấy từ Đa kênh
Với Zalo OA/Fanpage: SĐT khách đã được platform trả về qua trigger tin (nếu khách đã ghép SĐT với Zalo ID). Bot đọc từ biến `{{social_phone_number_linked}}` (nhóm Đa kênh) thay vì hỏi khách "cho em số điện thoại" — nhanh hơn, đỡ phiền, tránh sai chính tả. Nếu SĐT trong Đa kênh trống (khách chưa ghép) mới rơi vào flow hỏi thủ công.

## Cẩn thận reload/thao tác nhầm làm mất dữ liệu
- Thao tác click nhầm/Escape trong tab Kịch bản có thể xóa các "Trường hợp" khỏi state cục bộ. Nếu **chưa lưu** thì reload trang lấy lại được (dữ liệu server còn nguyên); nhưng nếu bấm "Lưu lại" khi state đang thiếu → **mất data server**.
- Sau mỗi lần bấm "Lưu lại", đổi tab qua "Đào tạo" rồi quay lại là cách ép reload nhẹ để kiểm chứng nhanh; nhưng cách chắc nhất vẫn là `navigate` full URL bot editor rồi `get_page_text` verify.
- Ô "Tên nút" trong drawer khi type text mới sẽ **APPEND vào tên cũ** thay vì thay thế — luôn Ctrl+A trước khi type để clear.

## Trước khi dựng flow — kiểm tra quota gói dịch vụ
Trước khi tạo OMIFlow/file dữ liệu đào tạo mới, luôn xem đèn quota ở nút "Thêm mới N/M" (M = tổng, N = đã dùng). Gói Trial thường:
- OMIFlow: 1/1 flow
- Dữ liệu đào tạo (Đào tạo → Dữ liệu khác): 1/1 file văn bản, 0/1 file online, 0/10 website
- Bot AI: quota theo gói riêng
Nếu chạm quota, hỏi user quyết định: gỡ cũ / gộp chức năng / nâng gói. **Đừng đoán** — quyết định này ảnh hưởng cost và cần user chốt.

# Credentials registry
Bảng creds + bot mẫu từng tenant: **`references/credentials.md`**. Tenant mới → thêm 1 dòng.

# Reference
Endpoint, schema bot top-level + campaign + ví dụ đã verify, checklist validation, captor script: **`references/api-reference.md`**.
MCP OMI — cài đặt, đăng nhập, công cụ cho từng bước, cách tiết kiệm token: **`references/omi-mcp.md`** (bản giống hệt trong 3 skill OMI). Token cho API: `scripts/omi_session.py`.

Base directory for this skill: C:\Users\User\.agents\skills\omicall-chatbot-gen-ai
Relative paths in this skill (e.g., scripts/, references/) are relative to this base directory.