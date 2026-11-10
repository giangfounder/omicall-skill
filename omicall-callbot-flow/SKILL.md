---
name: omicall-callbot-flow
description: >-
  [v1.12.0] Xây dựng và chỉnh sửa Callbot theo kịch bản cố định (loại NORMAL) của OMICall/OMICRM: cây hội thoại, ý định và thực thể NLU, dữ liệu huấn luyện cho giọng nói qua điện thoại, Kho tri thức, sinh luồng từ JSON, lưu và gọi thử. Áp dụng cho trang …/ai/callbot/script/update/{id} khi kịch bản không thuộc loại AI_AGENT; với SmartAgent sử dụng omicall-callbot-gen-ai.
---

# OMiCALL Callbot luồng cổ điển (NORMAL) + Kho tri thức — Generic Builder Playbook

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác (script tự bỏ qua nếu đã kiểm trong 1 giờ). Câu đầu tiên: `Đang dùng omicall-callbot-flow v<phiên bản>` (dòng `SKILL_VERSION`; script lỗi thì dùng v1.12.0). Script báo **SKILL.md đã thay đổi** → đọc lại từ đĩa rồi làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.
**Chế độ subagent / hỏi đáp**: là subagent hoặc chỉ hỏi tính năng → bỏ qua: bước này, hỏi domain, khảo sát (`parallel-brief.md`).
**Bước nào phải làm trên giao diện**: theo `references/ui-recipes.md` (URL thẳng bằng id, chờ bằng `find`, bấm theo ref, kiểm bằng JS hoặc GET; ≤ 1 ảnh mỗi màn hình).

## Bắt đầu và cách trao đổi (BẮT BUỘC)
Làm theo `references/conversation.md`, chung cho mọi skill OMI:
- Mục 1: hỏi domain → `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>` → `"need":"setup"` thì mở form cục bộ `omi_login.py setup --ui` trong agent (cách duy nhất; dự phòng: `references/omi-login.md` mục 2a). Không nhận mật khẩu qua chat, không gõ hay đọc form.
- Mục 2–6: khung 5 bước, cách hỏi lại, mẫu câu, lời thường.

## Đường nhanh
Script nằm ở `<thư mục skill>/scripts/`, chạy bằng đường dẫn tuyệt đối. Khối này chỉ là lối tắt; quy tắc gốc ở Rules, Workflow, Gotchas.
1. `ensure` `ok:true` → đi tiếp; `ok:false` → `scripts/omi_preflight.py --domain <domain>`: `login` → tự chạy `scripts/omi_login.py login --domain <domain>`; `blocked` → mở form đăng nhập theo `references/conversation.md` mục 1, không đọc cookie; trong lúc chờ làm offline bước 3.
2. `scripts/tenant_survey.py --out <scratch>/tenant_context.json` + MCP `list_agents`/`list_extensions` (API nhân viên: playbook Bước 0); đếm câu theo ý định bằng `references/browser-snippets.md` §2 (Python, ngoài trang) khi script chưa đếm.
3. Soạn bảng ý định/thực thể → **user duyệt** (Bước 2; song song/tuần tự: `references/parallel.md`). Soạn `spec_training.json` → `scripts/gen_training.py` → **user duyệt file** (Bước 3). Hai lần duyệt giữ riêng, không gộp.
4. Tenant trống (`training/search_v3` `total_items == 0`) mà cần dữ liệu mẫu hệ thống (`training/reset`) → **hỏi user riêng** trước khi bấm (playbook Bước 4.1); đã có câu huấn luyện thì không reset. Đẩy Excel **qua giao diện** (Rule 4; trạng thái `upload_excel`: `references/api-reference.md` §2) → khảo sát lại để có id ý định/thực thể trong `tenant_context.json`.
5. Trong lúc chờ huấn luyện: soạn `spec_callflow.json`; được chạy `build_callflow.py --allow-pending` để kiểm cấu trúc sớm (payload đó không lưu).
6. `scripts/build_callflow.py spec_callflow.json --context tenant_context.json --out payload.json` → `scripts/verify_callflow.py payload.json --context tenant_context.json --mode pre`.
7. `scripts/omi_save.py callflow payload.json --domain <domain> --new` `--context <scratch>/tenant_context.json` (cập nhật: `--update --base <bản mới nhất> --confirm-update`): tự GET lại + `verify_callflow --mode post --sent` kèm `--context` và (khi `--update`) `--base`/`--base-version`. FAIL → sửa spec, dựng lại.
8. Chờ huấn luyện `SUCCESS` → user tự gọi thử (Bước 6). Không Xuất bản, không gắn hotline khi user chưa yêu cầu.
Dùng builder thì KHÔNG cần đọc `references/api-reference.md` §5; chỉ đọc khi sửa tay hoặc loại node chưa có trong builder (tra `references/node-status.json`).

## Mặc định hành vi và kiểm thử
- Tình huống chung (từ chối, ngoài phạm vi, tức giận, im lặng, đòi gặp nhân viên, kết thúc): đối chiếu `references/default-behaviors.md` giữa callbot cổ điển, SmartAgent, chatbot; ô "—" là Cần xác nhận, không đoán.
- Trước khi giao: chạy bộ tình huống `references/test-cases.md`, báo `Đạt n/12`.

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
| kịch bản là SmartAgent (AI_AGENT) | `omicall-callbot-gen-ai` |
| cần webhook sang OMIFlow (tra cứu, popup, phiếu) | `omicall-omiflow` |
| gắn kịch bản vào hotline hoặc phím IVR, nhóm đích khi chuyển máy | `omicall-pbx-config` |
| dữ liệu thu thập phải ghi vào thuộc tính khách/phiếu chưa có | `omicall-crm-config` |
<!-- skill-links:end -->

## Rules (BẮT BUỘC)
1. **Skill dùng chung**: không ghi nội dung nghiệp vụ, câu thoại, tên sản phẩm, id tenant của khách vào skill. Mọi thứ riêng của dự án nằm trong file spec do agent soạn ở thư mục làm việc. Học được kiến thức nền tảng mới → ghi vào skill (kèm ví dụ JSON đã kiểm chứng), đọc trước khi ghi để tránh trùng.
2. **Suy luận từ tài liệu hiện tại**: bước, ý định, thực thể, lời thoại do agent tự phân tích; chỗ tài liệu không có ghi "Cần xác nhận", không bịa.
3. **Dùng lại trước khi tạo mới**: ưu tiên ý định/thực thể hệ thống (`omi_intent_*`, `omi_entity_*`, `khach_can_gap/*`).
4. **Kho tri thức dùng chung cho mọi kịch bản NORMAL của tenant**, mỗi lần nhập dữ liệu là một lần huấn luyện lại toàn bộ (10–20 phút) → gom dữ liệu vào **một file**, gửi user duyệt, **đẩy một lần qua giao diện**. Không xoá dữ liệu có sẵn khi user chưa yêu cầu.
5. Không bấm **Xuất bản**, không gắn kịch bản vào hotline/chiến dịch, không gọi thử khi user chưa yêu cầu và chưa đưa số.
6. Đăng nhập theo `references/conversation.md` mục 1 (form cục bộ `omi_login.py setup --ui`). Hết hạn hoặc 401 → tự chạy `omi_login.py login --domain <domain>`, không hỏi lại. Không nhận mật khẩu qua chat, không in mật khẩu/token, không ghi bí mật vào repo hoặc file tạm. Không đọc cookie hay token trong trang (JS/CDP); token chỉ lấy qua `scripts/omi_session.py`.

## Quy tắc kịch bản mặc định (user đã chốt, áp mọi dự án trừ khi user đổi)
- **Hỏi đáp**: trả lời **1 lần** (1 câu = trả lời + hỏi lại câu của bước); khách hỏi lại cùng chủ đề → bước "báo chuyển máy" → chuyển nhân viên.
- **Ngoài phạm vi / không khớp ý định** (`CUSTOMER_RESPONSE_WRONG`): nhắc lại câu của bước **1 lần**, lần thứ hai → chuyển nhân viên.
- **Khách muốn lặp lại**: đọc lại 1 lần, lần sau → chuyển nhân viên.
- **Khách đòi gặp nhân viên** → báo chuyển → chuyển máy (`transfer_collected_info:true`).
- **Khách tức giận** → xin lỗi, kết thúc. **Im lặng** → nhắc 1 lần → kết thúc lịch sự.
- **Xưng hô**: `{{gender1_ai}}` thay mọi "anh/chị" (hệ thống điền anh/chị theo giới tính khách).
- **Bố cục** dễ nhìn: cột theo thứ tự cuộc gọi, các bước kết thúc/báo chuyển dồn cột áp chót, chuyển máy cột cuối.
- Hỏi "còn cần hỗ trợ gì không" trước khi chào kết thúc; câu chào cuối cảm ơn + tạm biệt (+ số tổng đài nếu tài liệu có).

## Gotchas (đã gặp thật)
- Chưa huấn luyện xong thì ý định/câu mới chưa có hiệu lực → nhánh rơi vào phản hồi sai.
- Câu huấn luyện sai ý định làm lệch mọi kịch bản của tenant; tách rõ các ý định dễ lẫn (data-rules §5).
- `add_v2` chỉ gửi `id` (thiếu `uuid`) → sinh kịch bản trùng. Server tạo thêm 1 id kế tiếp cùng uuid cho editor; danh sách vẫn 1 bản.
- Bấm **Cập nhật** trên editor tạo phiên bản mới (đổi thứ tự biến, sinh lại id action thu thập, thêm `name` cho STAFF, đổi vị trí node) — logic giữ nguyên. Tab editor mở từ bản cũ bấm Cập nhật sẽ **ghi đè** bản mới → sau mỗi lần lưu qua API chuyển tab sang id mới; trước khi lưu qua API so phiên bản mới nhất.
- Browser pane không đọc được file trên máy → tải Excel bằng hộp chọn file Windows. Payload kịch bản chỉ lưu bằng `omi_save.py`, không đưa vào trang.
- Lỗi 401 "Error Occurred!!!" = token hết hạn hoặc cũ → `scripts/omi_login.py login --domain <domain>` rồi chạy lại (Rule 6).
- Trình biên tập chỉ vẽ node trong khung nhìn (`.react-flow__node` không đủ) — kiểm tra bằng API, không bằng DOM.
- Xoá ý định/thực thể hệ thống thừa có thể bị chặn quyền (dữ liệu dùng chung) → để user tự xoá trên UI hoặc bỏ qua; thừa không ảnh hưởng kịch bản.

## Chi tiết theo bước (`references/playbook.md`)
Đọc đúng mục khi tới bước đó, không đọc cả file. Định vị: `grep -n "^#" references/playbook.md`. Mục mà Đường nhanh hay Rules nhắc tới nhưng không có ở đây (Input contract, Workflow từ Bước 0 tới Bước 6, Lời thoại cho giọng đọc) đều nằm trong file này.
- Overview
- Input contract (hỏi MỘT LẦN rồi tự làm hết)
- Workflow
- Lời thoại cho giọng đọc
- Reference
- Bảo trì skill
