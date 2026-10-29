# OMICall — AI Assistant, Voice Insights, Chat Insights (dùng chung mọi tenant)

Nguồn: dựng thật flow "AI điền CRM sau cuộc gọi" và mẫu "Ghi kết quả AI Assistant vào phiếu" (10/2026), giao diện điều kiện OMIFlow, mô tả công cụ MCP OMI. Mục ghi **✔** đã làm thật; **[MCP]** theo mô tả công cụ; **Cần khảo sát** là chưa có dữ liệu — không suy đoán.

## 1. AI Assistant (phân tích cuộc gọi) ✔
- Cấu hình: Cấu hình > AI > AI Assistant (`/config/ai/call-assistant/config-criteria/edit/<id>`), ô **"Hướng dẫn các bước tổng hợp"**.
- Cú pháp mẫu mặc định: `- Tên trường: (mô tả)`, mỗi trường một dòng. Thêm trường thì giữ nguyên dòng cũ, thêm dòng mới cùng cú pháp.
- Trường sẽ ghi vào thuộc tính kiểu danh sách: ghi rõ `Chỉ ghi MỘT trong các giá trị: <A>, <B>, …, không có thì ghi: Không xác định`. Tập giá trị phải khớp đúng danh sách của thuộc tính đích (tra bằng `omicall-crm-config`).
- **Cấu hình dùng chung cho cả tổng đài**: chép lại nội dung gốc trước khi sửa để hoàn tác; chỉ lưu khi user đồng ý.
- Kết quả cho mỗi cuộc gọi: `{{ca_summarize}}` (tóm tắt) và `{{ca_ai_assistant}}` (văn bản liệt kê mọi trường theo hướng dẫn). AI Assistant chưa bật cho cuộc gọi đó → hai biến rỗng.
- **Ghi kết quả trễ** so với lúc cuộc gọi kết thúc → flow dùng kết quả phải Trì hoãn (vài giây tới vài phút) trước khi đọc.

## 2. Dùng kết quả trong OMIFlow ✔
- Chèn `{{ca_ai_assistant}}` vào mô tả phiếu (mẫu B5 của `omicall-omiflow`).
- Bóc từng trường bằng nút LLM (Biến liên kết tuỳ chỉnh → tab LLM) rồi gán thuộc tính khách; trường danh sách phải rẽ nhánh theo giá trị (`omicall-omiflow` `references/ui-build-and-test.md` mục 7).
- Nhóm điều kiện có sẵn trong trigger/điều kiện của flow: **AI Assistant – Cuộc gọi/Đa kênh**, **Voice Insights**, **Chat Insights**; trigger `GENERAL` có đối tượng "cuộc gọi AI phân tích". Danh sách thuộc tính trong từng nhóm: Cần khảo sát.

## 3. Đánh giá cuộc gọi và phiếu [MCP]
- `list_eval_criteria` → id tiêu chí; `evaluate_call(transaction_id, agent_id, values[{criteria_id, point 0–10}], comment)` ghi điểm cho một cuộc gọi.
- Phiếu: `get_ticket_eval_criteria`, `create_ticket_evaluation`.
- Ghi điểm là dữ liệu thật trên báo cáo nhân viên → chỉ chạy khi user đồng ý; test xong hỏi user có cần dọn không.

## 4. Speech-to-text [MCP]
`register_stt_webhook(url)` (chỉ HTTPS) đăng ký nhận bản chép lời cuộc gọi. URL đích do user cung cấp; không tự dựng endpoint ngoài. Đăng ký là thay đổi cấu hình tenant → hỏi trước.

## 5. Voice Insights — Cần khảo sát
Chưa có dữ liệu về màn hình cấu hình, chỉ số, cách bật. Khảo sát giao diện (chỉ xem, ít lần tải trang) rồi ghi: đường dẫn, các chỉ số, phạm vi (đầu số, nhóm, nhân viên), quan hệ với AI Assistant, biến dùng được trong OMIFlow.

## 6. Chat Insights — Cần khảo sát
Đã biết: điều kiện OMIFlow có nhóm Chat Insights (chỉ số hội thoại). Chưa biết: màn hình cấu hình, danh sách chỉ số, kênh áp dụng. Khảo sát như mục 5.

## 7. Kiểm thử
- AI Assistant: cần một cuộc gọi thật đã kết thúc (gọi thử chỉ khi user đồng ý) → `search_calls` lấy `transaction_id` → `get_call_detail` xem kết quả phân tích; flow dùng kết quả → tab Lịch sử của flow.
- So kết quả với hướng dẫn: mỗi trường có đúng một dòng, giá trị danh sách đúng nguyên văn.
