# OMIFlow Webhook — Mẫu cURL và response

URL kích hoạt trigger API: `https://external-v1-stg.omicrm.com/api/campaign/webhook/{kick_off.id}`. Lấy `kick_off.id` bằng GET flow; id/URL đổi khi nào: `api-reference.md` mục *Ba loại id và URL webhook*. Tên trường body lấy từ cột "Điều kiện kích hoạt" ở danh sách flow hoặc `multi_variables[]` (GET), không đoán.

## Mẫu 1: tạo khách nếu chưa có [đã chạy]

Biến trigger (tên do người dựng đặt): `so_dien_thoai_khach`, `ten_khach_da_kenh`.

```bash
curl -X POST 'https://external-v1-stg.omicrm.com/api/campaign/webhook/{kick_off.id}' \
  -H 'Content-Type: application/json' \
  -d '{"so_dien_thoai_khach": "<so_dien_thoai>", "ten_khach_da_kenh": "Test KH Mới"}'
```

Response mặc định (body cố định của `response_config`; `status_code` 9999 trong body không phải HTTP status):
```json
{"message": "success", "status_code": 9999}
```

Cấu trúc flow:
1. Trigger API (POST) nhận 2 biến từ body.
2. Điều kiện: Đa kênh → Số điện thoại = `{{so_dien_thoai_khach}}` (xác định khách theo SĐT).
3. Điều kiện: Kiểm tra khách hàng tồn tại. Nhánh "Đã tồn tại" → hết flow. Nhánh "Bước tiếp theo" (chưa có) → Hành động "Thêm khách hàng": Tên đầy đủ = `{{ten_khach_da_kenh}}`, Số điện thoại = `{{so_dien_thoai_khach}}`, phân bổ cho nhân viên cụ thể.

## Trả dữ liệu động cho bên gọi [suy luận]

`response_config` là body cố định, không chèn được dữ liệu tra cứu. Trả dữ liệu động dùng hành động "Trả kết quả qua API" (`SEND_RESPONSE_WEBHOOK_API`, schema chưa kiểm chứng: dựng thử một lần trên UI rồi GET — `node-catalog.md` mục 1a). Khung: trigger API nhận SĐT → xác định khách → `SEND_RESPONSE_WEBHOOK_API` trả body chèn `{{...}}`. Mẫu thiết kế: `design-patterns.md` mục C (dòng "Chatbot hoặc callbot cần tra CRM").

## Kiểm flow có chạy
1. Gọi cURL, kiểm HTTP 200.
2. OMIFlow → mở flow → tab **Lịch sử**: mỗi lượt một dòng, xem từng nút.
3. Kiểm kết quả nghiệp vụ (khách vừa tạo: `get_contact_by_phone`, hoặc mở hồ sơ khách).

Khi cURL lỗi: lấy lại URL từ GET `kick_off.id` trước tiên. Ý nghĩa từng mã HTTP (404, 401/403, 500) và cách sửa: Cần xác nhận. Body trả `status_code` 9999 = body cố định của `response_config`, không phải dữ liệu tra cứu.
