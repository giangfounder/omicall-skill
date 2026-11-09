---
name: omicall-callbot-gen-ai
description: >-
  [v1.19.0] Xây dựng và chỉnh sửa kịch bản Callbot Gen AI (SmartAgent, loại AI_AGENT) của OMICall/OMICRM: ý định, thu thập thông tin, phân loại, gọi API, truy xuất tri thức (RAG), chuyển máy và lời nhắc hệ thống cho tổng đài viên AI. Xây dựng từ tài liệu nghiệp vụ hoặc PDF; chỉnh sửa tại …/ai/callbot/script/update/{scriptId}; lưu qua chatbot-gateway và kiểm thử.
---

# OMiCALL Callbot Gen AI — Generic Builder Playbook (all tenants / all scripts)

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác, 1 lần/phiên (đã chạy rồi, kể cả ở skill khác, thì bỏ qua). Câu đầu tiên: `Đang dùng omicall-callbot-gen-ai v<phiên bản>` (dòng `SKILL_VERSION`; script lỗi thì dùng v1.19.0). Script báo **SKILL.md đã thay đổi** → đọc lại từ đĩa rồi làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.
**Chế độ subagent / hỏi đáp**: là subagent hoặc chỉ hỏi tính năng → bỏ qua bước này, hỏi domain, khảo sát (`parallel.md` mục 1).

## Bắt đầu và cách trao đổi (BẮT BUỘC)
Làm theo `references/conversation.md`, chung cho mọi skill OMI:
- Mục 1: hỏi domain → `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>` → `"need":"setup"` thì mở form cục bộ `omi_login.py setup --ui` trong agent (cách duy nhất; dự phòng: `references/omi-mcp.md` mục 2a). Không nhận mật khẩu qua chat, không gõ hay đọc form.
- Mục 2–6: khung 5 bước, cách hỏi lại, mẫu câu, lời thường, ít chụp ảnh.

## Đường nhanh
Chạy script bằng đường dẫn tuyệt đối `python "<thư mục skill>/scripts/<tên>.py"`; file ra ghi vào scratch (`OMI_SCRATCH`), không ghi vào thư mục skill. Đây chỉ là mục lục, quy tắc gốc nằm ở các mục bên dưới.
- **B0** `omi_preflight.py --domain <domain>` → `route` api/login/ui/blocked. `login`: agent tự chạy `omi_login.py login --domain <domain>`. `blocked`: mở form đăng nhập theo `references/conversation.md` mục 1; trong lúc chờ làm tiếp B2–B3.
- **B1** `tenant_survey.py --out <scratch>/tenant_context.json` + MCP `list_agents`/`list_extensions`/`list_hotlines` (cho `TRANSFER_CALL`).
- **B2** `extract_text.py <tài liệu> --out <scratch>/source.txt`.
- **B3** Thiết kế theo Bước 1–3 (song song/tuần tự: `references/parallel.md`); chỗ thiếu ghi "Cần xác nhận", không dừng hỏi. Tra `references/node-status.json` (nguồn trạng thái duy nhất): `status` verified → API, unverified → chỉ nhân bản từ GET baseline, enum/ui_only → UI hoặc "Cần xác nhận"; `builder` khong → ghép tay theo mục nguồn/`template`.
- **B4** Baseline `script_outline.py --list`, rồi `--id <id> --save` (file lưu chỉ che giá trị bí mật) → dùng file đó làm `--base`: `build_smartagent.py spec.json --base <file đã lưu> --new|--update` (spec theo `references/spec-smartagent.example.json`). Base còn `***` (script có header bí mật) thì builder dừng exit 2: phần đó sửa trên giao diện, ghi "Cần xác nhận".
- **B5** `validate_smartagent.py payload.json --mode pre` → phải `RESULT PASS` (mã C1–C11, X1–X14 = checklist api-reference).
- **B6** `omi_save.py callbot payload.json --domain <domain> --new`; sửa script đang chạy: `--update --confirm-update`. Lệnh tự GET lại, validate post. Rồi `goto.py <id mới>`.
- **B7** Giao theo khuôn ở playbook Bước 6. Gọi thử (`references/webcall-test.md`), xuất bản, gắn hotline chỉ khi user đồng ý.

Không bao giờ: bấm **Xuất bản** hay ghi đè script đang chạy khi user chưa duyệt (Gotchas). Không nhập mật khẩu hộ user, không đọc cookie hay in token (playbook Input contract). Không tạo cạnh hay `next_node` về BEGIN (Rules 3).

## Bảng tra (bảng duy nhất; đọc đúng mục khi tới bước đó, không đọc cả file)
| Việc | Đọc |
|---|---|
| Chi tiết từng bước: Input contract, Workflow (Bước 0–6), Gotchas, *Kết thúc và chuyển cuộc gọi* (mọi quy tắc END_CALL), bẫy *Lưu qua giao diện và tab editor cũ*, Bảo trì skill. Định vị: `grep -n "^#" references/playbook.md` | `references/playbook.md` |
| Đăng nhập (một cách: form `omi_login.py setup --ui`), cách trao đổi, mẫu câu | `references/conversation.md` mục 1–6 |
| MCP, công cụ cho từng bước, file phiên | `references/omi-mcp.md` |
| Schema node, intent, cạnh và id cạnh, chuyển máy (nhân viên, nhóm), checklist C1–C11/X1–X14 | `references/api-reference.md` |
| Loại node nào đã kiểm chứng, builder sinh được không (nguồn trạng thái duy nhất) | `references/node-status.json` |
| Mẫu node đã làm sạch (chuyển máy nhóm nội bộ) | `references/templates/TRANSFER_CALL_Ring_group.json` |
| Spec cho `build_smartagent.py` | `references/spec-smartagent.example.json` |
| Quy chuẩn viết kịch bản chung, mô tả biến, ý định, hành động, chuyển nút, thao tác UI | `references/agent-config-guide.md` |
| Prompt và lời thoại cho giọng đọc | `references/voice-rules.md` |
| Đánh giá/tối ưu nhiều kịch bản đã có (tách FAQ ra RAG, chuẩn hoá mã biến) | `references/optimize-existing.md` |
| Tình huống chung (từ chối, ngoài phạm vi, im lặng, đòi gặp nhân viên, kết thúc); ô "—" là Cần xác nhận | `references/default-behaviors.md` |
| Trước khi giao: chạy bộ tình huống, báo `Đạt n/12` | `references/test-cases.md` |
| Gọi thử bằng web call (khi user đồng ý), bộ ca và khuôn báo cáo kiểm thử | `references/webcall-test.md` |
| Dựng mới hoặc chạm nhiều module: hệ thống có gì, phân rã Sự kiện → Điều kiện → Hành động | `references/system-model.md`, `references/solution-method.md` |
| Song song/tuần tự, giao việc cho subagent | `references/parallel.md` |

<!-- skill-links:start (sinh từ shared/skill-graph.json bằng tools/gen_skill_links.py, đừng sửa tay) -->
## Gọi skill liên quan (tự động khi bài toán chạm tới)
Mắt xích thuộc skill khác (xem `references/system-model.md`) thì không tự làm theo trí nhớ: gọi skill đó rồi quay lại.
1. **Gọi**: công cụ Skill với đúng tên bên dưới; client không có thì đọc `<thư mục skill>/../<tên skill>/SKILL.md`. Chỉ làm đúng phần của mắt xích đó.
2. **Dùng chung**, không làm lại: domain, đăng nhập, `tenant_context.json` (chỉ đọc), `manifest.py`. Việc ghi vẫn chờ user duyệt như skill đích quy định.
3. **Trả lại**: ghi id/mã vừa tạo bằng `manifest.py set` (giá trị nền: `ctx-set`), rồi tiếp tục skill đang làm. Thứ tự khi cần nhiều phần: crm-config → ai-insight → pbx-config (nhóm, lời chào) → omiflow (webhook, nháp) → user xuất bản flow → bot/callbot (URL flow, nháp) → user xuất bản bot → pbx-config gắn số → gọi thử (hai cổng user duyệt).

| Khi gặp | Gọi skill |
|---|---|
| cần webhook tra hệ thống ngoài, popup hoặc phiếu khi chuyển máy | `omicall-omiflow` |
| gắn kịch bản vào hotline hoặc phím IVR, nhóm đích khi chuyển máy | `omicall-pbx-config` |
| dữ liệu thu thập phải ghi vào thuộc tính khách/phiếu chưa có | `omicall-crm-config` |
| yêu cầu là callbot cổ điển (NORMAL), không phải SmartAgent | `omicall-callbot-flow` |
<!-- skill-links:end -->

## Rules (BẮT BUỘC)
1. **Giữ skill tổng quát**: KHÔNG hardcode intent/prompt/tên script của một tenant cụ thể vào SKILL.md — phần riêng của tenant chỉ là phiên đăng nhập (MCP OMI / `omi_session.py`) và schema GET được (api-reference), còn thiết kế ý định/lời thoại là suy luận mỗi lần.
2. **Suy luận từ nghiệp vụ hiện tại**: đọc Kịch bản/tài liệu → tự tách nhánh luồng, intent, biến thu, prompt — chỉ dùng script tenant khác làm *tham chiếu hình dạng*, không copy nội dung.
3. **Cấm nối ngược về BEGIN** (validator X1, C6): không tạo `connection` có `target` là node BEGIN và không đặt `next_node` (intent, điều kiện hệ thống hay node phụ) bằng id BEGIN. Intent được xử lý ngay trong BEGIN dùng `next_node:null` và không có connection. Nhánh không chuyển máy hoặc kết thúc cuộc gọi dừng ở node cuối, không có cạnh đi ra; hệ thống tự quay về ngữ cảnh chính, không biểu diễn việc này bằng cạnh. Luồng chuẩn: `CUSTOM_INTENT` → `ADD_CLASSIFY` là node cuối nhánh (ví dụ Từ chối: không cúp ngay, bot vẫn ở hội thoại và hỏi khách còn cần hỗ trợ gì không), hoặc `ADD_CLASSIFY` → `TRANSFER_CALL`/`END_CALL` khi nghiệp vụ cần đi tiếp. Các nhánh đồng ý, bận, từ chối, sai người không nối `END_CALL`; chỉ intent Hoàn tất mới đi `END_CALL` (X6). Khách im lặng sau câu hỏi còn nhu cầu nào không thì hỏi lại một lần, vẫn im mới kết thúc lịch sự. Kiểm tra trước mỗi lần lưu bằng `validate_smartagent.py` (api-reference mục *Bất biến: không có cạnh ngược về BEGIN*).
4. **Kịch bản mới phải `--new`**: xoá `id`/`uuid`/`public_key` khỏi payload (server tự sinh), gửi `is_publish:false` (chỉ lưu nháp). `omi_save.py --new` chỉ xoá `id`/`uuid`/`public_key`, KHÔNG tự đổi `is_publish` (payload có `is_publish:true` thì dừng exit 2): agent tự đặt `is_publish:false` trong payload, hoặc dựng bằng `build_smartagent.py --new` (tự đặt `false`). Chỉ giữ `id` + `uuid` (`--update`, kèm `--confirm-update` của `omi_save.py`) khi user chỉ định đúng script cần sửa; không ghi đè script đang chạy khi user chưa chỉ định. Ngoại lệ duy nhất: kịch bản do chính agent vừa tạo bằng `--new` trong phiên này — lần lưu đầu dùng `--new`, các lần lưu sau dùng `--update --confirm-update` với `id` MỚI NHẤT + `uuid` mà response lần lưu trước trả về (không cần user chỉ định lại). Không `--new` lần nữa cho cùng kịch bản (sinh script trùng).

## Gotchas chí tử (tóm tắt; đầy đủ và lý do ở `references/playbook.md`)
- DUAL-SCHEMA: mỗi intent viết cả runtime `nodes[].ai_agent_config.ai_analyze.conditions[]` lẫn editor `org_nodes[<BEGIN>].data.conditions[]` (validator C2, C3).
- ADD_CLASSIFY: runtime key `data`, editor key `datas` (validator X4).
- END_CALL: mô tả trình tự kết thúc (C10, X7), hỏi còn nhu cầu trước khi cúp, chỉ intent Hoàn tất (X6): playbook mục *Kết thúc và chuyển cuộc gọi*.
- add_v2 multipart field `file`, dùng Python `requests`, không curl.
- Phiên bản tăng ngoài ý muốn, tab editor cũ ghi đè bản mới, bấm Cập nhật làm hỏng bản dựng bằng API: playbook Gotchas *Lưu qua giao diện và tab editor cũ*.
- `TRANSFER_CALL`: sau mọi lần lưu qua UI kiểm `actions[0].data.ids` khác rỗng (validator X3).
- Nhánh `bot_can_not_answer` luôn nối tới `TRANSFER_CALL` chuyển máy cho nhân viên (validator X2).
- Không bấm Xuất bản trừ khi user yêu cầu; token đúng tenant, không đọc cookie.
