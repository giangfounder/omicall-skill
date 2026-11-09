---
name: omicall-omiflow
description: >-
  [v1.21.2] Thiết kế, xây dựng và chỉnh sửa quy trình tự động OMIFlow của OMICall/OMICRM. Điều kiện bắt đầu: webhook API, cuộc gọi, phím bấm IVR, phiếu ghi, lịch, tệp Excel, đối tác, trạng thái khách hàng. Thành phần xử lý: điều kiện, trì hoãn, AI phân loại, gọi API ngoài, cập nhật khách hàng/phiếu ghi/cuộc gọi, cửa sổ tương tác cho nhân viên, SMS/ZNS, chạy hoặc liên kết Callbot/Chatbot. Đọc và lưu qua API campaign-v1. Cấu hình nền được giao cho omicall-crm-config, omicall-pbx-config và omicall-ai-insight.
---

# OMICall OMIFlow — Builder Playbook (mọi tenant, mọi bài toán)

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác, 1 lần/phiên (đã chạy rồi, kể cả ở skill khác, thì bỏ qua, không nhắc lại phiên bản) (`<thư mục skill>` = thư mục chứa SKILL.md này). Câu đầu tiên trả lời user: `Đang dùng omicall-omiflow v<phiên bản>` (lấy từ dòng `SKILL_VERSION`; script lỗi thì dùng v1.21.2). Script báo **SKILL.md đã thay đổi** → đọc lại SKILL.md từ đĩa rồi mới làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.

## Bắt đầu và cách trao đổi (BẮT BUỘC)
Làm theo `references/conversation.md`, chung cho mọi skill OMI:
- Mục 1: hỏi domain → `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>` → `"need":"setup"` thì mở form đăng nhập trong agent đúng các bước ở đó. Không nhận mật khẩu qua chat, không gõ hay đọc form.
- Mục 2–5: khung 5 bước, khi nào hỏi lại và hỏi thế nào, mẫu câu, lời thường thay thuật ngữ. Mục 6: ít chụp ảnh, chụp thì ghi lại.

## Đường nhanh
Chạy script bằng đường dẫn tuyệt đối `<thư mục skill>/scripts/...`. Khối này chỉ trỏ tới quy tắc gốc bên dưới; mâu thuẫn thì quy tắc gốc thắng.
1. **Token**: `python <thư mục skill>/scripts/omi_preflight.py --domain <domain>` → route `api` / `login` / `ui` / `blocked`. `login` → tự chạy `scripts/omi_login.py login --domain <domain>`; `blocked` → mở form đăng nhập theo `references/conversation.md` mục 1; không đọc cookie, không nhập mật khẩu hộ. Trong lúc chờ, làm tiếp bước 3 offline.
2. **Khảo sát (Bước 0, BẮT BUỘC trước thiết kế)**: `<thư mục skill>/scripts/tenant_survey.py --out <scratch>/tenant_context.json` + `config_survey.py` (tổng đài, AI) + công cụ MCP; giao diện chỉ khi API không có, ảnh chụp sau cùng (`references/omi-mcp.md` mục 4a) → kiểu thuộc tính (`is_list`), danh mục phiếu, tích hợp đã bật, quota flow và nút. Thiếu → "Cần xác nhận"; thiếu cấu hình nền (thuộc tính, tổng đài, AI Assistant) → mục *Skill con*.
3. **Thiết kế**: khung 8 câu (`references/design-patterns.md` mục A) → tra `references/node-status.json`: `verified` → đi API; `enum` / `ui_only` / `unverified` → đi UI hoặc ghi "Cần xác nhận".
4. **Dựng — API**: tạo vỏ flow trên UI (có `_id` nháp; cách tối thiểu để lưu được vỏ: Cần xác nhận, `references/api-reference.md` mục Lưu flow) → `flow_outline.py --save <id>` → sửa `nodes` + `edges` + `name_mappings` → `<thư mục skill>/scripts/omi_save.py flow payload.json --domain <domain>` (chỉ `save_draft_v2`, không xuất bản). `name_mappings` (bản editor) chưa `verified`: mỗi phần tử chỉ được **chép nguyên từ bản GET của một nút cùng loại đã dựng trên UI** (`references/node-catalog.md` mục 6, Cách học nhanh) rồi đổi id/giá trị cho khớp `nodes`, không tự viết; chưa có bản GET mẫu cho loại đó → dựng nút đó bằng UI. File `--save` đã che bí mật (`***`): flow có header `Authorization`/token ở nút Gọi API hay webhook thì `omi_save.py` dừng exit 2 (cố ý, tránh ghi đè bí mật thật) → phần đó sửa trên UI, ghi "Cần xác nhận".
5. **Dựng — UI**: mỗi flow một subagent, một tab (chia việc: `references/parallel.md`, thao tác ở `references/ui-build-and-test.md`).
6. **Kiểm**: `python <thư mục skill>/scripts/validate_flow.py payload.json --mode pre --context <scratch>/tenant_context.json`; sau lưu GET lại và chạy `--mode post --sent payload.json` (omi_save tự chạy). Có FAIL thì sửa, không lưu tiếp.
7. **Test**: cURL hoặc sự kiện thật chỉ khi user đồng ý; xem tab Lịch sử (Bước 4).
8. **Giao**: flow vẫn là nháp; user tự bấm **Xuất bản** sau khi duyệt (Rule 3).

Không bao giờ: xuất bản, bật, tắt hay xoá flow khi user chưa duyệt · đọc cookie, in token, nhập mật khẩu hộ · bịa schema cho loại chưa `verified` (Rule 2).

## Tư duy chức năng (trước khi chọn module)
- Chỉ khi dựng mới hoặc việc chạm nhiều module (sửa nhỏ một bước/lời nhắc thì bỏ qua, đọc đúng mục playbook cần): đọc `references/system-model.md` (hệ thống có gì, làm được gì, đường nhanh nhất cho từng việc) và `references/solution-method.md` (phân rã bài toán thành chuỗi Sự kiện → Điều kiện → Hành động, ghép module có sẵn). Không khớp mẫu theo ca; mắt xích chưa xác minh thì báo user, khảo sát một lần bằng log mạng rồi ghi vào `system-model.md`.

<!-- skill-links:start (sinh từ shared/skill-graph.json bằng tools/gen_skill_links.py, đừng sửa tay) -->
## Gọi skill liên quan (tự động khi bài toán chạm tới)
Mắt xích thuộc skill khác (xem `references/system-model.md`) thì không tự làm theo trí nhớ: gọi skill đó rồi quay lại.
1. **Gọi**: công cụ Skill với đúng tên bên dưới; client không có thì đọc `<thư mục skill>/../<tên skill>/SKILL.md`. Chỉ làm đúng phần của mắt xích đó.
2. **Dùng chung**, không làm lại: domain, đăng nhập, `tenant_context.json`, `manifest.py`. Việc ghi vẫn chờ user duyệt như skill đích quy định.
3. **Trả lại**: ghi id/mã trường/tên vừa tạo vào `tenant_context.json` hoặc manifest, rồi tiếp tục skill đang làm. Thứ tự khi cần nhiều phần: crm-config → ai-insight → pbx-config (nhóm, lời chào) → bot/callbot → omiflow (nháp) → user Xuất bản → pbx-config (gắn hotline/webhook).

| Khi gặp | Gọi skill |
|---|---|
| thuộc tính khách/phiếu, bộ trạng thái, chủ đề phiếu hoặc cấu hình phân bổ chưa có | `omicall-crm-config` |
| nhận phím IVR hoặc webhook Tương tác phím, nhóm nội bộ đích, lời chào, gắn kịch bản vào hotline | `omicall-pbx-config` |
| dùng {{ca_summarize}} hoặc {{ca_ai_assistant}}, điều kiện AI Assistant/Voice/Chat Insights | `omicall-ai-insight` |
| flow là webhook cho Callbot Gen AI (tra hệ thống ngoài, popup, phiếu lúc chuyển máy) | `omicall-callbot-gen-ai` |
| chatbot gọi flow WEB_HOOK hoặc flow chạy Chatbot | `omicall-chatbot-gen-ai` |
<!-- skill-links:end -->

## Rules (BẮT BUỘC)
1. **Suy luận từ bài toán**: chạy khung 8 câu hỏi ở `references/design-patterns.md` mục A, rồi chọn module. Mẫu đã chạy chỉ tham chiếu hình dạng.
2. **Không bịa schema**: module có nhãn [verify JSON] dùng JSON trong catalog; module [enum] phải dựng thử 1 lần (hoặc Ctrl+C một nút cùng loại trên canvas để đọc định dạng clipboard) → GET lại để lấy schema → ghi bổ sung vào catalog.
3. **An toàn dữ liệu khách**: chỉ đọc flow đang chạy. Sửa flow đang chạy → lưu nháp hoặc tạo flow mới, chỉ cập nhật bản đang chạy hay bật khi user đồng ý. Flow mới: giữ quy ước của user (**Hoạt động**, Không giới hạn lượt, không đặt khoảng hiệu lực — Gotchas "Mặc định mọi flow mới") nhưng **chỉ lưu nháp, chưa xuất bản** tới khi test xong và user duyệt; bản nháp có chạy sự kiện thật hay không: Cần xác nhận. Không xoá, không tắt flow của khách nếu không được yêu cầu. Kiểm tra quota flow ("Thêm mới N/M") và quota nút trước khi tạo.
4. **Không bịa dữ liệu nghiệp vụ**: URL API ngoài, danh mục phiếu, nhân viên nhận, đầu số… lấy từ tài liệu user hoặc từ tenant (GET); thiếu thì ghi "Cần xác nhận".
5. **Verify mọi lần lưu**: GET lại và chạy checklist trong `references/api-reference.md` (tự động bằng `scripts/validate_flow.py --mode post`); test bằng cURL hoặc sự kiện thật, xem tab **Lịch sử**.
6. **Bài học mới** (schema, module, gotcha): ghi theo mục *Bảo trì skill* trong `references/playbook.md`.

## Gotchas chí tử (tóm tắt; đầy đủ và lý do ở `references/playbook.md`)
- Trigger là node CONDITION đầu tiên (`is_first_node:true`); nhánh lưu hai nơi (node + `edges.connections`), `success_next_nodes`/`fail_next_nodes` là chuỗi, `next_nodes` là mảng.
- Trigger API không có đối tượng gốc: `GET_RELATED` hoặc điều kiện theo Số điện thoại chuẩn trước khi cập nhật khách/phiếu.
- Bản ghi cuộc gọi sinh trễ: `DELAY` 5–10 giây trước `GET_RELATED CLOSEST_CALL`.
- Thuộc tính kiểu danh sách không nhận biến → rẽ nhánh theo giá trị.
- Điều kiện trỏ biến không tồn tại luôn rỗng; tra API ngoài có thể rỗng → luôn có nhánh mặc định.
- Giới hạn số lần đi qua (mặc định 2) làm trigger im lặng khi hết lượt, kể cả lúc test.
- Xuất bản đổi id flow; webhook Tương tác phím chỉ lưu được khi flow đích đã xuất bản → xuất bản trước, gắn sau.
- Nút "Cập nhật" ở editor chỉ lưu nháp; Xuất bản, bật/tắt flow do user quyết; xoá flow là xoá vĩnh viễn kèm lịch sử → để user tự xoá.
- Header chứa API key: agent không nhập giá trị key, chỉ khai tên header; user tự dán key.
- Nhánh "BOT chủ động kết thúc" của nút AI Chatbot cũng chạy khi khách im lặng hết thời gian chờ (180 giây) → không đặt chuyển nhân viên / tin "ngoài giờ" ở đây; dùng flow phụ thuộc gọi từ bot (node-catalog).
- Khung giờ chỉ chạy khi đi cùng ≥1 điều kiện khác, chế độ VÀ (thiếu → UI lặng lẽ xoá điều kiện khi đóng ngăn); flow phụ thuộc vẫn cần thẻ "Điều kiện bắt đầu" (chọn trigger trước, đổi sang phụ thuộc sau).
- `add_v2` tạo flow mới bằng API nhưng ra luôn bản **đã xuất bản** (v1) → chỉ dùng khi user đã duyệt hoặc cho flow phụ thuộc; sửa flow đã xuất bản trên UI lưu vào bản nháp có `_id` riêng.

## Chi tiết theo bước (`references/playbook.md`)
Đọc đúng mục khi tới bước đó, không đọc cả file. Định vị: `grep -n "^#" references/playbook.md`. Mục mà Đường nhanh hay Rules nhắc tới nhưng không có ở đây (Input contract, Workflow, Gotchas, Skill con…) đều nằm trong file này.
- Overview
- Input contract (hỏi một lần rồi tự làm)
- Skill con (cấu hình nền mà flow phụ thuộc)
- Workflow
- Danh mục module (tóm tắt — chi tiết và JSON: `references/node-catalog.md`)
- Kết nối với Callbot và Chatbot
- Thao tác UI (khi phải dựng bằng tay)
- Gotchas
- Tài liệu tham khảo
- Bảo trì skill (sau khi giao)
