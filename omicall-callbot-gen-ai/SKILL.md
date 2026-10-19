---
name: omicall-callbot-gen-ai
description: Shared skill to build OMiCall/OMiCRM Callbot Gen AI (SmartAgent) scripts end-to-end — works for ANY tenant and ANY Kịch bản/Callbot. Use when wiring intents, adding ACTION/collect-info/ADD_CLASSIFY/API nodes, calling external APIs (knowledge.apis), using RAG (knowledge.files), forwarding calls, building a Callbot script from business docs/PDF/Kịch bản, editing the Callbot editor (…/ai/callbot/script/update/{scriptId}), verifying via the chatbot-gateway API, or showing work live on OMiCRM. The AI reasons the intents, handling, routing, and the agent-guiding prompt from the business content itself (no copy from other tenants). Schemas: read references/api-reference.md before building.
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

**Đăng nhập — giới hạn an toàn**: agent không tự gõ mật khẩu vào form đăng nhập hay tự gọi API đăng nhập bằng mật khẩu (quy tắc an toàn của agent, kể cả khi user đã đưa sẵn). Thứ tự ưu tiên: (a) công cụ MCP đăng nhập `omicall_login_omicall_mcp` nếu có trong phiên; (b) phiên đã đăng nhập sẵn (`~/.omicall-mcp/session.json`, hoặc cookie `{domain}_omicrm_io` trong browser pane); (c) nếu chưa có phiên nào, mở trang đăng nhập trong browser pane, nhờ user bấm đăng nhập đúng một lần rồi tự lấy token từ cookie và làm tiếp mọi bước còn lại. Không lưu mật khẩu vào file, `credentials.md` hay repo chia sẻ.

## Workflow

### Bước 0 — Login & API (giống mọi tenant)
1. Lấy phiên đăng nhập theo mục *Input contract* (MCP login → phiên có sẵn → user đăng nhập một lần) → ghi `tenant_id` từ payload JWT.
2. Token: `~/.omicall-mcp/session.json`→`accessToken`, hoặc cookie theo `references/credentials.md`.
3. Base API: `https://chatbot-gateway-v1-stg.omicrm.com` (header `Authorization: Bearer <token>`).
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
   - `content` = câu khách sẽ nói (1–3 câu tự nhiên, tách biệt giữa các intent).
   - `action_steps` = thu biến nào (`collect_variables`), hay gọi kiến thức/API (`search_knowledge`), hay không cần (`action_steps:null`).
   - `next_node` = BEGIN (trả lời/tư vấn trong kịch bản) / ACTION (chuyển, gửi thông báo, phân loại) / END (cúp).
   - Tên intent rõ nghĩa (CONVENTION: Intent xác nhận thường = tên nhóm khách thực, intent hành động = "Từ chối"/"Hoàn tất"/"Chốt lịch"...).
2. **Menu intent tối thiểu nên có** (điều chỉnh theo nghiệp vụ, tối thiểu **5 intent**):
   - Nhóm chính ≥1 (Chủ hàng/Nhà vận tải/KH mua/... — tuỳ nghiệp vụ).
   - Xác nhận/Đồng ý (lịch, đặt hàng, nhận tài liệu...) → TRANSFER.
   - Từ chối/Không có nhu cầu → END (kèm mô tả cách kết thúc) hoặc tư vấn.
   - Tra cứu/Hỏi thông tin → trả lời bằng RAG/API (ở lại BEGIN hoặc PUSH_NOTIFICATION).
   - Hoàn tất cuộc trò chuyện → END.
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
6. **Đọc số liệu** — SĐT đọc từng chữ số; tiền đọc tiếng Việt (98.000đ → "chín mươi tám nghìn đồng"); ngày/giờ tự nhiên; thuật ngữ tiếng Anh phiên âm Việt (implant → "im-plăng") khi có.
7. **Definition of Done** — thế nào là cuộc gọi thành công (đủ biến + phân loại + xác nhận được gì...).
`start_call_instruction` = câu mở đầu (chào + dẫn vào bước hỏi đầu tiên).

### Bước 4 — Dựng payload (schema: `references/api-reference.md` — đọc TRƯỚC khi build)
Lấy script GET của tenant làm baseline → overwrite BEGIN `ai_agent_config` (instruction, start_call_instruction, knowledge, collect_variables, ai_analyze.conditions) + thêm ACTION/ADD_CLASSIFY/END_CALL nodes + connections + org_nodes. Quy tắc: **DUAL-SCHEMA** cho mọi intent (sai → editor "Nhận diện ý định" trống); intent min **5**; 2 system conditions ở cuối.

### Bước 5 — Gắn next-node
Nối intent → node theo routing đã thiết kế: TRANSFER_CALL (chuyển ext + `transfer_collected_info:true`), PUSH_NOTIFICATION (gửi biến/`{{action_var}}` cho NV), ADD_CLASSIFY (nhãn phân loại trước bàn giao), END_CALL (kèm `description` cách kết thúc: cảm ơn + chúc sức khỏe + tạm biệt).

### Bước 6 — Lưu + Verify + Giao
1. **Lưu add_v2 LIÊN TỤC sau từng khối** (reload trang mất bản đang dở; server tự tăng version). Multipart field `file`, dùng Python `requests` (xem api-reference).
2. **Verify mỗi save**: `GET /callbot/script/get/{new_id}` + checklist đầy đủ trong api-reference.
3. **Giao**: editor URL `https://{domain}.omicrm.io/ai/callbot/script/update/{new_id}?lng=vi` + folder `D:\Tải Xuống\<SCRIPT_NAME>_Knowledge\` (text trích xuất, System Prompt, PDF gốc, README: script id, tenant, intents, biến, TTS, editor URL, lưu ý).

## Interactive OMiCRM (user xem realtime)
Chrome CDP port 9222, profile `C:\Users\User\AppData\Local\Temp\opencode\chrome-cdp`: `Start-Process chrome.exe -ArgumentList '--remote-debugging-port=9222',"--user-data-dir=C:\Users\User\AppData\Local\Temp\opencode\chrome-cdp",'--no-first-run','https://<domain>.omicrm.io'`. Sau mỗi `add_v2` chạy `python scripts/goto.py <new_id>`. Dashboard: `python scripts/refresh_status.py <script_id>`. UI thao tác: `cdp.py` (`find_omicrm_tab()` + `CDP(ws).eval_js/navigate`).

## Gotchas chí tử (mọi tenant — sai là hỏng)
- **DUAL-SCHEMA**: mỗi intent viết CẢ runtime `nodes[].ai_agent_config.ai_analyze.conditions[]` LẪN editor `org_nodes[<BEGIN>].data.conditions[]` — schema khác nhau, backend KHÔNG tự chuyển.
- **ADD_CLASSIFY**: runtime action key **`data`**, editor org action key **`datas`**. Sai key → lưu 200 nhưng editor không hiện phân loại / runtime `data:null`.
- **END_CALL phải mô tả cách kết thúc**: runtime `description` + org `data.description`/`data.content` (cảm ơn + chúc sức khỏe + tạm biệt rồi cúp).
- **add_v2 multipart** field `file`=JSON blob; dùng Python `requests`, KHÔNG curl (`invalid_param`).
- **Token theo tenant**: credentials.md (cookie key "2", có tenant URL-encode + HttpOnly → CDP `Network.getAllCookies`).
- Không bấm **Xuất bản** trên UI trừ khi user yêu cầu (`is_publish` giữ nguyên).

## Quy ước biên soạn và thao tác giao diện đã kiểm chứng

### Phân loại dùng lại theo cấu hình chung
- Khi nghiệp vụ cần phân loại sau mỗi intent, tạo toàn bộ **nhãn phân loại** một lần trong phần cấu hình phân loại chung, rồi chọn lại nhãn tương ứng trong từng node `ADD_CLASSIFY`. Không tạo nhãn trùng cho từng intent.
- Luồng chuẩn: `CUSTOM_INTENT` → `ADD_CLASSIFY` → bước tiếp theo (trở về `BEGIN`, `TRANSFER_CALL`, hoặc `END_CALL` theo nghiệp vụ).
- Nếu user nói rõ “trừ các phân loại” hoặc chỉ yêu cầu sửa prompt/mô tả intent, giữ nguyên top-level `classifies`, node `ADD_CLASSIFY`, tên nhãn và routing của các node phân loại. Chỉ cập nhật đúng trường user yêu cầu.

### Chuẩn tiếng Việt cho thoại và giọng đọc tự động
- Với callbot tiếng Việt, mọi câu khách nghe được — `instruction`, `start_call_instruction`, `CUSTOM_INTENT.data[].content` và `END_CALL.description/content` — phải viết bằng tiếng Việt tự nhiên, câu đầy đủ và ngắn.
- Không để chữ viết tắt, mã nội bộ, dấu gạch chéo, hoặc thuật ngữ kỹ thuật rút gọn xuất hiện trong lời thoại. Diễn giải đầy đủ bằng tiếng Việt; khi bắt buộc nêu tên riêng nước ngoài, thêm cách phiên âm để giọng đọc tự động phát âm rõ.
- Viết “anh hoặc chị”, không dùng dạng rút gọn có dấu gạch chéo trong câu khách nghe được. Đọc số điện thoại theo từng chữ số; diễn giải ngày, giờ, tiền và địa chỉ thư điện tử theo tiếng Việt tự nhiên.
- Mô tả intent cũng dùng từ đầy đủ để mô hình nhận dạng ổn định và để người quản trị có thể đọc, kiểm tra dễ dàng. Không thay đổi nhãn phân loại chỉ để chuẩn hóa câu thoại nếu user đã loại trừ phạm vi đó.

### Kết thúc và chuyển cuộc gọi
- Mỗi `END_CALL` phải mô tả rõ trình tự: nói lời cảm ơn → chúc khách hàng → thông báo xin phép kết thúc → tạm biệt → sau đó mới ngắt cuộc gọi. Không chỉ ghi “kết thúc” chung chung.
- **Hỏi nhu cầu còn lại trước khi cúp (bắt buộc, mọi kịch bản)**: trước khi vào `END_CALL`, bot phải hỏi khách còn nhu cầu nào cần hỗ trợ không (ví dụ: “Anh hoặc chị còn cần em hỗ trợ thêm vấn đề gì không ạ?”). Còn nhu cầu → tiếp tục hỗ trợ trong phạm vi kịch bản rồi hỏi lại. Chỉ chuyển sang kết thúc khi khách xác nhận đã xong (“không còn”, “hết rồi”, “cảm ơn”). Thực hiện ở ba chỗ:
  1. `instruction`: thêm bước “hỏi còn nhu cầu nào cần hỗ trợ không; chỉ kết thúc khi khách xác nhận không còn” vào luồng cuộc gọi và Điều kiện hoàn thành.
  2. Intent “Hoàn tất cuộc trò chuyện” có `content` là câu xác nhận không còn nhu cầu (“không còn gì nữa đâu”, “hết rồi, cảm ơn em”). Các nhánh khác (từ chối, bận) cũng hỏi một lần trước khi cúp, trừ khi khách yêu cầu dừng ngay hoặc sai người nghe máy.
  3. `END_CALL.description`: ghi rõ chỉ cúp sau khi khách đã xác nhận không còn nhu cầu.
  Khách im lặng sau câu hỏi này thì hỏi lại một lần, vẫn im mới kết thúc lịch sự.
- Nếu user yêu cầu chuyển đến nhân viên, cấu hình `TRANSFER_CALL` có `transfer_collected_info:true`; nối cả intent “khách yêu cầu gặp nhân viên” và system intent “bot không xử lý được” đến node chuyển máy, nếu đúng yêu cầu nghiệp vụ.
- Lời báo trước khi chuyển máy cũng cần bằng tiếng Việt đầy đủ, ví dụ: “Em xin phép kết nối anh hoặc chị với nhân viên phụ trách.” Không hứa thời gian liên hệ khi chưa có dữ liệu.

### Thao tác với trình biên tập OMiCRM
- Các ô nội dung dài trong trình biên tập là vùng nhập có thể nối thêm nội dung khi dán. Muốn thay toàn bộ prompt hoặc mô tả phải: đặt tiêu điểm vào ô → `Ctrl+A` → dán nội dung mới → đọc lại nội dung hiển thị để xác nhận không bị ghép với bản cũ.
- Sau khi thay prompt, intent hay node kết thúc, bấm **Cập nhật** để tạo phiên bản mới và kiểm tra lại prompt, các intent, mô tả kết thúc cùng số nhánh. Không bấm **Xuất bản** nếu user chưa yêu cầu.

Ví dụ JSON đã kiểm chứng cho mô tả kết thúc rõ ràng:
```json
{
  "id": "cogoEnd",
  "node_type": "END_CALL",
  "description": "Cảm ơn anh hoặc chị đã gọi đến ContainerGo. Chúc anh hoặc chị sức khỏe và một ngày tốt lành. Em xin phép kết thúc cuộc gọi tại đây. Tạm biệt anh hoặc chị.",
  "actions": [],
  "variables": [],
  "is_collapse": false
}
```

## Credentials registry (login 1 lần ghi lại dùng chung)
Bảng creds + script mẫu từng tenant: **`references/credentials.md`**. Tenant mới → thêm 1 dòng.

## Reference
Mọi schema (node/intent/system/collect/API/ADD_CLASSIFY/END_CALL/connection/org), save snippet, validation checklist: **`references/api-reference.md`**.
