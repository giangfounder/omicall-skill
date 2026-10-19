# OMIFlow — Tư duy thiết kế và thư viện mẫu

Mẫu **[đã chạy]** rút từ flow thật của một tenant y tế (đã ẩn danh). Mẫu **[suy luận]** ghép từ danh mục module (`node-catalog.md`): logic đúng theo năng lực, nhưng schema của module [enum] phải dựng thử một lần trên UI để lấy JSON.

## A. Khung suy luận: từ bài toán đến flow

Đọc bài toán, trả lời 8 câu theo thứ tự. Mỗi câu chọn ra một hoặc vài module.

| # | Câu hỏi | Chọn module |
|---|---|---|
| 1 | **Cái gì xảy ra thì flow phải chạy?** Hệ thống ngoài hoặc bot gọi vào? Sự kiện trong CRM (cuộc gọi kết thúc, bấm phím, phiếu mới, phiếu đổi trạng thái, khách mới)? Theo lịch? Theo danh sách? Đơn hàng đối tác? | `WEB_HOOK` · `GENERAL` / `TICKET` / `CONTACT` · `PERIOD` · `EXCEL` · `HARAVAN`/`SAPO`/… · `FORM` · `DIRECT_CALL` |
| 2 | **Đối tượng gốc là ai?** Flow đang cầm khách, cuộc gọi, phiếu hay hội thoại? Trigger API **không** tự có đối tượng gốc. | `GET_RELATED` (CLOSEST_CONTACT/CALL/TICKET/CONV) hoặc điều kiện xác định khách theo SĐT |
| 3 | **Thiếu dữ liệu gì để quyết định?** Dữ liệu ở hệ thống ngoài → gọi API lấy về biến. Dữ liệu là văn bản tự do (tóm tắt cuộc gọi, tin nhắn) → AI phân loại. Cần tính → tính toán. | `CREATE_CUSTOM_VARIABLE` API_V2 · CHAT_GPT · CALCULATION |
| 4 | **Rẽ nhánh theo gì?** Giá trị biến, phím IVR, trong hoặc ngoài giờ làm việc, khách đã tồn tại, trạng thái phiếu, kết quả AI. Có nhánh mặc định không? | `CONDITION` (mỗi tình huống một trường hợp + "Bước tiếp theo" làm nhánh mặc định) |
| 5 | **Kết quả nghiệp vụ là gì?** Ghi CRM (tạo hoặc cập nhật khách, phiếu, cuộc gọi, hội thoại), báo nhân viên, đẩy sang hệ thống ngoài, nhắn khách, gọi khách. | `ADD_TICKET`/`UPDATE_INFO_*` · `PUSH_NOTIFICATION`/`PUSH_REMINDER` · `SEND_WEBHOOK` · node kênh chat · `MARKETING` (SMS, ZNS, Callbot, AutoCall, Email) |
| 6 | **Có người tham gia giữa chừng không?** Nhân viên cần thấy thông tin hoặc điền form khi đang nghe máy. | `INFO_DIALOG` · `FORM_DIALOG` (nhánh hoàn thành) · `BUTTON_DIALOG` · `TRANSFER_CALL` · `HOLDING_CALL` |
| 7 | **Thời gian và chờ đợi?** Chờ bản ghi cuộc gọi sinh ra, chờ khách phản hồi, chỉ gửi trong giờ hành chính, nhắc lại sau N ngày. | `DELAY` (sau khoảng, đến thời điểm, theo khung giờ, chờ điều kiện) |
| 8 | **Ai gọi flow chờ kết quả gì? Chống lặp ra sao?** Callbot hoặc chatbot cần dữ liệu trả về; một khách không bị xử lý hai lần. | `SEND_RESPONSE_WEBHOOK_API` · `iteration_config` · `ADD_CLASSIFY` để báo cáo |

Quy tắc ghép:
- **Một flow, một mục đích**. Chuỗi việc dài hoặc dùng chung → tách flow con *phụ thuộc* và gọi bằng `START_OTHER_CAMPAIGN`. Nhưng nếu caller cần nhận dữ liệu tổng hợp qua webhook thì giữ trong một flow.
- **Luôn có nhánh lỗi**: API không trả dữ liệu, AI trả mã lạ, ngoài giờ → tạo phiếu "cần xử lý tay" hoặc thông báo nhân viên, không để luồng chết im.
- **Gom nhánh**: nhiều trường hợp cùng kết thúc giống nhau (gắn cuộc gọi, gán người liên quan) thì nối về **một** nút ACTION chung để tiết kiệm quota nút.
- **Ghi chú trên canvas** (`DESCRIPTION`): URL webhook, cURL mẫu, nguồn gọi ("nhận từ kịch bản callbot số 4").
- Đặt tên flow có số thứ tự và mục đích: `5 - [AI CALL BOT TẠO TICKET SAU GIỜ LÀM VIỆC]`.

## B. Mẫu đã chạy (tenant y tế)

### B1. Callbot → webhook → tra hệ thống ngoài → phiếu ghi gắn cuộc gọi [đã chạy]
Bài toán: ngoài giờ, callbot tiếp nhận; bot không xử lý được thì tạo phiếu cho nhân viên gọi lại.
```
WEB_HOOK(full_name, phone_number, summary, call_id)
 → ACTION: CREATE_CUSTOM_VARIABLE API_V2 (POST HIS /BenhNhan, phoneNumber) → biến Tên/Mã bệnh nhân
 → CONDITION: Tên bệnh nhân != ""  ──có──→ ACTION ADD_TICKET "[YÊU CẦU NGOÀI GIỜ]"
                    └─Bước tiếp theo→ COLLECT_INFO "Khách hàng mới" ─┘
 → DELAY 10 giây → ACTION GET_RELATED CLOSEST_CALL (ct_transaction_id = {{call_id}})
 → (tìm thấy) ACTION ASSIGN_TICKET_PIN_OBJECT (gắn cuộc gọi) + ASSIGN_TICKET_REPORTER
```
Biến thể: cấp cứu ngoài giờ (tạo phiếu danh mục Cấp cứu), cuộc gọi nhỡ (tạo phiếu "[GỌI NHỠ]").

### B2. Sự kiện cuộc gọi + phím IVR + giờ làm việc + AI phân loại → phiếu đúng danh mục [đã chạy]
```
GENERAL: cuộc gọi vào, đã kết thúc, ct_key_action ∈ {1..4}
 → API_V2 tra bệnh nhân theo {{ct_phone_number}} → DELAY 10 giây
 → CONDITION mã bệnh nhân rỗng? → (rỗng) COLLECT_INFO "Khách hàng mới"
 → CONDITION TIME_FRAME (trong giờ | ngoài giờ)
 → CONDITION theo phím: 4 = khiếu nại · 3 = cấp cứu · 2 = tư vấn
     4 → CHAT_GPT(intent từ {{ca_summarize}}) → CONDITION 17 mã intent → ADD_TICKET theo danh mục khiếu nại
                                                └ "thái độ nhân viên" → CHAT_GPT(đối tượng: lễ tân, bác sĩ…) → CONDITION → ADD_TICKET
     3 → ADD_TICKET "CẤP CỨU KHẨN CẤP - {{tên}} - {{sđt}}"
     2 → CHAT_GPT(dịch vụ hay vấn đề chung) → ADD_TICKET "TƯ VẤN …"
 → mọi nhánh dồn về 1 ACTION: ASSIGN_TICKET_REPORTER + ASSIGN_TICKET_PIN_OBJECT
```
Bài học: AI trả **mã** (snake_case) và điều kiện so `CONTAIN` mã đó. Giữ danh sách mã trong prompt và trong các trường hợp của CONDITION **giống hệt nhau**.

### B3. Đồng bộ hai chiều với hệ thống ngoài (đặt, sửa, huỷ lịch) [đã chạy]
```
WEB_HOOK(… status, appointmentID, patientID …)  ← callbot gọi
 → API_V2 GET hồ sơ theo SĐT
 → CONDITION status: new | update | cancel | (khác → PUSH_NOTIFICATION "CÓ LỖI")
   new    → GET_RELATED CLOSEST_CALL → ADD_TICKET "ĐĂNG KÝ KHÁM MỚI" (created_by CAMPAIGN_CALLBOT_CREATOR)
            → DELAY 5 giây → gắn cuộc gọi, người liên quan, chèn {{ca_ai_assistant}} vào mô tả → SEND_WEBHOOK POST /TaoLichKham
   update → GET_RELATED CLOSEST_TICKET (trạng thái đang mở, của khách có SĐT) → ASSIGN_TICKET_TYPE/ATTRIBUTE/DESCRIPTION → SEND_WEBHOOK /CapNhatLichKham
   cancel → GET_RELATED CLOSEST_TICKET → ASSIGN_TICKET_TYPE (trạng thái huỷ) → SEND_WEBHOOK /HuyLichKham
```
Chiều ngược lại (nhân viên tự tạo phiếu lịch hẹn): `GENERAL` NEW_TICKET thuộc danh mục lịch hẹn → `SEND_WEBHOOK` đẩy sang hệ thống ngoài.

### B4. Popup thông tin cho nhân viên khi chuyển máy [đã chạy]
```
WEB_HOOK(digits, customer_phone, ct_transaction_id)  ← tổng đài hoặc callbot gọi lúc chuyển máy
 → API_V2 tra hồ sơ → (không có) COLLECT_INFO "Bệnh nhân mới"
 → CONDITION digits: 2 → INFO_DIALOG "TƯ VẤN" · 3 → INFO_DIALOG "CẤP CỨU" · 4 → INFO_DIALOG "KHIẾU NẠI"
                     1 → FORM_DIALOG "PHIẾU ĐĂNG KÝ KHÁM" (điền sẵn tên, SĐT từ biến)
                           ├─hoàn thành→ ADD_TICKET "ĐĂNG KÝ KHÁM MỚI" từ dữ liệu form → DELAY 3 phút → gắn cuộc gọi, mô tả AI
                           └─Bước tiếp theo→ ADD_TICKET "TƯ VẤN" → DELAY chờ cuộc gọi kết thúc (tối đa 30 phút) → GET_RELATED cuộc gọi → gắn
```

### B5. Ghi kết quả AI Assistant vào phiếu [đã chạy]
`GENERAL` (cuộc gọi kết thúc) → `DELAY 5 giây` → `GET_RELATED CLOSEST_TICKET` (thuộc tính phiếu "mã cuộc gọi" = `{{ct_transaction_id}}`) → `ASSIGN_TICKET_DESCRIPTION` chèn `{{ca_ai_assistant}}` vào cuối mô tả.

### B6. Zalo cá nhân: gửi lời mời kết bạn khi chưa có hội thoại [đã chạy]
`WEB_HOOK(contactPhone, phoneAcountZalo)` → node `ZALO_PERSONAL_MESSAGE` hành động `REQUEST_FRIEND`.

## C. Mẫu mở rộng theo năng lực [suy luận]

| Lĩnh vực / bài toán | Thiết kế |
|---|---|
| **Chatbot hoặc callbot cần tra CRM giữa hội thoại** | `WEB_HOOK(sđt)` → `GET_RELATED CLOSEST_CONTACT` (SĐT = biến) → `CONDITION` có hay không → `SEND_RESPONSE_WEBHOOK_API` trả JSON gồm thuộc tính khách. Không tìm thấy → `ADD_NEW_CONTACT` → trả `{"is_new":true}`. Bot khai URL ở mục Truy vấn API. |
| **Lead từ biểu mẫu hoặc quảng cáo** | `FORM` hoặc `WEB_HOOK` → `ADD_NEW_CONTACT` (phân sale theo cấu hình) → `PUSH_NOTIFICATION` cho sale → `DELAY 15 phút` → `CONDITION` (cuộc gọi gần nhất của khách chưa có) → `PUSH_REMINDER` + `MARKETING CALLBOT` gọi chào. |
| **Nhắc lịch hẹn, tái khám, bảo dưỡng** | `PERIOD` hằng ngày (hoặc `EXCEL`) → `CONDITION` ngày hẹn = ngày mai → `MARKETING SEND_ZNS` → `DELAY` → `CONDITION` trạng thái gửi ZNS thất bại → `MARKETING CALLBOT` (gọi nhắc) → `ADD_CLASSIFY` kết quả. |
| **Chăm sóc sau bán, khảo sát CSAT** | Trigger `TICKET` (phiếu sang "Hoàn tất") → `DELAY 1 ngày` trong khung 8h–20h → `MARKETING CALLBOT` khảo sát → callbot gọi lại `WEB_HOOK` gửi điểm → `CONDITION` điểm ≤ 2 → `ADD_TICKET` "Khách không hài lòng" + `PUSH_NOTIFICATION` cho trưởng nhóm. |
| **SLA phiếu ghi, leo thang** | Trigger `TICKET` (trạng thái "Mới") → `DELAY 2 giờ` → `GET_RELATED` lại phiếu → `CONDITION` vẫn "Mới" → `ASSIGN_TICKET_PRIORITY` cao + `ASSIGN_TICKET_ASSIGNEE` trưởng nhóm + `PUSH_NOTIFICATION`. |
| **Thương mại điện tử: đơn hàng đối tác** | `HARAVAN`/`SAPO`/`KIOTVIET`/`SHOPIFY` (đơn tạo mới) → `ADD_NEW_CONTACT` hoặc `UPDATE_INFO_CONTACT` → `SEND_ZNS` xác nhận đơn. Đơn COD giá trị cao → `MARKETING CALLBOT` xác nhận → callbot gọi `WEB_HOOK` → `ORDER_*_ACTION` cập nhật trạng thái đơn. |
| **Thu hồi nợ, nhắc thanh toán** | `EXCEL` (danh sách đến hạn) → `RANDOM` 50/50 (A/B kịch bản) → `MARKETING CALLBOT` → `ADD_CLASSIFY` (hứa trả, từ chối, không nghe) → `CONDITION` không nghe → `DELAY 1 ngày` → gọi lại, tối đa N lần (`iteration_config`). |
| **Phân luồng cuộc gọi theo khách VIP** | `DIRECT_CALL` → `HOLDING_CALL` → `API_V2` tra hạng khách → `CONDITION` VIP → `TRANSFER_CALL` nhóm VIP + `INFO_DIALOG` thông tin khách; còn lại → `TRANSFER_CALL` nhóm chung. |
| **Đa kênh: khách nhắn ngoài giờ** | `GENERAL` (hội thoại mới) → `CONDITION` TIME_FRAME ngoài giờ → node AI Chatbot xử lý → `CHAT_GPT` phân loại → `ADD_TICKET` + `UPDATE_CONVERSATION` gắn nhãn → sáng hôm sau `PUSH_REMINDER`. |
| **Báo cáo nhanh ra Google Sheet** | Bất kỳ trigger → `UPLOAD_GOOGLE_SHEET` ghi dòng (thời gian, SĐT, kết quả, nhãn) cho bộ phận không dùng CRM. |
| **Ưu đãi, voucher** | `FORM` đăng ký → `CREATE_CUSTOM_VARIABLE` RANDOM (mã) hoặc gán voucher (`ASSIGN_VOUCHER_LINK_CONTACT`) → `SEND_ZNS`; `invitation` (COMBINE_IMAGE) tạo ảnh thư mời cá nhân hoá. |

## D. Lỗi thiết kế đã thấy trong flow thật (tránh lặp lại)
- So khớp kết quả AI với giá trị có khoảng trắng thừa (`"  vc"`) → không bao giờ khớp, rơi vào nhánh mặc định.
- Prompt AI tham chiếu một mã biến đã bị xoá → cảnh báo "biến liên kết có vấn đề", AI nhận chuỗi rỗng.
- Hai trường hợp trùng nghĩa (`"2"` và `"02"`) do phím IVR có thể được ghi khác nhau: gộp bằng `IN` hoặc `CONTAIN`, hoặc giữ cả hai có chủ đích.
- Nhiều nút ACTION y hệt nhau (cùng tạo một loại phiếu) ở các nhánh: gom bằng cách cho các trường hợp trỏ cùng một nút để giảm số nút.
