# OMICall Public API — Contact endpoints

Docs gốc: https://api.omicall.com/omicall-api/khach-hang

Base URL thật (docs `llms-full.txt`, mục Tổng quan): **`https://public-v1-stg.omicall.com`** (alias `public-v1-stg.omicrm.com` cũng phản hồi). `api.omicall.com` CHỈ là trang tài liệu, KHÔNG gọi API vào đó.
Auth: `GET {base}/api/auth?apiKey=<API_KEY>` → `payload.access_token` (Bearer, **hết hạn 24h**). API Key: OMICRM → Cấu hình → Tích hợp → Quản lý API. Header: `Authorization: Bearer <access_token>`. Sai token → body `Error Occurred!!!`.
Full docs dạng text: `https://api.omicall.com/llms-full.txt`.

Response chung: `{"status_code": 9999, "payload": ...}` — `status_code: 9999` = success. HTTP status luôn 200 nếu request được nhận.

## POST /api/v2/contact/search — Tìm KH (dùng nhất cho chatbot)

Query params:
- `page` (default 1)
- `size` (default 50) — chatbot cần 1 KH thì set `size=1`

Body raw JSON:
```json
{
  "keyword": "<so_dien_thoai>",
  "tags": ["VIP"],
  "business": ["..."],
  "categories": ["..."],
  "ranges": {"from": "...", "to": "..."},
  "includeIds": ["..."],
  "excludeIds": ["..."],
  "filterContactIds": ["..."]
}
```

`keyword` chấp nhận SĐT / email / họ tên. Chỉ cần `keyword`, các field khác optional.

Response (minh hoạ có chú thích `//` và `...`, không phải JSON hợp lệ):
```jsonc
{
  "status_code": 9999,
  "payload": {"total_items": 1, "items": [   // ⚠ docs thật: payload là object phân trang, KH nằm ở payload.items[]
    {
      "_id": "...",
      "fullName": "...",
      "phones": [{"data": "<so_dien_thoai>", "type": "personal"}],
      "emails": [...],
      "address": "...",
      "attribute_structure": {   // Cần xác nhận: object hay mảng — xem ghi chú ngay dưới khối này
        "field_ma_tuy_chinh_1": "value",
        "field_ma_tuy_chinh_2": "value",
        ...
      },
      "tags": [...],
      "business": [...],
      "categories": [...]
    }
  ]
}
```

⚠ **Cần xác nhận** dạng `attribute_structure`: ví dụ trên ghi dạng object, còn theo docs thật là **MẢNG** `[{field_code, field_type, value:[{display_value,data_type,value_type}]}]` (field_code: full_name, gender, phone_number, mail, address, job_title, note, ...). Chưa có lần gọi thật nào trong skill chốt dạng nào — gọi thử một lần với khách mẫu rồi ghi lại tại đây. `attribute_structure` chứa **toàn bộ** thuộc tính KH bao gồm custom attributes theo cấu hình tenant.

### cURL mẫu
```bash
curl -X POST "https://public-v1-stg.omicall.com/api/v2/contact/search?page=1&size=1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"keyword": "<so_dien_thoai>"}'
```

### Cấu hình trong chatbot "Truy vấn" (Ngữ cảnh bắt đầu)
- **Tên truy vấn**: "Lấy data KH từ CRM"
- **Hướng dẫn BOT**: "Gọi ở lượt đầu tiên để lấy hồ sơ KH đầy đủ thuộc tính. Dùng SĐT khách đã link từ kênh chat."
- **Cấu hình**:
  - Method: POST
  - URL: `https://public-v1-stg.omicall.com/api/v2/contact/search?page=1&size=1`
  - Request Headers: `Authorization: Bearer <TOKEN>` (thêm qua nút + Key-Value)
  - Body Type: raw
  - Body:
    ```json
    {
      "keyword": "{{social_phone_number_linked}}"
    }
    ```
- **Hướng dẫn BOT lấy kết quả**: mô tả schema `payload.items[0].attribute_structure[] (field_code → value[0].display_value)` và cách xử lý khi `payload` rỗng.

## POST /api/v2/contact/add — Tạo mới KH

Body required:
- `refId` (string): mã tham chiếu duy nhất
- `fullName` (string)
- `phones` (array): `[{"data": "0989...", "type": "personal", "valueType": "Cá nhân"}]`

Optional: `tags`, `business`, `categories`, `userOwnerEmail`, `gender`, `passport`, `jobTitle`, `address`, `emails`, `filterContacts`, ...

Response: `{"status_code": 9999, "payload": true/false}`

### cURL
```bash
curl -X POST https://public-v1-stg.omicall.com/api/v2/contact/add \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "refId": "CUST001",
    "fullName": "Nguyen Van A",
    "phones": [{"data": "<so_dien_thoai>", "type": "personal", "valueType": "Cá nhân"}]
  }'
```

## GET /api/v2/contact/get/:id — Chi tiết KH theo ID

Nhanh hơn search khi đã có contact_id. Response schema giống 1 phần tử trong `payload` của search.

## POST /api/v2/contact/update — Cập nhật KH

Body: `refId` HOẶC `_id` (để identify) + các field cần update. Đặc biệt:
- `tagRemoves`, `businessRemoves`, `categoriesRemoves`: xóa các tag/business/category cụ thể.
- `otherDynamicUpdates`: cập nhật custom attributes (key-value dạng object).

### cURL
```bash
curl -X POST https://public-v1-stg.omicall.com/api/v2/contact/update \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "_id": "contact_id_here",
    "otherDynamicUpdates": {
      "<ma_thuoc_tinh_1>": "<giá trị>",
      "<ma_thuoc_tinh_2>": "Có"
    }
  }'
```

## POST /api/v2/contact/addMany — Batch create

Body: `{"data": [<contact_object>, ...]}` — mỗi object cùng schema với `/contact/add`. Dùng khi import KH từ Excel.

## DELETE /api/contacts/delete/:id — Xóa KH
Cần xác nhận user trước khi gọi (không hoàn tác).

## POST /api/contacts/add-note — Thêm note interaction
Body: `{"note_by": "email@x.com", "content": "note text", "phone": "0989..."}` — thêm interaction note cho KH theo SĐT.

## GET /api/v2/contact/layout/list — Danh sách custom attribute definitions
Trả về cấu trúc custom fields của tenant — dùng khi cần biết trước có những field nào để mapping.

## GET /api/v2/contact/filterContact/list — Danh sách customer status pipelines

## POST /api/v3/agent/contact/transfer — Chuyển ownership Contact giữa agent
Header: `x-api-key` (khác Bearer). Body: `sourceEmail*`, `targetEmail*`, `previewChanges` (bool), `callbackResultConfig` (optional webhook). Async — trả `requestId`.

## Gotchas
- **`status_code: 9999` không phải HTTP status**. HTTP luôn 200 nếu request nhận được. Check field `status_code` trong body. Ngoại lệ đã gặp: dùng API Key trần làm Bearer cho `/api/v2/contact/search` nhận **HTTP 401** (api-reference.md mục "Diagnostic checks") → kiểm cả HTTP status lẫn `status_code`.
- **API Token khác JWT session**: JWT phiên đăng nhập chỉ dùng cho chatbot-gateway (internal). Public API (`https://public-v1-stg.omicall.com`; `api.omicall.com` chỉ là trang docs) cần access token đổi từ API Key của tenant (Cấu hình → Tích hợp → Quản lý API), hết hạn 24h.
- **`keyword` search khớp SĐT ở nhiều dạng**: `0989...`, `+84989...`, `84989...` — search thường trả kết quả cho cả 3.
- **`size=1` khi chatbot dùng**: chỉ cần 1 KH khớp, không cần phân trang.
- **Custom attributes trong `attribute_structure`**: field name = mã trường (không phải tên hiển thị) — dùng đúng mã đã cấu hình khi tạo attribute.
