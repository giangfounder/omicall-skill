# Chatbot ↔ CRM: Public API và OMIFlow

Đọc khi bot cần đọc hoặc ghi dữ liệu khách hàng qua mục **Truy vấn** của Ngữ cảnh bắt đầu. File này chỉ giữ phần nối chatbot với CRM. Chọn hướng nào (Hướng B mặc định cho bot chạy thật, Hướng A chỉ thử nhanh vì token 24 giờ): `playbook.md` mục "Bot cần dữ liệu CRM — chọn hướng".

## Hướng A (chỉ thử nhanh/demo ngắn): Truy vấn gọi thẳng OMICall Public API
- Method `POST`, URL `https://public-v1-stg.omicall.com/api/v2/contact/search?page=1&size=1` (⚠ `api.omicall.com` chỉ là trang docs, KHÔNG gọi API vào đó).
- Header: `Authorization: Bearer <API_TOKEN>` — token đổi từ API Key của tenant (`GET /api/auth?apiKey=`), KHÔNG phải cookie JWT của user. Hạn token: `omicall-public-api.md` dòng Auth.
- Body raw JSON: `{"keyword": "{{social_phone_number_linked}}"}`.
- Kết quả: `payload.items[0].attribute_structure[]` — **mảng**, tra theo `field_code` → `value[0].display_value` (chi tiết và phần còn Cần xác nhận: `omicall-public-api.md` mục "POST /api/v2/contact/search"). Viết "Hướng dẫn BOT lấy kết quả" theo dạng này.
- Ưu điểm: không tốn quota OMIFlow, response chuẩn OMI. Nhược: token hết hạn, Truy vấn tĩnh không tự làm mới; cần user cung cấp API Key.
- Endpoint khác (contact/add, update, get, layout/list…), cURL: `omicall-public-api.md`. Response chung `{"status_code": 9999, "payload": ...}` — 9999 = thành công (không phải HTTP status).

## Hướng B (mặc định cho bot chạy thật): Truy vấn trỏ webhook OMIFlow
Dựng flow (trigger WEB_HOOK, điều kiện "Kiểm tra khách hàng tồn tại", thêm/cập nhật khách, trả kết quả, mẫu 2 flow tạo/đọc khách, test bằng cURL, kéo nối cạnh): skill **`omicall-omiflow`** (`webhook-examples.md`, `node-catalog.md`, `design-patterns.md`). Không chép lại ở đây.

## Nguyên tắc chung
- **Đối chiếu tự động dùng field "Số điện thoại" CHUẨN của khách hàng** (không phải thuộc tính tùy chỉnh). Khi import hồ sơ, đặt SĐT thật vào field chuẩn.
- **Quota Flow theo gói**: Trial thường chỉ 1 flow — gộp việc đọc/tạo khách vào 1 flow.
- **Không tự đoán API token**: hỏi user, không tự trích xuất từ cookie/session (bị chặn bởi safety).
- Test webhook bằng cURL (theo skill `omicall-omiflow`) cho tới khi đúng schema rồi mới nối vào chatbot — tránh debug lồng nhau.

## Cấu hình Truy vấn chatbot trỏ OMIFlow
Trong drawer Ngữ cảnh bắt đầu → tab "Truy vấn" → nút "+" → điền:
- **Tên truy vấn** (bắt buộc): tên ngắn để LLM hiểu mục đích.
- **Hướng dẫn BOT** (bắt buộc): mô tả khi nào bot cần gọi. Trên bản UI hiện tại bot gọi mỗi lượt bất kể mô tả — nhưng vẫn viết rõ để mai này thay đổi/audit.
- **Cấu hình truy vấn**: bấm mở drawer con → chọn GET/POST → điền URL webhook OMIFlow → Body Type = `raw` → Body JSON dùng biến `{{social_phone_number_linked}}`, `{{social_customer_name_linked}}`. **Chú ý**: editor JSON tự động thêm `{}` bao ngoài — không paste thêm `{}` gây nested. Xoá sạch trước khi type (Ctrl+A → Delete).
- **Thời gian chờ**: 60s mặc định.
- **Hướng dẫn BOT lấy kết quả về từ API** (bắt buộc): schema JSON trả về (liệt kê từng field) + cách bot xử lý khi các field trống hoặc `status_code` trong body khác 9999 (theo `omicall-public-api.md` "Response chung"; webhook OMIFlow tự cấu hình kết quả trả về thì dùng đúng giá trị đã cấu hình).
- Schema JSON của Truy vấn (`api_knowledge`): `api-reference.md` mục "API Knowledge"; dựng bằng `scripts/build_bot.py` (spec `api_knowledge`).
