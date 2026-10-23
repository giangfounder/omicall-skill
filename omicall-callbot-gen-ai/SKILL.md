---
name: omicall-callbot-gen-ai
description: >-
  [v1.9.0] Dựng và sửa kịch bản Callbot Gen AI (SmartAgent, AI_AGENT) của OMiCall/OMiCRM: ý định, thu thập thông tin, phân loại, gọi API, RAG, chuyển máy, prompt cho tổng đài viên AI; dựng từ tài liệu nghiệp vụ hoặc PDF, sửa tại …/ai/callbot/script/update/{scriptId}, lưu qua chatbot-gateway và kiểm thử.
---

# OMiCALL Callbot Gen AI — Generic Builder Playbook (all tenants / all scripts)

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác (`<thư mục skill>` = thư mục chứa SKILL.md này). Câu đầu tiên trả lời user: `Đang dùng omicall-callbot-gen-ai v<phiên bản>` (lấy từ dòng `SKILL_VERSION`; script lỗi thì dùng v1.9.0). Script báo **SKILL.md đã thay đổi** → đọc lại SKILL.md từ đĩa rồi mới làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.

## Overview
Callbot **SmartAgent** (`type:"AI_AGENT"`): STT → LLM(+RAG/API) → TTS; tự đối thoại, nhận diện ý định, thu biến, chuyển/cúp máy. ≠ **Call Flow** (IVR/Rasa). Skill này là **bộ dùng chung**: mọi tenant, mọi kịch bản; intent, xử lý, routing, prompt hướng dẫn agent đều **do bạn (LLM) tự tư duy từ nghiệp vụ user cung cấp** — không bê nguyên từ script tenant khác hay từ ví dụ trong skill.

## Rules (BẮT BUỘC)
1. **Học kiến thức mới → ghi vào skill**: schema/key mới, loại node/action mới, pattern API, edge-case + cách fix, tenant mới đăng nhập được → cập nhật cuối phiên. File: `SKILL.md` (phần chung) hoặc `references/api-reference.md`; tenant mới chỉ thêm 1 dòng vào `references/credentials.md`.
2. **Đọc trước khi ghi** — tránh trùng lặp.
3. **Luôn kèm 1 ví dụ JSON thực tế** (từ script đã verify).
4. **Báo cáo phần đã update** trong summary cuối gửi user.
5. **Giữ skill tổng quát**: KHÔNG hardcode intent/prompt/tên script của một tenant cụ thể vào SKILL.md — tenant cụ thể chỉ là thông tin login (credentials.md) + schema (api-reference), còn thiết kế ý định/lời thoại là suy luận mỗi lần.
6. **Suy luận từ nghiệp vụ hiện tại**: đọc Kịch bản/tài liệu → tự tách nhánh luồng, intent, biến thu, prompt — chỉ dùng script tenant khác làm *tham chiếu hình dạng*, không copy nội dung.
7. **Cấm nối ngược về BEGIN**: không tạo `connection` có `target` là node BEGIN và không đặt `next_node` (intent hay node phụ) bằng id BEGIN. Nhánh không chuyển máy hoặc kết thúc cuộc gọi dừng ở node cuối, không có cạnh đi ra; hệ thống tự quay về ngữ cảnh chính. Kiểm tra trước mỗi `add_v2` theo api-reference mục *Bất biến: không có cạnh ngược về BEGIN*.

## Input contract (chỉ 3 thứ, hỏi MỘT LẦN rồi tự làm hết)
1. **Domain doanh nghiệp** (ví dụ `<tên>.omicrm.io`).
2. **Tài khoản** và thông tin xác thực cần thiết để agent tự cấu hình MCP OMI (không tự điền mật khẩu vào form hay API đăng nhập).
3. **Mô tả nghiệp vụ**: file (PDF/docx/xlsx/txt, ví dụ phiếu khảo sát hoặc kịch bản) và/hoặc prompt mô tả.

Có đủ 3 thứ này thì **không hỏi thêm**. Việc phân tích nghiệp vụ, đặt tên kịch bản (`SCRIPT_NAME` lấy theo doanh nghiệp + mục đích cuộc gọi), thiết kế intent/biến/phân loại, soạn prompt, dựng payload, lưu `add_v2`, verify, xuất thư mục giao đều do agent tự làm. Chỗ nghiệp vụ còn trống thì ghi "Cần xác nhận" trong báo cáo, không bịa và không dừng lại hỏi. Tenant đã có script phù hợp → dùng làm baseline qua `list-by-tenant`; tenant trống → dựng từ schema trong `references/api-reference.md`.

**Đăng nhập — ưu tiên MCP OMI** (chi tiết `references/omi-mcp.md`). Agent tự kiểm tra, tự cài và tự cấu hình MCP OMI ở phạm vi người dùng khi chưa có, trên mọi agent/client hỗ trợ MCP chứ không mặc định Codex hay Claude. Dùng thông tin đăng nhập đã được cung cấp mà không hỏi lại; không in mật khẩu/token và không ghi bí mật vào repo hoặc file tạm. Thứ tự:
- **(a) MCP OMI**: nếu chưa có thì tự cài theo `omi-mcp.md` mục 1; sau đó gọi `login_omicall_mcp` (+ `select_tenant` nếu nhiều tenant). Token cho API callbot lấy bằng `python scripts/omi_session.py` (đọc phiên `~/.omicall-mcp/session.json`, không in token).
- **(b) Phiên có sẵn**: biến `OMI_TOKEN_FILE`, hoặc cookie `{domain}_omicrm_io` trong browser pane.
- **(c) Dự phòng**: mở trang đăng nhập trong browser pane, nhờ user bấm đăng nhập đúng một lần, rồi lấy token từ cookie và làm tiếp.

Không lưu mật khẩu vào file, `credentials.md` hay repo chia sẻ.

## Workflow

### Bước 0 — Login & API (giống mọi tenant)
1. Đăng nhập theo mục *Input contract* (MCP OMI trước). `python scripts/omi_session.py` in `tenant_id`, `domain`, thời hạn token (không in token).
2. **Tra cứu một lần bằng MCP**, lưu `tenant_context.json` ở scratchpad: `get_service_package` (module đã bật), `list_agents` + `list_extensions` (cho `TRANSFER_CALL`), `list_hotlines`. Không mở giao diện để tra những thứ này.
3. Base API (MCP không có công cụ callbot): `https://chatbot-gateway-v1-stg.omicrm.com`, header lấy từ `omi_session.headers()`.
4. Lấy script cũ làm baseline: `GET /callbot/script/get/{id}` — **nguồn schema chuẩn** cho `nodes`/`org_nodes`/`connections` của TENANT ĐÓ (giữ id/uuid/public_key/voice/model, overwrite nội dung).

### Bước 1 — Hiểu nghiệp vụ (PHÂN TÍCH — do LLM)
Đọc toàn bộ Kịch bản/tài liệu (PDF: `pip install pymupdf`, extract text) rồi trả lời bằng suy luận:
- Mục đích cuộc gọi là gì (tư vấn/chăm sóc/bán hàng/CSKH), điểm thành công.
- Có mấy **nhóm khách / luồng bắt đầu** khác nhau → mỗi nhóm một hướng đối thoại riêng.
- Những **thông tin bắt buộc phải thu** của mỗi nhóm (CRM cần: nhóm khách, tên, SĐT, nhu cầu, thông số...) và **trình tự hỏi**.
- **Ai / bộ phận nào nhận bàn giao** cho từng nhóm (ext/agent), và **kết thúc ra sao** (cảm ơn + tạm biệt).

### Bước 2 — Thiết kế intent + xử lý + routing (do LLM tự tư duy)
Từ phân tích trên, **bạn tự đặt tên intent, viết câu khách nói, chọn hành động** theo khung sau (không phụ thuộc intent tenant khác):

1. **Danh sách intent** — với mỗi intent xác định 4 thứ:
   - `content` = **đúng 1 câu nhận dạng cho mỗi intent** (`data` chỉ có 1 phần tử): viết gộp mô tả ý định + vài cách nói mẫu cách nhau bằng dấu chấm phẩy. Ví dụ: "Khách đồng ý ghé cửa hàng hoặc đồng ý đặt lịch hẹn, ví dụ: được em, mai anh ghé; ok em đặt lịch cho chị thứ bảy nhé." Không tách thành nhiều câu nhận dạng.
   - `action_steps` = thu biến nào (`collect_variables`), hay gọi kiến thức/API (`search_knowledge`), hay không cần (`action_steps:null`).
   - `next_node` = id ACTION/END khi intent thật sự đi tới node đó; intent được xử lý ngay trong BEGIN dùng `null` và không có connection. (Rule 7)
   - Tên intent rõ nghĩa (CONVENTION: Intent xác nhận thường = tên nhóm khách thực, intent hành động = "Từ chối"/"Hoàn tất"/"Chốt lịch"...).
2. **Menu intent tối thiểu nên có** (điều chỉnh theo nghiệp vụ, tối thiểu **5 intent**):
   - Nhóm chính ≥1 (Chủ hàng/Nhà vận tải/KH mua/... — tuỳ nghiệp vụ).
   - Xác nhận/Đồng ý (lịch, đặt hàng, nhận tài liệu...) → TRANSFER.
   - Từ chối/Không có nhu cầu → ADD_CLASSIFY là **node cuối nhánh** (không nối tiếp), không cúp ngay; bot vẫn ở hội thoại, hỏi còn cần hỗ trợ gì không.
   - **Hỏi đáp, FAQ, tra cứu thông tin: KHÔNG dựng intent riêng.** Bot trả lời ngay trong BEGIN từ prompt, RAG hoặc API (`knowledge`). Chỉ dựng intent khi có hành động thật: thu biến, phân loại, chuyển máy, gửi thông báo, kết thúc.
   - Hoàn tất cuộc trò chuyện (khách xác nhận không còn yêu cầu, hoặc yêu cầu dừng ngay) → END. **Đây là intent duy nhất nối END_CALL.**
3. **Routing pattern** (chọn theo nghiệp vụ, có thể hỏi user muốn hướng nào):
   - **Tối giản**: bot tư vấn ngay trong BEGIN; chỉ intent có hành động thật mới nối sang ACTION/END.
   - **Chuyển ngay khi nhận diện**: mọi intent "có nhu cầu"→TRANSFER (bot chào + thu gọn + phân loại rồi bàn giao); tách nhiều node chuyển để mỗi nhóm thu bộ biến riêng.
   - **Kết hợp**: nhóm nào tư vấn được thì trả lời tại chỗ (RAG), nhóm nào cần NV thì chuyển.
4. **Quy trình bắt buộc trước TRANSFER/END**: sau intent thu thập xong phải có bước **PHÂN LOẠI khách (ADD_CLASSIFY) hoặc XÁC NHẬN lại thông tin**, rồi mới chuyển/cúp (không nhảy thẳng).
5. **RAG vs API — quyết định bằng suy luận**:
   - Tài liệu tĩnh (chính sách, giá, FAQ, sản phẩm) → **RAG** (`knowledge.files`).
   - Dữ liệu realtime/cá nhân hoá (tra cứu hoá đơn, máy, khách hàng) → **đấu API** (`knowledge.apis`).
   - Vừa cần cả 2 → cấu hình cả hai. Thiếu thông tin để quyết định → HỎI LẠI user.

### Bước 3 — Viết prompt hướng dẫn agent (do LLM tự soạn từ nghiệp vụ)
Soạn System Prompt (`instruction`) **từ nghiệp vụ hiện tại**, bám cấu trúc sau (điền nội dung bạn tự tư duy, không chép nguyên):
1. **Vai trò** — bot là ai, công ty, mục tiêu cuộc gọi (ưu tiên: phân loại → tư vấn/thu thập → bàn giao).
2. **Luồng cuộc gọi** — viết lại state machine: khách nói gì → bot phải làm gì → chuyển hướng nào (diễn giải tự nhiên để LLM theo).
3. **Quy tắc đối thoại** — mỗi lượt 1–3 câu, hỏi 1 ý/lần, lịch sự xưng hô Anh/Chị, khách bận/cúp/không phản hồi/khách khó chịu → cách xử lý.
4. **Guardrails** — chỉ dùng dữ liệu trong RAG/kịch bản; không bịa giá/ưu đãi; không hỏi dữ liệu nhạy cảm (CCCD/OTP/ngân hàng); tôn trọng từ chối; khi khách đồng ý → chuyển NV.
5. **BIẾN DỮ LIỆU** — mã + tên từng biến + khi nào thu (khớp `collect_variables`).
6. **Quy tắc đầu ra cho giọng đọc tiếng Việt (BẮT BUỘC, mọi prompt)** — chèn nguyên khối trong `references/voice-rules.md`, chỉ thay phần phiên âm tên riêng và ví dụ biến theo nghiệp vụ. LLM phải xuất văn bản tiếng Việt đọc to được ngay: không ký hiệu, không viết tắt, số viết thành chữ, tên nước ngoài phiên âm.
7. **Definition of Done** — thế nào là cuộc gọi thành công (đủ biến + phân loại + xác nhận được gì...).
`start_call_instruction` = câu mở đầu (chào + dẫn vào bước hỏi đầu tiên).

### Bước 4 — Dựng payload (schema: `references/api-reference.md` — đọc TRƯỚC khi build)
Lấy script GET của tenant làm baseline → overwrite BEGIN `ai_agent_config` (instruction, start_call_instruction, knowledge, collect_variables, ai_analyze.conditions) + thêm ACTION/ADD_CLASSIFY/END_CALL nodes + connections + org_nodes. Quy tắc: **DUAL-SCHEMA** cho mọi intent (sai → editor "Nhận diện ý định" trống); intent min **5**; 2 system conditions ở cuối.

### Bước 5 — Gắn next-node
Nối intent → node theo routing đã thiết kế: TRANSFER_CALL (chuyển ext + `transfer_collected_info:true`), PUSH_NOTIFICATION (gửi biến/`{{action_var}}` cho NV), ADD_CLASSIFY (nhãn phân loại trước bàn giao), END_CALL (kèm `description` cách kết thúc: cảm ơn + chúc sức khỏe + tạm biệt). Nhánh không chuyển máy/cúp máy dừng ở node cuối (Rule 7).

### Bước 6 — Lưu + Verify + Giao
1. **Lưu add_v2 LIÊN TỤC sau từng khối** (reload trang mất bản đang dở; server tự tăng version). Multipart field `file`, dùng Python `requests` (xem api-reference).
2. **Verify mỗi save**: `GET /callbot/script/get/{new_id}` + checklist đầy đủ trong api-reference. Chỉ in các trường cần kiểm tra, không in cả payload.
3. **Gọi thử bằng MCP** (khi user đồng ý gọi số thật): `click_to_call(extension, hotline, phone_number)` → `search_calls` hoặc `get_call_detail` để xem kết quả, tag, ghi chú. Nghe thử giọng: `text_to_speech`.
4. **Giao**: editor URL `https://{domain}.omicrm.io/ai/callbot/script/update/{new_id}?lng=vi` + thư mục `<SCRIPT_NAME>_Knowledge` trong thư mục làm việc (hoặc nơi user chỉ định) (text trích xuất, System Prompt, PDF gốc, README: script id, tenant, intents, biến, TTS, editor URL, lưu ý).

## Interactive OMiCRM (user xem realtime)
Chrome CDP port 9222, profile riêng: `Start-Process chrome.exe -ArgumentList '--remote-debugging-port=9222',"--user-data-dir=$env:TEMP\omicrm-cdp",'--no-first-run','https://<domain>.omicrm.io'`. Sau mỗi `add_v2` chạy `python scripts/goto.py <new_id>` (domain lấy từ phiên MCP). Dashboard: `python scripts/refresh_status.py <script_id>` ghi `status.json` vào `%TEMP%\omicrm-realtime\` (mở kèm `realtime_index.html` chép vào cùng thư mục). UI thao tác: `scripts/cdp.py` (`find_omicrm_tab()` + `CDP(ws).eval_js/navigate`, cần `pip install websocket-client`).

## Gotchas chí tử (mọi tenant — sai là hỏng)
- **DUAL-SCHEMA**: mỗi intent viết CẢ runtime `nodes[].ai_agent_config.ai_analyze.conditions[]` LẪN editor `org_nodes[<BEGIN>].data.conditions[]` — schema khác nhau, backend KHÔNG tự chuyển.
- **ADD_CLASSIFY**: runtime action key **`data`**, editor org action key **`datas`**. Sai key → lưu 200 nhưng editor không hiện phân loại / runtime `data:null`.
- **END_CALL phải mô tả cách kết thúc**: runtime `description` + org `data.description`/`data.content` (cảm ơn + chúc sức khỏe + tạm biệt rồi cúp).
- **add_v2 multipart** field `file`=JSON blob; dùng Python `requests`, KHÔNG curl (`invalid_param`).
- **Phiên bản có thể tăng ngoài ý muốn**: mở editor có thể tự tạo phiên bản mới (lưu bố cục), hoặc user sửa tay trên UI. Trước mỗi lần lưu từ file build: `list-by-tenant` lấy bản mới nhất; nếu `version` khác bản mình lưu lần trước thì GET bản đó, so `instruction`, intent và connections với file build. Có khác biệt do người sửa thì gộp vào trước khi lưu, không ghi đè.
- **Tab editor cũ ghi đè bản mới**: tab mở từ bản cũ bấm **Cập nhật** sẽ lưu trạng thái cũ thành bản mới nhất, mất các thay đổi lưu sau đó. Sau mỗi lần lưu qua API, dặn user tải lại hoặc đóng mọi tab editor của kịch bản; thấy nội dung quay về bản cũ thì báo user và lưu bản gộp. Lưu từ UI còn đổi cấu trúc runtime (END_CALL thêm `ai_agent_config.instruction`, ADD_CLASSIFY runtime chỉ còn `data.ids`) → luôn GET lại kiểm tra.
- **Token theo tenant**: credentials.md (cookie key "2", có tenant URL-encode + HttpOnly → CDP `Network.getAllCookies`).
- Không bấm **Xuất bản** trên UI trừ khi user yêu cầu (`is_publish` giữ nguyên).
- **Editor không nạp lại nhân viên đã chọn ở node `TRANSFER_CALL`**: mở trang thì card và ngăn cấu hình hiện "Chưa có dữ liệu" / "Chọn tùy chọn", kể cả khi dữ liệu do chính editor lưu. Dữ liệu chạy thật vẫn đúng. Nguy cơ: bấm **Cập nhật** trên UI mà không chọn lại nhân viên thì có thể ghi `ids:[""]`. Sau mọi lần lưu qua UI: GET lại, kiểm tra `nodes[xfer].actions[0].data.ids` khác rỗng.

## Quy ước biên soạn và thao tác giao diện đã kiểm chứng

### Phân loại dùng lại theo cấu hình chung
- Khi nghiệp vụ cần phân loại sau mỗi intent, tạo toàn bộ **nhãn phân loại** một lần trong phần cấu hình phân loại chung, rồi chọn lại nhãn tương ứng trong từng node `ADD_CLASSIFY`. Không tạo nhãn trùng cho từng intent.
- Luồng chuẩn: `CUSTOM_INTENT` → `ADD_CLASSIFY` (node cuối nhánh, Rule 7), hoặc `ADD_CLASSIFY` → `TRANSFER_CALL` / `END_CALL` khi nghiệp vụ cần đi tiếp. Chỉ intent Hoàn tất mới đi `END_CALL`.
- Nếu user nói rõ “trừ các phân loại” hoặc chỉ yêu cầu sửa prompt/mô tả intent, giữ nguyên top-level `classifies`, node `ADD_CLASSIFY`, tên nhãn và routing của các node phân loại. Chỉ cập nhật đúng trường user yêu cầu.

### Lời thoại và giọng đọc (chi tiết và khối mẫu: `references/voice-rules.md`)
- Mọi câu khách nghe (`instruction`, `start_call_instruction`, `CUSTOM_INTENT.data[].content`, `END_CALL.description/content`) là tiếng Việt đầy đủ, câu ngắn; không viết tắt, ký hiệu, chữ số; tên nước ngoài phiên âm.
- Bot xưng "em"; chưa rõ giới tính gọi "anh/chị", xác định được thì chỉ "anh" hoặc chỉ "chị"; không bao giờ viết "anh hoặc chị".
- Mọi prompt chèn mục `# XƯNG HÔ` (sau Vai trò) và khối `# QUY TẮC ĐẦU RA CHO GIỌNG ĐỌC TIẾNG VIỆT` (trước Điều kiện hoàn thành) lấy từ file trên.

### Kết thúc và chuyển cuộc gọi
- Mỗi `END_CALL` phải mô tả rõ trình tự: nói lời cảm ơn → chúc khách hàng → thông báo xin phép kết thúc → tạm biệt → sau đó mới ngắt cuộc gọi. Không chỉ ghi “kết thúc” chung chung.
- **Hỏi nhu cầu còn lại trước khi cúp (bắt buộc, mọi kịch bản)**: trước khi vào `END_CALL`, bot phải hỏi khách còn nhu cầu nào cần hỗ trợ không (ví dụ: “Anh/chị còn cần em hỗ trợ thêm vấn đề gì không ạ?”). Còn nhu cầu → tiếp tục hỗ trợ trong phạm vi kịch bản rồi hỏi lại. Chỉ chuyển sang kết thúc khi khách xác nhận đã xong (“không còn”, “hết rồi”, “cảm ơn”). Thực hiện ở ba chỗ:
  1. `instruction`: thêm bước “hỏi còn nhu cầu nào cần hỗ trợ không; chỉ kết thúc khi khách xác nhận không còn” vào luồng cuộc gọi và Điều kiện hoàn thành.
  2. Intent “Hoàn tất cuộc trò chuyện” có `content` là câu xác nhận không còn nhu cầu (“không còn gì nữa đâu”, “hết rồi, cảm ơn em”). Các nhánh khác (đồng ý, bận, từ chối, sai người) **không nối END_CALL**: intent → ADD_CLASSIFY là node cuối nhánh; chỉ intent Hoàn tất đưa tới END_CALL.
  3. `END_CALL.description`: ghi rõ chỉ cúp sau khi khách đã xác nhận không còn nhu cầu.
  Khách im lặng sau câu hỏi này thì hỏi lại một lần, vẫn im mới kết thúc lịch sự.
- **Nhánh hệ thống “bot không xử lý được” (`bot_can_not_answer`) LUÔN nối tới node `TRANSFER_CALL` chuyển máy cho nhân viên** (mọi kịch bản, `transfer_collected_info:true`). Lấy nhân viên và máy lẻ bằng MCP `list_agents`/`list_extensions`, hoặc API `agent-v1-stg.omicrm.com/get_all_agent/no_role` (`agent_id`, `_id` = contact_id, `sip_user`). Tenant chưa có nhân viên nào thì ghi "Cần xác nhận" trong báo cáo. Nối cả intent “khách yêu cầu gặp nhân viên” nếu nghiệp vụ có. Ba chỗ phải khớp (runtime condition + `ai_analyze.bot_can_not_answer.next_node`, connection, node `TRANSFER_CALL`): mẫu JSON ở api-reference mục *Nối `bot_can_not_answer` → TRANSFER_CALL*.
- Lời báo trước khi chuyển máy cũng cần bằng tiếng Việt đầy đủ, ví dụ: “Em xin phép kết nối anh/chị với nhân viên phụ trách.” Không hứa thời gian liên hệ khi chưa có dữ liệu.

### Thao tác với trình biên tập OMiCRM
- Các ô nội dung dài trong trình biên tập là vùng nhập có thể nối thêm nội dung khi dán. Muốn thay toàn bộ prompt hoặc mô tả phải: đặt tiêu điểm vào ô → `Ctrl+A` → dán nội dung mới → đọc lại nội dung hiển thị để xác nhận không bị ghép với bản cũ.
- Sau khi thay prompt, intent hay node kết thúc, bấm **Cập nhật** để tạo phiên bản mới và kiểm tra lại prompt, các intent, mô tả kết thúc cùng số nhánh. Không bấm **Xuất bản** nếu user chưa yêu cầu.

## Credentials registry (login 1 lần ghi lại dùng chung)
Bảng creds + script mẫu từng tenant: **`references/credentials.md`**. Tenant mới → thêm 1 dòng.

## Reference
Mọi schema (node/intent/system/collect/API/ADD_CLASSIFY/END_CALL/connection/org), save snippet, validation checklist: **`references/api-reference.md`**.
MCP OMI — cài đặt, đăng nhập, công cụ cho từng bước, cách tiết kiệm token: **`references/omi-mcp.md`** (bản giống hệt trong 3 skill OMI). Token cho API: `scripts/omi_session.py`.
