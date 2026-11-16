# omicall-chatbot-gen-ai — Chi tiết theo bước

Phần chi tiết tách nguyên văn khỏi SKILL.md để giảm token khi nạp skill. Đọc mục cần khi tới bước tương ứng; SKILL.md thắng khi mâu thuẫn. Bắt đầu, đăng nhập và cách trao đổi với user: `conversation.md`.

# Overview
AI **Chatbot** (text) — OMI gọi là **AI Chatbot / OmiBot** (`/ai/bot/...`), khác **Callbot** (`/ai/callbot/...`). Bot nhắn tin qua **Zalo OA / Fanpage FB / website (OMI LiveTalk)**; `type:"SCENARIO_HANDLER"`, LLM `gpt-4o-mini`. Điểm khác callbot: KHÔNG có STT/TTS, không có node chuyển máy dạng cuộc gọi — thay vào đó là **hội thoại văn bản + training/RAG** (`question_answer`, `vector_store`, `api_knowledge`) + **intents** trong `campaign` (BEGIN_CONTEXT). Prompt chính: `api-reference.md` mục "Prompt chính" (`ai_analyze.content` và `system_prompt`). Skill này là **bộ dùng chung**: thiết kế prompt/intent/routing/RAG do bạn (LLM) tự tư duy từ nghiệp vụ user — không chép từ tenant khác.

# Input contract
Hỏi một lần: (1) **domain doanh nghiệp**; (2) đăng nhập: không hỏi email/mật khẩu qua chat — `ensure` báo `need=setup` thì mở form cục bộ `omi_login.py setup --ui` cho user tự điền (mục *Đăng nhập an toàn*); (3) **mô tả nghiệp vụ** (kịch bản, FAQ, tài liệu dịch vụ hoặc prompt). Nếu thông tin đã có trong yêu cầu hoặc cấu hình bí mật thì không hỏi lại. Tên bot tự đặt theo doanh nghiệp và mục đích. Bot đã có sẵn đúng nhu cầu → reuse giữ nguyên `_id` (save ghi đè).

# Workflow

## Bước 0 — Đăng nhập (MCP OMI trước) & lấy token — chi tiết `references/omi-mcp.md`
- **MCP OMI + `omi_login.py` (chuẩn)**: `omi_preflight.py` báo `blocked` (hoặc `ensure` báo `need=setup`) → mở form đăng nhập cục bộ theo mục *Đăng nhập an toàn*. `route=login` (hết hạn, sai tenant) → agent tự chạy `omi_login.py login --domain <domain>`, không hỏi user. MCP có trong phiên thì `login_omicall_mcp` (+ `select_tenant`) cũng được. Token cho API lấy bằng `omi_session.py` (không in token). Chi tiết `references/omi-login.md` mục 2a. Script khác import `omi_session.headers()`.
- **Tra một lần bằng MCP**, lưu `tenant_context.json` ở scratchpad: `get_service_package` (module `integrated`, `ai`), `get_all_channels` (oa_id, page_id, widget, bot_id để gắn bot), `list_agents` (nhân viên nhận chuyển hội thoại).
- Dự phòng không có MCP: user tự đặt `OMI_TOKEN_FILE` (`omi_session.py` đọc), hoặc làm trên giao diện. Không đọc cookie bằng JS/CDP. Xem mục *Đăng nhập an toàn*.
- Base API (MCP không có công cụ chatbot): `https://chatbot-gateway-v1-stg.omicrm.com` (`Authorization: Bearer <token>`).

## Bước 1 — Baseline schema
- `POST /omiai_assistant/get/{bot_id}` body `{"_id": bot_id}` → cấu trúc bot hiện có (nếu cần tạo mới: dựng payload theo api-reference).
- Lưu ý: bot chatbot có `_id` ỔN ĐỊNH khi save (không tạo id mới như callbot add_v2). `is_draft:true`, `is_newest_version:false` khi ở bản nháp.

## Bước 2 — Hiểu nghiệp vụ (PHÂN TÍCH — do LLM tự suy luận)
Đọc tài liệu/Kịch bản rồi trả lời: mục đích bot (tư vấn/CSKH/bán), nhóm khách, thông tin cần thu, ai nhận bàn giao, kết thúc ra sao.

## Bước 3 — Thiết kế intent + xử lý + routing (do LLM tự tư duy)
- Danh sách **intent** → mỗi intent: mô tả ngôn ngữ tự nhiên (khi nào chọn, khi nào KHÔNG chọn, 2–3 câu ví dụ khách nói — `CUSTOM_INTENT`, không dùng ý định hệ thống), hành động (`collect_variables` / `search_knowledge` / trả lời RAG / chuyển NV / kết thúc), bước kế tiếp.
- Menu tối thiểu (>=5 intent): nhóm chính ≥1; đồng ý/xác nhận; từ chối→kết thúc lịch sự; hoàn tất→kết thúc. Thêm: yêu cầu gặp NV → chuyển; khiếu nại → chuyển. Hỏi đáp/tra cứu thuần KHÔNG thành trường hợp riêng — system_prompt + RAG/Truy vấn tự trả lời (mục "Chỉ liệt kê intent nào cần flow xử lý riêng").
- RAG vs API: tài liệu tĩnh→**RAG** (`vector_store` / `question_answer`); dữ liệu realtime/cá nhân→**đấu API** (`api_knowledge`); thiếu dữ kiện→HỎI LẠI user.
- Quy trình trước khi chuyển/kết thúc: xác nhận lại thông tin đã thu với khách.

## Bước 4 — Viết System Prompt (do LLM tự soạn từ nghiệp vụ)
Điền vào trường prompt chính theo `api-reference.md` mục "Prompt chính" (spec `begin_content`; **chỉ mô tả chung** — không mô tả chi tiết ý định):
1. **Vai trò** — bot là ai, công ty, kênh chat, mục tiêu cuộc trò chuyện.
2. **Luồng hội thoại chung** — mở đầu, hỏi nhu cầu, xử lý theo ý định, thu thập, xác nhận, bàn giao/kết thúc.
3. **Quy tắc đối thoại text** — 1–3 câu/tin, hỏi 1 ý/lần, Anh/Chị, khách im lặng/khó chịu → xử lý, không spam.
4. **Guardrails** — chỉ dùng dữ liệu RAG/API, không bịa giá/ưu đãi, không thu CCCD/OTP/thẻ, tôn trọng từ chối.
5. **BIẾN DỮ LIỆU** — mã + tên biến + khi nào thu (khớp `collect_variables`).
6. **Định dạng reply** — tiếng Việt có dấu, bulleting gọn, SĐT đọc từng chữ số, tiền/ngày rõ ràng.
7. **Definition of Success** — đủ biến + trả lời/bàn giao/kết thúc đúng nghiệp vụ.
- Các ý định mô tả NGẮN ở file riêng (kịch bản intent), prompt chính mô tả luồng chung.

## Bước 5 — Dựng payload & intent (schema: api-reference.md — đọc TRƯỚC khi build)
- Lấy GET làm baseline → overwrite prompt chính (mục "Prompt chính" trong api-reference), `assistant_name/description`, `history_config`, intents trong BEGIN_CONTEXT (`campaign.name_mappings[BEGIN].conditions` + `campaign.nodes[BEGIN].ai_analyze.conditions`, tìm BEGIN theo `type`/`node_type`, không theo vị trí) khi schema intent đã xác minh. Đường nhanh: `scripts/build_bot.py` (loại đã xác minh, xem `references/node-status.json`). Nếu intent schema chưa rõ → **dùng UI trên Chrome + bắt mạng (captor)** để học trước khi build API (`references/ui-gotchas.md`).
- Save: `POST /omiai_assistant/save_draft_v2` (multipart field `file`=JSON). Publish: `POST /omiai_assistant/publish_v2` (chỉ khi user yêu cầu).

## Bước 6 — RAG/Training + Verify + Giao (luồng VERIFIED)
1. Tạo dữ liệu đào tạo **"Dữ liệu khác"** bằng API (không cần UI): upload file lên `file_store/put_v2` (`business_type=warehouse_of_knowledge_files`, field `file_0`) → tạo record `warehouse_of_knowledge/other/add` (base `external-v1-stg.omicrm.com`, **Bearer token**, body có `object_info` + `add_bot_uuids`) → **gọi `other/training/<record _id>`** để chạy huấn luyện (sau `add` record còn `not_training`). Chi tiết + body chuẩn: `references/api-reference.md` mục **"RAG — Dữ liệu khác"** và "Tạo bot mới + nạp RAG" (đã verify end-to-end: file ≤15MB, ref_id = record `_id`). Script: `scripts/rag_upload.py` (`--dry-run` để xem trước; chạm quota thì dừng, hỏi user).
2. **Gắn file vào Ngữ cảnh bắt đầu → Kho tri thức → Dữ liệu khác**: set `vector_store` + `campaign.nodes[BEGIN].ai_analyze.vector_store_ids=[record _id]` rồi `save_draft_v2`. Sau save `file_training_status:"completed"` = đã train xong, bot trả lời được bằng kiến thức.
3. Test chat: `POST /omiai_assistant/bot_testing_v2` **chỉ để kiểm cấu hình** (trả `{"payload":true}` = ACK, không có câu trả lời — api-reference.md mục "Intent custom"); chat thật qua "Trò chuyện thử" hoặc widget LiveTalk test (Bước 7).
4. Verify: `GET bot` (chỉ in trường cần kiểm tra; `validate_bot.py --mode post --sent` tự kiểm checklist) + reload editor + test tin nhắn. Giao: editor URL `https://{domain}.omicrm.io/ai/bot/edit/{bot_id}?lng=vi`, nội dung theo mục "Giao kết quả".
5. **Kiểm thử bằng MCP**: `get_contact_by_phone` hoặc `search_contacts` để kiểm tra dữ liệu bot tra cứu; `search_conversations` + `search_channel_messages` để xem hội thoại thật bot đã trả lời; `create_contact` để tạo khách mẫu (dọn bằng `delete_contact` khi user đồng ý). `send_*_message` gửi cho người thật — chỉ khi user đồng ý.

## Bước 7 — Gắn LiveTalk, kiểm thử, tối ưu — chi tiết `references/livetalk-test-optimize.md`
1. **Gắn kênh**: chỉ dùng widget LiveTalk test riêng (không gắn vào kênh đang phục vụ khách thật). Chọn bot ngay trên kênh, hoặc OMIFlow `GENERAL` (hội thoại mới, lọc đúng widget test) → `OMI_BOT_AI` (skill `omicall-omiflow`; tốn quota flow → hỏi user).
2. **Chat thử**: "Trò chuyện thử" trong editor hoặc đóng vai khách trên widget test; `/end` theo Gotchas. Xác minh bản nháp hay bản xuất bản đang trả lời trước khi kết luận.
3. **Bộ câu hỏi** (hệ chấm duy nhất của skill này; không báo điểm theo thang 12 tình huống của `test-cases.md`): phủ 14 nhóm G1–G14 (mở đầu, FAQ, từng ý định, thu thông tin, API, ngoài dữ liệu, ngoài phạm vi, gặp nhân viên, khiếu nại, dữ liệu nhạy cảm, chống dẫn dắt, nhiều lượt, nhiều ý, kết thúc). Kỳ vọng chỉ lấy từ dữ liệu của bot.
4. **Chấm** 5 tiêu chí 0–2 (nội dung, ý định, không bịa, giọng văn, chuyển nhân viên) + đánh dấu lỗi nghiêm trọng; đạt khi không lỗi nghiêm trọng và ≥ 85%.
5. **Tối ưu** theo bảng triệu chứng → chỗ sửa; snapshot trước khi sửa, mỗi vòng một nhóm nguyên nhân, `save_draft_v2`, chạy lại toàn bộ bộ câu hỏi, tối đa 3 vòng.
6. **Báo cáo** trước/sau bằng `scripts/eval_report.py --strict` (ca thiếu kết quả tính là trượt); khung bộ câu hỏi: `scripts/bot_outline.py --testcases-skeleton`. Báo cáo chứa dữ liệu khách → để ngoài repo skill.

# Đăng nhập an toàn
- **Không** tự điền username/password vào form đăng nhập hay API đăng nhập bằng script/JS, kể cả khi đã có sẵn thông tin đăng nhập.
- **Một cách đăng nhập duy nhất** (`conversation.md` mục 1, chi tiết `omi-login.md` mục 2a): `ensure` báo `need=setup` → agent chạy nền `python "<thư mục skill>/scripts/omi_login.py" setup --ui --no-browser`, mở địa chỉ in ra trong khung trình duyệt của agent; user tự điền form (agent không đọc, không chụp form), chờ `OMI_LOGIN_RESULT=OK|FAIL`. Không có trình duyệt thì bỏ `--no-browser`. `setup` trong terminal (ô nhập ẩn) chỉ là dự phòng khi không mở được form. Về sau agent tự `omi_login.py login` hoặc `login_omicall_mcp`, đọc token bằng `scripts/omi_session.py`. Không nhận mật khẩu qua chat, không in mật khẩu/token, không ghi bí mật vào repo hoặc file tạm.
- **Dự phòng khi client chưa nạp MCP trong phiên hiện tại**: mở editor trong browser pane, nhờ user tự đăng nhập một lần rồi làm trên giao diện, hoặc user tự đặt `OMI_TOKEN_FILE`. Không đọc cookie bằng JS/CDP; bị lớp an toàn chặn thì không tìm cách lách — hoàn tất cấu hình MCP và yêu cầu mở lại phiên khi client bắt buộc.

# Gotchas chí tử (mọi tenant — sai là hỏng)
- **END POINT KHÁC callbot**: chatbot dùng `omiai_assistant/...` (KHÔNG phải `callbot/...`) trên cùng gateway.
- **RAG/warehouse**: dữ liệu đào tạo "Dữ liệu khác" nằm ở `external-v1-stg.omicrm.com` (`warehouse_of_knowledge/other/`) + `filestore` — **BẮT BUỘC Bearer token** (cookie → 500). List phải dùng `other/search` (không phải `get_list` → payload null).
- **ref_id trong `vector_store.vector_store_files` = record `_id` của `other/add`**, không phải `file_id`; `ai_analyze.vector_store_ids` được build từ đó khi save.
- **Prompt chính** ở `campaign.nodes[BEGIN].ai_analyze.content` (drawer "Hướng dẫn & Tính cách BOT"); quan hệ với `system_prompt`: `api-reference.md` mục "Prompt chính".
- **save_draft_v2/publish_v2 multipart** field `file`=JSON blob (như add_v2); `_id` giữ nguyên, KHÔNG đổi version/id mới.
- **DUAL**: intent khai CẢ `name_mappings[BEGIN].conditions` (editor) LẪN `nodes[BEGIN].ai_analyze.conditions` (runtime), cùng id, 2 điều kiện hệ thống cuối. Schema mặc định: kiểu ngôn ngữ tự nhiên ở `references/api-reference.md` mục "Trường hợp mô tả bằng ngôn ngữ tự nhiên (CUSTOM_INTENT)"; schema chip (`data[]` `OMI_BOT_INTENT`) chỉ để đọc bot cũ. Schema mới chưa có trong tài liệu → xác minh bằng captor, không tự đoán.
- **RAG cần training xong** mới trả lời đúng; `vector_store`/`question_answer` rỗng thì bot chỉ dựa `system_prompt`.
- Không bấm **Xuất bản** trên UI trừ khi user yêu cầu (`is_publish` giữ nguyên).
- **Làm trên giao diện** (Chrome CDP, captor, Escape, autosave tab Đào tạo, tải file, thêm ý định, ô nhập nối thêm, kiểm chứng sau khi lưu): đọc `references/ui-gotchas.md` trước khi thao tác.
- Chỉ dùng token đúng tenant: kiểm tra `domain`/`tenant_id` bằng `python scripts/omi_session.py` trước khi ghi; nhiều tenant thì mỗi tenant một server MCP hoặc `logout` rồi đăng nhập lại. Xem mục "Đăng nhập an toàn".
- **Trường hợp trong Ngữ cảnh bắt đầu = mô tả ngôn ngữ tự nhiên** (chế độ "Nhận dạng ý định" → `CUSTOM_INTENT`, ô "Hướng dẫn BOT" ghi khi nào chọn / khi nào KHÔNG chọn / câu ví dụ). Không chọn ý định hệ thống ở "Chủ đề / Ý định mong muốn". Schema: `references/api-reference.md`.
- **`/end` (quy tắc gốc, chỗ khác trỏ về đây)**: mỗi lần cập nhật bot (lưu nháp hoặc xuất bản), gõ `/end` trong khung chat thử để đóng phòng cũ rồi chat lại; phòng đang mở giữ phiên bản bot cũ, chưa `/end` thì không kết luận bản mới đúng hay sai. Hội thoại đã bị tắt chatbot (bàn giao nhân viên) thì `/end` **không** bật lại bot → test bằng hội thoại mới (bằng chứng: `livetalk-test-optimize.md` mục 8, `ui-gotchas.md`).
- **`SEND_WEBHOOK` theo đường vào**: 10/2026 từng ghi nhận bot giao qua `OMI_BOT_AI` (LiveTalk) không gọi webhook sau nút Thu thập thông tin. **11/2026 đã chạy được** trên LiveTalk qua flow đón chat + `OMI_BOT_AI`: trường hợp ở nút Thu thập → ACTION `SEND_WEBHOOK` → flow WEB_HOOK tạo phiếu thật, biến thu (`{{var_*}}`) có giá trị. Lần 10/2026 nhiều khả năng do phiên bot bị đóng sớm (xem gotcha `waiting_time` 0 bên dưới), không phải do đường vào. `START_OTHER_CAMPAIGN` cũng chạy qua `OMI_BOT_AI` (✔ 11/2026). Test qua đúng kênh thật trước khi giao. Flow phụ thuộc gọi bằng `START_OTHER_CAMPAIGN` **không nhận biến hội thoại** (`{{social_content}}`… rỗng).
- **Chuyển nhân viên = ACTION `START_OTHER_CAMPAIGN` gọi flow phụ thuộc**, không phải nút giao diện (spec `build_bot.py`: `handoff` + `flow`). Flow phụ thuộc làm khung giờ → `RE_DISTRIBUTE` + tắt chatbot. **Bot không im lặng được**: trước khi chuyển bot vẫn gửi 1 câu LLM tự soạn (✔ LiveTalk 11/2026, gpt-4o-mini và claude-3-haiku); ép prompt "để trống" thì bot im nhưng không chọn trường hợp → không chuyển. Báo user là giới hạn nền tảng (`ui-gotchas.md` mục "Bot không im lặng được"). Không đặt rẽ khung giờ/chuyển nhân viên ở nhánh "BOT chủ động kết thúc" của flow: nhánh này cũng chạy khi khách im lặng hết thời gian chờ (skill `omicall-omiflow` node-catalog).
- **Nút Thu thập thông tin**: case theo biến được xét ở **tin nhắn kế tiếp** của khách, không phải ngay tin chứa dữ liệu → hành động (webhook tạo lead) chạy trễ một lượt.
- **Nút Thu thập thông tin — `customer_not_response.waiting_time` = 0 làm phiên bot đóng ngay sau mỗi câu trả lời** (✔ log 11/2026): khách nhắn tiếp thì bot mở phiên mới từ Ngữ cảnh bắt đầu, quên hết thông tin, không bao giờ tới hành động phía sau. Nút dựng trên UI (rồi `build_bot.py` nhân bản) có thể mang giá trị 0. Luôn đặt runtime `ai_analyze.customer_not_response.waiting_time: 180` **và** editor `name_mappings[...].conditions[type=customer_not_response].waitingTime: 3` (đơn vị phút), biến thu `save_to_conv: true` (giống bot đang chạy đúng). Kiểm bằng GET trước khi giao.
- **Trường hợp ở nút Thu thập thông tin chỉ xét TIN NHẮN MỚI NHẤT của khách** (✔ log 11/2026): mô tả kiểu "khách đã cho biết số lượng" sẽ trượt nếu số lượng nằm ở tin trước còn tin cuối là "nè"/ảnh → không gọi webhook nhưng bot vẫn tự nói "đã tạo phiếu". Thiết kế chuẩn: khi đủ thông tin bot **tóm tắt và hỏi xác nhận**; trường hợp = "khách xác nhận thông tin vừa tóm tắt" ('đúng rồi', 'ok em'); câu báo kết quả chỉ gửi sau khi khách xác nhận. Hướng dẫn của nút phải tự đủ (lời thoại, xưng hô, thứ tự bước) — nút không bám prompt Ngữ cảnh bắt đầu chặt (từng xưng "tôi/bạn", lặp lại câu mở đầu).
- **Schema "Nhận dạng ý định" ở nút Thu thập thông tin khác Ngữ cảnh bắt đầu** (✔ GET 11/2026, user dựng UI): runtime `ai_analyze.conditions[i]` `{"type":"CUSTOM_INTENT","percent":40,"next_node":…,"data":[{"id":"<10 ký tự>","type":"OMI_BOT_INTENT","content":"<mô tả tự nhiên>"}]}`; editor `{"type":"CUSTOM_INTENT","name":"","personality":null,"intent":null,"data":[{"id":…,"content":"<mô tả>","targetType":"OMI_BOT_INTENT","isCustomComp":true}]}`. Kiểu `intent_name`/`personality` (đúng cho Ngữ cảnh bắt đầu) đặt vào nút Thu thập thì editor **không hiển thị** trường hợp → xuất bản từ editor có thể làm mất. `content` viết dài kiểu "Chọn khi… KHÔNG chọn khi… Ví dụ…" vẫn chạy.
- **Xuất bản từ tab editor cũ ghi đè bản nháp vừa lưu qua API** (✔ 11/2026): editor publish nội dung đang nạp trong tab. Luôn tải lại editor sau `omi_save.py` rồi mới bấm Xuất bản, và GET lại sau xuất bản; `omi_save.py` báo "VERSION LỆCH" khi bản server đã đổi.
- **HTML trong giá trị biến bị lọc khi đổ vào mô tả phiếu** (✔ 11/2026): body webhook gửi `<b>`, `<br>` hoặc `\n` đều mất định dạng. Muốn phiếu đẹp: bot gửi dữ liệu thô từng trường (nhãn/giá trị riêng), HTML/CSS inline nằm ở mẫu mô tả trong flow (xem skill `omicall-omiflow` `node-action-ticket.md`). Tách loại phiếu (đơn hàng/khiếu nại) bằng một biến `type` trong body + nút Điều kiện ở flow, mỗi nhánh một mẫu.
- **Biến Đa kênh dùng được trong body webhook của bot** (danh sách từ editor 11/2026, giá trị chưa đối chiếu hết): `social_customer_name`, `social_id`, `social_session_id`, `social_content`, `social_content_type`, `social_embedded_file` (file của tin hiện tại), `social_lt_phone_number`, `social_lt_email`, `social_phone_number_linked`, `social_channel`, `social_chatbot_waiting`… `social_embedded_file` chỉ chứa file của tin đang xử lý, không giữ ảnh tin trước.
- **File GET đã che** (`omi_bot_lib.py`, `bot_outline.py --save` ghi giá trị `Authorization` thành `***`): không dùng làm base để lưu khi bot có Truy vấn mang header Authorization — lưu sẽ ghi đè token thật (`validate_bot.py` báo FAIL X6). Cần xác nhận cách lấy base chưa che an toàn trước khi sửa bot loại này.
- **Editor kịch bản (UI)**: tạo nút con từ "Nút kế tiếp" rồi đi tiếp sang nút cháu trong cùng chuỗi ngăn kéo → cấu hình nút con bị mất khi lưu. Mỗi nút: điền → đóng hết ngăn kéo → Lưu lại → GET kiểm tra. Nút X của ngăn kéo cuối nằm trùng menu "Tổng đài": đóng ngăn kéo cuối bằng cách bấm vùng mờ bên trái, không bấm X. Chỉ tính là đã lưu khi thấy "Cập nhật thành công".
- **Kiểm tra `history_config.enable`** khi tối ưu (có bot mặc định `false` → quên lượt trước). Số liệu chốt (giá, điều kiện) đưa thẳng vào prompt, RAG lo phần chi tiết.
- **Giới hạn gói (plan) của tenant**: có thể chỉ cho 1 "File văn bản" mỗi lúc (`0/1`). Phải xoá/gỡ file cũ khỏi "Dữ liệu khác" (tab Đào tạo) trước khi thêm file mới nếu báo "đã đạt giới hạn cho phép".

## Chỉ liệt kê intent nào cần flow xử lý riêng
Hệ thống này chạy tương tự N8N: **chỉ những ý định cần rẽ nhánh/flow xử lý riêng (gọi API, thu biến, chuyển bước) mới cần khai báo trong Ngữ cảnh bắt đầu**. Ý định thuần Q&A (khách hỏi kiến thức chung) — bot đã tự trả lời qua system_prompt + RAG, KHÔNG cần liệt kê thành Trường hợp riêng. Trước khi thêm 1 Trường hợp, hỏi: "ý định này có phải bot làm gì đặc biệt ngoài việc trả lời văn bản không?" — nếu chỉ trả lời từ RAG thì bỏ qua.

## Truy vấn API trong Ngữ cảnh bắt đầu (khác với node Hành động)
Drawer "Ngữ cảnh bắt đầu" có mục **"Truy vấn"** (cạnh "Hướng dẫn & Tính cách BOT", "Kho tri thức") — đây là chỗ khai báo API bot **tự gọi mỗi lượt trước khi chọn ý định**. Đặt các call API "chung, mỗi lượt" ở đây (vd: xác thực KH, lấy data CRM), không dùng node "Hành động" sau case ý định. Config gồm: Tên truy vấn, Hướng dẫn BOT (khi nào dùng — thực tế bot gọi mỗi lượt), Cấu hình (GET/POST/URL/Headers/Body raw JSON), Thời gian chờ, Hướng dẫn BOT lấy kết quả (schema JSON trả về + cách xử lý lỗi).
- Body dùng biến động qua `{{tên_biến}}` — biến Đa kênh chuẩn: `{{social_phone_number_linked}}` (SĐT khách đã link), `{{social_customer_name_linked}}` (tên khách đã link), `{{social_session_id}}`. Danh sách đầy đủ 106 thuộc tính Đa kênh xem trong picker khi bấm "Đa kênh" ở footer drawer.
- Node "Hành động → API" (mở qua right-click canvas → Hành động) dùng cho trường hợp khác: chỉ chạy khi 1 case cụ thể match. Đừng nhầm 2 chỗ này.
- Header `Authorization` tĩnh trong Truy vấn hỏng sau 24 giờ: quy tắc ở mục kế tiếp.

## Bot cần dữ liệu CRM — chọn hướng (quy tắc gốc về token 24 giờ; cấu hình chi tiết `references/crm-integration.md`)
- **Hướng B (mặc định cho bot chạy thật)**: Truy vấn trỏ webhook OMIFlow (flow đọc/tạo khách, phân bổ nhân viên, tích hợp bên thứ ba); không phụ thuộc token Public API hết hạn. Tốn quota flow (gói Trial thường 1 flow). Dựng flow bằng skill `omicall-omiflow`.
- **Hướng A (chỉ thử nhanh/demo ngắn)**: một Truy vấn gọi thẳng OMICall Public API `contact/search` với header Bearer **API token của tenant** (khác JWT phiên; hỏi user, không tự trích từ cookie). Không tốn quota flow.
  - ⚠ Token đổi từ apiKey (`GET /api/auth?apiKey=`) **hết hạn sau 24 giờ** (`references/omicall-public-api.md` dòng Auth) → header Authorization tĩnh trong Truy vấn sẽ hỏng sau 24 giờ. Chỉ dùng khi user đồng ý và biết hạn 24 giờ (`validate_bot.py` WARN X8, `build_bot.py` WARN). Chưa có cách tự làm mới token trong Truy vấn (Cần xác nhận) → bot chạy thật đi Hướng B.
- **Kết hợp**: OMIFlow để tạo/cập nhật, Public API để đọc — cũng vướng token 24 giờ như Hướng A. Đối chiếu khách theo trường "Số điện thoại" chuẩn, không theo thuộc tính tuỳ chỉnh.

# Quy ước biên soạn
- Prompt chính (`api-reference.md` mục "Prompt chính") viết bằng tiếng Việt tự nhiên, KHÔNG chứa mô tả ý định chi tiết; ý định liệt kê riêng (file kịch bản intent) để user tự mô tả ngữ cảnh.
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
Bộ thuộc tính miniCRM CRM của OMICall cho phép cấu hình động. Khi thiết kế bot cần thuộc tính mới (ví dụ `<ma_truong_moi>`), tự đặt mã trường theo spec — không cần chờ tenant có sẵn thuộc tính đó rồi mới viết flow. User sẽ tự tạo/import thuộc tính theo spec đã cho.

## Không thu SĐT từ khách chat — lấy từ Đa kênh
Với Zalo OA/Fanpage: SĐT khách đã được platform trả về qua trigger tin (nếu khách đã ghép SĐT với Zalo ID). Bot đọc từ biến `{{social_phone_number_linked}}` (nhóm Đa kênh) thay vì hỏi khách "cho em số điện thoại" — nhanh hơn, đỡ phiền, tránh sai chính tả. Nếu SĐT trong Đa kênh trống (khách chưa ghép) mới rơi vào flow hỏi thủ công.

## Trước khi dựng flow — kiểm tra quota gói dịch vụ
Trước khi tạo OMIFlow/file dữ liệu đào tạo mới, luôn xem đèn quota ở nút "Thêm mới N/M" (M = tổng, N = đã dùng). Gói Trial thường:
- OMIFlow: 1/1 flow
- Dữ liệu đào tạo (Đào tạo → Dữ liệu khác): 1/1 file văn bản, 0/1 file online, 0/10 website
- Bot AI: quota theo gói riêng
Nếu chạm quota, hỏi user quyết định: gỡ cũ / gộp chức năng / nâng gói. **Đừng đoán** — quyết định này ảnh hưởng cost và cần user chốt.

# Giao kết quả
Báo user, không kèm token hay dữ liệu bí mật:
- Link editor `https://<domain>.omicrm.io/ai/bot/edit/<bot_id>?lng=vi`; nhắc tải lại hoặc đóng tab editor cũ.
- Trạng thái `is_draft`, `is_publish` (không đổi khi user chưa yêu cầu xuất bản); dòng `RESULT` của `validate_bot.py --mode post`.
- Đã làm gì (prompt, trường hợp, node, Truy vấn, RAG + trạng thái training) và còn gì phải làm trên giao diện.
- Đã test gì (kênh, `/end`, điểm `eval_report.py`) và chưa test gì; các điểm "Cần xác nhận".
- Phần skill đã cập nhật (mục "Bảo trì skill").

# Reference
Endpoint, schema bot top-level + campaign + ví dụ đã verify, checklist validation, captor script: **`references/api-reference.md`**. Trạng thái xác minh từng loại node/hành động: **`references/node-status.json`**. Mẫu spec cho `build_bot.py`: **`references/spec-bot.example.json`**.
Chatbot ↔ CRM (Hướng A Public API, cấu hình Truy vấn trỏ OMIFlow; dựng flow ở skill `omicall-omiflow`): **`references/crm-integration.md`**. Thao tác giao diện: **`references/ui-gotchas.md`**.
Gắn LiveTalk, bộ câu hỏi thử, tiêu chí chấm, bảng lỗi → chỗ sửa, báo cáo trước/sau: **`references/livetalk-test-optimize.md`** + `scripts/eval_report.py`.
MCP OMI — cài đặt, đăng nhập, công cụ cho từng bước, cách tiết kiệm token: **`references/omi-mcp.md`** (bản chép từ `shared/`, giống hệt trong 7 skill OMI). Token cho API: `scripts/omi_session.py`.
Script riêng: `scripts/validate_bot.py` (checklist C1–C7 + X1–X10), `scripts/bot_outline.py`, `scripts/build_bot.py`, `scripts/rag_upload.py`, `scripts/omi_bot_lib.py`, `scripts/eval_report.py`.

# Bảo trì skill
1. **Học kiến thức mới → ghi vào skill**: schema/key mới (intent, action, RAG, cách lưu), edge-case → cập nhật `SKILL.md` / `references/api-reference.md` / `references/node-status.json` (nhãn chỉ nâng khi có bằng chứng GET thật).
2. Đọc trước khi ghi — tránh trùng lặp.
3. Luôn kèm **ví dụ JSON thật** (từ bot đã verify), đã làm sạch: placeholder `<domain>`, `<tenant_id>`, `<bot uuid>`, `<so_dien_thoai>`; không token, không SĐT/tên/dữ liệu khách.
4. Báo phần đã update trong summary cuối.
5. **Giữ skill tổng quát**: KHÔNG hardcode prompt/intent/tên bot, domain hay thông tin đăng nhập của một tenant vào skill; chỉ ghi kiến thức nền tảng + schema ở `references/api-reference.md`.
