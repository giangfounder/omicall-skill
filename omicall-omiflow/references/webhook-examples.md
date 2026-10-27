# OMIFlow Webhook — Mẫu cURL + Response Schema

## Mẫu 1: Flow "Tạo hồ sơ KH nếu chưa có" (tenant demo)

### URL
`https://external-v1-stg.omicrm.com/api/campaign/webhook/{tenant_id}-{token}`

### Trigger biến khai báo
- `so_dien_thoai_khach` — SĐT khách gửi lên (từ body)
- `ten_khach_da_kenh` — Tên khách gửi lên (từ body)

### cURL test
```bash
curl -X POST 'https://external-v1-stg.omicrm.com/api/campaign/webhook/{tenant_id}-{token}' \
  -H 'Content-Type: application/json' \
  -d '{
    "so_dien_thoai_khach": "<so_dien_thoai>",
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
     - Phân bổ: Nhân viên cụ thể = <nhân viên phụ trách>

## Mẫu 2: Flow "Lấy data KH từ CRM" (TODO — chưa dựng do quota)

### Trigger biến khai báo (dự kiến)
- `so_dien_thoai_khach`

### cURL test dự kiến
```bash
curl -X POST 'https://external-v1-stg.omicrm.com/api/campaign/webhook/{tenant_id}-{token_B}' \
  -H 'Content-Type: application/json' \
  -d '{"so_dien_thoai_khach": "<so_dien_thoai>"}'
```

### Response schema dự kiến
**Sai nếu đặt vào `response_config`**: `response_config` của trigger API là body cố định, không chèn được dữ liệu tra cứu. Trả dữ liệu động phải dùng hành động "Trả kết quả qua API" (`SEND_RESPONSE_WEBHOOK_API`, schema chưa kiểm chứng: dựng thử một lần trên UI rồi GET — `SKILL.md` Gotchas, `node-catalog.md` mục 1a). Khối dưới chỉ là hình dạng body mong muốn:
```json
{
  "status_code": 200,
  "data": {
    "<ma_thuoc_tinh_1>": "{{<biến thuộc tính 1>}}",
    "<ma_thuoc_tinh_2>": "{{<biến thuộc tính 2>}}",
    "...": "..."
  }
}
```

### Cấu trúc flow dự kiến
1. **Trigger API** (POST) nhận `so_dien_thoai_khach`.
2. **Điều kiện**: Đa kênh → Số điện thoại = `{{so_dien_thoai_khach}}`.
3. Hành động `SEND_RESPONSE_WEBHOOK_API` trả body chèn biến `{{...}}` cho từng thuộc tính KH đã identify (chưa kiểm chứng).

## Bài học verify webhook

### Kiểm tra flow thực sự chạy
1. Gọi cURL, kiểm tra HTTP 200.
2. Vào menu OMIFlow → click flow → tab "Lịch sử": mỗi lượt trigger có timestamp + trạng thái từng node.
3. Vào menu Khách hàng → search theo SĐT vừa test: xác nhận Contact xuất hiện đúng (nếu Flow A) hoặc data trả đúng (nếu Flow B).

### Khi cURL fail
- HTTP 404: URL sai — copy lại từ nút "Copy cURL" trong UI.
- HTTP 401/403: token trong URL hết hạn — mở lại flow → cấu hình trigger API → nút refresh URL.
- HTTP 500: flow bị lỗi nội bộ — xem log ở tab Lịch sử.
- Response `status_code: 9999`: body cố định của `response_config` — nếu là Flow B thì phải thêm hành động `SEND_RESPONSE_WEBHOOK_API` (chưa kiểm chứng), sửa `response_config` không trả được dữ liệu động.
