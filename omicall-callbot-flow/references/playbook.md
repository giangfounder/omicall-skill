# omicall-callbot-flow — Chi tiết theo bước

Phần chi tiết tách nguyên văn khỏi SKILL.md để giảm token khi nạp skill. Đọc mục cần khi tới bước tương ứng; SKILL.md thắng khi mâu thuẫn. Bắt đầu, đăng nhập và cách trao đổi với user: `conversation.md`.

## Overview
Kịch bản `type:"NORMAL"` là **luồng cố định**: bot đọc lời soạn sẵn ở node `STAFF`, nghe khách, **mô hình NLU của tenant** (học từ Kho tri thức) nhận ra **ý định** + **thực thể** để rẽ sang nhánh `CONDITION`. Không có LLM sinh câu: mọi câu bot nói phải viết sẵn, và mô hình chỉ hiểu đúng những gì đã được dạy.

| | NORMAL (skill này) | AI_AGENT (`omicall-callbot-gen-ai`) |
|---|---|---|
| Lời bot | Soạn sẵn từng câu | LLM sinh từ prompt |
| Hiểu khách | NLU tenant: `intent_code` + `entity_code` | LLM so mô tả ý định |
| Chuẩn bị | Dữ liệu huấn luyện + chờ huấn luyện | Không |
| Hợp với | Câu chữ cố định, sản lượng lớn, đo theo nhãn | Tư vấn mở |
Nghiệp vụ cần tư vấn tự do thì đề xuất AI_AGENT.

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

## Lời thoại cho giọng đọc
Câu ngắn, tiếng Việt đầy đủ, không viết tắt, không ký hiệu (trừ biến `{{...}}`); số viết bằng chữ, số điện thoại đọc từng nhóm ngăn bằng dấu phẩy; tên nước ngoài/thương hiệu viết theo cách đọc tiếng Việt (có gạch nối giữa các âm khi cần). Biến chiến dịch được đọc nguyên văn → dữ liệu chiến dịch nên nhập dạng chữ (ngày "hai mươi lăm tháng mười", không "25/10/2026"); ghi rõ yêu cầu này khi giao.

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
