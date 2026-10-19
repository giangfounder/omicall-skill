# OMIFlow Webhook — Mẫu cURL + Response Schema

## Mẫu 1: Flow "Tạo hồ sơ KH nếu chưa có" (tenant oanhtesting)

### URL
`https://external-v1-stg.omicrm.com/api/campaign/webhook/6ab9d2c8949dfc02813731e6-IBHxKkTczPcbaqmT8XFG`

### Trigger biến khai báo
- `so_dien_thoai_khach` — SĐT khách gửi lên (từ body)
- `ten_khach_da_kenh` — Tên khách gửi lên (từ body)

### cURL test
```bash
curl -X POST 'https://external-v1-stg.omicrm.com/api/campaign/webhook/6ab9d2c8949dfc02813731e6-IBHxKkTczPcbaqmT8XFG' \
  -H 'Content-Type: application/json' \
  -d '{
    "so_dien_thoai_khach": "0912345678",
    "ten_khach_da_kenh": "Test KH Mới"
  }'
```

### Response schema (default)
```json
{
  "message": "success",
  "status_code": 9999
}
```

### Cấu trúc flow
1. **Trigger API** (POST) nhận 2 biến từ body.
2. **Điều kiện #1**: Đa kênh → Số điện thoại = `{{so_dien_thoai_khach}}` → identify Contact theo SĐT.
3. **Điều kiện #2**: Đa kênh → Kiểm tra khách hàng tồn tại.
   - Nhánh "Đã tồn tại" → hết flow (không làm gì).
   - Nhánh "Bước tiếp theo" (chưa tồn tại) → node Hành động "Tạo mới khách hàng":
     - Tên đầy đủ = `{{ten_khach_da_kenh}}`
     - Số điện thoại = `{{so_dien_thoai_khach}}`
     - Phân bổ: Nhân viên cụ thể = TESTING_DUY

## Mẫu 2: Flow "Lấy data KH từ CRM" (TODO — chưa dựng do quota)

### Trigger biến khai báo (dự kiến)
- `so_dien_thoai_khach`

### cURL test dự kiến
```bash
curl -X POST 'https://external-v1-stg.omicrm.com/api/campaign/webhook/{tenant_id}-{token_B}' \
  -H 'Content-Type: application/json' \
  -d '{"so_dien_thoai_khach": "0912345678"}'
```

### Response schema dự kiến
```json
{
  "status_code": 200,
  "data": {
    "hotel_id": "25539435",
    "ten_khach_san": "Ha Long Hotel",
    "ly_do_lien_he": "lượng phòng bán ra giảm 20.9%",
    "co_van_de_phong": "Có",
    "muc_thieu_phong": "chua_ro",
    "hang_phong_dong": "Single With Private Bathroom",
    "co_van_de_gia": "Có",
    "chenh_lech_gia": "20.6%",
    "san_pham_de_xuat": "Private Sale",
    "muc_giam_de_xuat": "giảm thêm khoảng 10% so với giá BAR",
    "bang_gia_chat": "..."
  }
}
```

### Cấu trúc flow dự kiến
1. **Trigger API** (POST) nhận `so_dien_thoai_khach`.
2. **Điều kiện**: Đa kênh → Số điện thoại = `{{so_dien_thoai_khach}}`.
3. Trả response chèn biến `{{...}}` cho từng thuộc tính KH đã identify.

## Bài học verify webhook

### Kiểm tra flow thực sự chạy
1. Gọi cURL, kiểm tra HTTP 200.
2. Vào menu OMIFlow → click flow → tab "Lịch sử": mỗi lượt trigger có timestamp + trạng thái từng node.
3. Vào menu Khách hàng → search theo SĐT vừa test: xác nhận Contact xuất hiện đúng (nếu Flow A) hoặc data trả đúng (nếu Flow B).

### Khi cURL fail
- HTTP 404: URL sai — copy lại từ nút "Copy cURL" trong UI.
- HTTP 401/403: token trong URL hết hạn — mở lại flow → cấu hình trigger API → nút refresh URL.
- HTTP 500: flow bị lỗi nội bộ — xem log ở tab Lịch sử.
- Response `status_code: 9999`: default schema chưa custom — nếu là Flow B thì phải sửa response schema.
