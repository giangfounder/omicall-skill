# OMIFlow — Khái niệm cốt lõi (dùng chung mọi tenant)

Nguồn: tài liệu chính thức OMI tại `https://omicrm.io/post/topic/omiflow-7` (Tổng quan OMIFlow, Nút Trì hoãn, Biến liên kết, Đối tượng trong OMIFlow, Đối tác tích hợp, Đối tác tự định nghĩa, Google Sheet, các kịch bản mẫu Haravan và WOAY), đối chiếu với JSON flow thật.

**Nguyên tắc**: bộ trigger, nút và hành động là của **nền tảng**, tenant nào cũng như nhau. Tenant chỉ khác ở:
- dữ liệu cấu hình: danh mục và trạng thái phiếu, thuộc tính động, nhân viên, nhóm, phân bổ, tag;
- tích hợp đã bật: Zalo OA, Facebook, nhà cung cấp SMS hoặc Email, ESMS cho ZNS, Google, đối tác bán hàng, callbot;
- gói dịch vụ: quota flow, quota nút, AI.

Thiết kế luôn dựa trên năng lực nền tảng. Còn id cụ thể và tích hợp sẵn có thì tra trong tenant.

---

## 1. Đối tượng (object) — khái niệm quan trọng nhất

Mỗi lượt chạy flow mang theo các **đối tượng**: Khách hàng, Phiếu ghi, Cuộc gọi, Cuộc trò chuyện, Nhân viên, Voucher, Đơn hàng, Khách hàng hoặc Hoá đơn của đối tác. Hành động chỉ tác động được lên đối tượng **đã có trong luồng**; thiếu đối tượng thì hành động bị bỏ qua, luồng vẫn chạy tiếp.

**Đối tượng vào luồng từ trigger** (đối tượng gốc):

| Trigger | Đối tượng gốc |
|---|---|
| Điều kiện | Khách hàng, Phiếu ghi, Cuộc gọi, Cuộc gọi được AI phân tích, hoặc Cuộc trò chuyện thoả điều kiện |
| Biểu mẫu | Lượt hoàn thành biểu mẫu |
| Định kỳ | Các đối tượng thoả điều kiện so sánh của kịch bản định kỳ |
| File Excel | Mỗi dòng |
| API | Không có đối tượng nào, chỉ có biến |
| Đối tác | Đơn hàng, Khách hàng hoặc Hoá đơn của đối tác |

**Đối tượng tự kéo theo**:
- Phiếu ghi → khách hàng, cuộc gọi, cuộc trò chuyện đính kèm phiếu.
- Cuộc gọi → khách hàng (nếu cuộc gọi đã gắn với khách).
- Cuộc trò chuyện → khách hàng đã liên kết.
- Biểu mẫu, File Excel → phiếu, khách hàng, cuộc trò chuyện, cuộc gọi, nếu biến được khai báo liên kết.
- Đơn hàng, Hoá đơn → khách hàng của đối tác.
- Lượt đánh giá ZNS → khách hàng theo SĐT.

**Gán thêm giữa chừng**: hành động *Gán đối tượng liên quan* (`GET_RELATED`) tìm theo thuộc tính hoặc bộ lọc, có thể tìm qua đối tượng khác (ví dụ tìm hội thoại Messenger *của khách có SĐT = biến*). Không tìm thấy thì luồng vẫn chạy, chỉ thiếu đối tượng đó.

**Vị trí**: đối tượng đầu tiên mỗi loại là vị trí 0 (không cần cấu hình). Các đối tượng cùng loại gán thêm có vị trí 1–5 (tối đa 5). Điều kiện và hành động muốn trỏ tới đối tượng thứ hai trở đi phải chọn vị trí. Ví dụ: gửi Zalo cho cả cha và mẹ (2 khách, 2 hội thoại); cập nhật 3 phiếu cùng chủ đề.

**Đối tượng cần có trước từng loại hành động**:

| Hành động | Cần |
|---|---|
| Marketing (SMS, ZNS, Email, Callbot, AutoCall) | Người nhận "Khách hàng" → khách phải trong luồng; người nhận "Tuỳ chỉnh" → chỉ cần biến SĐT hoặc email (biến form, API, đơn hàng…); hoặc gửi cho nhân viên |
| Gửi tin nhắn kênh (Messenger, Zalo, Telegram, LiveTalk…) | Cuộc trò chuyện của **đúng kênh** đã trong luồng (mỗi kênh gán riêng), hoặc tuỳ chỉnh bằng ID cuộc trò chuyện |
| Cập nhật đơn hàng đối tác | ID đơn hàng (từ sự kiện đơn hoặc lưu ở thuộc tính khách, phiếu) |
| Cập nhật khách, phiếu, cuộc gọi, hội thoại | Đối tượng đó đã trong luồng |

Kiểm tra: tab **Lịch sử** của flow hiển thị các đối tượng (item) của mỗi lượt chạy. Không có item tức là chưa đưa được đối tượng vào → thêm *Gán đối tượng liên quan*. Có thể dùng nút Điều kiện kiểm tra thuộc tính rỗng để biết đã gán thành công chưa.

## 2. Trigger — cơ chế kích hoạt
- **Điều kiện**:
  - Chỉ dùng *điều kiện thuộc tính đối tượng*: flow chạy khi đối tượng được **thêm mới hoặc cập nhật** và thoả điều kiện. Ví dụ "khách mang tag VIP": chạy khi khách mới có tag hoặc khách được cập nhật thêm tag.
  - Kết hợp *điều kiện mở rộng* (sự kiện đặc biệt như khách đánh giá ZNS, khách quan tâm OA, cuộc gọi kết thúc…): flow chỉ chạy **khi có sự kiện đó**; điều kiện thuộc tính trở thành điều kiện kèm.
- **Xảy ra định kỳ**: hằng ngày, hằng tuần (chọn thứ), hằng tháng (chọn ngày), **trước khi** hoặc **sau khi** một thuộc tính kiểu thời gian (ví dụ trước sinh nhật khách 2 ngày, trước hạn phiếu 15 phút), hoặc một thời điểm cụ thể.
- **API**: GET, POST, PUT, DELETE, PATCH; khai báo biến từ body; trả response cố định, hoặc động bằng hành động *Trả về kết quả API* (chỉ dùng được với trigger API).
- **File Excel**: khai báo biến theo cột rồi tải file; mỗi dòng là một lượt.
- **Biểu mẫu**: lượt hoàn thành mới; dùng mọi thuộc tính khách đã gửi để so sánh và làm biến. *Trả về kết quả biểu mẫu* chỉ dùng được với trigger Biểu mẫu.
- **Đối tác**, ba hình thức:
  1. *Liên kết trực tiếp* (Haravan, KiotViet, Sapo, WooCommerce, Pancake…): sự kiện định nghĩa sẵn (đơn tạo mới, thanh toán, cập nhật trạng thái giao, khách cập nhật, hoá đơn…), hành động cập nhật ngược (xác nhận đơn, huỷ, ghi chú, đóng đơn), gán liên quan đơn hàng hoặc khách, tự kéo khách của đối tác. Điều kiện kết hợp: sự kiện đơn với thuộc tính đơn và khách; sự kiện hoá đơn với thuộc tính hoá đơn và khách; sự kiện khách chỉ với thuộc tính khách.
  2. *Liên kết không trực tiếp* hoặc *Webhook*: chỉ nhận dữ liệu gửi sang; tự phân biệt sự kiện bằng thuộc tính (ví dụ trạng thái "Đang vận chuyển"); cập nhật ngược bằng hành động API.
  3. *Đối tác tự định nghĩa*: khai báo tên, mã, logo đối tác; mỗi đối tượng có **thuộc tính định danh** (duy nhất, dùng cho giới hạn số lần đi qua) và **thuộc tính hiển thị** (hiện ở Lịch sử); kiểu thuộc tính Text, Date (`HH:mm`, `dd/MM/yyyy`, `HH:mm dd/MM/yyyy`), Option (ánh xạ giá trị, ví dụ 1→Nam). Mã thuộc tính dùng cú pháp truy vấn ở mục 4.

## 3. Biến liên kết
Cú pháp `{{ten_bien}}`, dùng được ở mọi ô nhập văn bản.
- **Thuộc tính hệ thống** (tên có nghĩa): `{{full_name}}`, `{{age}}`, `{{gender1}}` (Anh hoặc Chị theo giới tính), `{{current_time}}`, `{{ticket_unique_id}}`, `{{ct_transaction_id}}`, `{{ct_phone_number}}`, `{{social_customer_name}}`, `{{social_zalo_user_id}}`, `{{haravan-order_number}}`, `{{sapo_customer-name}}`, `{{ca_summarize}}`, `{{ca_ai_assistant}}`…
- **Thuộc tính động**: thuộc tính doanh nghiệp tự thêm cho khách, phiếu, hội thoại; mã ngẫu nhiên. Xem bằng công cụ "Biến liên kết đã sử dụng" trên canvas.
- **Biến tuỳ chỉnh và dữ liệu thu thập**: mã ngẫu nhiên; **chỉ có hiệu lực trong flow hiện tại**, không truyền sang flow được gọi bằng *Gọi đến kịch bản khác*. Nguồn tạo: hành động Biến liên kết tuỳ chỉnh (API, Random, Phép toán, ChatGPT, Ảnh thư mời), cột Excel, nút Thu thập thông tin hoặc phần thu thập trong nút gửi tin nhắn (AI bóc thực thể).
- **Biến đối tác chưa khai báo**: vẫn dùng được với cú pháp `{{<doitac>_<loai>-<duong_dan>}}`, trong đó loai là `order`, `customer` hoặc `invoice`. Ví dụ: `{{haravan_order-billing_address-ward_code}}`, `{{kiotviet_invoice-branchName}}`. So sánh bằng điều kiện "Tuỳ chỉnh".
- Biến đối tác đã khai báo được OMI định dạng lại (thời gian → `10:13 03/07/2023`, giới tính 1 → Nam).

## 4. Cú pháp truy vấn JSON (webhook, đối tác tự định nghĩa, API)
- Trường ở gốc: `personName`.
- Trường trong object: `today-checkinTime` (dấu `-` đi vào object con). Trong JSON lưu của API_V2: `query:[{"key":"data"},{"key":"game_url"}]`, `shorthand_query:"data.game_url"`.
- Phần tử mảng: `month|1-checkinTime` (vị trí bắt đầu từ 1). Trong API_V2: `{"type":"array","key":"data","pos":1}`, `shorthand_query:"data|1.mabenhnhan"`.
- Ghép nhiều trường: bật "Kết hợp nhiều biến", liệt kê `placeName, deviceName`.

## 5. Nút Logic và nút AI
- **Trì hoãn (Delay)**:
  - *Sau khoảng thời gian* (giây, phút, giờ, ngày).
  - *Thời gian cụ thể*: mốc trong quá khứ thì bỏ qua nút.
  - *Khung giờ tiếp tục*: chỉ chạy tiếp trong khung giờ và ngày chọn. Ví dụ đặt 08:00–17:30 thứ 2–6 trước khi gọi Callbot hoặc gửi ZNS để không vi phạm khung giờ nhà mạng.
  - *Hoặc điều kiện đến trước*: điều kiện khách, phiếu, cuộc gọi, đa kênh thoả thì đi tiếp ngay. Nếu hết giờ mới đi tiếp nghĩa là điều kiện chưa xảy ra, ví dụ khách chưa xem tin.
  - Lượt chạy đang ở trạng thái *Đang trì hoãn* vẫn chờ kể cả khi flow bị ngưng. Trong Lịch sử có thể *Tiếp tục kịch bản* hoặc *Huỷ kịch bản* từng lượt hoặc hàng loạt.
- **Random**: chia nhánh theo tỉ lệ (A/B test nội dung, kịch bản, kênh).
- **Phân tích thông tin** (`AI_ANALYZE`): đưa một đoạn nội dung (tin nhắn khách, mô tả, ghi chú, biến) cho AI phân loại theo **Chủ đề hoặc Ý định đã đào tạo** ở mô-đun AI, rồi chia nhánh. Khác với ChatGPT trong *Biến liên kết tuỳ chỉnh*: ChatGPT trả về một giá trị tuỳ ý theo prompt, sau đó phải dùng nút Điều kiện để rẽ nhánh.
- **Thu thập thông tin** (`COLLECT_INFO`): AI bóc **Đối tượng hoặc Thực thể** (SĐT, email, ngày, thực thể tự đào tạo) từ một đoạn nội dung, lưu vào biến. Tuỳ chọn `FROM_DEFINED_VARIABLE` gán thẳng một giá trị cố định (cách dùng làm giá trị mặc định).
- **Ghi chú**: chỉ hiển thị trên canvas, không có hiệu lực.

## 6. Nút Marketing và nút Trò chuyện
- **Marketing**: SMS (theo nhà cung cấp SMS đã cấu hình), ZNS (cần OA liên kết + ESMS + template), Yêu cầu cuộc gọi ZCC (khách đồng ý thì OA gọi miễn phí trong 30 ngày), Email (nhà cung cấp email), Gọi tự động (kịch bản thường: lời chào, phím), CallBot (kịch bản AI), Viber Business. Người nhận: khách hàng, tuỳ chỉnh bằng biến, nhân viên, nhóm, hoặc nhân viên thoả điều kiện. Có điều kiện kiểm tra trạng thái gửi (SMS, ZNS, Email, AutoCall, Callbot, quyền gọi ZCC) để rẽ nhánh sau khi gửi.
- **Trò chuyện**: dựng chatbot theo kênh. Loại tin hỗ trợ khác nhau theo kênh:
  - Facebook: văn bản, ảnh, âm thanh, video, file, thẻ;
  - Bình luận Facebook: văn bản, ảnh, video, thả like;
  - Zalo: văn bản, ảnh, file, thả cảm xúc, trích dẫn, yêu cầu thông tin, tin giao dịch, tin truyền thông;
  - LiveTalk: các loại trên + menu;
  - Telegram: menu nút;
  - Viber: đường dẫn, liên lạc, thẻ.

  Phân nhánh theo từ khoá, nút bấm (mỗi nút là một nhánh), hoặc AI phân tích câu trả lời. Có phần thu thập thông tin từ câu trả lời của khách.

## 7. Dựng nhanh bằng dán JSON (clipboard của editor)
Editor cho phép **dán JSON nút trực tiếp vào canvas** (tài liệu OMI dùng cách này để chia sẻ nút mẫu). Định dạng clipboard là **định dạng editor** (camelCase), khác JSON lưu qua API (snake_case):
```json
{"datas":[{"id":"<nodeId>","name":"Lấy link chơi game","type":"ACTION",
  "actions":[{"id":"<a>","type":"CREATE_CUSTOM_VARIABLE","datas":{
     "typeVar":"api","url":"https://<api>","method":"POST","customTimeout":60,
     "listVariable":[{"id":"<i>","key":"partner_user_id","value":"{{social_zalo_user_id}}"}],
     "headers":[{"id":"<h>","key":"Authorization","value":"<token>"}],
     "multiVariables":[{"id":"<m>","fieldCode":"<code10>","fieldName":"game_url","shorthandQuery":"data.game_url","wholeResponse":false,
        "query":[{"id":"<q>","value":"data","type":{"label":"Value","value":"object"}},{"id":"<q>","value":"game_url","type":{"label":"Value","value":"object"}}]}]},
   "objVariables":{}}],
  "handlers":{"SOURCE":{"id":"1","type":"target","position":"left"},"NEXT_STEP":{"id":"2","type":"source","position":"right"}},
  "variables":[{"variable":"social_zalo_user_id","selected":null}],
  "relatedPosition":{"ticket":null,"contact":null,"call_transaction":null,"conv":null},
  "pos":{"x":1900,"y":640,"h":204}}],
 "isRflow":true,"feature":"campaign","tenantId":"<tenant_id>"}
```
Dùng khi: API lưu flow chưa kiểm chứng cho tenant, hoặc muốn dựng từng cụm nút rồi để người dùng xem trước khi bấm Xuất bản. Cách làm: tạo JSON → đưa vào clipboard → bấm vào canvas → Ctrl+V → kiểm tra → lưu. Chú ý `relatedPosition` = vị trí đối tượng (mục 1). Sao chép một nút có sẵn trên canvas (Ctrl+C) là cách nhanh nhất để xem đúng định dạng của từng loại nút.

## 8. Nguồn sự kiện ngoài OMI
- **Google Sheet → OMIFlow**: App Script gắn thư viện của OMI, kích hoạt khi sửa sheet, POST vào URL trigger API. Cấu hình: `url`, `sheetName`, `triggerRange` (ví dụ `D2:D`), `triggerCol`, `trigerVal`, `compareOperator` (`=`, `!=`, `>`, `contain`, `start_with`…). Body nhận được: `data:[{col,value}]`, `current_row`, `last_row`, `action` (insert hoặc update), `execute_time`, `sheet_name`, `spread_sheet_name`.
- **Thiết bị hoặc phần mềm có webhook** (chấm công, POS, game marketing…): dùng Đối tác tự định nghĩa (tái sử dụng thuộc tính cho nhiều flow) hoặc trigger API.
