---
name: omicall-chatbot-gen-ai
description: >-
  [v1.9.0] Dựng, kiểm thử và tối ưu Chatbot AI (OmiBot) của OMiCALL/OMiCRM cho Zalo OA, Facebook, LiveTalk: lời nhắc hệ thống, ý định trong Ngữ cảnh bắt đầu, RAG Dữ liệu khác, Truy vấn API, lưu nháp hoặc xuất bản qua chatbot-gateway, chat thử trên LiveTalk, chấm điểm trước/sau. Kích hoạt khi có đường dẫn omicrm.io/ai/bot/.
---

# OMiCALL/OMiCRM AI Chatbot (OmiBot) Gen AI — Generic Builder Playbook (mọi tenant / mọi bot)

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác (`<thư mục skill>` = thư mục chứa SKILL.md này). Câu đầu tiên trả lời user: `Đang dùng omicall-chatbot-gen-ai v<phiên bản>` (lấy từ dòng `SKILL_VERSION`; script lỗi thì dùng v1.9.0). Script báo **SKILL.md đã thay đổi** → đọc lại SKILL.md từ đĩa rồi mới làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.

## Bắt đầu: hỏi domain, rồi yêu cầu đăng nhập
1. Câu hỏi đầu tiên cho user chỉ là **tên domain** doanh nghiệp (`<tên>.omicrm.io`); domain đã có trong yêu cầu thì bỏ qua.
2. `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>` (một lệnh: kiểm token, tự đăng nhập lại từ kho bí mật). `"ok":true` → sang bước 4, không nói gì thêm về đăng nhập.
3. `"need":"setup"` → yêu cầu user đăng nhập trên **trang đăng nhập OMI thật**: mở `https://<domain>.omicrm.io/?lng=vi` trong trình duyệt của agent (browser pane của Claude, Chrome MCP… — agent nào có trình duyệt thì dùng trình duyệt đó), điền sẵn email nếu user đã cho, rồi nhắn đúng một câu: "Anh/chị nhập mật khẩu trên trang OMI vừa mở rồi bấm Đăng nhập." Agent KHÔNG gõ vào ô mật khẩu, không đọc cookie hay token của trang. Tự kiểm trang (ảnh chụp/văn bản) tới khi vào được trong ứng dụng thì làm tiếp; phiên này chỉ dùng cho thao tác giao diện (route `ui`). Muốn đi đường API/MCP (nhanh hơn) thì user chạy thêm một lần lệnh `command` của `ensure` trong terminal (ô nhập ẩn, `references/omi-mcp.md` mục 2a). Không nhận mật khẩu qua chat; user lỡ gửi thì không dùng, không nhắc lại, khuyên đổi mật khẩu.
4. Đăng nhập xong mới nhận mô tả nghiệp vụ và làm tiếp theo Đường nhanh.

## Đường nhanh
Chạy script bằng đường dẫn tuyệt đối `<thư mục skill>/scripts/...`. Mỗi bước chỉ trỏ tới quy tắc gốc bên dưới, không thay thế.
1. `omi_preflight.py --domain <domain>` → route `api`/`login`/`ui`/`blocked`, không in token. `login` → tự chạy `omi_login.py login --domain <domain>`; `blocked` → mở terminal cho user chạy `omi_login.py setup` (Bước 0); không đọc cookie.
2. `tenant_survey.py --out <scratch>/tenant_context.json` + MCP `get_all_channels`, `get_service_package`: kênh, widget LiveTalk test, quota Bot/Dữ liệu khác/OMIFlow (mục "kiểm tra quota"). Thiếu → "Cần xác nhận".
3. `bot_outline.py --id <bot_id> --domain <domain> --save` (hoặc `--file <GET.json>`) → baseline: trường hợp, node, cạnh, biến, Truy vấn, RAG, `is_draft`/`is_publish`.
4. Spec theo `references/spec-bot.example.json` (Bước 2–4). Tra `references/node-status.json`: `verified` → API; chưa có JSON (gửi tin, kết thúc, chuyển nhân viên, Kích hoạt ngữ cảnh) → UI, mỗi nút: điền → đóng hết ngăn kéo → Lưu lại → GET (Gotchas).
5. `build_bot.py spec.json --base <GET.json> --out payload.json`: chỉ vá trên baseline, giữ `_id`, tự chạy `validate_bot.py --mode pre`.
6. `omi_save.py bot payload.json --domain <domain>`: `save_draft_v2` → GET lại → `validate_bot.py --mode post --sent`. Không có cờ xuất bản.
7. Có tài liệu RAG: `rag_upload.py <file> --bot payload.json` (Bước 6) rồi lưu lại bằng `omi_save.py`.
8. Chat thử trên widget LiveTalk test (gắn kênh chỉ khi user đồng ý), gõ `/end` sau mỗi lần cập nhật bot; chấm bằng `eval_report.py --strict` (Bước 7).
9. Giao theo mục "Giao kết quả". Xuất bản chỉ khi user yêu cầu.

# Overview
AI **Chatbot** (text) — OMI gọi là **AI Chatbot / OmiBot** (`/ai/bot/...`), khác **Callbot** (`/ai/callbot/...`). Bot nhắn tin qua **Zalo OA / Fanpage FB / website (OMI LiveTalk)**; `type:"SCENARIO_HANDLER"`, LLM `gpt-4o-mini`. Điểm khác callbot: KHÔNG có STT/TTS, không có node chuyển máy dạng cuộc gọi — thay vào đó là **hội thoại văn bản + training/RAG** (`question_answer`, `vector_store`, `api_knowledge`) + **intents** trong `campaign` (BEGIN_CONTEXT). System Prompt nằm ở top-level `system_prompt` (UI: Kịch bản → Ngữ cảnh bắt đầu). Skill này là **bộ dùng chung**: thiết kế prompt/intent/routing/RAG do bạn (LLM) tự tư duy từ nghiệp vụ user — không chép từ tenant khác.

# Rules (BẮT BUỘC)
1. **Suy luận từ nghiệp vụ**: đọc tài liệu → tự tách nhóm khách, intent, biến thu, prompt — chỉ dùng bot tenant khác làm tham chiếu hình dạng.
2. **Không bịa** schema, giá, chính sách hay dữ liệu nghiệp vụ: thiếu dữ kiện → hỏi lại user hoặc ghi "Cần xác nhận".
3. Bảo trì skill (ghi kiến thức mới vào skill, đọc trước khi ghi, ví dụ JSON thật, giữ skill tổng quát, báo phần đã update): mục **"Bảo trì skill"** cuối file.

# Input contract
Hỏi một lần: (1) **domain doanh nghiệp**; (2) **email** đăng nhập — mật khẩu user gõ một lần vào ô nhập ẩn của `omi_login.py setup` trong terminal, không gửi qua chat; (3) **mô tả nghiệp vụ** (kịch bản, FAQ, tài liệu dịch vụ hoặc prompt). Nếu thông tin đã có trong yêu cầu hoặc cấu hình bí mật thì không hỏi lại. Tên bot tự đặt theo doanh nghiệp và mục đích. Bot đã có sẵn đúng nhu cầu → reuse giữ nguyên `_id` (save ghi đè).

# Workflow

## Bước 0 — Đăng nhập (MCP OMI trước) & lấy token — chi tiết `references/omi-mcp.md`
- **MCP OMI + `omi_login.py` (chuẩn)**: `omi_preflight.py` báo `blocked` → agent mở terminal cho user với `python "<thư mục skill>/scripts/omi_login.py" setup --domain <domain> --email <email>`; user gõ mật khẩu vào ô nhập ẩn đúng một lần, script cất vào kho bí mật hệ điều hành, tự đăng nhập MCP OMI và đăng ký server `OMICall-<domain>` (cấu hình không chứa mật khẩu); agent đi đường API ngay. `route=login` (hết hạn, sai tenant) → agent tự chạy `omi_login.py login --domain <domain>`, không hỏi user. MCP có trong phiên thì `login_omicall_mcp` (+ `select_tenant`) cũng được. Token cho API lấy bằng `omi_session.py` (không in token). Chi tiết `references/omi-mcp.md` mục 2a. Script khác import `omi_session.headers()`.
- **Tra một lần bằng MCP**, lưu `tenant_context.json` ở scratchpad: `get_service_package` (module `integrated`, `ai`), `get_all_channels` (oa_id, page_id, widget, bot_id để gắn bot), `list_agents` (nhân viên nhận chuyển hội thoại).
- Dự phòng không có MCP: user tự đặt `OMI_TOKEN_FILE` (`omi_session.py` đọc), hoặc làm trên giao diện. Không đọc cookie bằng JS/CDP. Xem mục *Đăng nhập an toàn*.
- Base API (MCP không có công cụ chatbot): `https://chatbot-gateway-v1-stg.omicrm.com` (`Authorization: Bearer <token>`).

## Bước 1 — Baseline schema
- `POST /omiai_assistant/get/{bot_id}` body `{"_id": bot_id}` → cấu trúc bot hiện có (nếu cần tạo mới: dựng payload theo api-reference).
- Lưu ý: bot chatbot có `_id` ỔN ĐỊNH khi save (không tạo id mới như callbot add_v2). `is_draft:true`, `is_newest_version:false` khi ở bản nháp.

## Bước 2 — Hiểu nghiệp vụ (PHÂN TÍCH — do LLM tự suy luận)
Đọc tài liệu/Kịch bản rồi trả lời: mục đích bot (tư vấn/CSKH/bán), nhóm khách, thông tin cần thu, ai nhận bàn giao, kết thúc ra sao.

## Bước 3 — Thiết kế intent + xử lý + routing (do LLM tự tư duy)
- Danh sách **intent** → mỗi intent: `content` (câu khách nói, 1–3 câu), hành động (`collect_variables` / `search_knowledge` / trả lời RAG / chuyển NV / kết thúc), bước kế tiếp.
- Menu tối thiểu (>=5 intent): nhóm chính ≥1; đồng ý/xác nhận; từ chối→kết thúc lịch sự; hoàn tất→kết thúc. Thêm: yêu cầu gặp NV → chuyển; khiếu nại → chuyển. Hỏi đáp/tra cứu thuần KHÔNG thành trường hợp riêng — system_prompt + RAG/Truy vấn tự trả lời (mục "Chỉ liệt kê intent nào cần flow xử lý riêng").
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
- Lấy GET làm baseline → overwrite `system_prompt`, `assistant_name/description`, `history_config`, intents trong BEGIN_CONTEXT (`campaign.name_mappings[BEGIN].conditions` + `campaign.nodes[BEGIN].ai_analyze.conditions`, tìm BEGIN theo `type`/`node_type`, không theo vị trí) khi schema intent đã xác minh. Đường nhanh: `scripts/build_bot.py` (loại đã xác minh, xem `references/node-status.json`). Nếu intent schema chưa rõ → **dùng UI trên Chrome + bắt mạng (captor)** để học trước khi build API (`references/ui-gotchas.md`).
- Save: `POST /omiai_assistant/save_draft_v2` (multipart field `file`=JSON). Publish: `POST /omiai_assistant/publish_v2` (chỉ khi user yêu cầu).

## Bước 6 — RAG/Training + Verify + Giao (luồng VERIFIED)
1. Tạo dữ liệu đào tạo **"Dữ liệu khác"** bằng API (không cần UI): upload file lên `file_store/put_v2` (`business_type=warehouse_of_knowledge_files`, field `file_0`) → tạo record `warehouse_of_knowledge/other/add` (base `external-v1-stg.omicrm.com`, **Bearer token**, body có `object_info` + `add_bot_uuids`) → **gọi `other/training/<record _id>`** để chạy huấn luyện (sau `add` record còn `not_training`). Chi tiết + body chuẩn: `references/api-reference.md` mục **"RAG — Dữ liệu khác"** và "Tạo bot mới + nạp RAG" (đã verify end-to-end: file ≤15MB, ref_id = record `_id`). Script: `scripts/rag_upload.py` (`--dry-run` để xem trước; chạm quota thì dừng, hỏi user).
2. **Gắn file vào Ngữ cảnh bắt đầu → Kho tri thức → Dữ liệu khác**: set `vector_store` + `campaign.nodes[BEGIN].ai_analyze.vector_store_ids=[record _id]` rồi `save_draft_v2`. Sau save `file_training_status:"completed"` = đã train xong, bot trả lời được bằng kiến thức.
3. Test chat: `POST /omiai_assistant/bot_testing_v2` **chỉ để kiểm cấu hình** (trả `{"payload":true}` = ACK, không có câu trả lời — api-reference.md mục "Intent custom"); chat thật qua "Trò chuyện thử" hoặc widget LiveTalk test (Bước 7).
4. Verify: `GET bot` (chỉ in trường cần kiểm tra; `validate_bot.py --mode post --sent` tự kiểm checklist) + reload editor + test tin nhắn. Giao: editor URL `https://{domain}.omicrm.io/ai/bot/edit/{bot_id}?lng=vi`, nội dung theo mục "Giao kết quả".
5. **Kiểm thử bằng MCP**: `get_contact_by_phone` hoặc `search_contacts` để kiểm tra dữ liệu bot tra cứu; `search_conversations` + `search_channel_messages` để xem hội thoại thật bot đã trả lời; `create_contact` để tạo khách mẫu (dọn bằng `delete_contact` khi user đồng ý). `send_*_message` gửi cho người thật — chỉ khi user đồng ý.

## Bước 7 — Gắn LiveTalk, kiểm thử, tối ưu — chi tiết `references/livetalk-test-optimize.md`
1. **Gắn kênh**: chỉ dùng widget LiveTalk test riêng (không gắn vào kênh đang phục vụ khách thật). Chọn bot ngay trên kênh, hoặc OMIFlow `GENERAL` (hội thoại mới, lọc đúng widget test) → `OMI_BOT_AI` (skill `omicall-omiflow`; tốn quota flow → hỏi user).
2. **Chat thử**: "Trò chuyện thử" trong editor hoặc đóng vai khách trên widget test. Xác minh bản nháp hay bản xuất bản đang trả lời trước khi kết luận.
3. **Bộ câu hỏi**: phủ 14 nhóm (mở đầu, FAQ, từng ý định, thu thông tin, API, ngoài dữ liệu, ngoài phạm vi, gặp nhân viên, khiếu nại, dữ liệu nhạy cảm, chống dẫn dắt, nhiều lượt, nhiều ý, kết thúc). Kỳ vọng chỉ lấy từ dữ liệu của bot.
4. **Chấm** 5 tiêu chí 0–2 (nội dung, ý định, không bịa, giọng văn, chuyển nhân viên) + đánh dấu lỗi nghiêm trọng; đạt khi không lỗi nghiêm trọng và ≥ 85%.
5. **Tối ưu** theo bảng triệu chứng → chỗ sửa; snapshot trước khi sửa, mỗi vòng một nhóm nguyên nhân, `save_draft_v2`, chạy lại toàn bộ bộ câu hỏi, tối đa 3 vòng.
6. **Báo cáo** trước/sau bằng `scripts/eval_report.py --strict` (ca thiếu kết quả tính là trượt); khung bộ câu hỏi: `scripts/bot_outline.py --testcases-skeleton`. Báo cáo chứa dữ liệu khách → để ngoài repo skill.

# Đăng nhập an toàn
- **Không** tự điền username/password vào form đăng nhập hay API đăng nhập bằng script/JS, kể cả khi đã có sẵn thông tin đăng nhập.
- **Ưu tiên MCP OMI**: đăng nhập một lần bằng `scripts/omi_login.py setup` (user gõ mật khẩu trong terminal), về sau agent tự `omi_login.py login` hoặc `login_omicall_mcp`, đọc token bằng `scripts/omi_session.py`. Đây là đường chính để gọi API chatbot (Bước 5/6). Không in mật khẩu/token và không ghi bí mật vào repo hoặc file tạm.
- **Dự phòng khi client chưa nạp MCP trong phiên hiện tại**: mở editor trong browser pane, nhờ user tự đăng nhập một lần rồi làm trên giao diện, hoặc user tự đặt `OMI_TOKEN_FILE`. Không đọc cookie bằng JS/CDP; bị lớp an toàn chặn thì không tìm cách lách — hoàn tất cấu hình MCP và yêu cầu mở lại phiên khi client bắt buộc.

# Gotchas chí tử (mọi tenant — sai là hỏng)
- **END POINT KHÁC callbot**: chatbot dùng `omiai_assistant/...` (KHÔNG phải `callbot/...`) trên cùng gateway.
- **RAG/warehouse**: dữ liệu đào tạo "Dữ liệu khác" nằm ở `external-v1-stg.omicrm.com` (`warehouse_of_knowledge/other/`) + `filestore` — **BẮT BUỘC Bearer token** (cookie → 500). List phải dùng `other/search` (không phải `get_list` → payload null).
- **ref_id trong `vector_store.vector_store_files` = record `_id` của `other/add`**, không phải `file_id`; `ai_analyze.vector_store_ids` được build từ đó khi save.
- **Prompt của Ngữ cảnh bắt đầu** nằm ở `campaign.nodes[BEGIN].ai_analyze.content` (drawer "Hướng dẫn & Tính cách BOT"), song song top-level `system_prompt`.
- **save_draft_v2/publish_v2 multipart** field `file`=JSON blob (như add_v2); `_id` giữ nguyên, KHÔNG đổi version/id mới.
- **DUAL**: intent khai CẢ `name_mappings[BEGIN].conditions` (editor) LẪN `nodes[BEGIN].ai_analyze.conditions` (runtime), cùng id, 2 điều kiện hệ thống cuối. Schema mặc định: kiểu ngôn ngữ tự nhiên ở `references/api-reference.md` mục "Trường hợp mô tả bằng ngôn ngữ tự nhiên (CUSTOM_INTENT)"; schema chip (`data[]` `OMI_BOT_INTENT`) chỉ để đọc bot cũ. Schema mới chưa có trong tài liệu → xác minh bằng captor, không tự đoán.
- **RAG cần training xong** mới trả lời đúng; `vector_store`/`question_answer` rỗng thì bot chỉ dựa `system_prompt`.
- Không bấm **Xuất bản** trên UI trừ khi user yêu cầu (`is_publish` giữ nguyên).
- **Làm trên giao diện** (Chrome CDP, captor, Escape, autosave tab Đào tạo, tải file, thêm ý định, ô nhập nối thêm, kiểm chứng sau khi lưu): đọc `references/ui-gotchas.md` trước khi thao tác.
- Chỉ dùng token đúng tenant: kiểm tra `domain`/`tenant_id` bằng `python scripts/omi_session.py` trước khi ghi; nhiều tenant thì mỗi tenant một server MCP hoặc `logout` rồi đăng nhập lại. Xem mục "Đăng nhập an toàn".
- **Trường hợp trong Ngữ cảnh bắt đầu = mô tả ngôn ngữ tự nhiên** (chế độ "Nhận dạng ý định" → `CUSTOM_INTENT`, ô "Hướng dẫn BOT" ghi khi nào chọn / khi nào KHÔNG chọn / câu ví dụ). Không chọn ý định hệ thống ở "Chủ đề / Ý định mong muốn". Schema: `references/api-reference.md`.
- **Test lại sau mỗi lần sửa bot: gõ `/end` trong khung chat** để đóng phòng cũ; phòng đang mở giữ phiên bản bot cũ. Chưa `/end` thì không kết luận được.
- **Hành động trong bot chạy khác nhau theo đường vào**: chat "Trò chuyện thử" → bot gọi webhook/flow bình thường; bot được OMIFlow giao qua nút `OMI_BOT_AI` (kênh thật, vd. LiveTalk) → bot trả lời nhưng hành động trong kịch bản bot có thể không chạy. Luôn test qua đúng kênh thật trước khi giao. Flow phụ thuộc gọi bằng `START_OTHER_CAMPAIGN` **không nhận biến hội thoại** (`{{social_content}}`… rỗng).
- **Nút Thu thập thông tin**: case theo biến được xét ở **tin nhắn kế tiếp** của khách, không phải ngay tin chứa dữ liệu → hành động (webhook tạo lead) chạy trễ một lượt.
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
- Header `Authorization` tĩnh trong Truy vấn: token Public API đổi từ apiKey hết hạn sau 24 giờ → Cần xác nhận cách làm mới (mục kế tiếp, Hướng A).

## Bot cần dữ liệu CRM — chọn hướng (chi tiết `references/crm-integration.md`)
- **Hướng A (mặc định)**: một Truy vấn gọi thẳng OMICall Public API `POST https://public-v1-stg.omicall.com/api/v2/contact/search?page=1&size=1`, body `{"keyword": "{{social_phone_number_linked}}"}`, header Bearer **API token của tenant** (khác JWT phiên; hỏi user, không tự trích từ cookie). Không tốn quota flow. Endpoint, cURL, cấu hình Truy vấn: `references/omicall-public-api.md`.
  - ⚠ Token đổi từ apiKey (`GET /api/auth?apiKey=`) **hết hạn sau 24 giờ** (`references/omicall-public-api.md` dòng Auth) → header Authorization tĩnh trong Truy vấn sẽ hỏng sau 24 giờ. Dùng thật: "Cần xác nhận" cách làm mới token với user, hoặc đi Hướng B.
- **Hướng B**: Truy vấn trỏ webhook OMIFlow khi cần tạo khách nếu chưa có, phân bổ nhân viên, tích hợp bên thứ ba; tốn quota flow (gói Trial thường 1 flow). Dựng flow bằng skill `omicall-omiflow`.
- **Kết hợp**: OMIFlow để tạo/cập nhật, Public API để đọc. Đối chiếu khách theo trường "Số điện thoại" chuẩn, không theo thuộc tính tuỳ chỉnh.

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
Chatbot ↔ CRM (Public API, OMIFlow, cấu hình Truy vấn, test cURL): **`references/crm-integration.md`**. Thao tác giao diện: **`references/ui-gotchas.md`**.
Gắn LiveTalk, bộ câu hỏi thử, tiêu chí chấm, bảng lỗi → chỗ sửa, báo cáo trước/sau: **`references/livetalk-test-optimize.md`** + `scripts/eval_report.py`.
MCP OMI — cài đặt, đăng nhập, công cụ cho từng bước, cách tiết kiệm token: **`references/omi-mcp.md`** (bản giống hệt trong 4 skill OMI). Token cho API: `scripts/omi_session.py`.
Script riêng: `scripts/validate_bot.py` (checklist C1–C7 + X1–X9), `scripts/bot_outline.py`, `scripts/build_bot.py`, `scripts/rag_upload.py`, `scripts/omi_bot_lib.py`, `scripts/eval_report.py`.

# Bảo trì skill
1. **Học kiến thức mới → ghi vào skill**: schema/key mới (intent, action, RAG, cách lưu), edge-case → cập nhật `SKILL.md` / `references/api-reference.md` / `references/node-status.json` (nhãn chỉ nâng khi có bằng chứng GET thật).
2. Đọc trước khi ghi — tránh trùng lặp.
3. Luôn kèm **ví dụ JSON thật** (từ bot đã verify), đã làm sạch: placeholder `<domain>`, `<tenant_id>`, `<bot uuid>`, `<so_dien_thoai>`; không token, không SĐT/tên/dữ liệu khách.
4. Báo phần đã update trong summary cuối.
5. **Giữ skill tổng quát**: KHÔNG hardcode prompt/intent/tên bot, domain hay thông tin đăng nhập của một tenant vào skill; chỉ ghi kiến thức nền tảng + schema ở `references/api-reference.md`.
