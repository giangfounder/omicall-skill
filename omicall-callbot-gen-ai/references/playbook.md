# omicall-callbot-gen-ai — Chi tiết theo bước

Phần chi tiết tách nguyên văn khỏi SKILL.md để giảm token khi nạp skill. Đọc mục cần khi tới bước tương ứng; SKILL.md thắng khi mâu thuẫn. Bắt đầu, đăng nhập và cách trao đổi với user: `conversation.md`.

## Overview
Callbot **SmartAgent** (`type:"AI_AGENT"`): STT → LLM(+RAG/API) → TTS; tự đối thoại, nhận diện ý định, thu biến, chuyển/cúp máy. ≠ **Call Flow** (IVR/Rasa). Skill này là **bộ dùng chung**: mọi tenant, mọi kịch bản; intent, xử lý, routing, prompt hướng dẫn agent đều **do bạn (LLM) tự tư duy từ nghiệp vụ user cung cấp** — không bê nguyên từ script tenant khác hay từ ví dụ trong skill.

## Input contract (chỉ 3 thứ, hỏi MỘT LẦN rồi tự làm hết)
1. **Domain doanh nghiệp** (ví dụ `<domain>.omicrm.io`).
2. **Email** và **mật khẩu**: user tự điền một lần vào form đăng nhập cục bộ (`omi_login.py setup --ui`), không gửi qua chat (agent không điền mật khẩu vào form hay API đăng nhập).
3. **Mô tả nghiệp vụ**: file (PDF/docx/xlsx/txt, ví dụ phiếu khảo sát hoặc kịch bản) và/hoặc prompt mô tả.

Có đủ 3 thứ này thì **không hỏi thêm**. Việc phân tích nghiệp vụ, đặt tên kịch bản (`SCRIPT_NAME` lấy theo doanh nghiệp + mục đích cuộc gọi), thiết kế intent/biến/phân loại, chọn routing, soạn prompt, dựng payload, lưu `add_v2`, verify, xuất thư mục giao đều do agent tự làm. Chỗ nghiệp vụ còn trống (kể cả lựa chọn mặc định agent đã tự chọn) thì ghi "Cần xác nhận" trong báo cáo hoặc `pending[]` của spec, không bịa và không dừng lại hỏi. Tenant đã có script phù hợp → dùng làm baseline qua `list-by-tenant`; tenant trống → dựng từ schema trong `references/api-reference.md`.

**Đăng nhập — một cách duy nhất**: theo `references/conversation.md` mục 1. `omi_login.py ensure --domain <domain>` trả `"need":"setup"` (hoặc `omi_preflight.py` báo `blocked`) → agent chạy nền `omi_login.py setup --ui --no-browser` và mở form cục bộ cho user tự điền (các bước, kể cả dự phòng khi không mở được trình duyệt: `references/omi-login.md` mục 2a). Sau lần đầu, agent tự đăng nhập lại: `route=login` hoặc 401 → `omi_login.py login --domain <domain>`, không hỏi user. Token cho API lấy bằng `omi_session.py` (không in token). Không đọc cookie hay token bằng JS/CDP.

Không lưu mật khẩu vào file, `credentials.md` hay repo chia sẻ.

## Workflow

### Bước 0 — Login & API (giống mọi tenant)
1. Đăng nhập theo mục *Input contract* (MCP OMI trước). `python "<thư mục skill>/scripts/omi_session.py"` in `tenant_id`, `domain`, thời hạn token (không in token).
2. **Tra cứu một lần bằng MCP**, lưu `tenant_context.json` ở scratchpad (`tenant_survey.py` + MCP): `get_service_package` (module đã bật), `list_agents` + `list_extensions` (cho `TRANSFER_CALL`), `list_hotlines`. Không mở giao diện để tra những thứ này.
3. Base API (MCP không có công cụ callbot): `https://chatbot-gateway-v1-stg.omicrm.com`, header lấy từ `omi_session.headers()`.
4. Lấy script cũ làm baseline: `GET /callbot/script/get/{id}` (`script_outline.py --id <id> --save`) — **nguồn schema chuẩn** cho `nodes`/`org_nodes`/`connections` của TENANT ĐÓ: giữ voice/model, cấu trúc và mặc định của BEGIN, overwrite nội dung. `id`/`uuid`/`public_key` chỉ giữ khi sửa đúng script user chỉ định; dựng kịch bản mới từ baseline thì xoá chúng (Rules 4).

### Bước 1 — Hiểu nghiệp vụ (PHÂN TÍCH — do LLM)
Đọc toàn bộ Kịch bản/tài liệu (`extract_text.py`; PDF cần `pip install pymupdf`) rồi trả lời bằng suy luận:
- Mục đích cuộc gọi là gì (tư vấn/chăm sóc/bán hàng/CSKH), điểm thành công.
- Có mấy **nhóm khách / luồng bắt đầu** khác nhau → mỗi nhóm một hướng đối thoại riêng.
- Những **thông tin bắt buộc phải thu** của mỗi nhóm (CRM cần: nhóm khách, tên, SĐT, nhu cầu, thông số...) và **trình tự hỏi**.
- **Ai / bộ phận nào nhận bàn giao** cho từng nhóm (ext/agent), và **kết thúc ra sao** (cảm ơn + tạm biệt).

### Bước 2 — Thiết kế intent + xử lý + routing (do LLM tự tư duy)
Từ phân tích trên, **bạn tự đặt tên intent, viết câu khách nói, chọn hành động** theo khung sau (không phụ thuộc intent tenant khác):

1. **Danh sách intent** — với mỗi intent xác định 4 thứ:
   - `content` = **đúng 1 câu nhận dạng cho mỗi intent** (`data` chỉ có 1 phần tử): viết gộp mô tả ý định + vài cách nói mẫu cách nhau bằng dấu chấm phẩy. Ví dụ: "Khách đồng ý ghé cửa hàng hoặc đồng ý đặt lịch hẹn, ví dụ: được em, mai anh ghé; ok em đặt lịch cho chị thứ bảy nhé." Không tách thành nhiều câu nhận dạng.
   - `action_steps` = thu biến nào (`collect_variables`), hay gọi kiến thức/API (`search_knowledge`), hay không cần (`action_steps:null`).
   - `next_node` = id ACTION/END khi intent thật sự đi tới node đó (theo Rules 3).
   - Tên intent rõ nghĩa (CONVENTION: Intent xác nhận thường = tên nhóm khách thực, intent hành động = "Từ chối"/"Hoàn tất"/"Chốt lịch"...).
2. **Menu intent tối thiểu nên có** (điều chỉnh theo nghiệp vụ, quy ước tối thiểu **5 intent**; validator chỉ WARN, số thật "Cần xác nhận" theo nghiệp vụ):
   - Nhóm chính ≥1 (khách mới / khách cũ / đại lý / ... — tuỳ nghiệp vụ).
   - Xác nhận/Đồng ý (lịch, đặt hàng, nhận tài liệu...) → TRANSFER.
   - Từ chối/Không có nhu cầu → ADD_CLASSIFY là node cuối nhánh (Rules 3).
   - **Hỏi đáp, FAQ, tra cứu thông tin: KHÔNG dựng intent riêng.** Bot trả lời ngay trong BEGIN từ prompt, RAG hoặc API (`knowledge`). Chỉ dựng intent khi có hành động thật: thu biến, phân loại, chuyển máy, gửi thông báo, kết thúc.
   - Hoàn tất cuộc trò chuyện (khách xác nhận không còn yêu cầu, hoặc yêu cầu dừng ngay) → END. **Đây là intent duy nhất nối END_CALL.**
3. **Routing pattern** — mặc định **Kết hợp**; tài liệu nêu rõ hướng khác thì theo tài liệu. Ghi lựa chọn đã dùng vào "Cần xác nhận"/`pending[]`, không dừng chờ user:
   - **Tối giản**: bot tư vấn ngay trong BEGIN; chỉ intent có hành động thật mới nối sang ACTION/END.
   - **Chuyển ngay khi nhận diện**: intent "có nhu cầu" không thu biến → TRANSFER ngay; có thu biến thì intent thu biến để trống nút kế tiếp → intent "khách xác nhận" (đọc lại xong) → phân loại → chuyển máy; tách nhiều node chuyển để mỗi nhóm thu bộ biến riêng.
   - **Kết hợp**: nhóm nào tư vấn được thì trả lời tại chỗ (RAG), nhóm nào cần NV thì chuyển.
4. **Quy trình bắt buộc trước TRANSFER/END/API**: intent thu biến để **trống nút kế tiếp** (hệ thống chuyển nút ngay khi đủ biến, câu đọc lại bị bỏ qua) → câu đọc lại ở Kịch bản chung → intent riêng **"khách xác nhận"** (builder: cặp `collect` có `confirm_by` + `confirm`) → **PHÂN LOẠI (ADD_CLASSIFY) hoặc API gửi dữ liệu** → mới chuyển/cúp. Không nối intent thu biến thẳng tới phân loại, API hay END (validator WARN X13, builder WARN X14). Chi tiết: `references/agent-config-guide.md` mục 4.
5. **RAG vs API — quyết định bằng suy luận**:
   - Tài liệu tĩnh (chính sách, giá, FAQ, sản phẩm) → **RAG** (`knowledge.files`). Tải file docx/pdf lên "File đào tạo": `scripts/rag_upload.py <file> --base GET.json --out payload.json` rồi `omi_save.py callbot … --update` (chuỗi ở `references/api-reference.md` mục "RAG — File đào tạo").
   - Dữ liệu realtime/cá nhân hoá (tra cứu hoá đơn, máy, khách hàng) → **đấu API** (`knowledge.apis`), chỉ khi tài liệu nêu endpoint; không bịa endpoint.
   - Vừa cần cả 2 → cấu hình cả hai. Thiếu thông tin để quyết định → mặc định RAG cho tài liệu tĩnh, API chỉ khi tài liệu nêu endpoint; ghi "Cần xác nhận", không dừng hỏi.

### Bước 3 — Viết prompt hướng dẫn agent (do LLM tự soạn từ nghiệp vụ)
Soạn System Prompt (`instruction`) **từ nghiệp vụ hiện tại**, bám cấu trúc sau (điền nội dung bạn tự tư duy, không chép nguyên):
1. **Vai trò** — bot là ai, công ty, mục tiêu cuộc gọi (ưu tiên: phân loại → tư vấn/thu thập → bàn giao).
2. **Luồng cuộc gọi** — viết lại state machine: khách nói gì → bot phải làm gì → chuyển hướng nào (diễn giải tự nhiên để LLM theo).
3. **Quy tắc đối thoại** — mỗi lượt 1–3 câu, hỏi 1 ý/lần, lịch sự xưng hô Anh/Chị, khách bận/cúp/không phản hồi/khách khó chịu → cách xử lý.
4. **Guardrails** — chỉ dùng dữ liệu trong RAG/kịch bản; không bịa giá/ưu đãi; không hỏi dữ liệu nhạy cảm (CCCD/OTP/ngân hàng); tôn trọng từ chối; khi khách đồng ý → chuyển NV.
5. **BIẾN DỮ LIỆU** — mã + tên từng biến + khi nào thu (khớp `collect_variables`).
6. **Quy tắc đầu ra cho giọng đọc tiếng Việt (BẮT BUỘC, mọi prompt)** — chèn nguyên khối trong `references/voice-rules.md`, chỉ thay phần phiên âm tên riêng và ví dụ biến theo nghiệp vụ. LLM phải xuất văn bản tiếng Việt đọc to được ngay: không ký hiệu, không viết tắt, số viết thành chữ, tên nước ngoài phiên âm. Tự kiểm bằng `tts_lint.py` (validator X9).
7. **Definition of Done** — thế nào là cuộc gọi thành công (đủ biến + phân loại + xác nhận được gì...).
`start_call_instruction` = câu mở đầu (chào + dẫn vào bước hỏi đầu tiên).

### Bước 4 — Dựng payload (schema: `references/api-reference.md` — đọc TRƯỚC khi build)
Lấy script GET của tenant làm baseline → overwrite BEGIN `ai_agent_config` (instruction, start_call_instruction, knowledge, collect_variables, ai_analyze.conditions) + thêm ACTION/ADD_CLASSIFY/END_CALL nodes + connections + org_nodes. Có `build_smartagent.py` thì dùng nó (nhân bản từ baseline; loại có cột `builder` = `khong` trong `node-status.json`, hoặc base không có mẫu, sẽ dừng với exit 2). Quy tắc: **DUAL-SCHEMA** cho mọi intent (Gotchas; validator C2, C3); quy ước tối thiểu 5 intent; 2 system conditions ở cuối.

### Bước 5 — Gắn next-node
Nối intent → node theo routing đã thiết kế: TRANSFER_CALL (chuyển nhân viên hoặc nhóm nội bộ, `transfer_collected_info:true`), SEND_WEBHOOK, PUSH_NOTIFICATION (gửi biến/`{{action_var}}` cho NV), ADD_CLASSIFY (nhãn phân loại trước bàn giao), END_CALL (mục *Kết thúc và chuyển cuộc gọi*). Loại nào đã kiểm chứng, builder sinh được hay phải ghép tay/dựng trên UI: tra `references/node-status.json` (cột `status`, `builder`, `template`). Nhánh không chuyển máy/cúp máy dừng ở node cuối (Rules 3).

### Bước 6 — Lưu + Verify + Giao
1. **Lưu LIÊN TỤC sau từng khối** (reload trang mất bản đang dở; server tự tăng version): lần đầu của kịch bản mới `omi_save.py callbot payload.json --domain <domain> --new`; các lần sau (và khi sửa script user chỉ định) `--update --confirm-update` với `id` mới nhất + `uuid` từ response lần lưu trước (Rules 4). Chưa có `omi_save.py` thì lưu `add_v2` multipart field `file` bằng Python `requests` (xem api-reference).
2. **Verify mỗi save**: `GET /callbot/script/get/{new_id}` + checklist đầy đủ trong api-reference = `validate_smartagent.py <GET.json> --mode post --sent payload.json` (omi_save tự chạy). Chỉ in các trường cần kiểm tra (`script_outline.py`), không in cả payload.
3. **Gọi thử bằng MCP** (khi user đồng ý gọi số thật): `click_to_call(extension, hotline, phone_number)` → `search_calls` hoặc `get_call_detail` để xem kết quả, tag, ghi chú. Nghe thử giọng: `text_to_speech`.
4. **Giao** — báo cáo theo khuôn 4 phần:
   - **Link editor**: `https://<domain>.omicrm.io/ai/callbot/script/update/{new_id}?lng=vi`.
   - **Checklist**: dòng `RESULT PASS` của validator mode post kèm `id` và `version` đã GET.
   - **Cần xác nhận**: mọi chỗ nghiệp vụ còn trống, lựa chọn mặc định agent đã tự chọn, mục validator WARN.
   - **Việc user cần làm**: xuất bản, gắn hotline, gọi thử (agent chỉ làm khi user đồng ý).
   Kèm thư mục `<SCRIPT_NAME>_Knowledge` trong thư mục làm việc (hoặc nơi user chỉ định): text trích xuất, System Prompt, PDF gốc, README (script id, tenant, intents, biến, TTS, editor URL, lưu ý).

## Interactive OMiCRM (user xem realtime)
Chrome CDP port 9222, profile riêng: `Start-Process chrome.exe -ArgumentList '--remote-debugging-port=9222',"--user-data-dir=$env:TEMP\omicrm-cdp",'--no-first-run','https://<domain>.omicrm.io'`. Sau mỗi lần lưu chạy `python "<thư mục skill>/scripts/goto.py" <new_id>` (domain lấy từ phiên MCP hoặc `--domain`). UI thao tác: `scripts/cdp.py` (`find_omicrm_tab()` + `CDP(ws).eval_js/navigate`, cần `pip install websocket-client`). Không dùng CDP để đọc cookie hay token.

## Gotchas chí tử (mọi tenant — sai là hỏng)
- **DUAL-SCHEMA**: mỗi intent viết CẢ runtime `nodes[].ai_agent_config.ai_analyze.conditions[]` LẪN editor `org_nodes[<BEGIN>].data.conditions[]` — schema khác nhau, backend KHÔNG tự chuyển. Thiếu `isCustomComp`/`targetType` ở editor → ô "Nhận diện ý định" trống (validator C2, C3).
- **ADD_CLASSIFY**: runtime action key **`data`**, editor org action key **`datas`**. Sai key → lưu 200 nhưng editor không hiện phân loại / runtime `data:null` (validator X4).
- **END_CALL**: mọi quy tắc (mô tả trình tự kết thúc C10/X7, chỉ intent Hoàn tất X6, hỏi còn nhu cầu) ở mục *Kết thúc và chuyển cuộc gọi* bên dưới.
- **add_v2 multipart** field `file`=JSON blob; dùng Python `requests`, KHÔNG curl (`invalid_param`).
- **Lưu qua giao diện và tab editor cũ** (mục duy nhất về bẫy này trong skill):
  - *Phiên bản có thể tăng ngoài ý muốn*: mở editor có thể tự tạo phiên bản mới (lưu bố cục), hoặc user sửa tay trên UI. Trước mỗi lần lưu từ file build: `list-by-tenant` lấy bản mới nhất; nếu `version` khác bản mình lưu lần trước thì GET bản đó, so `instruction`, intent và connections với file build. Có khác biệt do người sửa thì gộp vào trước khi lưu, không ghi đè.
  - *Tab editor cũ ghi đè bản mới*: tab mở từ bản cũ bấm **Cập nhật**, hoặc tab còn mở tự lưu, sẽ lưu trạng thái cũ thành bản mới nhất (hỏng), mất các thay đổi lưu sau đó. Trước khi lưu add_v2: nhờ user đóng mọi tab editor của kịch bản. Lưu xong: GET kiểm; dặn user tải lại nếu mở lại editor; id/version đã nhảy hoặc nội dung quay về bản cũ thì báo user và lưu bản gộp trên id mới nhất.
  - *Bấm Cập nhật trên script dựng bằng API làm hỏng bản*: server tạo id mới (hoặc bản nháp riêng cùng uuid, id cũ, `is_draft:true`), ADD_CLASSIFY mất nhãn (runtime chỉ còn `data.ids`), `knowledge.apis` về rỗng, END_CALL mất mô tả hoặc thêm `ai_agent_config.instruction`, TRANSFER_CALL `ids:[""]`, đổi mã biến thu, mất sắp xếp điều kiện (C2, C8, C9, C10 FAIL). Dùng bản giao diện chỉ để lấy JSON của nút vừa dựng, ghép vào payload gốc rồi `omi_save.py --update --confirm-update` với id mới nhất + uuid; không lấy cả bản giao diện làm gốc. Luôn GET lại kiểm tra.
- **Token theo tenant**: token gắn với tenant và domain của phiên; kiểm bằng `omi_preflight.py --domain <domain>` hoặc `omi_session.py` (claim `tenant_id`/`domain`), không đọc cookie bằng JS/CDP. Để nhận diện: phiên web nằm ở cookie `{domain}_omicrm_{io|com}` key `"2"` (có thể URL-encode, HttpOnly) — chỉ user hoặc MCP OMI lấy, agent không tự đọc.
- Không bấm **Xuất bản** trên UI trừ khi user yêu cầu (`is_publish` giữ nguyên; ngữ nghĩa `is_publish` còn "Cần xác nhận", xem api-reference).
- **Editor không nạp lại nhân viên đã chọn ở node `TRANSFER_CALL`**: mở trang thì card và ngăn cấu hình hiện "Chưa có dữ liệu" / "Chọn tùy chọn", kể cả khi dữ liệu do chính editor lưu. Dữ liệu chạy thật vẫn đúng. Nguy cơ: bấm **Cập nhật** trên UI mà không chọn lại nhân viên thì có thể ghi `ids:[""]`. Sau mọi lần lưu qua UI: GET lại, kiểm tra `nodes[xfer].actions[0].data.ids` khác rỗng (validator X3).

## Quy ước biên soạn và thao tác giao diện đã kiểm chứng

### Phân loại dùng lại theo cấu hình chung
- Khi nghiệp vụ cần phân loại sau mỗi intent, tạo toàn bộ **nhãn phân loại** một lần trong phần cấu hình phân loại chung, rồi chọn lại nhãn tương ứng trong từng node `ADD_CLASSIFY`. Không tạo nhãn trùng cho từng intent.
- Luồng chuẩn intent → phân loại → đi tiếp: theo Rules 3.
- Nếu user nói rõ “trừ các phân loại” hoặc chỉ yêu cầu sửa prompt/mô tả intent, giữ nguyên top-level `classifies`, node `ADD_CLASSIFY`, tên nhãn và routing của các node phân loại. Chỉ cập nhật đúng trường user yêu cầu.

### Lời thoại và giọng đọc (chi tiết và khối mẫu: `references/voice-rules.md`)
- Mọi câu khách nghe (`instruction`, `start_call_instruction`, `CUSTOM_INTENT.data[].content`, `END_CALL.description/content`) là tiếng Việt đầy đủ, câu ngắn; không viết tắt, ký hiệu, chữ số; tên nước ngoài phiên âm.
- Bot xưng "em"; chưa rõ giới tính gọi "anh/chị", xác định được thì chỉ "anh" hoặc chỉ "chị"; không bao giờ viết "anh hoặc chị".
- Mọi prompt chèn mục `# XƯNG HÔ` (sau Vai trò) và khối `# QUY TẮC ĐẦU RA CHO GIỌNG ĐỌC TIẾNG VIỆT` (trước Điều kiện hoàn thành) lấy từ file trên.

### Kết thúc và chuyển cuộc gọi
Mục duy nhất về quy tắc `END_CALL` trong skill (schema JSON: api-reference mục *END_CALL*; nơi khác chỉ trỏ về đây).
- **Mô tả `END_CALL` bắt buộc** (validator C10, X7): runtime `description` + org `data.description`/`data.content`, ghi rõ trình tự nói lời cảm ơn → chúc khách hàng (chúc sức khỏe) → thông báo xin phép kết thúc → tạm biệt → sau đó mới ngắt cuộc gọi. Không chỉ ghi “kết thúc” chung chung. Gọi khách theo cách đã xác định (`voice-rules.md`).
- **Cách hệ thống chạy**: lệnh endcall thực thi ngay sau khi model làm xong hướng dẫn trong nút endcall.
- **Chỉ intent “Hoàn tất cuộc trò chuyện” (không có biến) nối `END_CALL`** (validator X6). Không nối tới `END_CALL` từ: intent thu biến (hệ thống ngắt ngay khi đủ biến, bỏ qua câu đọc lại; validator WARN X13), intent “khách xác nhận”, điều kiện biến thu thập, hay các nhánh đồng ý/bận/từ chối/sai người (Rules 3).
- **Hỏi nhu cầu còn lại trước khi cúp (bắt buộc, mọi kịch bản)**: trước khi vào `END_CALL`, bot phải hỏi khách còn nhu cầu nào cần hỗ trợ không (ví dụ: “Anh/chị còn cần em hỗ trợ thêm vấn đề gì không ạ?”). Còn nhu cầu → tiếp tục hỗ trợ trong phạm vi kịch bản rồi hỏi lại. Chỉ chuyển sang kết thúc khi khách xác nhận đã xong (“không còn”, “hết rồi”, “cảm ơn”). Thực hiện ở ba chỗ:
  1. `instruction`: thêm bước “hỏi còn nhu cầu nào cần hỗ trợ không; chỉ kết thúc khi khách xác nhận không còn” vào luồng cuộc gọi và Điều kiện hoàn thành.
  2. Intent “Hoàn tất cuộc trò chuyện” có `content` là câu xác nhận không còn nhu cầu (“không còn gì nữa đâu”, “hết rồi, cảm ơn em”). Các nhánh khác đi theo Rules 3.
  3. `END_CALL.description`: ghi rõ chỉ cúp sau khi khách đã xác nhận không còn nhu cầu.
  Khách im lặng sau câu hỏi này: theo Rules 3.
- **Nhánh hệ thống “bot không xử lý được” (`bot_can_not_answer`) LUÔN nối tới node `TRANSFER_CALL` chuyển máy cho nhân viên** (mọi kịch bản, `transfer_collected_info:true`; validator X2). Lấy nhân viên và máy lẻ bằng MCP `list_agents`/`list_extensions` (`agent_id`, `_id`, `contact_id`, `sip_user`). API nhân viên gọi trực tiếp (host là dịch vụ `agent` trong `scripts/omi_api.py`, đường `get_all_agent/no_role`) chưa đủ tiền tố và chưa có lần gọi kiểm chứng → Cần xác nhận, không gọi. Trường nào điền vào `ids`/`value`: api-reference mục *ACTION — TRANSFER_CALL chuyển nhân viên* (Cần xác nhận). Chuyển cho nhóm nội bộ: mục *ACTION — TRANSFER_CALL nhóm nội bộ (Ring_group)* và `references/templates/TRANSFER_CALL_Ring_group.json`. Tenant chưa có nhân viên nào thì ghi "Cần xác nhận" trong báo cáo. Nối cả intent “khách yêu cầu gặp nhân viên” nếu nghiệp vụ có. Ba chỗ phải khớp (runtime condition + `ai_analyze.bot_can_not_answer.next_node`, connection, node `TRANSFER_CALL`): mẫu JSON ở api-reference mục *Nối `bot_can_not_answer` → TRANSFER_CALL*.
- Lời báo trước khi chuyển máy cũng cần bằng tiếng Việt đầy đủ, ví dụ: “Em xin phép kết nối anh/chị với nhân viên phụ trách.” Không hứa thời gian liên hệ khi chưa có dữ liệu.

### Quy chuẩn cấu hình Agent (chi tiết: `references/agent-config-guide.md`)
- Câu thoại cố định (chào, đọc lại thông tin, cảm ơn) và quy tắc thu thập biến đặt ở Kịch bản chung, câu cần nói đúng để trong ngoặc kép.
- Mô tả biến chỉ ghi mục tiêu + định dạng kết quả, kèm 1–2 ví dụ dễ nhận sai; không ghi luồng hỏi hay câu dẫn dắt.
- Trong một Ý định: tra kho tri thức thì Hướng dẫn Agent đặt TRƯỚC Thu thập thông tin; gọi API cần tham số thì Thu thập thông tin TRƯỚC, Hướng dẫn Agent SAU và gọi bằng `{{request_api_<tên truy vấn>}}`. Hướng dẫn viết ngắn, không chứa hội thoại mẫu.
- Luồng sản phẩm/đặt hàng tách 2 trường hợp: khách chưa rõ sản phẩm → tư vấn theo nhu cầu rồi gợi ý; khách đã nói rõ tên → tra đúng tên đó, xác nhận lại, đặt theo đúng nhu cầu khách đã nói, không hỏi lại thông tin tư vấn.
- Ý định có biến giữ tương tác đến khi đủ biến rồi chuyển nút ngay, nên bước xác nhận lại có thể bị bỏ. Luồng cần xác nhận: Ý định thu thập để trống nút kế tiếp + Ý định riêng "khách xác nhận thông tin đã đọc lại" → phân loại/chuyển máy. Không nối Ý định thu biến thẳng tới END_CALL.

- Không đặt Phân loại và Chuyển tiếp cuộc gọi chung một node (Chuyển tiếp bị khoá sau Phân loại): node Phân loại → node Chuyển máy. Thông báo cho nhân viên (Tạo thông báo) đặt chung node Phân loại được.
- "Bước tiếp theo" chỉ tạo node mới; nối tới node có sẵn bằng kéo dây trên canvas. Bỏ liên kết bằng dấu x sẽ xoá luôn node mồ côi. Chi tiết thao tác, canvas, sao chép sang tenant khác, đăng nhập MCP trên Claude desktop: `references/agent-config-guide.md` mục 8–10.

### Thao tác với trình biên tập OMiCRM
- Các ô nội dung dài trong trình biên tập là vùng nhập có thể nối thêm nội dung khi dán. Muốn thay toàn bộ prompt hoặc mô tả phải: đặt tiêu điểm vào ô → `Ctrl+A` → dán nội dung mới → đọc lại nội dung hiển thị để xác nhận không bị ghép với bản cũ.
- Sau khi thay prompt, intent hay node kết thúc, bấm **Cập nhật** để tạo phiên bản mới và kiểm tra lại prompt, các intent, mô tả kết thúc cùng số nhánh. Không bấm **Xuất bản** nếu user chưa yêu cầu.

## Reference
Bảng tra file: SKILL.md mục *Bảng tra* (bảng duy nhất). Schema: `references/api-reference.md`; trạng thái kiểm chứng và builder: `references/node-status.json`; mẫu node đã làm sạch: `references/templates/`. Token cho API: `scripts/omi_session.py`.

## Bảo trì skill (sau khi giao)
Chỉ làm khi user cho phép, ghi vào repo nguồn của skill; không ghi vào bản cài trong thư mục skill (khớp mục *Bước bắt buộc*).
1. **Học kiến thức mới → ghi vào skill**: schema/key mới, loại node/action mới, pattern API, edge-case + cách fix → cập nhật cuối phiên. File: `SKILL.md` (phần chung), `references/api-reference.md` hoặc `references/node-status.json`. Không ghi dữ liệu tenant (domain, tenant id, tên khách, số điện thoại, token).
2. **Đọc trước khi ghi** — tránh trùng lặp.
3. **Luôn kèm 1 ví dụ JSON thực tế** (từ script đã verify, đã làm sạch); template mới chỉ đánh dấu verified qua `extract_template.py --mark-verified` khi agent chính hoặc user duyệt.
4. **Báo cáo phần đã update** trong summary cuối gửi user.
