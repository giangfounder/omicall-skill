# OMICall — Bản đồ kết hợp module cho bài toán khách hàng

Dùng ở Bước 1 (phân tích bài toán), trước khi chọn nút OMIFlow. Nhãn: **[đã chạy]** = đã dựng thật (mẫu B trong `design-patterns.md`); **[cấu hình sẵn]** = tính năng có sẵn đã thấy trên giao diện 10/2026, không cần flow; **[suy luận]** = ghép từ các khối đã kiểm chứng nhưng chưa chạy trọn chuỗi — báo khách là phương án, test trước khi cam kết.

## 1. Bốn lớp và ai giữ lớp nào
| Lớp | Làm gì | Skill |
|---|---|---|
| Dữ liệu CRM | thuộc tính khách/phiếu, bộ trạng thái khách (WIN/LOST), chủ đề phiếu có hạn xử lý + ca làm việc, phân bổ, tag/nhóm/ngành, tự tạo khách từ cuộc gọi | `omicall-crm-config` |
| Tổng đài | đầu số → kịch bản cuộc gọi (tiêu chí, lời chào, chuyển tiếp) → Tương tác phím → nhóm nội bộ (chiến lược, hàng đợi) / AI Callbot / hộp thư thoại; Autocall dùng lại các khối này | `omicall-pbx-config` |
| AI phân tích | AI Assistant (tóm tắt, tag, gợi ý/tạo phiếu và khách), Voice Insights (chấm điểm cuộc gọi có ghi âm theo mục đích), Chat Insights | `omicall-ai-insight` |
| Điều phối | OMIFlow: phản ứng sự kiện, rẽ nhánh, trì hoãn/SLA, gọi API ngoài, popup, SMS/ZNS/Zalo, Autocall, Callbot/Chatbot | `omicall-omiflow` (+ skill callbot/chatbot) |

## 2. Nguyên tắc chọn
1. **Cấu hình sẵn trước, flow sau**: tính năng nền làm được thì không dựng flow (ít nút, ít quota, ít chỗ hỏng). Ví dụ: hạn phiếu theo chủ đề thay cho flow đếm giờ; "Thêm khách hàng tự động qua cuộc gọi" thay cho flow tạo khách; AI Assistant "Tạo phiếu ghi" có nhân viên xác nhận thay cho flow LLM.
2. **Dựng từ dưới lên**: trường đích (crm) → trường AI bóc (ai, khớp tập giá trị) → tổng đài (nhóm, lời chào, phím) → flow (nháp) → user Xuất bản flow → gắn webhook TTP / gắn kịch bản vào hotline.
3. **Kiểm gói và quota** trước khi hứa: `get_service_package` (module, cờ tính năng, `total_call_assistant`, `total_call_bot_script`…), quota flow/nút, quota trợ lý AI ("N/M").
4. **Một nơi giữ một sự thật**: định tuyến cuộc gọi ở tổng đài, SLA phiếu ở chủ đề, phân lead ở cấu hình phân bổ; flow chỉ phản ứng và bù phần thiếu.

## 3. Công thức theo bài toán
| Bài toán | Ghép module | Nhãn |
|---|---|---|
| Hotline CSKH chia bộ phận bằng phím, nhân viên thấy khách bấm gì | pbx: TTP phím N → nhóm nội bộ N, bật webhook → omiflow B4b (WEB_HOOK → điều kiện `digits` → cửa sổ thông tin) | [đã chạy] (B4b chờ test cuộc gọi thật) |
| Callbot nghe máy trước, cần người thì chuyển | pbx: kịch bản cuộc gọi "Chuyển tiếp đến kịch bản AI Callbot" hoặc phím → "Kịch bản AI Callbot"; callbot gọi webhook OMIFlow lúc chuyển máy → popup/phiếu (B1, B4) | [đã chạy] B1, B4; phần gắn kịch bản [cấu hình sẵn] |
| Gọi vào không ai nghe / ngoài giờ | pbx: hàng đợi nhóm nội bộ, hộp thư thoại hoặc callbot; crm: phân bổ **cuộc gọi nhỡ**; omiflow: điều kiện "Kiểm tra tương tác khách hàng" (không gọi lại trong N phút) → thông báo/thu hồi | [suy luận]; tiêu chí giờ của kịch bản cuộc gọi: Cần khảo sát |
| Sau cuộc gọi tự điền CRM | ai: AI Assistant (Tạo phiếu/Tạo khách, tự điền ghi chú-tag) — nhân viên xác nhận; tự động hoàn toàn → omiflow: trigger cuộc gọi trả lời → trì hoãn → LLM bóc `{{ca_ai_assistant}}` → cập nhật khách (mục 7 ui-build-and-test), B5 chèn vào phiếu | [cấu hình sẵn] / [đã chạy] |
| Chấm chất lượng nhân viên | crm/pbx: Mục đích cuộc gọi (Cấu hình → Doanh nghiệp → Cuộc gọi) → ai: bộ tiêu chí Voice Insights theo mục đích, nhóm nhân viên; flow cảnh báo quản lý khi điểm thấp qua nhóm điều kiện Voice Insights | [cấu hình sẵn]; phần flow [suy luận] |
| Lead từ form/chat → chia sale → SLA gọi → thu hồi | crm: bộ trạng thái khách, cấu hình phân bổ; omiflow B7 (2 flow nối bằng trạng thái, điều kiện SLA, thu hồi) | [đã chạy] |
| Khiếu nại/yêu cầu có hạn xử lý | crm: chủ đề phiếu (độ ưu tiên → hạn, ca làm việc, nhắc trước, trạng thái hoàn thành tính đúng/chậm hạn); omiflow chỉ leo thang (phiếu sắp/đã quá hạn → thông báo cấp trên) | [cấu hình sẵn]; leo thang [suy luận] |
| Gọi ra hàng loạt nhắc lịch/thu nợ/khảo sát | omiflow Marketing `AUTOCALL` (TTS có biến) hoặc Callbot; Autocall bước `ivrMenu`/`ringGroup` cho khách bấm phím gặp nhân viên, `autoPause` khi hết người rảnh; kết quả → phiếu/thuộc tính | [đã chạy] AUTOCALL TTS; IVR/ringGroup [suy luận] |
| Chatbot cần dữ liệu CRM hoặc tạo phiếu | chatbot gọi flow `WEB_HOOK` → `GET_RELATED`/`API_V2` → trả kết quả; LiveTalk lấy SĐT từ `{{social_lt_phone_number}}` | [đã chạy] |
| Đồng bộ hệ thống ngoài (CRM/ERP/HIS) | omiflow B3 (tạo/sửa/huỷ); hiển thị dữ liệu ngoài khi nhân viên gọi: Cấu hình → Doanh nghiệp → Cuộc gọi → **Truy vấn mở rộng** (không cần flow) hoặc flow popup | [đã chạy] B3; Truy vấn mở rộng [cấu hình sẵn, chi tiết Cần khảo sát] |

## 4. Câu hỏi chốt với khách trước khi chọn
Kênh vào (hotline, Zalo, form, đối tác)? Ai nhận và theo luật gì (bộ phận, ca, tỉ lệ)? Kết quả nghiệp vụ là bản ghi nào (khách, phiếu chủ đề nào, trạng thái nào)? Có hạn xử lý không, theo ca nào? Cần AI làm gì (tóm tắt, điền trường, chấm điểm)? Hệ thống ngoài nào, có API chưa? Gói đang bật module nào?
