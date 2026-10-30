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

### 3a. Dựng Voice Insights trên giao diện ✔ UI 10/2026
Tenant mới có thể **chưa có thông số nào** (danh sách trống) — phải tự thêm. Thứ tự: thông số → mục đích cuộc gọi → bộ tiêu chí.

**Thông số phân tích** — nút Thêm mới mở bảng chọn 13 thẻ (lọc Tất cả / Ngôn ngữ tự nhiên / Âm thanh). 12 thẻ gắn **PRO**, chỉ **Lịch sự** không PRO; gói chưa mở PRO → bấm thẻ báo "Bạn không có quyền sử dụng tính năng này" (kiểm trước khi hứa với khách). Bấm thẻ → ngăn "Thêm thông số" bên phải → nút **Thêm mới** lưu, bảng chọn vẫn mở để thêm tiếp (thẻ đã thêm bị mờ).
| Thông số | Ô bắt buộc trong form |
|---|---|
| Từ khóa | Áp dụng tất cả / Theo đối tượng; danh sách dòng **Từ khóa** + **Phiên âm** (tuỳ chọn, ≤48 ký tự), nút + thêm dòng |
| Cảm xúc âm thanh | **Khoảng chênh lệch*** (delta; gợi ý trên form: tốt nhất từ 30 delta) |
| Độ trễ tín hiệu | **Độ trễ tín hiệu*** (ms) |
| Thời gian phản hồi | **Thời gian phản hồi*** (giây) |
| Tốc độ thoại | **Tốc độ thoại*** (từ/phút) + tuỳ chọn trừ điểm khi lớn hơn / nhỏ hơn giá trị chênh lệch |
| Lịch sự, Cảm xúc, Tạp âm, Câu hỏi, Lời hẹn, Độc thoại, Cường độ âm thanh | chỉ ô chọn đối tượng (Nhân viên / Khách hàng) |
| Đánh giá dịch vụ, Từ chối dịch vụ | chỉ đối tượng Khách hàng |

**Mục đích cuộc gọi** — `/config/company/call/list`, khối "Mục đích cuộc gọi" → Chỉnh sửa → danh sách ô **Tên mục đích** (≤48 ký tự, nút + thêm dòng) → Cập nhật. Có giá trị thì **nhân viên phải chọn mục đích trước khi gọi** → báo khách trước.

**Bộ tiêu chí** — `/config/ai/call-analysis/evaluation-criteria/add/new`, 2 bước:
1. Thông tin chung: **Tên bộ tiêu chí*** (≤48), Mục đích cuộc gọi (mặc định "Không áp dụng"), Mô tả (≤256), **Khung điểm** (Thêm khung điểm → Tiêu đề*, Từ*, Đến*; ví dụ trên form "0–30 = Không đạt"), Nhân viên / Nhóm nhân viên (trống = áp dụng tất cả) → Tiếp tục.
2. Cấu hình tiêu chí (`…/evaluation-criteria/config/list`): cột trái danh sách tiêu chí, trọng số tự chia đều (link "Cấu hình" để chỉnh, tổng 100%); chọn tiêu chí → ô **Tiêu chí** (tên) + "Thêm thông số" mở ngăn điều kiện. Danh mục điều kiện bên phải: Tuỳ chỉnh (Chủ đề Ý định/Mong muốn, Tự định nghĩa), Cơ bản (Thời lượng cuộc gọi, Tỉ lệ thoại, Bao gồm từ khoá, Không bao gồm từ khoá), Ngôn ngữ tự nhiên (Lịch sự, Cảm xúc, Đánh giá dịch vụ, Từ chối dịch vụ, Câu hỏi, Lời hẹn), Âm thanh (Độc thoại, Thời gian phản hồi, Cảm xúc âm thanh, Cường độ âm thanh…). Mỗi điều kiện: Đối tượng (Tất cả / Nhân viên / Khách hàng — **giữ lựa chọn của lần trước**, kiểm lại), giá trị cần đếm (Lịch sự: Lịch sự/Không lịch sự; Cảm xúc: Vui vẻ/Bình thường/Khó chịu; Đánh giá dịch vụ: Hài lòng-Khen/Trung lập/Chê), **Số lần** hoặc **Phần trăm xuất hiện** với Trong khoảng Từ–Đến (bỏ trống Đến = "Trên X"), tuỳ chọn khung thời gian, "Thêm trường hợp khác". Trọng số các thông số trong tiêu chí tự chia đều. Nút **Thêm mới** cuối trang lưu cả bộ.
- Gotcha: bấm vào thẻ điều kiện đã thêm mở "Chỉnh sửa" (nút Cập nhật/Đóng), không phải Thêm thông số — nút "Thêm thông số" nằm dưới thẻ cuối.
- Danh sách bộ tiêu chí hiện tên, số tiêu chí, khung điểm, mục đích, phạm vi nhân viên. Trên một số tenant tab thứ 4 là "Kho dữ liệu mẫu" thay cho "Trọng số" (Cần khảo sát).

## 4. Chat Insights ✔ UI 10/2026
Cấu hình → AI → **Chat Insights** (`/config/ai/natural-language-analysis/evaluation-criteria`): một tab **Bộ tiêu chí** (cột Nhân viên, Ngày tạo). Nội dung form bộ tiêu chí, chỉ số đầu ra: Cần khảo sát (tenant khảo sát chưa có bộ nào).

## 5. Đánh giá thủ công và API
- Cấu hình → Doanh nghiệp → **Đánh giá** (`/config/company/evaluation/list`): Cần khảo sát.
- [MCP] `list_eval_criteria`, `evaluate_call(transaction_id, agent_id, values[{criteria_id, point 0–10}], comment)`, `get_ticket_eval_criteria`, `create_ticket_evaluation` — **`list_eval_criteria` trả 404 trên tenant miền `.omicrm.com` (10/2026)**. Ghi điểm là dữ liệu thật → chỉ khi user đồng ý.
- [API công khai] Voice Insights và Speech-to-Text chạy bất đồng bộ: đăng ký webhook `POST /api/ai/register_webhook_ai` (header apiKey, body `url`) → gửi file multipart (`file` .wav/.mp3/.m4a + `tracking_id`) tới `/api/ai/call_analyze` hoặc `/api/ai/speech_to_text` → kết quả đẩy về webhook, khớp bằng `tracking_id`; Voice Insights trả `criteria_classification_result` và `quality_evaluation_result` (STAFF/CUSTOMER). Dùng khi khách muốn phân tích file ghi âm từ hệ thống khác. Nguồn: https://api.omicall.com/omicall-api/ai-api/voice-insights-api , https://api.omicall.com/omicall-api/ai-api/speech-to-text-api
- [MCP] `register_stt_webhook(url)` (chỉ HTTPS). apiKey và URL đích do user cung cấp; agent không tự lấy key.

## 5a. Đọc hiện trạng bằng API (✔ GET 10/2026, không mở giao diện)
`python <thư mục skill>/scripts/config_survey.py --out <scratch>/tenant_context.json --domain <domain>` → khoá `ai_config`:

| Đối tượng | Endpoint (token phiên) |
|---|---|
| AI Assistant | `POST cdr-v1-stg.omicrm.com/call_transaction/assistant/list` body `{}` → `{name, desc, type ("call"), enable, call_types, call_purpose_id, contact_ids, agent_cate_ids, numbers, keywords, channels, min_agent_messages_to_start, min_customer_messages_to_start, features[{type, items[{id, prompt, auto_assign, field_type}]}]}`; `features[].type` đã thấy `SUMMARY` (Tổng hợp nội dung); mã của Phân loại Tag / Tạo phiếu / Tạo khách: Cần xác nhận |
| Mục đích cuộc gọi | `POST cdr-v1-stg.omicrm.com/call_transaction/purpose/get_list` |
| Tiêu chí Chat Insights | `POST ai-v1-stg.omicrm.com/natural_language/criteria/get_list` |
| Tiêu chí đánh giá (thủ công) | `GET contact-v1-stg.omicrm.com/evaluation_criteria/get_all` → `{name, scopes[], contact_ids, contact_category_ids}` |

Ghi (thấy trong mã giao diện, chưa chạy): `call_transaction/assistant/add`, `…/update`. Sửa hướng dẫn tổng hợp vẫn làm trên giao diện cho tới khi đã thử ghi bằng API trên một trợ lý mới, có sự đồng ý của user.

## 6. Kiểm thử
- AI Assistant: một cuộc gọi thật thoả phạm vi (đúng chiều, nhân viên, đầu số, mục đích) — gọi thử chỉ khi user đồng ý → xem cửa sổ/lịch sử cuộc gọi; flow dùng kết quả → tab Lịch sử của flow.
- So kết quả với hướng dẫn: mỗi trường đúng một dòng, giá trị danh sách đúng nguyên văn.
- Voice Insights: cuộc gọi phải có ghi âm và đúng mục đích của bộ tiêu chí.
