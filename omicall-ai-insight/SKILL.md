---
name: omicall-ai-insight
description: >-
  [v1.9.0] Cấu hình và khai thác các chức năng phân tích bằng trí tuệ nhân tạo của OMICall/OMICRM: AI Assistant (hướng dẫn tổng hợp, các trường thông tin trích xuất từ cuộc gọi, biến ca_summarize và ca_ai_assistant), Voice Insights, Chat Insights, đánh giá cuộc gọi và phiếu ghi, chuyển giọng nói thành văn bản. Là skill con của omicall-omiflow, có thể sử dụng độc lập.
---

# OMICall AI Insight — AI Assistant, Voice Insights, Chat Insights (mọi tenant)

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác (script tự bỏ qua nếu đã kiểm trong 1 giờ). Câu đầu tiên: `Đang dùng omicall-ai-insight v<phiên bản>` (dòng `SKILL_VERSION`; script lỗi thì dùng v1.9.0). Script báo **SKILL.md đã thay đổi** → đọc lại từ đĩa rồi làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.
**Chế độ subagent / hỏi đáp**: là subagent hoặc chỉ hỏi tính năng → bỏ qua: bước này, hỏi domain, khảo sát (`parallel-brief.md`).
**Bước nào phải làm trên giao diện**: theo `references/ui-recipes.md` (URL thẳng bằng id, chờ bằng `find`, bấm theo ref, kiểm bằng JS hoặc GET; ≤ 1 ảnh mỗi màn hình).

## Bắt đầu và cách trao đổi (BẮT BUỘC)
Làm theo `references/conversation.md`, chung cho mọi skill OMI:
- Mục 1: hỏi domain → `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>` → `"need":"setup"` thì mở form cục bộ `omi_login.py setup --ui` trong agent (cách duy nhất; dự phòng: `references/omi-login.md` mục 2a). Không nhận mật khẩu qua chat, không gõ hay đọc form.
- Mục 2–6: khung 5 bước, cách hỏi lại, mẫu câu, lời thường.

## Đường nhanh
Chạy script bằng đường dẫn tuyệt đối `<thư mục skill>/scripts/...`. Mâu thuẫn thì quy tắc gốc bên dưới thắng.
1. **Token**: `ensure` (mục trên) `ok:true` (`route=api`) → đi tiếp; `ok:false` → `python <thư mục skill>/scripts/omi_preflight.py --domain <domain>` → `login` / `ui` / `blocked` (xử lý như omiflow).
2. **Khảo sát bằng API, không chụp ảnh**: `get_service_package` (cờ `omi_call_assistant*`, `call_analysis`, quota) + `python <thư mục skill>/scripts/config_survey.py --out <scratch>/tenant_context.json --domain <domain>` (trợ lý, phạm vi, mục đích cuộc gọi, tiêu chí); bản gốc hướng dẫn tổng hợp lưu từ kết quả API vào scratch để hoàn tác. Thứ tự nguồn: `references/omi-mcp.md` mục 4a.
3. **Chọn lớp AI** (`references/ai-insight.md` mục 0): dữ liệu nghiệp vụ vào CRM → AI Assistant (Tổng hợp / Phân loại Tag / Tạo phiếu / Tạo khách); chấm chất lượng → Voice/Chat Insights (cần Mục đích cuộc gọi). Lập bảng *trường → thuộc tính đích (mã, kiểu, tập giá trị) → dòng hướng dẫn*; mã lấy qua `omicall-crm-config`; thiếu → "Cần xác nhận".
4. **Duyệt** (song song/tuần tự: `references/parallel.md`): gửi bản hướng dẫn mới (chỉ thêm dòng, giữ dòng cũ) cho user; lưu chỉ khi user đồng ý.
5. **Lưu trên giao diện**: Cấu hình > AI > AI Assistant (`references/ai-insight.md` mục 1); tải lại để kiểm nội dung đã lưu.
6. **Kiểm**: một cuộc gọi thật sau khi lưu (gọi thử chỉ khi user đồng ý) → `search_calls`, `get_call_detail`: mỗi trường đúng một dòng, giá trị danh sách đúng nguyên văn.
7. **Giao**: bản hướng dẫn đã lưu, bản gốc, bảng trường → thuộc tính, các điểm "Cần xác nhận". Cần ghi vào CRM tự động → quay lại `omicall-omiflow` (flow sau cuộc gọi).

Không bao giờ: xoá hay viết lại dòng hướng dẫn cũ, ghi điểm đánh giá, đăng ký webhook STT khi user chưa duyệt · Xuất bản hay lưu cấu hình AI chưa được duyệt · đọc cookie, in token, nhập mật khẩu hộ.

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
| trường đích (thuộc tính khách/phiếu) chưa có | `omicall-crm-config` |
| tự động hoàn toàn: flow dùng {{ca_ai_assistant}} để điền CRM | `omicall-omiflow` |
| cấu hình Chat Insights cho hội thoại của bot | `omicall-chatbot-gen-ai` |
<!-- skill-links:end -->

## Rules (BẮT BUỘC)
1. **Cấu hình AI dùng chung cả tổng đài/kênh**: lưu bản gốc trước khi sửa; chỉ thêm, không xoá dòng cũ trừ khi user yêu cầu.
2. **Không bịa**: Voice Insights, Chat Insights chưa có dữ liệu khảo sát → chỉ khảo sát (xem, ít lần tải trang) và ghi "Cần khảo sát"/"Cần xác nhận"; không mô tả tính năng chưa thấy.
3. **Khớp với CRM**: tên trường và tập giá trị trong hướng dẫn phải khớp thuộc tính đích, nếu không flow rẽ nhánh sẽ trượt.
4. **Kết quả AI ghi trễ**: flow đọc `{{ca_ai_assistant}}` phải có Trì hoãn trước.
5. **Đánh giá, STT là dữ liệu/cấu hình thật**: `evaluate_call`, `create_ticket_evaluation`, `register_stt_webhook` chỉ khi user đồng ý.

## Quan hệ với skill khác
- `omicall-omiflow`: flow dùng `{{ca_summarize}}`, `{{ca_ai_assistant}}` (mẫu B5; `omicall-omiflow/references/ui-build-and-test.md` mục *AI điền CRM sau cuộc gọi*), điều kiện nhóm AI Assistant / Voice Insights / Chat Insights.
- `omicall-crm-config`: thuộc tính đích (mã, kiểu danh sách, tập giá trị).
- `omicall-chatbot-gen-ai`: chỉ số Chat Insights dùng trong điều kiện flow nhận tin nhắn.

## Tài liệu tham khảo
- `references/ai-insight.md` — so sánh ba lớp AI, AI Assistant (phạm vi, 4 chức năng, cú pháp hướng dẫn, ghi trễ), dùng kết quả có/không OMIFlow, Voice Insights (14 thông số, dựng trên giao diện, trọng số, mục đích cuộc gọi), Chat Insights, đánh giá và API Voice Insights/STT, kiểm thử.
- `references/voice-insights-scoring.md` — Voice Insights: quy trình phân tích, công thức điểm Đánh giá chất lượng, Bộ tiêu chí, SmartCall, khuyến nghị cấu hình ban đầu.
- `references/omi-mcp.md` — MCP OMI: đăng nhập, công cụ nhóm AI và Tổng đài.
- `scripts/omi_preflight.py`, `scripts/omi_login.py`, `scripts/omi_session.py`, `scripts/omi_api.py`, `scripts/tenant_survey.py` — script dùng chung.

## Bảo trì skill
Điều gì phải mở giao diện hoặc chụp ảnh mới biết thì ghi ngay vào reference (`references/ui-recipes.md` mục 5) để lần sau không chụp lại. Khảo sát được màn hình Voice Insights, Chat Insights, API cấu hình AI → cập nhật `references/ai-insight.md` (gắn ✔ và tháng), chỉ ghi vào repo nguồn khi user cho phép. Không ghi nội dung hướng dẫn riêng của khách, URL hay tenant id vào skill.
