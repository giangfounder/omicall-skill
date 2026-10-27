---
name: omicall-callbot-flow
description: >-
  [v1.5.0] Dựng và sửa Callbot luồng cổ điển (kịch bản NORMAL) của OMiCall/OMiCRM: cây hội thoại, ý định và thực thể NLU, dữ liệu huấn luyện giọng điện thoại, Kho tri thức, sinh luồng từ JSON, lưu và gọi thử. Dùng cho trang …/ai/callbot/script/update/{id} khi kịch bản không phải AI_AGENT; SmartAgent dùng omicall-callbot-gen-ai.
---

# OMiCALL Callbot luồng cổ điển (NORMAL) + Kho tri thức — Generic Builder Playbook

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác (`<thư mục skill>` = thư mục chứa SKILL.md này). Câu đầu tiên trả lời user: `Đang dùng omicall-callbot-flow v<phiên bản>` (lấy từ dòng `SKILL_VERSION`; script lỗi thì dùng v1.5.0). Script báo **SKILL.md đã thay đổi** → đọc lại SKILL.md từ đĩa rồi mới làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.

## Bắt đầu: hỏi domain, rồi yêu cầu đăng nhập
1. Câu hỏi đầu tiên cho user chỉ là **tên domain** doanh nghiệp (`<tên>.omicrm.io`); domain đã có trong yêu cầu thì bỏ qua.
2. `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>` (một lệnh: kiểm token, tự đăng nhập lại từ kho bí mật). `"ok":true` → sang bước 4, không nói gì thêm về đăng nhập.
3. `"need":"setup"` → yêu cầu user đăng nhập trên **trang đăng nhập OMI thật**: mở `https://<domain>.omicrm.io/?lng=vi` trong trình duyệt của agent (browser pane của Claude, Chrome MCP… — agent nào có trình duyệt thì dùng trình duyệt đó), điền sẵn email nếu user đã cho, rồi nhắn đúng một câu: "Anh/chị nhập mật khẩu trên trang OMI vừa mở rồi bấm Đăng nhập." Agent KHÔNG gõ vào ô mật khẩu, không đọc cookie hay token của trang. Tự kiểm trang (ảnh chụp/văn bản) tới khi vào được trong ứng dụng thì làm tiếp; phiên này chỉ dùng cho thao tác giao diện (route `ui`). Muốn đi đường API/MCP (nhanh hơn) thì user chạy thêm một lần lệnh `command` của `ensure` trong terminal (ô nhập ẩn, `references/omi-mcp.md` mục 2a). Không nhận mật khẩu qua chat; user lỡ gửi thì không dùng, không nhắc lại, khuyên đổi mật khẩu.
4. Đăng nhập xong mới nhận mô tả nghiệp vụ và làm tiếp theo Đường nhanh.

## Đường nhanh
Script nằm ở `<thư mục skill>/scripts/`, chạy bằng đường dẫn tuyệt đối. Khối này chỉ là lối tắt; quy tắc gốc ở Rules, Workflow, Gotchas.
1. `scripts/omi_preflight.py --domain <domain>`: route `api` → đi tiếp; `login` → tự chạy `scripts/omi_login.py login --domain <domain>`; `blocked` → mở terminal cho user chạy `scripts/omi_login.py setup` (Rule 6), không đọc cookie; trong lúc chờ làm offline bước 3.
2. `scripts/tenant_survey.py --out <scratch>/tenant_context.json` + MCP `list_agents`/`list_extensions`; đếm câu theo ý định bằng `references/browser-snippets.md` §3 khi script chưa đếm.
3. Soạn bảng ý định/thực thể → **user duyệt** (Bước 2). Soạn `spec_training.json` → `scripts/gen_training.py` → **user duyệt file** (Bước 3). Hai lần duyệt giữ riêng, không gộp.
4. Đẩy Excel **qua giao diện** (Rule 4; `upload_excel` bằng API chưa kiểm chứng) → khảo sát lại để có id ý định/thực thể trong `tenant_context.json`.
5. Trong lúc chờ huấn luyện: soạn `spec_callflow.json`; được chạy `build_callflow.py --allow-pending` để kiểm cấu trúc sớm (payload đó không lưu).
6. `scripts/build_callflow.py spec_callflow.json --context tenant_context.json --out payload.json` → `scripts/verify_callflow.py payload.json --context tenant_context.json --mode pre`.
7. `scripts/omi_save.py callflow payload.json --domain <domain> --new` `--context <scratch>/tenant_context.json` (cập nhật: `--update --base <bản mới nhất> --confirm-update`): tự GET lại + `verify_callflow --mode post --sent` kèm `--context` và (khi `--update`) `--base`/`--base-version`. FAIL → sửa spec, dựng lại.
8. Chờ huấn luyện `SUCCESS` → user tự gọi thử (Bước 6). Không Xuất bản, không gắn hotline khi user chưa yêu cầu.
Dùng builder thì KHÔNG cần đọc `references/api-reference.md` §5; chỉ đọc khi sửa tay hoặc loại node chưa có trong builder (tra `references/node-status.json`).

## Overview
Kịch bản `type:"NORMAL"` là **luồng cố định**: bot đọc lời soạn sẵn ở node `STAFF`, nghe khách, **mô hình NLU của tenant** (học từ Kho tri thức) nhận ra **ý định** + **thực thể** để rẽ sang nhánh `CONDITION`. Không có LLM sinh câu: mọi câu bot nói phải viết sẵn, và mô hình chỉ hiểu đúng những gì đã được dạy.

| | NORMAL (skill này) | AI_AGENT (`omicall-callbot-gen-ai`) |
|---|---|---|
| Lời bot | Soạn sẵn từng câu | LLM sinh từ prompt |
| Hiểu khách | NLU tenant: `intent_code` + `entity_code` | LLM so mô tả ý định |
| Chuẩn bị | Dữ liệu huấn luyện + chờ huấn luyện | Không |
| Hợp với | Câu chữ cố định, sản lượng lớn, đo theo nhãn | Tư vấn mở |
Nghiệp vụ cần tư vấn tự do thì đề xuất AI_AGENT.

## Rules (BẮT BUỘC)
1. **Skill dùng chung**: không ghi nội dung nghiệp vụ, câu thoại, tên sản phẩm, id tenant của khách vào skill. Mọi thứ riêng của dự án nằm trong file spec do agent soạn ở thư mục làm việc. Học được kiến thức nền tảng mới → ghi vào skill (kèm ví dụ JSON đã kiểm chứng), đọc trước khi ghi để tránh trùng.
2. **Suy luận từ tài liệu hiện tại**: bước, ý định, thực thể, lời thoại do agent tự phân tích; chỗ tài liệu không có ghi "Cần xác nhận", không bịa.
3. **Dùng lại trước khi tạo mới**: ưu tiên ý định/thực thể hệ thống (`omi_intent_*`, `omi_entity_*`, `khach_can_gap/*`).
4. **Kho tri thức dùng chung cho mọi kịch bản NORMAL của tenant**, mỗi lần nhập dữ liệu là một lần huấn luyện lại toàn bộ (10–20 phút) → gom dữ liệu vào **một file**, gửi user duyệt, **đẩy một lần qua giao diện**. Không xoá dữ liệu có sẵn khi user chưa yêu cầu.
5. Không bấm **Xuất bản**, không gắn kịch bản vào hotline/chiến dịch, không gọi thử khi user chưa yêu cầu và chưa đưa số.
6. Đăng nhập qua MCP OMI bằng `scripts/omi_login.py` (`references/omi-mcp.md` mục 2a): lần đầu agent mở terminal cho user chạy `python "<thư mục skill>/scripts/omi_login.py" setup --domain <domain> --email <email>` và user gõ mật khẩu vào ô nhập ẩn; script cất vào kho bí mật hệ điều hành, tự đăng nhập, đăng ký server MCP không chứa mật khẩu. Về sau hết hạn hoặc 401 thì agent tự chạy `omi_login.py login --domain <domain>`, không hỏi lại. Áp dụng cho mọi agent/client hỗ trợ MCP. Không in mật khẩu/token, không ghi bí mật vào repo hoặc file tạm. Chỉ dùng browser pane khi không đăng nhập được bằng đường này.

## Input contract (hỏi MỘT LẦN rồi tự làm hết)
1. **Domain tenant** (`<tên>.omicrm.io` hoặc `.omicrm.com`).
2. **Email** đăng nhập; mật khẩu user gõ một lần vào `omi_login.py setup` trong terminal, không gửi qua chat (Rule 6).
3. **Nghiệp vụ**: file kịch bản (docx/pdf/xlsx/txt) và/hoặc mô tả.
Có đủ 3 thứ thì không hỏi thêm cho tới bước cần duyệt (bảng ý định/thực thể, file dữ liệu) và bước gọi thử (cần số điện thoại).

## Workflow

### Bước 0 — Đăng nhập, khảo sát tenant (chỉ đọc)
- Token: `scripts/omi_preflight.py` báo đường đi (bảng quyết định token trong `references/omi-mcp.md`: MCP OMI → `OMI_TOKEN_FILE` do user đặt → giao diện). Script dùng `scripts/omi_session.py`. Đang ở browser pane đã đăng nhập thì gọi API ngay trong trang (cookie `{domain}_omicrm_{io|com}` key `"2"`, đoạn mã sẵn: `references/browser-snippets.md` §1–3), chỉ trả bản tóm tắt; đọc cookie bị chặn thì dừng, không thử đường khác.
- Lấy: danh sách kịch bản (`list-by-tenant` trả cả nodes), Kho tri thức (intent, entity, số câu từng intent, lịch sử huấn luyện), nhân viên + máy lẻ để chuyển máy (ưu tiên MCP `list_agents`/`list_extensions`; API `agent-v1-stg …/get_all_agent/no_role` mới có nửa đường dẫn — Cần xác nhận host đầy đủ trước khi gọi). Lưu `tenant_context.json` ở scratchpad (khuôn `references/tenant_context.template.json`; ý định/thực thể ghi vào khối `kho_tri_thuc` (`intents` kèm `system_intent_id` nếu có, `entity_types`, `training_history`) để `build_callflow.py --context` điền id).

### Bước 1 — Phân tích nghiệp vụ thành cây hội thoại
Từ tài liệu: mục tiêu cuộc gọi, biến đầu vào (chiến dịch), các **bước bot nói** (mỗi bước = 1 STAFF), ở mỗi bước **khách có thể đáp gì** (mỗi kiểu đáp = 1 nhánh), dữ liệu cần thu, nhãn kết quả, ai nhận chuyển máy, cách kết thúc. Nhánh rẽ theo biến chiến dịch (ví dụ nội dung khác nhau theo loại khách) → node so biến (`routes`). Xuất bảng bước – phản hồi – đích.

### Bước 2 — Chọn ý định và thực thể
- Mỗi **kiểu phản hồi** = 1 ý định dùng chung giữa các bước; ưu tiên hệ thống (đồng ý, từ chối, từ chối dịch vụ, xác nhận đúng/sai, lời hẹn, gọi lại sau, lặp lại, tức giận, đặt câu hỏi, gặp nhân viên...).
- **Hỏi đáp**: 1 ý định "khách đặt câu hỏi" + **mỗi chủ đề hỏi 1 thực thể** (STRING), tách nhánh bằng `entity_code`.
- **Giá trị cần thu** (ngày hẹn, số, tên): thực thể hệ thống (`omi_entity_datetime`...) + thêm biến lấy nguyên câu.
- Gửi user duyệt **bảng ý định/thực thể** (mã, tên, dùng ở bước nào, đi đâu) — điểm duyệt 1.

### Bước 3 — Sinh dữ liệu huấn luyện (`references/data-rules.md`)
- Soạn `spec_training.json` (mẫu: `references/spec-training.example.json`): mỗi ý định ≥30 lõi câu theo ngữ cảnh từng bước, mỗi thực thể ≥15 mẫu câu có `[đoạn thực thể]`, danh sách tên riêng cần phiên âm.
- Chạy `python scripts/gen_training.py spec_training.json --out <file>.xlsx [--existing <file đã đẩy>.xlsx]` → **≥200 câu mới mỗi ý định và mỗi thực thể**, giống chữ STT tổng đài (phiên âm tiếng Anh, nghe nhầm, từ đệm, cắt câu), lọc trùng, đúng mẫu Excel hệ thống, kèm báo cáo kiểm tra. Đọc mẫu ngẫu nhiên, sửa lõi câu gượng rồi chạy lại.
- Gửi file cho user duyệt — điểm duyệt 2, riêng với điểm duyệt 1; chưa duyệt thì không đẩy.

### Bước 4 — Nạp Kho tri thức (sau khi user duyệt)
1. Tenant chưa có câu huấn luyện (trang hiện "Đào tạo dữ liệu mẫu của hệ thống") → bấm nút đó (`training/reset`): nạp ~4.800 câu mẫu hệ thống, tự huấn luyện ~10 phút. Đợi `SUCCESS` rồi mới đẩy file.
2. **Đẩy file qua giao diện**: Kho tri thức → Đào tạo → "Tải lên File Excel" → "Chọn file Excel" (mở hộp chọn file Windows) → Windows-MCP `Type` đường dẫn vào ô File name + `press_enter` → bấm "Tải lên File Excel". Kiểm tra `upload_excel/status/{session}`: `successTotalRecord == total`, `errorTotalRecord == 0`; số entity không tăng bất thường (không sinh trùng).
3. Lấy id ý định/thực thể (`intent/list-by-tenant`, `entity-type/search`) vào `tenant_context.json` (`kho_tri_thuc.intents`, `kho_tri_thuc.entity_types`; ý định hệ thống ghi thêm `system_intent_id` vì `tenant_survey.py` chưa lấy trường này) cho bước 5 — có ngay sau khi nhập, không cần đợi huấn luyện.

### Bước 5 — Dựng kịch bản trong lúc huấn luyện
- Soạn `spec_callflow.json` (mẫu: `references/spec-callflow.example.json`): bước, nhánh, câu trả lời hỏi đáp, hành động (phân loại, chuyển máy, thông báo), node so biến, biến, nhân viên chuyển máy (theo `ext`/`email`), mã ý định/thực thể; id lấy từ `tenant_context.json` qua `--context` (bước 4).
- Chạy `python scripts/build_callflow.py spec_callflow.json --context tenant_context.json --out payload.json`: kiểm spec trước (`next` và `branches` loại trừ nhau; bước có nhánh phải có im lặng + phản hồi sai qua `common` hoặc `nr_to`/`wrong_to`; biến của `routes`, key `layout`, mã ý định/thực thể phải khai báo), tự thêm **nhánh chung theo quy tắc mặc định** (dưới), dựng cấu trúc kép runtime/editor + connections, xếp bố cục, tự kiểm tra và cảnh báo lời thoại (còn "anh/chị", chữ số, viết tắt). Còn placeholder `<...>` hoặc mã không có trong context → dừng; `--allow-pending` chỉ để dựng thử khi Kho tri thức chưa nhập, payload đó không lưu. Id node tính theo tên kịch bản; không để `seed` cố định.
- Kiểm trước khi lưu: `python scripts/verify_callflow.py payload.json --context tenant_context.json --mode pre` (mã C1..C7 = checklist `references/api-reference.md` §6).
- Lưu: `scripts/omi_save.py callflow payload.json --domain <domain> --new|--update` (gọi `add_v2` multipart field `file`, GET lại, chạy `verify_callflow.py --mode post --sent`). Tạo mới → không gửi id/uuid; cập nhật → lấy **bản mới nhất** (`list-by-tenant`) rồi gửi cả `id` + `uuid` (`build_callflow.py --base-id/--base-uuid`, `omi_save.py --update --base … --confirm-update`). Không có token ngoài trang → payload vài trăm KB đưa vào trang bằng clipboard + dán thật (`references/browser-snippets.md` §5).

### Bước 6 — Kiểm tra và giao
- GET lại và kiểm bằng `scripts/verify_callflow.py <bản GET>.json --sent payload.json --context tenant_context.json --mode post [--base <bản mới nhất trước khi sửa>.json]`. `omi_save.py` tự chạy lệnh này: chỉ khi truyền `--context` cho `omi_save.py` thì C4 (mã ý định/thực thể, tenant_id) mới kiểm đủ; `--update` thì tự kèm `--base <file --base>` hoặc `--base-version <version bản mới nhất ở bước guard>` cho C7. Quên `--context` → C4 chỉ ra WARN, phải tự chạy lại đủ tham số trên bản GET `omi_save.py` đã ghi (`*_get_<id>.json`). Kiểm: số node/dây khớp, chuyển máy có `ids` nhân viên, mọi câu dùng `{{gender1_ai}}`, dây khớp `next_nodes`, version tăng so với `--base` (kịch bản tạo mới thì không có bản gốc, C7 in WARN). Mục script không tự suy được (nhánh hỏi đáp/lặp lại/phản hồi sai trỏ đúng bước báo chuyển) in WARN → soát bằng mắt theo spec. Chỉ khi kiểm trong trang (không có token ngoài) mới dùng dự phòng `references/browser-snippets.md` §6. Mở trình biên tập bản mới (đóng/chuyển tab bản cũ).
- Đợi huấn luyện `SUCCESS` (7–8 nghìn câu mất khoảng 25 phút) → **gọi thử**:
  - Trình biên tập → "Gọi thử nghiệm": **không gọi ra điện thoại**; mở cuộc gọi giả lập ngay trên trình duyệt (khung "Gọi đi"), người thử nói qua **micro máy tính**, số nhập chỉ là số khách giả lập, biến chiến dịch để trống. Browser pane của agent bị chặn micro → cuộc gọi đứng 00:00 → hướng dẫn **user tự bấm trên trình duyệt của họ** (đã đăng nhập tenant, cho phép micro). "Đóng và lưu lại" lưu bản ghi cuộc gọi thử vào lịch sử.
  - Muốn bot gọi tới điện thoại thật (và truyền biến chiến dịch): cần chiến dịch Callbot/OMIFlow gọi ra với hotline, kịch bản đã xuất bản, có phát sinh cước → chỉ làm khi user đồng ý rõ (skill `omicall-omiflow`).
  - Xem kết quả: lịch sử cuộc gọi hoặc MCP `search_calls`, `get_call_detail` (nội dung hội thoại, ý định từng lượt, nhãn, biến thu được).
- Giao theo khuôn: link editor (`https://<domain>.omicrm.<io|com>/ai/callbot/script/update/<id>`, đúng đuôi miền của tenant) | checklist C1..C7 PASS kèm `id`/`version` đã GET | các điểm "Cần xác nhận" | việc user cần làm (Xuất bản, gắn hotline/chiến dịch, gọi thử, nhập biến chiến dịch dạng chữ). Kèm file dữ liệu đã đẩy, spec, bảng ý định/thực thể.

## Quy tắc kịch bản mặc định (user đã chốt, áp mọi dự án trừ khi user đổi)
- **Hỏi đáp**: trả lời **1 lần** (1 câu = trả lời + hỏi lại câu của bước); khách hỏi lại cùng chủ đề → bước "báo chuyển máy" → chuyển nhân viên.
- **Ngoài phạm vi / không khớp ý định** (`CUSTOMER_RESPONSE_WRONG`): nhắc lại câu của bước **1 lần**, lần thứ hai → chuyển nhân viên.
- **Khách muốn lặp lại**: đọc lại 1 lần, lần sau → chuyển nhân viên.
- **Khách đòi gặp nhân viên** → báo chuyển → chuyển máy (`transfer_collected_info:true`).
- **Khách tức giận** → xin lỗi, kết thúc. **Im lặng** → nhắc 1 lần → kết thúc lịch sự.
- **Xưng hô**: `{{gender1_ai}}` thay mọi "anh/chị" (hệ thống điền anh/chị theo giới tính khách).
- **Bố cục** dễ nhìn: cột theo thứ tự cuộc gọi, các bước kết thúc/báo chuyển dồn cột áp chót, chuyển máy cột cuối.
- Hỏi "còn cần hỗ trợ gì không" trước khi chào kết thúc; câu chào cuối cảm ơn + tạm biệt (+ số tổng đài nếu tài liệu có).

## Lời thoại cho giọng đọc
Câu ngắn, tiếng Việt đầy đủ, không viết tắt, không ký hiệu (trừ biến `{{...}}`); số viết bằng chữ, số điện thoại đọc từng nhóm ngăn bằng dấu phẩy; tên nước ngoài/thương hiệu viết theo cách đọc tiếng Việt (có gạch nối giữa các âm khi cần). Biến chiến dịch được đọc nguyên văn → dữ liệu chiến dịch nên nhập dạng chữ (ngày "hai mươi lăm tháng mười", không "25/10/2026"); ghi rõ yêu cầu này khi giao.

## Gotchas (đã gặp thật)
- Chưa huấn luyện xong thì ý định/câu mới chưa có hiệu lực → nhánh rơi vào phản hồi sai.
- Câu huấn luyện sai ý định làm lệch mọi kịch bản của tenant; tách rõ các ý định dễ lẫn (data-rules §5).
- `add_v2` chỉ gửi `id` (thiếu `uuid`) → sinh kịch bản trùng. Server tạo thêm 1 id kế tiếp cùng uuid cho editor; danh sách vẫn 1 bản.
- Bấm **Cập nhật** trên editor tạo phiên bản mới (đổi thứ tự biến, sinh lại id action thu thập, thêm `name` cho STAFF, đổi vị trí node) — logic giữ nguyên. Tab editor mở từ bản cũ bấm Cập nhật sẽ **ghi đè** bản mới → sau mỗi lần lưu qua API chuyển tab sang id mới; trước khi lưu qua API so phiên bản mới nhất.
- Browser pane: không đọc file máy, chặn `fetch` localhost, không cho đọc clipboard, phím `ctrl+v` của công cụ trình duyệt không lấy clipboard Windows → dùng hộp chọn file Windows (Excel) và Windows-MCP `ctrl+v` thật (payload).
- Token trong trang có thể bị thay khi trang tải lại → đọc lại cookie trước mỗi lô gọi API; lỗi 401 "Error Occurred!!!" = token cũ.
- Trình biên tập chỉ vẽ node trong khung nhìn (`.react-flow__node` không đủ) — kiểm tra bằng API, không bằng DOM.
- Xoá ý định/thực thể hệ thống thừa có thể bị chặn quyền (dữ liệu dùng chung) → để user tự xoá trên UI hoặc bỏ qua; thừa không ảnh hưởng kịch bản.

## Reference
- `references/data-rules.md` — quy tắc dữ liệu huấn luyện (STT tổng đài, số câu, xưng hô, ý định dễ lẫn, mẫu Excel).
- `references/api-reference.md` — API Kho tri thức + kịch bản NORMAL, cấu trúc runtime/editor đã kiểm chứng, checklist.
- `references/browser-snippets.md` — đoạn mã chạy trong trang (token, khảo sát, đếm câu, theo dõi huấn luyện, lưu payload, kiểm tra).
- `references/spec-training.example.json`, `references/spec-callflow.example.json` — spec mẫu trung tính.
- `references/omi-mcp.md` — MCP OMI (bản giống trong các skill OMI).
- `references/node-status.json` — trạng thái từng loại node/hành động (verified/enum/unverified, nguồn file:dòng): verified → builder/API, còn lại → UI hoặc "Cần xác nhận".
- `scripts/gen_training.py`, `scripts/stt_noise.py`, `scripts/build_callflow.py`, `scripts/verify_callflow.py`, `scripts/omi_session.py`; dùng chung: `scripts/omi_preflight.py`, `scripts/tenant_survey.py`, `scripts/omi_save.py`.
- Skill liên quan: `omicall-callbot-gen-ai` (AI_AGENT), `omicall-omiflow` (gắn kịch bản vào chiến dịch/flow).

## Bảo trì skill
- Học được loại node/hành động mới: dựng 1 nút trên UI, GET JSON, thêm vào `references/api-reference.md` kèm nhãn và nguồn, cập nhật `references/node-status.json`. Không tự nâng nhãn `verified`: chỉ agent chính hoặc user duyệt, kèm báo cáo `verify_callflow.py --mode post` RESULT PASS trên bản GET thật.
- Sửa `build_callflow.py`, `verify_callflow.py`, `gen_training.py` → chạy test offline `tests/omicall-callbot-flow/` của repo skill; mã C1..C7 của validator phải khớp checklist api-reference §6.
- Không ghi dữ liệu khách (tên, số điện thoại, id tenant, câu thoại nghiệp vụ) vào skill; ví dụ dùng placeholder `<domain>`, `<tenant_id>`, `<id>`.
