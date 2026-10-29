---
name: omicall-ai-insight
description: >-
  [v1.1.0] Cấu hình và khai thác AI phân tích của OMICall/OMICRM: AI Assistant (hướng dẫn tổng hợp, trường bóc từ cuộc gọi, biến ca_summarize và ca_ai_assistant), Voice Insights, Chat Insights, đánh giá cuộc gọi và phiếu, speech-to-text. Skill con của omicall-omiflow; gọi riêng được.
---

# OMICall AI Insight — AI Assistant, Voice Insights, Chat Insights (mọi tenant)

## Bước bắt buộc: cập nhật skill
Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác (`<thư mục skill>` = thư mục chứa SKILL.md này). Câu đầu tiên trả lời user: `Đang dùng omicall-ai-insight v<phiên bản>` (lấy từ dòng `SKILL_VERSION`; script lỗi thì dùng v1.1.0). Script báo **SKILL.md đã thay đổi** → đọc lại SKILL.md từ đĩa rồi mới làm tiếp. Không cập nhật được → báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.

## Bắt đầu: domain và đăng nhập
Được `omicall-omiflow` gọi trong cùng phiên thì dùng lại domain, đăng nhập và `tenant_context.json` đã có, bỏ qua mục này. Gọi riêng: làm đúng mục "Bắt đầu" của `omicall-omiflow/SKILL.md` — hỏi domain, `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>`, `"need":"setup"` thì mở trang đăng nhập OMI thật để user tự nhập mật khẩu. Agent không gõ mật khẩu, không đọc cookie hay token.

## Đường nhanh
Chạy script bằng đường dẫn tuyệt đối `<thư mục skill>/scripts/...`. Mâu thuẫn thì quy tắc gốc bên dưới thắng.
1. **Token**: `python <thư mục skill>/scripts/omi_preflight.py --domain <domain>` → `api` / `login` / `ui` / `blocked` (xử lý như omiflow).
2. **Khảo sát**: `get_service_package` (module `ai`: cờ `omi_call_assistant*`, `call_analysis`, quota `total_call_assistant`); mở AI Assistant (tab Cuộc gọi/Đa kênh, quota N/M), Voice Insights, Chat Insights chỉ để xem; chép nguyên phạm vi và "Hướng dẫn các bước tổng hợp" hiện tại vào scratch (bản gốc để hoàn tác).
3. **Chọn lớp AI** (`references/ai-insight.md` mục 0): dữ liệu nghiệp vụ vào CRM → AI Assistant (Tổng hợp / Phân loại Tag / Tạo phiếu / Tạo khách); chấm chất lượng → Voice/Chat Insights (cần Mục đích cuộc gọi). Lập bảng *trường → thuộc tính đích (mã, kiểu, tập giá trị) → dòng hướng dẫn*; mã lấy qua `omicall-crm-config`; thiếu → "Cần xác nhận".
4. **Duyệt**: gửi bản hướng dẫn mới (chỉ thêm dòng, giữ dòng cũ) cho user; lưu chỉ khi user đồng ý.
5. **Lưu trên giao diện**: Cấu hình > AI > AI Assistant (`references/ai-insight.md` mục 1); tải lại để kiểm nội dung đã lưu.
6. **Kiểm**: một cuộc gọi thật sau khi lưu (gọi thử chỉ khi user đồng ý) → `search_calls`, `get_call_detail`: mỗi trường đúng một dòng, giá trị danh sách đúng nguyên văn.
7. **Giao**: bản hướng dẫn đã lưu, bản gốc, bảng trường → thuộc tính, các điểm "Cần xác nhận". Cần ghi vào CRM tự động → quay lại `omicall-omiflow` (flow sau cuộc gọi).

Không bao giờ: xoá hay viết lại dòng hướng dẫn cũ, ghi điểm đánh giá, đăng ký webhook STT khi user chưa duyệt · Xuất bản hay lưu cấu hình AI chưa được duyệt · đọc cookie, in token, nhập mật khẩu hộ.

## Rules (BẮT BUỘC)
1. **Cấu hình AI dùng chung cả tổng đài/kênh**: lưu bản gốc trước khi sửa; chỉ thêm, không xoá dòng cũ trừ khi user yêu cầu.
2. **Không bịa**: Voice Insights, Chat Insights chưa có dữ liệu khảo sát → chỉ khảo sát (xem, ít lần tải trang) và ghi "Cần khảo sát"/"Cần xác nhận"; không mô tả tính năng chưa thấy.
3. **Khớp với CRM**: tên trường và tập giá trị trong hướng dẫn phải khớp thuộc tính đích, nếu không flow rẽ nhánh sẽ trượt.
4. **Kết quả AI ghi trễ**: flow đọc `{{ca_ai_assistant}}` phải có Trì hoãn trước.
5. **Đánh giá, STT là dữ liệu/cấu hình thật**: `evaluate_call`, `create_ticket_evaluation`, `register_stt_webhook` chỉ khi user đồng ý.

## Quan hệ với skill khác
- `omicall-omiflow`: flow dùng `{{ca_summarize}}`, `{{ca_ai_assistant}}` (mẫu B5, mục 7 `omicall-omiflow/references/ui-build-and-test.md`), điều kiện nhóm AI Assistant / Voice Insights / Chat Insights.
- `omicall-crm-config`: thuộc tính đích (mã, kiểu danh sách, tập giá trị).
- `omicall-chatbot-gen-ai`: chỉ số Chat Insights dùng trong điều kiện flow nhận tin nhắn.

## Tài liệu tham khảo
- `references/ai-insight.md` — so sánh ba lớp AI, AI Assistant (phạm vi, 4 chức năng, cú pháp hướng dẫn, ghi trễ), dùng kết quả có/không OMIFlow, Voice Insights (13 thông số, trọng số, mục đích cuộc gọi), Chat Insights, đánh giá và API Voice Insights/STT, kiểm thử.
- `references/omi-mcp.md` — MCP OMI: đăng nhập, công cụ nhóm AI và Tổng đài.
- `scripts/omi_preflight.py`, `scripts/omi_login.py`, `scripts/omi_session.py`, `scripts/omi_api.py`, `scripts/tenant_survey.py` — script dùng chung.

## Bảo trì skill
Khảo sát được màn hình Voice Insights, Chat Insights, API cấu hình AI → cập nhật `references/ai-insight.md` (gắn ✔ và tháng), chỉ ghi vào repo nguồn khi user cho phép. Không ghi nội dung hướng dẫn riêng của khách, URL hay tenant id vào skill.
