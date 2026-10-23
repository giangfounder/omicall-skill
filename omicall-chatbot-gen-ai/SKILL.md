---
name: omicall-chatbot-gen-ai
description: >-
  [v1.5.0] Dựng, kiểm thử và tối ưu Chatbot AI (OmiBot) của OMiCALL/OMiCRM cho Zalo OA, Facebook, LiveTalk: lời nhắc hệ thống, ý định trong Ngữ cảnh bắt đầu, RAG Dữ liệu khác, Truy vấn API, lưu nháp hoặc xuất bản qua chatbot-gateway, chat thử trên LiveTalk, chấm điểm trước/sau. Kích hoạt khi có đường dẫn omicrm.io/ai/bot/.
---

# OMiCALL/OMiCRM AI Chatbot (OmiBot) Gen AI — Generic Builder Playbook (mọi tenant / mọi bot)

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác (`<thư mục skill>` = thư mục chứa SKILL.md này). Câu đầu tiên trả lời user: `Đang dùng omicall-chatbot-gen-ai v<phiên bản>` (lấy từ dòng `SKILL_VERSION`; script lỗi thì dùng v1.5.0). Script báo **SKILL.md đã thay đổi** → đọc lại SKILL.md từ đĩa rồi mới làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.

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
Hỏi một lần: (1) **domain doanh nghiệp**; (2) **tài khoản và thông tin xác thực cần thiết** để agent tự cấu hình MCP OMI; (3) **mô tả nghiệp vụ** (kịch bản, FAQ, tài liệu dịch vụ hoặc prompt). Nếu thông tin đã có trong yêu cầu hoặc cấu hình bí mật thì không hỏi lại. Tên bot tự đặt theo doanh nghiệp và mục đích. Bot đã có sẵn đúng nhu cầu → reuse giữ nguyên `_id` (save ghi đè).

# Workflow

## Bước 0 — Đăng nhập (MCP OMI trước) & lấy token — chi tiết `references/omi-mcp.md`
- **MCP OMI**: nếu chưa có thì agent tự cài và tự cấu hình ở phạm vi người dùng theo `omi-mcp.md` mục 1 trên mọi agent/client hỗ trợ MCP, không mặc định Codex hay Claude; sau đó gọi `login_omicall_mcp` (+ `select_tenant`) → `python scripts/omi_session.py` (đọc phiên MCP, in tenant/domain/hạn, không in token); script khác import `omi_session.headers()`.
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
- Lấy GET làm baseline → overwrite `system_prompt`, `assistant_name/description`, `history_config`, intents trong BEGIN_CONTEXT (`campaign.name_mappings[0].conditions` + `campaign.nodes[0].ai_analyze.conditions`) khi schema intent đã xác minh. Nếu intent schema chưa rõ → **dùng UI trên Chrome + bắt mạng (captor)** để học trước khi build API (`references/ui-gotchas.md`).
- Save: `POST /omiai_assistant/save_draft_v2` (multipart field `file`=JSON). Publish: `POST /omiai_assistant/publish_v2` (chỉ khi user yêu cầu).

## Bước 6 — RAG/Training + Verify + Giao (luồng VERIFIED)
1. Tạo dữ liệu đào tạo **"Dữ liệu khác"** bằng API (không cần UI): upload file lên `file_store/put_v2` (`business_type=warehouse_of_knowledge_files`, field `file_0`) → tạo record `warehouse_of_knowledge/other/add` (base `external-v1-stg.omicrm.com`, **Bearer token**, body có `object_info` + `add_bot_uuids`). Chi tiết + body chuẩn: `references/api-reference.md` mục **"RAG — Dữ liệu khác"** (đã verify end-to-end: file ≤15MB, ref_id = record `_id`).
2. **Gắn file vào Ngữ cảnh bắt đầu → Kho tri thức → Dữ liệu khác**: set `vector_store` + `campaign.nodes[0].ai_analyze.vector_store_ids=[record _id]` rồi `save_draft_v2`. Sau save `file_training_status:"completed"` = đã train xong, bot trả lời được bằng kiến thức.
3. Test chat: `POST /omiai_assistant/bot_testing_v2` hoặc nút "Trò chuyện thử".
4. Verify: `GET bot` (chỉ in trường cần kiểm tra) + reload editor + test tin nhắn. Giao: editor URL `https://{domain}.omicrm.io/ai/bot/edit/{bot_id}?lng=vi`.
5. **Kiểm thử bằng MCP**: `get_contact_by_phone` hoặc `search_contacts` để kiểm tra dữ liệu bot tra cứu; `search_conversations` + `search_channel_messages` để xem hội thoại thật bot đã trả lời; `create_contact` để tạo khách mẫu (dọn bằng `delete_contact` khi user đồng ý). `send_*_message` gửi cho người thật — chỉ khi user đồng ý.

## Bước 7 — Gắn LiveTalk, kiểm thử, tối ưu — chi tiết `references/livetalk-test-optimize.md`
1. **Gắn kênh**: chỉ dùng widget LiveTalk test riêng (không gắn vào kênh đang phục vụ khách thật). Chọn bot ngay trên kênh, hoặc OMIFlow `GENERAL` (hội thoại mới, lọc đúng widget test) → `OMI_BOT_AI` (skill `omicall-omiflow`; tốn quota flow → hỏi user).
2. **Chat thử**: "Trò chuyện thử" trong editor hoặc đóng vai khách trên widget test. Xác minh bản nháp hay bản xuất bản đang trả lời trước khi kết luận.
3. **Bộ câu hỏi**: phủ 14 nhóm (mở đầu, FAQ, từng ý định, thu thông tin, API, ngoài dữ liệu, ngoài phạm vi, gặp nhân viên, khiếu nại, dữ liệu nhạy cảm, chống dẫn dắt, nhiều lượt, nhiều ý, kết thúc). Kỳ vọng chỉ lấy từ dữ liệu của bot.
4. **Chấm** 5 tiêu chí 0–2 (nội dung, ý định, không bịa, giọng văn, chuyển nhân viên) + đánh dấu lỗi nghiêm trọng; đạt khi không lỗi nghiêm trọng và ≥ 85%.
5. **Tối ưu** theo bảng triệu chứng → chỗ sửa; snapshot trước khi sửa, mỗi vòng một nhóm nguyên nhân, `save_draft_v2`, chạy lại toàn bộ bộ câu hỏi, tối đa 3 vòng.
6. **Báo cáo** trước/sau bằng `scripts/eval_report.py`; báo cáo chứa dữ liệu khách → để ngoài repo skill.

# Đăng nhập an toàn
- **Không** tự điền username/password vào form đăng nhập hay API đăng nhập bằng script/JS, kể cả khi đã có sẵn thông tin đăng nhập.
- **Ưu tiên MCP OMI**: agent tự kiểm tra, tự cài và tự cấu hình MCP theo `references/omi-mcp.md`, rồi gọi `login_omicall_mcp` và đọc token từ phiên MCP bằng `scripts/omi_session.py`. Đây là đường chính để gọi API chatbot (Bước 5/6). Không in mật khẩu/token và không ghi bí mật vào repo hoặc file tạm.
- **Dự phòng khi client chưa nạp MCP trong phiên hiện tại**: mở editor trong browser pane, nhờ user tự đăng nhập một lần. Nếu việc đọc cookie bị lớp an toàn chặn thì không tìm cách lách; hoàn tất cấu hình MCP và yêu cầu mở lại phiên khi client bắt buộc.

# Gotchas chí tử (mọi tenant — sai là hỏng)
- **END POINT KHÁC callbot**: chatbot dùng `omiai_assistant/...` (KHÔNG phải `callbot/...`) trên cùng gateway.
- **RAG/warehouse**: dữ liệu đào tạo "Dữ liệu khác" nằm ở `external-v1-stg.omicrm.com` (`warehouse_of_knowledge/other/`) + `filestore` — **BẮT BUỘC Bearer token** (cookie → 500). List phải dùng `other/search` (không phải `get_list` → payload null).
- **ref_id trong `vector_store.vector_store_files` = record `_id` của `other/add`**, không phải `file_id`; `ai_analyze.vector_store_ids` được build từ đó khi save.
- **Prompt của Ngữ cảnh bắt đầu** nằm ở `campaign.nodes[0].ai_analyze.content` (drawer "Hướng dẫn & Tính cách BOT"), song song top-level `system_prompt`.
- **save_draft_v2/publish_v2 multipart** field `file`=JSON blob (như add_v2); `_id` giữ nguyên, KHÔNG đổi version/id mới.
- **DUAL trí**: nếu intent phải khai CẢ `name_mappings[0].conditions` (editor) LẪN `nodes[].ai_analyze.conditions` (runtime) như callbot — xác minh bằng captor, không tự đoán.
- **RAG cần training xong** mới trả lời đúng; `vector_store`/`question_answer` rỗng thì bot chỉ dựa `system_prompt`.
- Không bấm **Xuất bản** trên UI trừ khi user yêu cầu (`is_publish` giữ nguyên).
- **Làm trên giao diện** (Chrome CDP, captor, Escape, autosave tab Đào tạo, tải file, thêm ý định, ô nhập nối thêm, kiểm chứng sau khi lưu): đọc `references/ui-gotchas.md` trước khi thao tác.
- Chỉ dùng token đúng tenant: kiểm tra `domain`/`tenant_id` bằng `python scripts/omi_session.py` trước khi ghi; nhiều tenant thì mỗi tenant một server MCP hoặc `logout` rồi đăng nhập lại. Xem mục "Đăng nhập an toàn".
- **Giới hạn gói (plan) của tenant**: có thể chỉ cho 1 "File văn bản" mỗi lúc (`0/1`). Phải xoá/gỡ file cũ khỏi "Dữ liệu khác" (tab Đào tạo) trước khi thêm file mới nếu báo "đã đạt giới hạn cho phép".

## Chỉ liệt kê intent nào cần flow xử lý riêng
Hệ thống này chạy tương tự N8N: **chỉ những ý định cần rẽ nhánh/flow xử lý riêng (gọi API, thu biến, chuyển bước) mới cần khai báo trong Ngữ cảnh bắt đầu**. Ý định thuần Q&A (khách hỏi kiến thức chung) — bot đã tự trả lời qua system_prompt + RAG, KHÔNG cần liệt kê thành Trường hợp riêng. Trước khi thêm 1 Trường hợp, hỏi: "ý định này có phải bot làm gì đặc biệt ngoài việc trả lời văn bản không?" — nếu chỉ trả lời từ RAG thì bỏ qua.

## Truy vấn API trong Ngữ cảnh bắt đầu (khác với node Hành động)
Drawer "Ngữ cảnh bắt đầu" có mục **"Truy vấn"** (cạnh "Hướng dẫn & Tính cách BOT", "Kho tri thức") — đây là chỗ khai báo API bot **tự gọi mỗi lượt trước khi chọn ý định**. Đặt các call API "chung, mỗi lượt" ở đây (vd: xác thực KH, lấy data CRM), không dùng node "Hành động" sau case ý định. Config gồm: Tên truy vấn, Hướng dẫn BOT (khi nào dùng — thực tế bot gọi mỗi lượt), Cấu hình (GET/POST/URL/Headers/Body raw JSON), Thời gian chờ, Hướng dẫn BOT lấy kết quả (schema JSON trả về + cách xử lý lỗi).
- Body dùng biến động qua `{{tên_biến}}` — biến Đa kênh chuẩn: `{{social_phone_number_linked}}` (SĐT khách đã link), `{{social_customer_name_linked}}` (tên khách đã link), `{{social_session_id}}`. Danh sách đầy đủ 106 thuộc tính Đa kênh xem trong picker khi bấm "Đa kênh" ở footer drawer.
- Node "Hành động → API" (mở qua right-click canvas → Hành động) dùng cho trường hợp khác: chỉ chạy khi 1 case cụ thể match. Đừng nhầm 2 chỗ này.

## Bot cần dữ liệu CRM — chọn hướng (chi tiết `references/crm-integration.md`)
- **Hướng A (mặc định)**: một Truy vấn gọi thẳng OMICall Public API `POST https://public-v1-stg.omicall.com/api/v2/contact/search?page=1&size=1`, body `{"keyword": "{{social_phone_number_linked}}"}`, header Bearer **API token của tenant** (khác JWT phiên; hỏi user, không tự trích từ cookie). Không tốn quota flow. Endpoint, cURL, cấu hình Truy vấn: `references/omicall-public-api.md`.
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

# Credentials registry
Bảng creds + bot mẫu từng tenant: **`references/credentials.md`**. Tenant mới → thêm 1 dòng.

# Reference
Endpoint, schema bot top-level + campaign + ví dụ đã verify, checklist validation, captor script: **`references/api-reference.md`**.
Chatbot ↔ CRM (Public API, OMIFlow, cấu hình Truy vấn, test cURL): **`references/crm-integration.md`**. Thao tác giao diện: **`references/ui-gotchas.md`**.
Gắn LiveTalk, bộ câu hỏi thử, tiêu chí chấm, bảng lỗi → chỗ sửa, báo cáo trước/sau: **`references/livetalk-test-optimize.md`** + `scripts/eval_report.py`.
MCP OMI — cài đặt, đăng nhập, công cụ cho từng bước, cách tiết kiệm token: **`references/omi-mcp.md`** (bản giống hệt trong 3 skill OMI). Token cho API: `scripts/omi_session.py`.
