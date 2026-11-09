---
name: omicall-chatbot-gen-ai
description: >-
  [v1.13.0] Xây dựng, kiểm thử và tối ưu Chatbot AI (OmiBot) của OMICall/OMICRM trên Zalo OA, Facebook và LiveTalk: lời nhắc hệ thống, ý định trong Ngữ cảnh bắt đầu, truy xuất tri thức (RAG) từ Dữ liệu khác, Truy vấn API, lưu bản nháp hoặc xuất bản qua chatbot-gateway, trò chuyện thử trên LiveTalk và chấm điểm trước/sau khi chỉnh sửa. Áp dụng khi có đường dẫn omicrm.io/ai/bot/.
---

# OMiCALL/OMiCRM AI Chatbot (OmiBot) Gen AI — Generic Builder Playbook (mọi tenant / mọi bot)

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác, 1 lần/phiên (đã chạy rồi, kể cả ở skill khác, thì bỏ qua). Câu đầu tiên: `Đang dùng omicall-chatbot-gen-ai v<phiên bản>` (dòng `SKILL_VERSION`; script lỗi thì dùng v1.13.0). Script báo **SKILL.md đã thay đổi** → đọc lại từ đĩa rồi làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.
**Chế độ subagent / hỏi đáp**: là subagent hoặc chỉ hỏi tính năng → bỏ qua bước này, hỏi domain, khảo sát (`parallel.md` mục 1).

## Bắt đầu và cách trao đổi (BẮT BUỘC)
Làm theo `references/conversation.md`, chung cho mọi skill OMI:
- Mục 1: hỏi domain → `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>` → `"need":"setup"` thì mở form cục bộ `omi_login.py setup --ui` trong agent (cách duy nhất; dự phòng: `references/omi-mcp.md` mục 2a). Không nhận mật khẩu qua chat, không gõ hay đọc form.
- Mục 2–6: khung 5 bước, cách hỏi lại, mẫu câu, lời thường, ít chụp ảnh.

## Đường nhanh
Chạy script bằng đường dẫn tuyệt đối `<thư mục skill>/scripts/...`. Mỗi bước chỉ trỏ tới quy tắc gốc bên dưới, không thay thế.
1. `omi_preflight.py --domain <domain>` → route `api`/`login`/`ui`/`blocked`, không in token. `login` → tự chạy `omi_login.py login --domain <domain>`; `blocked` → form `omi_login.py setup --ui` theo `references/conversation.md` mục 1; không đọc cookie.
2. `tenant_survey.py --out <scratch>/tenant_context.json` + MCP `get_all_channels`, `get_service_package`: kênh, widget LiveTalk test, quota Bot/Dữ liệu khác/OMIFlow (mục "kiểm tra quota"). Thiếu → "Cần xác nhận".
3. `bot_outline.py --id <bot_id> --domain <domain> --save` (hoặc `--file <GET.json>`) → baseline: trường hợp, node, cạnh, biến, Truy vấn, RAG, `is_draft`/`is_publish`.
4. Spec theo `references/spec-bot.example.json` (Bước 2–4; song song/tuần tự: `references/parallel.md`). Tra `references/node-status.json`: `verified` → API (chuyển nhân viên = `handoff` → flow phụ thuộc); chưa có JSON (gửi tin, kết thúc, Kích hoạt ngữ cảnh) → UI, mỗi nút: điền → đóng hết ngăn kéo → Lưu lại → GET (Gotchas).
5. `build_bot.py spec.json --base <GET.json> --out payload.json`: chỉ vá trên baseline, giữ `_id`, tự chạy `validate_bot.py --mode pre`.
6. `omi_save.py bot payload.json --domain <domain>`: `save_draft_v2` → GET lại → `validate_bot.py --mode post --sent`. Không có cờ xuất bản.
7. Có tài liệu RAG: `rag_upload.py <file> --bot payload.json` (Bước 6) rồi lưu lại bằng `omi_save.py`.
8. Chat thử trên widget LiveTalk test (gắn kênh chỉ khi user đồng ý), gõ `/end` sau mỗi lần cập nhật bot (Gotchas); chấm G1–G14 bằng `eval_report.py --strict` (Bước 7).
9. Giao theo mục "Giao kết quả". Xuất bản chỉ khi user yêu cầu.

# Rules (BẮT BUỘC)
1. **Suy luận từ nghiệp vụ**: đọc tài liệu → tự tách nhóm khách, intent, biến thu, prompt — chỉ dùng bot tenant khác làm tham chiếu hình dạng.
2. **Không bịa** schema, giá, chính sách hay dữ liệu nghiệp vụ: thiếu dữ kiện → hỏi lại user hoặc ghi "Cần xác nhận".
3. Bảo trì skill (ghi kiến thức mới vào skill, đọc trước khi ghi, ví dụ JSON thật, giữ skill tổng quát, báo phần đã update): mục **"Bảo trì skill"** trong `references/playbook.md`.

## Mặc định hành vi và kiểm thử
- Tình huống chung (từ chối, ngoài phạm vi, tức giận, im lặng, đòi gặp nhân viên, kết thúc): đối chiếu `references/default-behaviors.md` giữa callbot cổ điển, SmartAgent, chatbot; ô "—" là Cần xác nhận, không đoán.
- Trước khi giao: chạy bộ câu hỏi G1–G14 và chấm theo `references/livetalk-test-optimize.md` mục 4–5, báo bằng `scripts/eval_report.py --strict`. Đây là hệ chấm duy nhất của skill này.

## Tư duy chức năng (trước khi chọn module)
- Chỉ khi dựng mới hoặc việc chạm nhiều module (sửa nhỏ một bước/lời nhắc thì bỏ qua, đọc đúng mục playbook cần): đọc `references/system-model.md` (hệ thống có gì, làm được gì, đường nhanh nhất cho từng việc) và `references/solution-method.md` (phân rã bài toán thành chuỗi Sự kiện → Điều kiện → Hành động, ghép module có sẵn). Không khớp mẫu theo ca; mắt xích chưa xác minh thì báo user, khảo sát một lần bằng log mạng rồi ghi vào `system-model.md`.

<!-- skill-links:start (sinh từ shared/skill-graph.json bằng tools/gen_skill_links.py, đừng sửa tay) -->
## Gọi skill liên quan (tự động khi bài toán chạm tới)
Mắt xích thuộc skill khác (xem `references/system-model.md`) thì không tự làm theo trí nhớ: gọi skill đó rồi quay lại.
1. **Gọi**: công cụ Skill với đúng tên bên dưới; client không có thì đọc `<thư mục skill>/../<tên skill>/SKILL.md`. Chỉ làm đúng phần của mắt xích đó.
2. **Dùng chung**, không làm lại: domain, đăng nhập, `tenant_context.json` (chỉ đọc), `manifest.py`. Việc ghi vẫn chờ user duyệt như skill đích quy định.
3. **Trả lại**: ghi id/mã vừa tạo bằng `manifest.py set` (giá trị nền: `ctx-set`), rồi tiếp tục skill đang làm. Thứ tự khi cần nhiều phần: crm-config → ai-insight → pbx-config (nhóm, lời chào) → omiflow (webhook, nháp) → user xuất bản flow → bot/callbot (URL flow, nháp) → user xuất bản bot → pbx-config gắn số → gọi thử (hai cổng user duyệt).

| Khi gặp | Gọi skill |
|---|---|
| bot cần tra CRM hoặc tạo phiếu qua flow WEB_HOOK | `omicall-omiflow` |
| thuộc tính khách hoặc pipeline trạng thái khách chưa có | `omicall-crm-config` |
| đánh giá hội thoại bot bằng Chat Insights | `omicall-ai-insight` |
<!-- skill-links:end -->

## Gotchas chí tử (5 quy tắc an toàn; danh sách đầy đủ và lý do: `references/playbook.md` mục "Gotchas chí tử", giao diện: `references/ui-gotchas.md`)
- Không bấm Xuất bản trừ khi user yêu cầu. Đăng nhập an toàn: không đọc cookie, không in token; kiểm `domain`/`tenant_id` bằng `omi_session.py` trước khi ghi (mục "Đăng nhập an toàn" trong playbook).
- DUAL: intent khai cả `name_mappings[BEGIN].conditions` lẫn `nodes[BEGIN].ai_analyze.conditions`, cùng id; trường hợp viết bằng ngôn ngữ tự nhiên (`CUSTOM_INTENT`), không chọn ý định hệ thống.
- File GET đã che `Authorization` không dùng làm base để lưu (validator X6).
- Chuyển nhân viên = trường hợp → ACTION `START_OTHER_CAMPAIGN` gọi flow phụ thuộc (spec `handoff`), không phải nút giao diện; bot vẫn gửi 1 câu LLM tự soạn trước khi chuyển (giới hạn nền tảng, báo user).
- Mỗi lần cập nhật bot: `/end` rồi chat lại, test qua đúng kênh thật trước khi giao (quy tắc gốc trong playbook Gotchas).

## Chi tiết theo bước (`references/playbook.md`)
Đọc đúng mục khi tới bước đó, không đọc cả file. Định vị: `grep -n "^#" references/playbook.md`. Mục mà Đường nhanh hay Rules nhắc tới nhưng không có ở đây (Input contract, Workflow, Gotchas, Skill con…) đều nằm trong file này.
- Overview
- Input contract
- Workflow
- Bước 0 — Đăng nhập (MCP OMI trước) & lấy token — chi tiết `references/omi-mcp.md`
- Bước 1 — Baseline schema
- Bước 2 — Hiểu nghiệp vụ (PHÂN TÍCH — do LLM tự suy luận)
- Bước 3 — Thiết kế intent + xử lý + routing (do LLM tự tư duy)
- Bước 4 — Viết System Prompt (do LLM tự soạn từ nghiệp vụ)
- Bước 5 — Dựng payload & intent (schema: api-reference.md — đọc TRƯỚC khi build)
- Bước 6 — RAG/Training + Verify + Giao (luồng VERIFIED)
- Bước 7 — Gắn LiveTalk, kiểm thử, tối ưu — chi tiết `references/livetalk-test-optimize.md`
- Đăng nhập an toàn
- Gotchas chí tử (mọi tenant — sai là hỏng)
- Chỉ liệt kê intent nào cần flow xử lý riêng
- Truy vấn API trong Ngữ cảnh bắt đầu (khác với node Hành động)
- Bot cần dữ liệu CRM — chọn hướng (chi tiết `references/crm-integration.md`)
- Quy ước biên soạn
- Suy luận nghiệp vụ TỪ tài liệu, không tự vẽ lại
- CRM cho phép thuộc tính động — không lăn tăn nếu chưa có sẵn
- Không thu SĐT từ khách chat — lấy từ Đa kênh
- Trước khi dựng flow — kiểm tra quota gói dịch vụ
- Giao kết quả
- Reference
- Bảo trì skill
