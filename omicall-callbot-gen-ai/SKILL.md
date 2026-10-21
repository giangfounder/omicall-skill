---
name: omicall-callbot-gen-ai
description: Shared skill to build OMiCall/OMiCRM Callbot Gen AI (SmartAgent) scripts end-to-end — works for ANY tenant and ANY Kịch bản/Callbot. Use when wiring intents, adding ACTION/collect-info/ADD_CLASSIFY/API nodes, calling external APIs (knowledge.apis), using RAG (knowledge.files), forwarding calls, building a Callbot script from business docs/PDF/Kịch bản, editing the Callbot editor (…/ai/callbot/script/update/{scriptId}), verifying via the chatbot-gateway API, or showing work live on OMiCRM. The AI reasons the intents, handling, routing, and the agent-guiding prompt from the business content itself (no copy from other tenants). Schemas: read references/api-reference.md before building. Logs in via the OMI MCP server (omicall-mcp: login_omicall_mcp) when available and uses its tools for lookups/testing — see references/omi-mcp.md.
---

# OMiCALL Callbot Gen AI — Generic Builder Playbook (all tenants / all scripts)

## Overview
Callbot **SmartAgent** (`type:"AI_AGENT"`): STT → LLM(+RAG/API) → TTS; tự đối thoại, nhận diện ý định, thu biến, chuyển/cúp máy. ≠ **Call Flow** (IVR/Rasa). Skill này là **bộ dùng chung**: mọi tenant, mọi kịch bản; intent, xử lý, routing, prompt hướng dẫn agent đều **do bạn (LLM) tự tư duy từ nghiệp vụ user cung cấp** — không bê nguyên từ script tenant khác hay từ ví dụ trong skill.

## Rules (BẮT BUỘC)
1. **Học kiến thức mới → ghi vào skill**: schema/key mới, loại node/action mới, pattern API, edge-case + cách fix, tenant mới đăng nhập được → cập nhật cuối phiên. File: `SKILL.md` (phần chung) hoặc `references/api-reference.md`; tenant mới chỉ thêm 1 dòng vào `references/credentials.md`.
2. **Đọc trước khi ghi** — tránh trùng lặp.
3. **Luôn kèm 1 ví dụ JSON thực tế** (từ script đã verify).
4. **Báo cáo phần đã update** trong summary cuối gửi user.
5. **Giữ skill tổng quát**: KHÔNG hardcode intent/prompt/tên script của một tenant cụ thể vào SKILL.md — tenant cụ thể chỉ là thông tin login (credentials.md) + schema (api-reference), còn thiết kế ý định/lời thoại là suy luận mỗi lần.
6. **Suy luận từ nghiệp vụ hiện tại**: đọc Kịch bản/tài liệu → tự tách nhánh luồng, intent, biến thu, prompt — chỉ dùng script tenant khác làm *tham chiếu hình dạng*, không copy nội dung.

## Input contract (chỉ 3 thứ, hỏi MỘT LẦN rồi tự làm hết)
1. **Domain doanh nghiệp** (ví dụ `<tên>.omicrm.io`).
2. **Tài khoản đăng nhập**: user + mật khẩu.
3. **Mô tả nghiệp vụ**: file (PDF/docx/xlsx/txt, ví dụ phiếu khảo sát hoặc kịch bản) và/hoặc prompt mô tả.

Có đủ 3 thứ này thì **không hỏi thêm**. Việc phân tích nghiệp vụ, đặt tên kịch bản (`SCRIPT_NAME` lấy theo doanh nghiệp + mục đích cuộc gọi), thiết kế intent/biến/phân loại, soạn prompt, dựng payload, lưu `add_v2`, verify, xuất thư mục giao đều do agent tự làm. Chỗ nghiệp vụ còn trống thì ghi "Cần xác nhận" trong báo cáo, không bịa và không dừng lại hỏi. Tenant đã có script phù hợp → dùng làm baseline qua `list-by-tenant`; tenant trống → dựng từ schema trong `references/api-reference.md`.

**Đăng nhập — ưu tiên MCP OMI** (chi tiết `references/omi-mcp.md`). Agent không tự gõ mật khẩu vào form hay gọi API đăng nhập bằng mật khẩu, kể cả khi user đã đưa sẵn. Mật khẩu chỉ nằm trong cấu hình MCP do user tự cài. Thứ tự:
- **(a) MCP OMI**: `login_omicall_mcp` (+ `select_tenant` nếu nhiều tenant) → token cho API callbot lấy bằng `python scripts/omi_session.py` (đọc phiên `~/.omicall-mcp/session.json`, không in token). Nếu MCP chưa cài cho domain này: đưa user lệnh `claude mcp add …` ở omi-mcp.md mục 1 (user tự điền mật khẩu) thay vì hỏi mật khẩu trong chat.
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
   - `next_node` = BEGIN (trả lời/tư vấn trong kịch bản) / ACTION (chuyển, gửi thông báo, phân loại) / END (cúp).
   - Tên intent rõ nghĩa (CONVENTION: Intent xác nhận thường = tên nhóm khách thực, intent hành động = "Từ chối"/"Hoàn tất"/"Chốt lịch"...).
2. **Menu intent tối thiểu nên có** (điều chỉnh theo nghiệp vụ, tối thiểu **5 intent**):
   - Nhóm chính ≥1 (Chủ hàng/Nhà vận tải/KH mua/... — tuỳ nghiệp vụ).
   - Xác nhận/Đồng ý (lịch, đặt hàng, nhận tài liệu...) → TRANSFER.
   - Từ chối/Không có nhu cầu → ADD_CLASSIFY là **node cuối nhánh** (không nối tiếp), không cúp ngay; bot vẫn ở hội thoại, hỏi còn cần hỗ trợ gì không.
   - **Hỏi đáp, FAQ, tra cứu thông tin: KHÔNG dựng intent riêng.** Bot trả lời ngay trong BEGIN từ prompt, RAG hoặc API (`knowledge`). Chỉ dựng intent khi có hành động thật: thu biến, phân loại, chuyển máy, gửi thông báo, kết thúc.
   - Hoàn tất cuộc trò chuyện (khách xác nhận không còn yêu cầu, hoặc yêu cầu dừng ngay) → END. **Đây là intent duy nhất nối END_CALL.**
3. **Routing pattern** (chọn theo nghiệp vụ, có thể hỏi user muốn hướng nào):
   - **Tối giản**: bot tư vấn trong BEGIN; chỉ intent cuối nối node — Từ chối→END, Đồng ý/Chốt→TRANSFER; intent tư vấn có `next_node`=BEGIN (vòng kịch bản).
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
6. **Quy tắc đầu ra cho giọng đọc tiếng Việt (BẮT BUỘC, mọi prompt)** — chèn nguyên khối ở mục *Khối quy tắc đầu ra cho giọng đọc* bên dưới, chỉ thay phần phiên âm tên riêng và ví dụ biến theo nghiệp vụ. LLM phải xuất văn bản tiếng Việt đọc to được ngay: không ký hiệu, không viết tắt, số viết thành chữ, tên nước ngoài phiên âm.
7. **Definition of Done** — thế nào là cuộc gọi thành công (đủ biến + phân loại + xác nhận được gì...).
`start_call_instruction` = câu mở đầu (chào + dẫn vào bước hỏi đầu tiên).

### Bước 4 — Dựng payload (schema: `references/api-reference.md` — đọc TRƯỚC khi build)
Lấy script GET của tenant làm baseline → overwrite BEGIN `ai_agent_config` (instruction, start_call_instruction, knowledge, collect_variables, ai_analyze.conditions) + thêm ACTION/ADD_CLASSIFY/END_CALL nodes + connections + org_nodes. Quy tắc: **DUAL-SCHEMA** cho mọi intent (sai → editor "Nhận diện ý định" trống); intent min **5**; 2 system conditions ở cuối.

### Bước 5 — Gắn next-node
Nối intent → node theo routing đã thiết kế: TRANSFER_CALL (chuyển ext + `transfer_collected_info:true`), PUSH_NOTIFICATION (gửi biến/`{{action_var}}` cho NV), ADD_CLASSIFY (nhãn phân loại trước bàn giao), END_CALL (kèm `description` cách kết thúc: cảm ơn + chúc sức khỏe + tạm biệt).

### Bước 6 — Lưu + Verify + Giao
1. **Lưu add_v2 LIÊN TỤC sau từng khối** (reload trang mất bản đang dở; server tự tăng version). Multipart field `file`, dùng Python `requests` (xem api-reference).
2. **Verify mỗi save**: `GET /callbot/script/get/{new_id}` + checklist đầy đủ trong api-reference. Chỉ in các trường cần kiểm tra, không in cả payload.
3. **Gọi thử bằng MCP** (khi user đồng ý gọi số thật): `click_to_call(extension, hotline, phone_number)` → `search_calls` hoặc `get_call_detail` để xem kết quả, tag, ghi chú. Nghe thử giọng: `text_to_speech`.
4. **Giao**: editor URL `https://{domain}.omicrm.io/ai/callbot/script/update/{new_id}?lng=vi` + folder `D:\Tải Xuống\<SCRIPT_NAME>_Knowledge\` (text trích xuất, System Prompt, PDF gốc, README: script id, tenant, intents, biến, TTS, editor URL, lưu ý).

## Interactive OMiCRM (user xem realtime)
Chrome CDP port 9222, profile `C:\Users\User\AppData\Local\Temp\opencode\chrome-cdp`: `Start-Process chrome.exe -ArgumentList '--remote-debugging-port=9222',"--user-data-dir=C:\Users\User\AppData\Local\Temp\opencode\chrome-cdp",'--no-first-run','https://<domain>.omicrm.io'`. Sau mỗi `add_v2` chạy `python scripts/goto.py <new_id>`. Dashboard: `python scripts/refresh_status.py <script_id>`. UI thao tác: `cdp.py` (`find_omicrm_tab()` + `CDP(ws).eval_js/navigate`).

## Gotchas chí tử (mọi tenant — sai là hỏng)
- **DUAL-SCHEMA**: mỗi intent viết CẢ runtime `nodes[].ai_agent_config.ai_analyze.conditions[]` LẪN editor `org_nodes[<BEGIN>].data.conditions[]` — schema khác nhau, backend KHÔNG tự chuyển.
- **ADD_CLASSIFY**: runtime action key **`data`**, editor org action key **`datas`**. Sai key → lưu 200 nhưng editor không hiện phân loại / runtime `data:null`.
- **END_CALL phải mô tả cách kết thúc**: runtime `description` + org `data.description`/`data.content` (cảm ơn + chúc sức khỏe + tạm biệt rồi cúp).
- **add_v2 multipart** field `file`=JSON blob; dùng Python `requests`, KHÔNG curl (`invalid_param`).
- **Phiên bản có thể tăng ngoài ý muốn**: mở editor có thể tự tạo phiên bản mới (lưu bố cục), hoặc user sửa tay trên UI. Trước mỗi lần lưu từ file build: `list-by-tenant` lấy bản mới nhất; nếu `version` khác bản mình lưu lần trước thì GET bản đó, so `instruction`, intent và connections với file build. Có khác biệt do người sửa thì gộp vào trước khi lưu, không ghi đè.
- **Tab editor cũ ghi đè bản mới** (sự cố thật 2026-10-20): một tab editor mở từ bản cũ, bấm **Cập nhật** sẽ lưu nguyên trạng thái cũ thành phiên bản mới nhất, xoá mất các thay đổi đã lưu sau đó (prompt, node chuyển máy, nhánh hệ thống). Phòng tránh: sau mỗi lần lưu qua API, dặn user **tải lại hoặc đóng mọi tab editor** của kịch bản đó trước khi sửa tay; trước khi sửa tay trên UI phải tải lại trang. Phát hiện: so bản mới nhất với bản mình lưu gần nhất (prompt, `nodes`, `connections`); nếu thấy nội dung quay về bản cũ thì báo user và lưu bản gộp (phần user sửa + phần đã mất). Lưu từ UI còn đổi cấu trúc runtime (END_CALL có thêm `ai_agent_config.instruction`, ADD_CLASSIFY runtime chỉ còn `data.ids`), nên luôn GET lại kiểm tra.
- **Token theo tenant**: credentials.md (cookie key "2", có tenant URL-encode + HttpOnly → CDP `Network.getAllCookies`).
- Không bấm **Xuất bản** trên UI trừ khi user yêu cầu (`is_publish` giữ nguyên).
- **Editor không nạp lại nhân viên đã chọn ở node `TRANSFER_CALL`**: mở trang thì card và ngăn cấu hình hiện "Chưa có dữ liệu" / "Chọn tùy chọn", kể cả khi dữ liệu do chính editor lưu. Dữ liệu chạy thật vẫn đúng. Nguy cơ: bấm **Cập nhật** trên UI mà không chọn lại nhân viên thì có thể ghi `ids:[""]`. Sau mọi lần lưu qua UI: GET lại, kiểm tra `nodes[xfer].actions[0].data.ids` khác rỗng.

## Quy ước biên soạn và thao tác giao diện đã kiểm chứng

### Phân loại dùng lại theo cấu hình chung
- Khi nghiệp vụ cần phân loại sau mỗi intent, tạo toàn bộ **nhãn phân loại** một lần trong phần cấu hình phân loại chung, rồi chọn lại nhãn tương ứng trong từng node `ADD_CLASSIFY`. Không tạo nhãn trùng cho từng intent.
- Luồng chuẩn: `CUSTOM_INTENT` → `ADD_CLASSIFY` (node cuối nhánh), hoặc `ADD_CLASSIFY` → `TRANSFER_CALL` / `END_CALL` khi nghiệp vụ cần đi tiếp. **KHÔNG BAO GIỜ kéo dây từ node phụ (ADD_CLASSIFY, PUSH_NOTIFICATION, SEND_WEBHOOK…) quay về node chính BEGIN** — sai thiết kế hệ thống (user đã sửa lại, 2026-10-20). Node phụ là điểm cuối của nhánh: không có connection đi ra, hội thoại vẫn tiếp tục ở BEGIN. Chỉ nối tiếp node phụ khi nghiệp vụ cần đi tiếp tới `TRANSFER_CALL` hoặc `END_CALL`. Chỉ intent Hoàn tất mới đi `END_CALL`.
- Nếu user nói rõ “trừ các phân loại” hoặc chỉ yêu cầu sửa prompt/mô tả intent, giữ nguyên top-level `classifies`, node `ADD_CLASSIFY`, tên nhãn và routing của các node phân loại. Chỉ cập nhật đúng trường user yêu cầu.

### Chuẩn tiếng Việt cho thoại và giọng đọc tự động
- Với callbot tiếng Việt, mọi câu khách nghe được — `instruction`, `start_call_instruction`, `CUSTOM_INTENT.data[].content` và `END_CALL.description/content` — phải viết bằng tiếng Việt tự nhiên, câu đầy đủ và ngắn.
- Không để chữ viết tắt, mã nội bộ, dấu gạch chéo (trừ "anh/chị"), hoặc thuật ngữ kỹ thuật rút gọn xuất hiện trong lời thoại. Diễn giải đầy đủ bằng tiếng Việt; khi bắt buộc nêu tên riêng nước ngoài, thêm cách phiên âm để giọng đọc tự động phát âm rõ.
- **Xưng hô** (user yêu cầu 2026-10-20): bot xưng "em"; khi chưa biết khách là nam hay nữ thì gọi **"anh/chị"**; ngay khi xác định được (khách tự xưng "anh"/"chị", khách sửa cách gọi, tên đệm rõ giới tính như "Văn" hoặc "Thị") thì từ đó **chỉ gọi "anh" hoặc chỉ gọi "chị"**, nhất quán đến hết cuộc gọi. **Tuyệt đối không viết "anh hoặc chị"**: giọng đọc tự động đọc nguyên văn nghe rất máy móc. Mọi prompt có mục `# XƯNG HÔ` (mẫu bên dưới); câu cố định (`start_call_instruction`, `END_CALL`) dùng "anh/chị".
- Đọc số điện thoại theo từng chữ số; diễn giải ngày, giờ, tiền và địa chỉ thư điện tử theo tiếng Việt tự nhiên.
- Mô tả intent cũng dùng từ đầy đủ để mô hình nhận dạng ổn định và để người quản trị có thể đọc, kiểm tra dễ dàng. Không thay đổi nhãn phân loại chỉ để chuẩn hóa câu thoại nếu user đã loại trừ phạm vi đó.

### Mục xưng hô (chèn đầu `instruction`, sau Vai trò) — đã dùng thật 2026-10-20
```
# XƯNG HÔ
- Khi chưa biết khách là nam hay nữ: gọi "anh/chị".
- Xác định ngay khi có dấu hiệu: khách tự xưng "anh" hoặc "chị" (ví dụ "anh đang bận", "chị không cần"), khách sửa cách gọi, hoặc tên khách {{<biến tên>}} rõ giới tính (tên đệm "Văn" thường là anh, "Thị" thường là chị). Không chắc thì giữ "anh/chị" cho đến khi khách tự xưng.
- Đã xác định thì từ đó chỉ gọi "anh" hoặc chỉ gọi "chị", không dùng "anh/chị" nữa, giữ nhất quán đến hết cuộc gọi.
- Tuyệt đối không nói "anh hoặc chị".
```
`END_CALL.description` thêm: Gọi khách đúng cách đã xác định trong cuộc gọi: chỉ “anh” hoặc chỉ “chị”, chưa rõ thì “anh/chị”.

### Khối quy tắc đầu ra cho giọng đọc (chèn vào cuối `instruction`, trước Điều kiện hoàn thành)
Đã dùng thật (kịch bản gọi ra, 2026-10-20). Thay phần trong `<...>` theo nghiệp vụ, giữ nguyên các quy tắc:
```
# QUY TẮC ĐẦU RA CHO GIỌNG ĐỌC TIẾNG VIỆT (BẮT BUỘC)
Mọi câu em nói được chuyển thẳng thành giọng nói tiếng Việt, vì vậy chỉ viết đúng những chữ cần đọc to.
1. Chỉ dùng tiếng Việt có dấu đầy đủ, câu ngắn tự nhiên như nói chuyện điện thoại. Mỗi lượt tối đa ba câu, mỗi câu không quá hai mươi lăm chữ. Dùng dấu phẩy để ngắt hơi, dấu chấm hoặc dấu chấm hỏi để kết câu.
2. Không dùng định dạng hay ký hiệu: không dấu sao, dấu thăng, gạch đầu dòng, gạch chéo (trừ cách gọi "anh/chị" khi chưa biết giới tính), dấu ngoặc, mũi tên, biểu tượng cảm xúc, không xuống dòng để liệt kê. Cần liệt kê thì nói thành câu: thứ nhất, thứ hai.
3. Không viết tắt và không viết in hoa cả chữ: nói đầy đủ "<cụm từ nghiệp vụ hay bị viết tắt>", "số điện thoại", "anh/chị".
4. Mọi con số viết thành chữ theo cách đọc tiếng Việt:
   số lượng và thứ tự: "mười hai hạng mục", "lần thứ hai";
   số điện thoại và mã số: đọc từng chữ số, chia nhóm bằng dấu phẩy, ví dụ "không chín một hai, ba bốn năm, sáu bảy tám";
   ngày giờ: "ngày hai mươi lăm tháng mười", "tám giờ ba mươi sáng";
   tiền và tỉ lệ: "chín mươi tám nghìn đồng", "mười phần trăm"; năm: "năm hai nghìn không trăm hai mươi sáu".
5. Từ và tên nước ngoài viết theo cách đọc tiếng Việt: <tên thương hiệu → phiên âm, ví dụ Honda → "Hon-đa">, "ô kê". Ký hiệu đọc thành chữ: dấu cộng là "cộng", dấu phần trăm là "phần trăm", dấu và là "và".
6. Giá trị biến <liệt kê biến đầu vào> có thể ở dạng số hoặc ký hiệu, ví dụ "25/10/2026". Khi nói phải đổi sang cách đọc theo các quy tắc trên. Không bao giờ đọc ký hiệu ngoặc nhọn của biến; biến trống thì bỏ qua.
7. Không đọc đường dẫn, địa chỉ thư điện tử hay mã nội bộ; cần thì mời khách gọi tổng đài.
```
Áp dụng cả cho `start_call_instruction` và `END_CALL.content`: tự kiểm tra trước khi lưu, không còn chữ số, ký hiệu hay chữ viết tắt trong câu khách nghe.

### Kết thúc và chuyển cuộc gọi
- Mỗi `END_CALL` phải mô tả rõ trình tự: nói lời cảm ơn → chúc khách hàng → thông báo xin phép kết thúc → tạm biệt → sau đó mới ngắt cuộc gọi. Không chỉ ghi “kết thúc” chung chung.
- **Hỏi nhu cầu còn lại trước khi cúp (bắt buộc, mọi kịch bản)**: trước khi vào `END_CALL`, bot phải hỏi khách còn nhu cầu nào cần hỗ trợ không (ví dụ: “Anh/chị còn cần em hỗ trợ thêm vấn đề gì không ạ?”). Còn nhu cầu → tiếp tục hỗ trợ trong phạm vi kịch bản rồi hỏi lại. Chỉ chuyển sang kết thúc khi khách xác nhận đã xong (“không còn”, “hết rồi”, “cảm ơn”). Thực hiện ở ba chỗ:
  1. `instruction`: thêm bước “hỏi còn nhu cầu nào cần hỗ trợ không; chỉ kết thúc khi khách xác nhận không còn” vào luồng cuộc gọi và Điều kiện hoàn thành.
  2. Intent “Hoàn tất cuộc trò chuyện” có `content` là câu xác nhận không còn nhu cầu (“không còn gì nữa đâu”, “hết rồi, cảm ơn em”). Các nhánh khác (đồng ý, bận, từ chối, sai người) **không nối END_CALL**: intent → ADD_CLASSIFY là node cuối nhánh (không kéo dây về BEGIN). Bot vẫn ở hội thoại, hỏi còn cần hỗ trợ gì không; khách trả lời không còn (hoặc yêu cầu dừng ngay) thì intent Hoàn tất mới đưa tới END_CALL.
  3. `END_CALL.description`: ghi rõ chỉ cúp sau khi khách đã xác nhận không còn nhu cầu.
  Khách im lặng sau câu hỏi này thì hỏi lại một lần, vẫn im mới kết thúc lịch sự.
- **Nhánh hệ thống “bot không xử lý được” (`bot_can_not_answer`) LUÔN nối tới node `TRANSFER_CALL` chuyển máy cho nhân viên** (mọi kịch bản, `transfer_collected_info:true`). Lấy nhân viên và máy lẻ bằng MCP `list_agents`/`list_extensions`, hoặc API `agent-v1-stg.omicrm.com/get_all_agent/no_role` (`agent_id`, `_id` = contact_id, `sip_user`). Tenant chưa có nhân viên nào thì ghi "Cần xác nhận" trong báo cáo. Nối cả intent “khách yêu cầu gặp nhân viên” nếu nghiệp vụ có. Ba chỗ phải khớp (đã kiểm chứng 2026-10-20):
  - runtime `ai_analyze.conditions[id=bot_can_not_answer].next_node = "<xfer_id>"` **và** `ai_analyze.bot_can_not_answer.next_node = "<xfer_id>"`;
  - connection `{"source":"<begin_id>","sourceHandle":"bot_can_not_answer","target":"<xfer_id>","targetHandle":"1","id":"reactflow__edge-<begin_id>bot_can_not_answer-<xfer_id>1","type":"custom"}`;
  - node ACTION `TRANSFER_CALL`: runtime `data:{"ids":["<agent_id>"],"actionType":"Extension","sip_number":"<ext>","transfer_collected_info":true,"transfer_customize_info":false}`; org `datas.selected` = `{"sipNumber":"<ext>","gender":"male","fullName":"<tên>","avatar":"","label":"<ext> - <tên>","contact_id":"<contact_id>","value":"<agent_id>","email":""}`, `typeOptions.Extension=[<cùng option>]`, `transferType:"Extension"`, `isTransferCollectedInfo:true`.
- Lời báo trước khi chuyển máy cũng cần bằng tiếng Việt đầy đủ, ví dụ: “Em xin phép kết nối anh/chị với nhân viên phụ trách.” Không hứa thời gian liên hệ khi chưa có dữ liệu.

### Thao tác với trình biên tập OMiCRM
- Các ô nội dung dài trong trình biên tập là vùng nhập có thể nối thêm nội dung khi dán. Muốn thay toàn bộ prompt hoặc mô tả phải: đặt tiêu điểm vào ô → `Ctrl+A` → dán nội dung mới → đọc lại nội dung hiển thị để xác nhận không bị ghép với bản cũ.
- Sau khi thay prompt, intent hay node kết thúc, bấm **Cập nhật** để tạo phiên bản mới và kiểm tra lại prompt, các intent, mô tả kết thúc cùng số nhánh. Không bấm **Xuất bản** nếu user chưa yêu cầu.

Ví dụ JSON đã kiểm chứng cho mô tả kết thúc rõ ràng:
```json
{
  "id": "cogoEnd",
  "node_type": "END_CALL",
  "description": "Cảm ơn anh/chị đã gọi đến ContainerGo. Chúc anh/chị sức khỏe và một ngày tốt lành. Em xin phép kết thúc cuộc gọi tại đây. Tạm biệt anh/chị.",
  "actions": [],
  "variables": [],
  "is_collapse": false
}
```

## Credentials registry (login 1 lần ghi lại dùng chung)
Bảng creds + script mẫu từng tenant: **`references/credentials.md`**. Tenant mới → thêm 1 dòng.

## Reference
Mọi schema (node/intent/system/collect/API/ADD_CLASSIFY/END_CALL/connection/org), save snippet, validation checklist: **`references/api-reference.md`**.
MCP OMI — cài đặt, đăng nhập, công cụ cho từng bước, cách tiết kiệm token: **`references/omi-mcp.md`** (bản giống hệt trong 3 skill OMI). Token cho API: `scripts/omi_session.py`.
