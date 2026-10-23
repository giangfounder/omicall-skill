# OMIFlow — Tư duy thiết kế và thư viện mẫu

Module là của nền tảng, dùng chung mọi tenant; mẫu chỉ khác nhau ở **nghiệp vụ**. Mẫu **[tài liệu OMI]** lấy từ hướng dẫn chính thức; mẫu **[đã chạy]** rút từ flow thật (ví dụ ở một tenant y tế, đã ẩn danh; khung áp dụng cho mọi ngành có tổng đài và hệ thống ngoài); mẫu **[suy luận]** ghép từ danh mục module, logic đúng theo năng lực, nhưng schema của module [enum] phải dựng thử một lần để lấy JSON.

## A. Khung suy luận: từ bài toán đến flow

Đọc bài toán, trả lời 8 câu theo thứ tự. Mỗi câu chọn ra một hoặc vài module.

| # | Câu hỏi | Chọn module |
|---|---|---|
| 1 | **Cái gì xảy ra thì flow phải chạy?** Hệ thống ngoài hoặc bot gọi vào? Sự kiện trong CRM (cuộc gọi kết thúc, bấm phím, phiếu mới, phiếu đổi trạng thái, khách mới)? Theo lịch? Theo danh sách? Đơn hàng đối tác? | `WEB_HOOK` · `GENERAL` / `TICKET` / `CONTACT` · `PERIOD` · `EXCEL` · `HARAVAN`/`SAPO`/… · `FORM` · `DIRECT_CALL` |
| 2 | **Đối tượng nào phải có trong luồng?** Đối tượng gốc từ trigger là gì, cái gì tự kéo theo, hành động phía sau cần đối tượng nào (gửi Zalo cần hội thoại Zalo, gửi ZNS cho "Khách hàng" cần khách, cập nhật đơn cần ID đơn)? Trigger API **không** có đối tượng gốc. Xem `concepts.md` mục 1. | `GET_RELATED` (khách, phiếu, cuộc gọi, hội thoại, nhân viên, đơn hàng đối tác; có thể tìm qua đối tượng khác; vị trí 1–5) |
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

## B0. Mẫu trong tài liệu chính thức [tài liệu OMI]

### B0.1 Bán lẻ — chatbot xác nhận đơn và báo giao hàng (Haravan + Messenger)
```
Đối tác Haravan · trường hợp 1: Đơn hàng tạo mới | trường hợp 2: Đơn cập nhật + trạng thái giao = Đang giao
 → GET_RELATED Cuộc trò chuyện (kênh Facebook Tin nhắn), tìm qua Khách hàng có SĐT = {{SĐT đặt hàng Haravan}}
 → node FACEBOOK_CHAT_MESSAGE: mã đơn, địa chỉ, tổng tiền + 2 nút [Xác nhận] [Từ chối]
     ├─ Xác nhận → Hành động Đối tác: Haravan "Xác nhận đơn" (ID đơn = biến)
     └─ Từ chối  → Hành động Đối tác: Haravan "Huỷ đơn"
 (trường hợp 2) → GET_RELATED hội thoại → tin "Đơn đang được giao"
```
Biến thể: gửi ZNS khi đơn mới; điều kiện kèm (đơn trên 1 triệu, kênh bán, đã thanh toán, khách có doanh thu tích luỹ ≥ 10 triệu).

### B0.2 Marketing game — Zalo OA + nền tảng game (2 flow)
```
Flow 1: Sự kiện khách quan tâm OA → Biến tuỳ chỉnh API (POST lấy link game, partner_user_id = {{social_zalo_user_id}})
        → gửi Tin giao dịch Zalo chứa {{game_url}}
Flow 2: API (nền tảng game gọi về khi có kết quả quay thưởng) → điều kiện trúng/không → gửi Tin giao dịch chúc mừng hoặc cảm ơn
```
Trigger của flow 1 có thể thay bằng: khách bấm menu OA, quét QR, nhắn từ khoá hoặc ý định (AI), hoàn thành biểu mẫu, admin gửi hàng loạt.

### B0.3 Nhân sự — chấm công từ thiết bị (Đối tác tự định nghĩa)
Đối tác "Thiết bị chấm công" có 2 đối tượng: *Lượt chấm công*, *Đơn xin nghỉ*. Thuộc tính khai báo bằng cú pháp truy vấn (`personName`, `today-checkinTime`, `month|1-checkinTime`). Flow: sự kiện lượt chấm công → điều kiện giờ vào > 08:00 → thông báo cho quản lý hoặc ghi Google Sheet.

### B0.4 Vận hành — sự kiện từ Google Sheet
App Script trên sheet POST vào trigger API khi cột "Trạng thái" = "Xác nhận" → flow nhận `data[]`, `action` → tạo phiếu, gửi ZNS hoặc gọi Callbot cho dòng đó.

## B. Mẫu đã chạy trong flow thật (ví dụ ngành y tế, khung dùng chung)

### B1. Callbot → webhook → tra hệ thống ngoài (CRM, ERP, HIS…) → phiếu ghi gắn cuộc gọi [đã chạy]
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

### B3. Đồng bộ hai chiều với hệ thống ngoài: tạo, sửa, huỷ một bản ghi (lịch hẹn, đơn, hợp đồng…) [đã chạy]
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

### B7. Phân lead có bước duyệt + SLA gọi + thu hồi (2 flow nối bằng trạng thái) [đã chạy]
Khung dùng chung cho mọi bài toán "giao việc cho người, quá hạn không xử lý thì nhắc rồi thu hồi" (lead, phiếu, yêu cầu).
```
Flow A — FORM (hoặc WEB_HOOK / sự kiện kênh) · không giới hạn lượt
 → ACTION: ADD_NEW_CONTACT (ánh xạ biến form) + UPDATE_INFO_CONTACT (phụ trách = người duyệt, trạng thái = "chờ duyệt" + ghi chú)
           + PUSH_NOTIFICATION cho người duyệt
        ↓ người duyệt đổi trạng thái pipeline sang "đã duyệt"  (mốc nối, không cần tag/form mới)
Flow B — GENERAL: thuộc tính trạng thái = "đã duyệt" · giới hạn lượt có chủ đích
 → ACTION: UPDATE_INFO_CONTACT (phụ trách = người xử lý hoặc cấu hình phân bổ) + PUSH_NOTIFICATION "xử lý trong N phút"
 → DELAY N → CONDITION Mở rộng "Kiểm tra tương tác khách hàng": Không có tương tác [Cuộc gọi] trong N phút
       ├─ thoả → PUSH_NOTIFICATION cảnh báo → DELAY M → CONDITION: Không có tương tác [Cuộc gọi, Ghi chú] trong N+M phút
       │            ├─ thoả → UPDATE_INFO_CONTACT (phụ trách = admin/phân bổ lại, ghi chú "thu hồi") + PUSH_NOTIFICATION
       │            └─ Bước tiếp theo → kết thúc
       └─ Bước tiếp theo (đã gọi) → kết thúc
```
- Trigger theo trạng thái chỉ bắt lúc chuyển vào trạng thái: sửa thông tin khác không làm Flow B chạy lại; người dùng chỉ cần một thao tác (đổi trạng thái) để chuyển giai đoạn.
- Chọn rõ người tương tác ở điều kiện (nhân viên cụ thể/tất cả), không tick "Hệ thống" nếu flow tự ghi log.
- Phải xác nhận với KH: thu hồi khi "không gọi VÀ không ghi chú" hay "thiếu một trong hai"; "ghi chú trạng thái" là Ghi chú hay Chuyển trạng thái; giới hạn lượt Flow B; đối tượng đang trong SLA mà kích hoạt lại Flow A thì xử lý thế nào (lượt SLA cũ vẫn chạy).
- Flow A cập nhật khách cũ: khai báo cả các thuộc tính cần làm mới (tên…) trong UPDATE_INFO_CONTACT, nếu không khách cũ chỉ được đổi phụ trách/trạng thái.

## C. Mẫu mở rộng theo năng lực [suy luận]

| Lĩnh vực / bài toán | Thiết kế |
|---|---|
| **Chatbot hoặc callbot cần tra CRM giữa hội thoại** | `WEB_HOOK(sđt)` → `GET_RELATED CLOSEST_CONTACT` (SĐT = biến) → `CONDITION` có hay không → `SEND_RESPONSE_WEBHOOK_API` trả JSON gồm thuộc tính khách. Không tìm thấy → `ADD_NEW_CONTACT` → trả `{"is_new":true}`. Bot khai URL ở mục Truy vấn API. |
| **Lead từ biểu mẫu hoặc quảng cáo** | Khung đã chạy: B7. Biến thể: bỏ bước duyệt (Flow A phân sale thẳng bằng cấu hình phân bổ), hoặc nhánh quá hạn → `PUSH_REMINDER` + `MARKETING CALLBOT` gọi chào thay vì thu hồi. |
| **Nhắc lịch hẹn, tái khám, bảo dưỡng** | `PERIOD` hằng ngày (hoặc `EXCEL`) → `CONDITION` ngày hẹn = ngày mai → `MARKETING SEND_ZNS` → `DELAY` → `CONDITION` trạng thái gửi ZNS thất bại → `MARKETING CALLBOT` (gọi nhắc) → `ADD_CLASSIFY` kết quả. |
| **Chăm sóc sau bán, khảo sát CSAT** | Trigger `TICKET` (phiếu sang "Hoàn tất") → `DELAY 1 ngày` trong khung 8h–20h → `MARKETING CALLBOT` khảo sát → callbot gọi lại `WEB_HOOK` gửi điểm → `CONDITION` điểm ≤ 2 → `ADD_TICKET` "Khách không hài lòng" + `PUSH_NOTIFICATION` cho trưởng nhóm. |
| **SLA phiếu ghi, leo thang** | Trigger `TICKET` (trạng thái "Mới") → `DELAY 2 giờ` → `GET_RELATED` lại phiếu → `CONDITION` vẫn "Mới" → `ASSIGN_TICKET_PRIORITY` cao + `ASSIGN_TICKET_ASSIGNEE` trưởng nhóm + `PUSH_NOTIFICATION`. |
| **Thương mại điện tử: đơn hàng đối tác** | `HARAVAN`/`SAPO`/`KIOTVIET`/`SHOPIFY` (đơn tạo mới) → `ADD_NEW_CONTACT` hoặc `UPDATE_INFO_CONTACT` → `SEND_ZNS` xác nhận đơn. Đơn COD giá trị cao → `MARKETING CALLBOT` xác nhận → callbot gọi `WEB_HOOK` → `ORDER_*_ACTION` cập nhật trạng thái đơn. |
| **Thu hồi nợ, nhắc thanh toán** | `EXCEL` (danh sách đến hạn) → `RANDOM` 50/50 (A/B kịch bản) → `MARKETING CALLBOT` → `ADD_CLASSIFY` (hứa trả, từ chối, không nghe) → `CONDITION` không nghe → `DELAY 1 ngày` → gọi lại, tối đa N lần (`iteration_config`). |
| **Phân luồng cuộc gọi theo khách VIP** | `DIRECT_CALL` → `HOLDING_CALL` → `API_V2` tra hạng khách → `CONDITION` VIP → `TRANSFER_CALL` nhóm VIP + `INFO_DIALOG` thông tin khách; còn lại → `TRANSFER_CALL` nhóm chung. |
| **Đa kênh: khách nhắn ngoài giờ** | `GENERAL` (hội thoại mới) → `CONDITION` TIME_FRAME ngoài giờ → node AI Chatbot xử lý → `CHAT_GPT` phân loại → `ADD_TICKET` + `UPDATE_CONVERSATION` gắn nhãn → sáng hôm sau `PUSH_REMINDER`. |
| **Đón tin nhắn LiveTalk giao cho AI Chatbot (chat thử bot)** | `GENERAL` (hội thoại thêm mới; điều kiện kênh LiveTalk **và đúng widget test** — thiếu điều kiện widget là bắt cả khách thật) → `OMI_BOT_AI` chọn bot; `iteration_config` để mỗi hội thoại giao bot một lần; nhân viên nhận thì `UPDATE_SOCIAL_CHATBOT_STATUS` tắt bot. Chỉ dựng khi kênh không có ô chọn bot sẵn (tốn quota flow). Quy trình kiểm thử bot: skill `omicall-chatbot-gen-ai`, `references/livetalk-test-optimize.md`. |
| **Báo cáo nhanh ra Google Sheet** | Bất kỳ trigger → `UPLOAD_GOOGLE_SHEET` ghi dòng (thời gian, SĐT, kết quả, nhãn) cho bộ phận không dùng CRM. |
| **Ưu đãi, voucher** | `FORM` đăng ký → `CREATE_CUSTOM_VARIABLE` RANDOM (mã) hoặc gán voucher (`ASSIGN_VOUCHER_LINK_CONTACT`) → `SEND_ZNS`; `invitation` (COMBINE_IMAGE) tạo ảnh thư mời cá nhân hoá. |

## D. Lỗi thiết kế đã thấy trong flow thật (tránh lặp lại)
- So khớp kết quả AI với giá trị có khoảng trắng thừa (`"  vc"`) → không bao giờ khớp, rơi vào nhánh mặc định.
- Prompt AI tham chiếu một mã biến đã bị xoá → cảnh báo "biến liên kết có vấn đề", AI nhận chuỗi rỗng.
- Hai trường hợp trùng nghĩa (`"2"` và `"02"`) do phím IVR có thể được ghi khác nhau: gộp bằng `IN` hoặc `CONTAIN`, hoặc giữ cả hai có chủ đích.
- Nhiều nút ACTION y hệt nhau (cùng tạo một loại phiếu) ở các nhánh: gom bằng cách cho các trường hợp trỏ cùng một nút để giảm số nút.
- Kiểm tra "chưa gọi trong N phút" bằng cách tự đếm (chụp `interactive_call` vào biến, so `last_call_transaction_time` với mốc giao): phức tạp và dễ sai → dùng điều kiện Mở rộng "Kiểm tra tương tác khách hàng".
- Để giới hạn số lần đi qua mặc định (2) mà không cân nhắc: đối tượng được duyệt/giao lại lần 3 bị flow bỏ qua im lặng.
