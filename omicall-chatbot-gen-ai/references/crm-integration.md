# Chatbot ↔ CRM: Public API và OMIFlow

Đọc khi bot cần đọc hoặc ghi dữ liệu khách hàng qua mục **Truy vấn** của Ngữ cảnh bắt đầu. Dựng flow (trigger, điều kiện, node, lưu JSON) theo skill **`omicall-omiflow`**; file này chỉ giữ phần nối chatbot với CRM.

## Kiến trúc gọi API — 2 hướng

### Hướng A (khuyên dùng): Chatbot gọi thẳng OMICall Public API
OMICall có API public `POST https://public-v1-stg.omicall.com/api/v2/contact/search` (⚠ `api.omicall.com` chỉ là trang docs, KHÔNG gọi API vào đó; token lấy bằng `GET /api/auth?apiKey=`, hết hạn 24h — xem references/omicall-public-api.md) (docs: https://api.omicall.com/omicall-api/khach-hang#tim-kiem-khach-hang) — cho phép tìm Contact theo SĐT/email/tên và trả về `attribute_structure` đầy đủ (bao gồm cả custom attributes). Chatbot cấu hình 1 "Truy vấn" trỏ thẳng URL này:
- Method: POST
- URL: `https://public-v1-stg.omicall.com/api/v2/contact/search?page=1&size=1`
- Header: `Authorization: Bearer <API_TOKEN>` (token của tenant, KHÔNG phải cookie JWT của user)
- Body raw JSON: `{"keyword": "{{social_phone_number_linked}}"}`
- Response chứa `payload.items[0].attribute_structure[]` (mảng `{field_code, value[0].display_value}`) với mọi field KH → bot đọc trực tiếp để tư vấn.

**Ưu điểm**: không tốn quota OMIFlow; response chuẩn OMI, đầy đủ dữ liệu. **Nhược**: cần user cung cấp API Token (Bearer) hợp lệ — token này khác với JWT session user, thường lấy từ menu Cấu hình → API Key.

Các endpoint khác của OMICall Public API (base `https://public-v1-stg.omicall.com`):
- `POST /api/v2/contact/add` — tạo 1 KH
- `POST /api/v2/contact/addMany` — tạo nhiều KH
- `POST /api/v2/contact/search?page=&size=` — search theo keyword (SĐT/email/tên)
- `GET  /api/v2/contact/get/:id` — chi tiết KH theo id (nhanh hơn search nếu đã có contact_id)
- `POST /api/v2/contact/update` — cập nhật KH (có `otherDynamicUpdates` cho custom attributes)
- `DELETE /api/contacts/delete/:id` — xóa
- `POST /api/contacts/add-note` — thêm note interaction
- `GET  /api/v2/contact/layout/list` — danh sách attribute definitions (custom fields)
- `GET  /api/v2/contact/filterContact/list` — customer status pipelines

Response chung: `{"status_code": 9999, "payload": ...}` — status_code 9999 = success (không phải HTTP status).

### Hướng B: Chatbot gọi OMIFlow (webhook trigger)
Dùng khi cần workflow phức tạp (tạo Contact có phân bổ agent, tích hợp thêm, đa hành động...). Chi tiết trong skill **`omicall-omiflow`**. Ưu điểm: cấu hình visual, không cần code; hỗ trợ chain flow. Nhược điểm: tốn quota flow, response schema tự cấu hình.

### Khi nào dùng hướng nào
- Chỉ cần **đọc data KH** để bot tư vấn → **Hướng A** (đơn giản, 1 API call).
- Cần **tạo KH mới nếu chưa có, phân bổ agent, tích hợp Google Sheet/API bên thứ 3** → Hướng B (OMIFlow).
- **Hybrid**: dùng OMIFlow cho tạo/cập nhật (idempotent qua điều kiện Kiểm tra tồn tại), dùng OMICall Public API để đọc data — mỗi bên làm việc tối ưu của mình.

### Nguyên tắc chung
- **Đối chiếu tự động dùng field "Số điện thoại" CHUẨN của khách hàng** (không phải thuộc tính tùy chỉnh). Khi import hồ sơ, đặt SĐT thật vào field chuẩn.
- **Quota Flow theo gói**: Trial thường chỉ 1 flow — cân nhắc Hướng A trước khi tạo flow.
- **Không tự đoán API token**: hỏi user, không tự trích xuất từ cookie/session (bị chặn bởi safety).

## Kiến trúc chuẩn: 2 OMIFlow riêng (khi đủ quota)
Cho luồng "định danh + đọc data KH" từ chatbot, thiết kế đúng là **2 flow riêng biệt**, KHÔNG gộp:
- **Flow A — "Tạo hồ sơ KH nếu chưa có"**: Trigger API nhận `so_dien_thoai_khach` + `ten_khach_da_kenh` → Điều kiện #1 so SĐT → Điều kiện #2 "Kiểm tra KH tồn tại". Nhánh `else` (chưa tồn tại) → Hành động "Tạo mới khách hàng" (điền Tên = biến `ten_khach_da_kenh`, SĐT = biến `so_dien_thoai_khach`, phân bổ Nhân viên cụ thể/Cấu hình phân bố). Nhánh `đã tồn tại` không cần làm gì. Trả về `{message:"success", status_code:200}`.
- **Flow B — "Lấy data KH từ CRM"**: Trigger API nhận SĐT → tìm KH đã tồn tại (Điều kiện) → Trả về JSON body chứa toàn bộ thuộc tính KH (các mã thuộc tính bot cần, ví dụ `<ma_thuoc_tinh_1>`, `<ma_thuoc_tinh_2>`, ...). Field "Kết quả trả về" trong trigger API cho phép cấu hình JSON schema trả về, dùng biến `{{...}}` để chèn giá trị thuộc tính KH.
- **Chatbot gọi cả 2**: 2 mục "Truy vấn" riêng trong drawer "Ngữ cảnh bắt đầu" — Truy vấn #1 trỏ Flow A (chỉ tạo nếu chưa có, response không dùng), Truy vấn #2 trỏ Flow B (đọc data → bot dùng để tư vấn). Bot gọi cả 2 mỗi lượt; Flow A idempotent nhờ Điều kiện #2 tự skip khi KH đã có.
- **Tại sao không gộp 1 flow**: gộp làm response schema phức tạp hóa cho cả 2 nhánh (tồn tại + mới tạo), và Truy vấn chatbot chỉ hiểu 1 response schema cố định. Chỉ gộp khi quota gói chỉ cho 1 flow.

## OMIFlow — Trigger API chi tiết
Cấu hình trigger:
- **Method**: POST (mặc định GET, đổi sang POST khi gửi Body JSON).
- **URL** (auto-generated): copy vào cấu hình bên chatbot.
- **Request Headers**: có ô thêm Key/Value (thường không cần cho webhook nội bộ).
- **Khai báo biến liên kết**: tạo các biến (`so_dien_thoai_khach`, `ten_khach_da_kenh`, ...) — mỗi biến có mã liên kết dạng `{{cX7BecmQK8}}` tự sinh, dùng ở các node sau. Chọn **"Truy vấn từ Body"** (mặc định) để hệ thống tự parse Body request và gán vào biến theo tên khớp; hoặc **"Toàn bộ Body"** nếu muốn cả body vào 1 biến JSON.
- **Điều kiện truy vấn**: mỗi biến có 1 hàng "Value" — nhập tên field trong body (VD `so_dien_thoai_khach`) để lấy giá trị.
- **Kết quả trả về**: JSON schema webhook trả cho caller khi kích hoạt thành công. Mặc định `{"message":"success","status_code":9999}`. Sửa thành schema chứa các biến `{{...}}` khi cần trả data (như Flow B).
- **Thời gian chờ**: 60s mặc định (giới hạn thời gian OMIFlow chạy trước khi timeout).

## OMIFlow — Điều kiện chi tiết
Node "Điều kiện" có 5 nhóm điều kiện so sánh:
- **Khách hàng**: các field chuẩn của Contact (Tên, SĐT, Email, ...).
- **Đa kênh** (106 thuộc tính): `{{social_phone_number_linked}}`, `{{social_customer_name_linked}}`, `{{social_customer_name}}`, `{{social_session_id}}`, ...
- **Dữ liệu thu thập**: biến bot tự thu qua node "Thu thập thông tin".
- **Chat Insights**: metrics từ Chat Insights.
- **Biến liên kết tùy chỉnh**: biến khai báo trong trigger API hoặc "Biến liên kết tùy chỉnh" của node Hành động.

Phép toán: `=`, `>`, `<`, `>=`, `<=`, `!=`, `IN`, `NOT IN`, `BETWEEN`, `CONTAIN`, `NOT CONTAIN`, `STARTWITH`, `ENDWITH`, `NOTSTARTWITH`, `NOTENDWITH`. Value là **giá trị cố định gõ tay HOẶC dùng biến `{{...}}`** — không có nút "so khớp thuộc tính này với thuộc tính khác của contact khác".

**Điều kiện "Kiểm tra khách hàng tồn tại"** đặc biệt trong nhóm Đa kênh: 2 giá trị chọn `Là | Không là` × `Khách hàng đã tồn tại | Khách hàng chưa tồn tại`. Cơ chế: hệ thống tự tra Contact theo giá trị field "Số điện thoại" chuẩn khớp SĐT nhận từ webhook (đã set ở Điều kiện trước — thường là Điều kiện #1). Vì thế **thứ tự Điều kiện #1 (so SĐT) → Điều kiện #2 (kiểm tra tồn tại) BẮT BUỘC** — bỏ #1 thì #2 không biết tra ai.

## OMIFlow — Node Hành động "Thêm khách hàng" / "Cập nhật khách hàng"
- **Nhân viên cụ thể**: chọn 1 nhân viên (agent) sẽ được phân bổ khi tạo/cập nhật KH. Cấu hình phân bố: theo % / theo round-robin.
- **Ưu tiên nhân viên thực hiện cuộc gọi** / **Ưu tiên nhân viên tiếp nhận cuộc trò chuyện**: 2 toggle, ưu tiên phân bổ khi khớp.
- **Tên đầy đủ**, **Số điện thoại** (có prefix +84), **Email**: 3 ô input cơ bản. Click ô → footer hiện các chip "Khách hàng | Đa kênh | Dữ liệu thu thập | Biểu mẫu | Cuộc gọi | ... | Biến liên kết tùy chỉnh" — chọn chip tương ứng → picker biến hiện ra → chọn biến để chèn `{{...}}` vào ô.
- Node này chỉ update **đối tượng gốc đã identify** — không tạo KH mới nếu đã identify được KH khác (dùng "Thêm khách hàng" thay vì "Cập nhật khách hàng" khi cần tạo).

## OMIFlow — Trạng thái hành động (nhánh success/fail)
Node Hành động có mục "**Trạng thái hành động**" bên dưới "Danh sách hành động" — có thể thêm nhánh xử lý riêng cho `success` và `fail` của hành động đó. Nếu bỏ qua, mặc định đi tiếp qua "Bước tiếp theo".

## Cấu hình Truy vấn chatbot trỏ OMIFlow
Trong drawer Ngữ cảnh bắt đầu → tab "Truy vấn" → nút "+" → điền:
- **Tên truy vấn** (bắt buộc): tên ngắn để LLM hiểu mục đích.
- **Hướng dẫn BOT** (bắt buộc): mô tả khi nào bot cần gọi. Trên bản UI hiện tại bot gọi mỗi lượt bất kể mô tả — nhưng vẫn viết rõ để mai này thay đổi/audit.
- **Cấu hình truy vấn**: bấm mở drawer con → chọn GET/POST → điền URL webhook OMIFlow → Body Type = `raw` → Body JSON dùng biến `{{social_phone_number_linked}}`, `{{social_customer_name_linked}}`. **Chú ý**: editor JSON tự động thêm `{}` bao ngoài — không paste thêm `{}` gây nested. Xoá sạch trước khi type (Ctrl+A → Delete).
- **Thời gian chờ**: 60s mặc định.
- **Hướng dẫn BOT lấy kết quả về từ API** (bắt buộc): schema JSON trả về (liệt kê từng field) + cách bot xử lý khi các field trống hoặc status_code != 200.

## Test webhook OMIFlow bằng cURL trước khi nối vào chatbot
Trên trang cấu hình trigger API có nút "Test API" — nhưng cách chắc chắn là dùng cURL/Postman gửi POST tới webhook URL với body mẫu, xác nhận:
1. Response về đúng schema.
2. KH mới thực sự được tạo trong CRM (nếu Flow A) hoặc data KH trả đúng (nếu Flow B).
3. Log flow trong tab "Lịch sử" của flow hiển thị đã chạy qua các bước đúng.
Sau khi cURL pass mới nối vào chatbot — tránh debug lồng nhau.

## Kết nối edge / xóa node trong React Flow
UI OMIFlow và một số phần của Chatbot editor dựng bằng React Flow. Kéo edge từ output handle bên phải → input handle bên trái KHÔNG luôn hoạt động qua chuột (do target handle không hover-visible cho tới khi source active). Cách chắc chắn: dispatch `PointerEvent` qua JS. Nút "Xóa node" (`button[aria-label="Xóa node"]`) chỉ hiện khi node được select. Chi tiết code + selectors → xem skill **`omicall-omiflow`** (`references/react-flow-selectors.md`).
