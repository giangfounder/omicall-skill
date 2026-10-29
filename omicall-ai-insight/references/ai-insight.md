# OMICall — AI Assistant, Voice Insights, Chat Insights (dùng chung mọi tenant)

Nhãn nguồn: **✔ UI 10/2026** = đã xem trên giao diện tenant thật (chỉ xem, không lưu); **✔ flow** = đã dựng flow thật dùng kết quả; **[tài liệu]** = hướng dẫn trên omicrm.io; **[API công khai]** = `api.omicall.com` (xác thực bằng apiKey doanh nghiệp). Chưa có dữ liệu thì ghi **Cần khảo sát**, không suy đoán.

## 0. Ba lớp AI và khác nhau ở đâu
| Lớp | Đầu vào | Đầu ra | Dùng khi |
|---|---|---|---|
| **AI Assistant** (Cuộc gọi / Đa kênh) | từng cuộc gọi (hoặc hội thoại) thoả phạm vi | tóm tắt, ghi chú, tag, gợi ý giá trị thuộc tính phiếu/khách, biến `{{ca_summarize}}`, `{{ca_ai_assistant}}` | cần dữ liệu nghiệp vụ từ cuộc gọi đổ vào CRM/OMIFlow |
| **Voice Insights** | cuộc gọi **có ghi âm** | điểm chất lượng theo thông số và bộ tiêu chí có trọng số | QA/chấm điểm nhân viên, phát hiện từ khoá, từ chối dịch vụ |
| **Chat Insights** | hội thoại đa kênh | điểm theo bộ tiêu chí (theo nhân viên) | QA kênh chat |

Gói dịch vụ (`get_service_package`, module `ai`) có cờ `omi_call_assistant`, `omi_call_assistant_multichannel`, `call_analysis`, `conversation_history_analyzed`, `api_speech_to_text`, `api_call_analysis` và giới hạn `total_call_assistant`, `total_social_assistant` → kiểm trước khi hứa với khách.

## 1. AI Assistant ✔ UI 10/2026
Cấu hình → AI → **AI Assistant** (`/config/ai/call-assistant/criteria`): hai tab **Cuộc gọi** và **Đa kênh**; nút Thêm mới hiện quota dạng `N/M` trợ lý.

Mở một trợ lý (`/config/ai/call-assistant/config-criteria/edit/<id>`) gồm 2 bước:
1. **Thông tin chung** — Hoạt động/Ngưng hoạt động, Tên trợ lý*, **Mục đích cuộc gọi** (lấy từ Cấu hình → Doanh nghiệp → Cuộc gọi → Mục đích cuộc gọi), Mô tả, **Cuộc gọi áp dụng*** (Cuộc gọi đi / Cuộc gọi đến), **Nhân viên**, **Nhóm nhân viên**, **Đầu số**. Cuộc gọi không thoả phạm vi → không được phân tích, biến rỗng.
2. **Cấu hình trợ lý cuộc gọi** — danh sách chức năng, "Thêm mới" chọn một trong:
   - **Tổng hợp nội dung cuộc gọi** (mặc định): ô **"Hướng dẫn các bước tổng hợp"*** viết theo cú pháp `- Tên trường: (mô tả)` mỗi dòng; chip **Gợi ý** chèn sẵn trường (Tiêu đề, Nội dung, Tên khách hàng, Email, Số điện thoại, Tên công ty, Bước tiếp theo, Từ khóa, Mức độ ưu tiên); công tắc **"Tự động điền kết quả phân tích vào ghi chú - Tag"** (cập nhật ghi chú và tag trong cửa sổ gọi).
   - **Phân loại Tag**: mỗi tag có mô tả/hướng dẫn; tag bật "gán tự động và không cho nhân viên thay đổi" thì nhân viên không gỡ được [tài liệu].
   - **Tạo phiếu ghi** / **Tạo khách hàng**: mỗi thuộc tính có hướng dẫn trích xuất riêng; khi nhân viên tạo phiếu/khách từ cửa sổ gọi, form được **gợi ý sẵn** giá trị đã bóc [tài liệu]. Cấu hình chi tiết từng thuộc tính: Cần khảo sát.

Nguồn tài liệu: https://omicrm.io/post/detail/gioi-thieu-omicall-assistant-tro-ly-dac-luc-cho-moi-cuoc-goi-post121

Quy tắc viết hướng dẫn ✔ flow:
- Giữ nguyên dòng cũ, chỉ thêm dòng mới cùng cú pháp; **chép bản gốc trước khi sửa** (cấu hình dùng chung cho mọi cuộc gọi thoả phạm vi).
- Trường sẽ ghi vào thuộc tính kiểu danh sách: `Chỉ ghi MỘT trong các giá trị: <A>, <B>, …, không có thì ghi: Không xác định` — tập giá trị khớp nguyên văn thuộc tính đích (`omicall-crm-config`).
- Kết quả **ghi trễ** sau khi cuộc gọi kết thúc → flow đọc kết quả phải Trì hoãn trước.

## 2. Dùng kết quả AI Assistant ✔ flow
- Không cần OMIFlow: bật "Tự động điền… ghi chú - Tag" và chức năng Tạo phiếu/Tạo khách (nhân viên xác nhận trên cửa sổ gọi). Ưu tiên cách này khi nhân viên còn ngồi xem cuộc gọi.
- Cần tự động hoàn toàn (không người xác nhận) → OMIFlow: chèn `{{ca_ai_assistant}}` vào mô tả phiếu (mẫu B5), hoặc bóc từng trường bằng nút LLM rồi gán thuộc tính; trường danh sách rẽ nhánh theo giá trị (`omicall-omiflow` `references/ui-build-and-test.md` mục 7).
- Điều kiện/trigger OMIFlow có nhóm **AI Assistant – Cuộc gọi/Đa kênh**, **Voice Insights**, **Chat Insights**; trigger `GENERAL` có đối tượng "cuộc gọi AI phân tích". Danh sách thuộc tính từng nhóm: Cần khảo sát.

## 3. Voice Insights ✔ UI 10/2026
Cấu hình → AI → **Voice Insights** (`/config/ai/call-analysis/analysis-parameters`), 4 tab: **Thông số phân tích**, **Bộ tiêu chí**, **SmartCall**, **Trọng số**.
- 13 thông số có sẵn: Tạp âm, Lịch sự, Cảm xúc, Cảm xúc âm thanh (độ chênh Hz giữa hai đoạn thoại), Độ trễ tín hiệu (ping, tốt < 90 ms), Thời gian phản hồi (tốt 2–4 giây), Tốc độ thoại (tốt 125–200 từ/phút), Cường độ âm thanh (dB), Từ khóa, Lời hẹn, Câu hỏi (khách quan tâm), Đánh giá dịch vụ (hài lòng/không), Từ chối dịch vụ, Độc thoại. Thông số có "Đối tượng áp dụng" và ngưỡng.
- Điểm tiêu chí = trọng số các thông số; điểm bộ tiêu chí = trọng số các tiêu chí; trọng số nâng cao theo điều kiện VÀ/HOẶC. Bộ tiêu chí gắn **mục đích cuộc gọi**, giới hạn được theo nhân viên/nhóm. **Chỉ cuộc gọi có ghi âm** được phân tích [tài liệu: https://omicrm.io/post/detail/phan-tich-cuoc-goi-voi-ai-post110 — bài 2023–2024, tên menu cũ "Phân tích cuộc gọi"].
- → Muốn chấm theo loại cuộc gọi: tạo giá trị **Mục đích cuộc gọi** trước (Cấu hình → Doanh nghiệp → Cuộc gọi), rồi mới tạo bộ tiêu chí.
- Tab SmartCall: Cần khảo sát.

## 4. Chat Insights ✔ UI 10/2026
Cấu hình → AI → **Chat Insights** (`/config/ai/natural-language-analysis/evaluation-criteria`): một tab **Bộ tiêu chí** (cột Nhân viên, Ngày tạo). Nội dung form bộ tiêu chí, chỉ số đầu ra: Cần khảo sát (tenant khảo sát chưa có bộ nào).

## 5. Đánh giá thủ công và API
- Cấu hình → Doanh nghiệp → **Đánh giá** (`/config/company/evaluation/list`): Cần khảo sát.
- [MCP] `list_eval_criteria`, `evaluate_call(transaction_id, agent_id, values[{criteria_id, point 0–10}], comment)`, `get_ticket_eval_criteria`, `create_ticket_evaluation` — **`list_eval_criteria` trả 404 trên tenant miền `.omicrm.com` (10/2026)**. Ghi điểm là dữ liệu thật → chỉ khi user đồng ý.
- [API công khai] Voice Insights và Speech-to-Text chạy bất đồng bộ: đăng ký webhook `POST /api/ai/register_webhook_ai` (header apiKey, body `url`) → gửi file multipart (`file` .wav/.mp3/.m4a + `tracking_id`) tới `/api/ai/call_analyze` hoặc `/api/ai/speech_to_text` → kết quả đẩy về webhook, khớp bằng `tracking_id`; Voice Insights trả `criteria_classification_result` và `quality_evaluation_result` (STAFF/CUSTOMER). Dùng khi khách muốn phân tích file ghi âm từ hệ thống khác. Nguồn: https://api.omicall.com/omicall-api/ai-api/voice-insights-api , https://api.omicall.com/omicall-api/ai-api/speech-to-text-api
- [MCP] `register_stt_webhook(url)` (chỉ HTTPS). apiKey và URL đích do user cung cấp; agent không tự lấy key.

## 6. Kiểm thử
- AI Assistant: một cuộc gọi thật thoả phạm vi (đúng chiều, nhân viên, đầu số, mục đích) — gọi thử chỉ khi user đồng ý → xem cửa sổ/lịch sử cuộc gọi; flow dùng kết quả → tab Lịch sử của flow.
- So kết quả với hướng dẫn: mỗi trường đúng một dòng, giá trị danh sách đúng nguyên văn.
- Voice Insights: cuộc gọi phải có ghi âm và đúng mục đích của bộ tiêu chí.
