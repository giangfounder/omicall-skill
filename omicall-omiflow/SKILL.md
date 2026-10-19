---
name: omicall-omiflow
description: ""
---

# OMICall OMIFlow — Workflow Builder Playbook

# Overview
**OMIFlow** là công cụ workflow tự động của OMICall/OMICRM (menu chính: OMIFlow, path `/flow/list`). Hoạt động tương tự N8N / Zapier / Make: dựng flow có điều kiện bắt đầu (trigger) → chuỗi node xử lý (điều kiện, hành động, tin nhắn, ...) → kết quả. UI dựng bằng **React Flow** — nút dạng card kéo-thả trên canvas.

Skill này là **bộ dùng chung** cho mọi tenant/nghiệp vụ. Dùng khi:
- Cần xử lý logic tự động không phù hợp trong Chatbot/Callbot (search Contact theo attribute, tạo/cập nhật KH, tích hợp bên thứ 3, xử lý webhook).
- Chatbot/Callbot cần gọi ra ngoài để làm việc CRM (chatbot không tự search được → phải qua OMIFlow API trigger).
- Marketing/CSKH tự động theo lịch định kỳ, biểu mẫu, hoặc sự kiện.

# Rules (BẮT BUỘC)
1. **Kiểm tra quota trước khi tạo Flow**: menu Flow → nút "Thêm mới N/M" — nếu chạm giới hạn (Trial thường 1/1), HỎI user trước (gộp/xóa cũ/nâng gói), không tự quyết.
2. **Verify sau khi lưu**: mọi thay đổi Flow phải reload trang + đọc lại state qua `get_page_text` — UI có state cục bộ, không tin thấy trên màn hình nếu chưa reload.
3. **Không tự động hoá đăng nhập**: user tự nhập user/pass trong browser pane; không extract token/cookie thay user.
4. **Test webhook bằng cURL trước khi nối chatbot**: tránh debug lồng nhau (chatbot → OMIFlow → CRM).
5. **Ghi bài học mới vào skill này**: bug, gotcha, schema mới của OMIFlow — cập nhật vào `SKILL.md`.

# Cấu trúc 1 Flow

## Tab "Thông tin Flow"
- **Tên kịch bản** (bắt buộc)
- **Hoạt động / Ngưng hoạt động**: toggle bật/tắt flow.
- **Thời gian hiệu lực**: khoảng ngày flow hoạt động.
- **Mô tả** (rich text).
- **Tag** (multi-select).
- **Tùy chọn — Số lần đối tượng đi qua**: `Giới hạn` (N lần, thời gian giới hạn) / `Giới hạn theo nhánh` / `Không giới hạn` — dùng để chống loop hoặc chống spam contact.
- **Tùy chọn cách bắt đầu**: `Không phụ thuộc` (flow độc lập) / `Phụ thuộc Flow khác` (chain flows).

## Tab "Kịch bản"
Canvas React Flow chứa các node. Bắt buộc bắt đầu bằng 1 node **Điều kiện bắt đầu** (trigger). Sau đó nối các node tùy ý.

# Điều kiện bắt đầu (Trigger)

Chỉ chọn 1 lần khi tạo flow. Các loại:

## 1. Biểu mẫu (Form)
Kịch bản bắt đầu khi khách hàng hoàn thành hoặc chỉnh sửa Biểu mẫu (Form module của OMICall).

## 2. Xảy ra định kỳ
Chạy theo lịch: hàng ngày / hàng tuần / hàng tháng. Dùng cho marketing tự động, báo cáo định kỳ.

## 3. Điều kiện
Chạy khi thoả điều kiện nhất định trên dữ liệu (VD: KH có thuộc tính X = Y, hoặc đơn hàng chuyển trạng thái).

## 4. API (webhook)
Chạy khi bên thứ 3 gửi request tới URL webhook. **Đây là trigger dùng để chatbot/callbot gọi ra**.
- URL auto-generated dạng: `https://external-v1-stg.omicrm.com/api/campaign/webhook/{tenant_id}-{token}` (STG); PROD tương tự đổi domain.
- Cấu hình method: GET / POST / PUT / DELETE / PATCH.
- **Danh sách trường hợp**: cho phép nhiều case trigger (mỗi case URL khác nhau) — thường chỉ dùng 1 case "Trường hợp 1".
- **Request Headers**: ô Key-Value tùy chọn (thường bỏ trống với webhook nội bộ).
- **Khai báo biến liên kết**: khai từng biến sẽ dùng ở các node sau. Mỗi biến có:
  - Tên biến liên kết (VD `so_dien_thoai_khach`)
  - Mã trong flow tự sinh (VD `{{cX7BecmQK8}}`) — nhấn vào tên biến trong các ô nhập ở node khác sẽ chèn mã này.
  - **"Truy vấn từ Body"** (default) — parse JSON body của request, lấy field theo tên vào biến / hoặc **"Toàn bộ Body"** — cả body vào 1 biến.
  - **Điều kiện truy vấn**: với "Truy vấn từ Body", điền "Value" = tên field trong body (VD `so_dien_thoai_khach` → lấy `body.so_dien_thoai_khach` vào biến).
- **Kết quả trả về** (response schema): JSON trả cho caller khi webhook chạy thành công. Mặc định `{"message":"success","status_code":9999}`. Sửa để trả data — chèn biến `{{...}}` từ node trước để lấy giá trị KH tra được.
- **Copy cURL**: nút copy cURL mẫu để test bằng Postman/terminal.
- **Test API**: nút test ngay trong UI (nếu có).

## 5. Kích hoạt bằng File Excel
Chạy hàng loạt khi user upload Excel — mỗi hàng = 1 đối tượng đi qua flow.

## 6. Đối tác
Kịch bản kích hoạt khi nhận sự kiện hoặc Webhook từ Đối tác (integration).

## 7. Cuộc gọi đang diễn ra
Kịch bản bắt đầu khi có cuộc gọi diễn ra (Callbot integration).

# Node trên canvas

## Palette (right-click canvas → context menu)

### Nhóm Logic
- **Điều kiện**: rẽ nhánh theo giá trị của các thuộc tính.
- **Trì hoãn (Delay)**: dừng flow một khoảng thời gian.
- **Random**: rẽ nhánh ngẫu nhiên (A/B test).
- **Phân tích thông tin**: phân tích data.

### Nhóm Tương tác
- **Hành động**: tập hợp các thao tác dữ liệu (chi tiết dưới).
- **Marketing**: gửi campaign marketing.
- **Cửa sổ tương tác**: mở cửa sổ chat với nhân viên.

### Nhóm Trò chuyện (mỗi kênh 1 node)
- Tin nhắn, Bình luận, WhatsApp, Email SMTP, LiveTalk, Zalo, Telegram, Zalo cá nhân, TikTok Business, Gửi tin nhắn chung, Viber Bot, ChatGPT, ChatX, AI Chatbot, ProAI, Partner AI Chatbot.

### Nhóm Khác
- **Thu thập thông tin**: chỉ trong callbot flow (thu biến từ khách qua STT).
- **Ghi chú**: note trên canvas.

## Node "Điều kiện" — chi tiết

Cho phép định nghĩa nhiều **Trường hợp** (case). Mỗi case chứa 1 hoặc nhiều điều kiện, ghép bằng "Điều kiện VÀ" / "Điều kiện HOẶC".

### Nhóm điều kiện so sánh (5 nhóm)
- **Khách hàng**: các field chuẩn của Contact (`Tên`, `Số điện thoại`, `Email`, thuộc tính tùy chỉnh, ...).
- **Đa kênh** (106 thuộc tính): dữ liệu từ tin nhắn/session của kênh chat/social:
  - `{{social_session_id}}` — ID phiên
  - `{{social_customer_name}}` — Tên KH platform trả về
  - `{{social_customer_name_linked}}` — Tên KH đã link với Contact
  - `{{social_phone_number_linked}}` — SĐT KH đã link
  - Và nhiều field khác từ Zalo/FB/... (mở picker để xem)
- **Dữ liệu thu thập**: biến bot đã thu (từ chatbot/callbot).
- **Chat Insights**: metrics session chat.
- **Biến liên kết tùy chỉnh**: biến đã khai báo (từ trigger API hoặc "Biến liên kết tùy chỉnh" trong Hành động).
- **Nhân viên** (chỉ dùng khi flow gắn với agent): field của agent.
- **Cuộc gọi**, **Phiếu ghi**, **Voice Insights**, **AI Assistant - Cuộc gọi / Đa kênh**, **Voucher**, **Biểu mẫu**, **AI Chatbot**, **Mở rộng**, **Tùy chỉnh**: các nhóm khác.

### Phép toán
`=`, `>`, `<`, `>=`, `<=`, `!=`, `IN`, `NOT IN`, `BETWEEN`, `CONTAIN`, `NOT CONTAIN`, `STARTWITH`, `ENDWITH`, `NOTSTARTWITH`, `NOTENDWITH`.

### Value
- **Giá trị cố định**: gõ tay text/số.
- **Biến `{{...}}`**: chèn từ picker (footer drawer).
- **KHÔNG có** kiểu so khớp giá trị này với giá trị của một object khác (kiểu foreign-key JOIN) — mọi so khớp là so với đối tượng gốc / hằng / biến.

### Điều kiện đặc biệt "Kiểm tra khách hàng tồn tại"
Nằm trong nhóm **Đa kênh**. Kéo vào 1 case → chọn `Là | Không là` × `Khách hàng đã tồn tại | Khách hàng chưa tồn tại`.

**Cơ chế nội bộ**: khi flow chạy tới node có điều kiện này, hệ thống tra Contact theo giá trị field "Số điện thoại" chuẩn khớp SĐT đã được set ở **điều kiện trước đó** (thường điều kiện #1 = "Số điện thoại liên kết = biến SĐT nhận vào"). Nếu tìm được Contact → "đã tồn tại", ngược lại → "chưa tồn tại".

**Thứ tự BẮT BUỘC**: Điều kiện #1 (set SĐT) → Điều kiện #2 (kiểm tra tồn tại). Bỏ #1 thì #2 không biết tra ai.

### Handle output của Điều kiện
Mỗi case là 1 output handle riêng ở cạnh phải node. Ngoài ra có 1 handle "**Bước tiếp theo**" cuối cùng = **else** (không case nào match). Với Điều kiện "Kiểm tra tồn tại" thường:
- Case "Khách hàng đã tồn tại" → handle 1
- Bước tiếp theo (else = chưa tồn tại) → handle "Bước tiếp theo"

## Node "Hành động" — chi tiết

Palette các hành động (drawer con):
- **Thêm khách hàng**: Gán cho nhân viên cụ thể hoặc cấu hình Phân Sale.
- **Cập nhật khách hàng**: Update thuộc tính KH đã identify. Có nhóm chip "Gán mới, thay thế, chèn" / "Gỡ giá trị" / "Mở rộng" — phân biệt cách update field.
- **Tạo phiếu ghi**: dùng thuộc tính từ biểu mẫu hoặc tự định nghĩa.
- **Cập nhật phiếu ghi**: nếu phiếu đã tồn tại.
- **Tạo thông báo**: gửi thông báo tới nhân viên hoặc nhóm.
- **Tạo nhắc nhở**: reminder cho nhân viên.
- **Biến liên kết tùy chỉnh**: khai báo biến mới ở giữa flow.
- **Gán đối tượng liên quan**: thêm đối tượng liên quan đến đối tượng gốc.
- **Google Sheet**: sync sang Google Sheet đã link.
- **Cập nhật cuộc trò chuyện**: update thuộc tính conversation.
- **Cập nhật lịch sử cuộc gọi** / **Cập nhật nhân viên** / **Cập nhật Voucher**.
- **API**: gửi HTTP request đi bên ngoài (GET/POST/PUT/DELETE/PATCH — same UI như trigger API nhưng làm caller thay vì receiver).
- **Phân loại**: đánh dấu/phân loại lịch sử chiến dịch.
- **Gọi đến kịch bản khác**: kích hoạt Flow khác (chain flow).

### Node "Hành động → Thêm khách hàng" chi tiết
- **Nhân viên cụ thể** vs **Cấu hình phân bổ**: 2 mode phân agent cho KH mới.
- **Ưu tiên nhân viên thực hiện cuộc gọi** / **Ưu tiên nhân viên tiếp nhận cuộc trò chuyện**: 2 toggle.
- **Tên đầy đủ**, **Số điện thoại** (prefix +84), **Email**: 3 ô cơ bản. Click → footer hiện chip 5-7 nhóm biến → chọn chip → picker biến hiện ra → chọn biến chèn `{{...}}`.
- Có thể "**Mở rộng**" để chỉ định `Vị trí` (khi có nhiều đối tượng cùng loại đi qua flow).

### Danh sách hành động (nhiều actions trong 1 node)
1 node Hành động có thể chứa NHIỀU actions chạy tuần tự (nút "Thêm hành động"). Danh sách bên trái drawer liệt kê.

### Trạng thái hành động
Bên dưới "Danh sách hành động" có mục "**Trạng thái hành động**" — thêm nhánh xử lý riêng cho `success` / `fail` của action. Nếu không thêm, mặc định luôn đi tiếp qua "Bước tiếp theo".

### Đối tượng gốc
Node Hành động "Cập nhật khách hàng" chỉ update **đối tượng gốc đã identify** — nghĩa là Contact đã được xác định qua các Điều kiện trước đó (VD điều kiện "SĐT = biến X"). Trigger API không có sẵn đối tượng gốc → PHẢI có Điều kiện #1 set trước, hoặc dùng "Thêm khách hàng" để tạo.

## Kết nối edge

Kéo từ **output handle** (bên phải node source) đến **input handle** (bên trái node target). React Flow lưu edges tự động khi kéo thành công.

### Handle input không "hover-visible"
Trên các node Hành động, handle input bên trái **không tự hiện** khi kéo tới — do source chưa được "active" trước khi drag. Kết quả: kéo bằng chuột thường thất bại.

### Giải pháp: dispatch PointerEvent qua JS
```js
// List all handles
const handles = document.querySelectorAll('.react-flow__handle');
// Mỗi handle có dataset.handlepos (top/left/right/bottom) và dataset.handleid
// Cho Điều kiện: handleid = "1" (case 1), "2" (Bước tiếp theo = else)

// Nối từ handles[src_idx] → handles[tgt_idx]
function fire(el, type, x, y) {
  el.dispatchEvent(new PointerEvent(type, {
    bubbles: true, cancelable: true, pointerType: 'mouse', button: 0, buttons: 1,
    clientX: x, clientY: y, screenX: x, screenY: y
  }));
}
const src = handles[SRC_INDEX], tgt = handles[TGT_INDEX];
const s = src.getBoundingClientRect(), t = tgt.getBoundingClientRect();
const sx = s.x + s.width/2, sy = s.y + s.height/2;
const tx = t.x + t.width/2, ty = t.y + t.height/2;

fire(src, 'pointerdown', sx, sy);
await new Promise(r => setTimeout(r, 50));
for (let i = 1; i <= 10; i++) {
  const mx = sx + (tx - sx) * i / 10;
  const my = sy + (ty - sy) * i / 10;
  fire(document.elementFromPoint(mx, my) || document.body, 'pointermove', mx, my);
  await new Promise(r => setTimeout(r, 20));
}
fire(tgt, 'pointerup', tx, ty);
```

### List node để tìm ID
```js
document.querySelectorAll('.react-flow__node').forEach(n => {
  const r = n.getBoundingClientRect();
  console.log(n.dataset.id, r.x, r.y, n.textContent.substring(0, 40));
});
```

## Toolbar hover trên node
Khi node được select (click 1 lần vào giữa card, KHÔNG mở drawer), toolbar hover bên phải hiện:
- ➕ **Thêm nút liền kề**: mở palette để thêm node kế tiếp.
- 📋 **Sao chép**: copy node.
- 💾 **Lưu vào kho nút**: lưu node vào "Kho nút đã lưu" để tái sử dụng ở flow khác.
- 🗑️ **Xóa node**.

Selector nút xóa: `button[aria-label="Xóa node"]`.

## Kho nút đã lưu
Sidebar bên trái có nhóm "Các nút đã lưu" + "Biến liên kết đã sử dụng" + "Hướng dẫn thao tác" + "Tài liệu hướng dẫn" + "Số lượng nút N/M".
- **Các nút đã lưu**: node đã lưu qua nút 💾 — kéo thả vào canvas.
- **Số lượng nút**: quota gói (VD 4/20 = đã dùng 4/20 node).

# Kiến trúc "Chatbot gọi OMIFlow"

## Vấn đề
Chatbot OmiBot không có sẵn chức năng "search Contact by attribute". Muốn tra KH theo SĐT (từ Đa kênh) để đọc thuộc tính → phải qua OMIFlow API trigger.

## Kiến trúc chuẩn (2 flow riêng)
- **Flow A "Tạo hồ sơ KH nếu chưa có"**: Trigger API nhận SĐT + tên → Điều kiện #1 (set SĐT) → Điều kiện #2 (kiểm tra tồn tại) → nhánh else → Hành động "Tạo mới KH" (điền Tên + SĐT). Trả response `{status_code: 200}`.
- **Flow B "Lấy data KH từ CRM"**: Trigger API nhận SĐT → Điều kiện identify KH → node Hành động "Biến liên kết tùy chỉnh" hoặc lấy thẳng qua biến → cấu hình response schema chứa `{{tên_biến}}` để trả về đầy đủ thuộc tính KH.

Chatbot khai 2 "Truy vấn" trong Ngữ cảnh bắt đầu, trỏ 2 URL — mỗi lượt chat bot gọi cả 2 (Flow A idempotent, Flow B luôn trả data mới nhất).

## Kiến trúc khi quota chỉ cho 1 flow
Gộp 1 flow đa mục đích:
- Trigger API nhận SĐT + tên.
- Điều kiện #1 (set SĐT) → Điều kiện #2 (kiểm tra tồn tại).
- Nhánh "đã tồn tại" → thẳng ra response (data KH có sẵn từ đối tượng gốc).
- Nhánh "chưa tồn tại" → Hành động "Tạo mới KH" → thẳng ra response.
- Response schema thống nhất: `{status_code: 200, data: {hotel_id: {{...}}, ten_khach_san: {{...}}, ...}}`.

Nhược điểm: schema response phức tạp hơn, khó config data cho KH vừa tạo (chưa có thuộc tính nghiệp vụ). Cần lưu ý.

# Test webhook

## cURL từ terminal
```bash
curl -X POST 'https://external-v1-stg.omicrm.com/api/campaign/webhook/{tenant_id}-{token}' \
  -H 'Content-Type: application/json' \
  -d '{"so_dien_thoai_khach": "0912345678", "ten_khach_da_kenh": "Nguyen Van A"}'
```
Response mẫu: `{"message":"success","status_code":9999}` (default) hoặc schema đã cấu hình.

## Verify KH đã tạo
- Vào menu Khách hàng → tìm theo SĐT vừa test → xác nhận Contact xuất hiện với đúng Tên/SĐT.
- Xem tab "Lịch sử" của Flow → mỗi lượt trigger có log với timestamp + trạng thái từng node.

## Test API nút built-in
Trên UI trigger API có nút "Test API" (nếu tenant có tính năng này) — gõ body mẫu → chạy → xem response ngay.

# Gotchas

- **Quota Flow**: Trial 1/1. Kiểm tra ở nút "Thêm mới N/M" trước khi tạo mới. Chạm quota → hỏi user (xóa cũ / nâng gói / gộp).
- **Ô "Tên nút" append thay vì thay thế**: khi type tên mới, luôn Ctrl+A trước để clear text cũ. Không Ctrl+A → tên cũ và mới ghép lại.
- **URL webhook dài, sao chép chính xác**: dùng nút "Copy cURL" hoặc bôi đen field URL → Ctrl+C. Đừng gõ tay dễ sai.
- **Response schema mặc định `status_code: 9999` không phải HTTP status**: đây là mã trong body, HTTP status vẫn 200 nếu webhook trigger thành công. Chatbot đọc kết quả cần check field trong body, không phải HTTP status.
- **Trigger API không tự identify đối tượng gốc**: khác trigger Biểu mẫu / Xảy ra định kỳ (đã có đối tượng). Trigger API luôn cần Điều kiện identify KH trước Hành động cập nhật.
- **Đối chiếu KH dùng field "Số điện thoại" CHUẨN** — không phải thuộc tính tùy chỉnh. Khi import KH: điền SĐT thật vào ô "Số điện thoại" của Contact, không chỉ vào thuộc tính tùy chỉnh (VD `sdt_nhan_zbs`).
- **Không dùng phím Escape** trong drawer node — có thể reset state cục bộ hoặc trigger dialog "Rời trang không lưu". Dùng nút X hoặc mũi tên back trên header drawer.
- **Reload để verify** sau khi lưu: `navigate` full URL flow → `get_page_text` xác nhận node + edge vẫn còn.
- **Body JSON editor tự bọc `{}` bao ngoài**: paste raw JSON có `{}` sẽ nested. Ctrl+A → Delete rồi type mới.
- **Chain flows**: node "Gọi đến kịch bản khác" gọi Flow B từ Flow A — nhưng response Flow B KHÔNG dễ trả về Flow A gọi được response API webhook. Nếu cần response tổng hợp, thiết kế 1 flow duy nhất.

# Tài liệu tham khảo
- `references/webhook-examples.md` — mẫu cURL + response schema đã verify (tenant → thêm mẫu vào đây).
- `references/react-flow-selectors.md` — cheat-sheet DOM selectors của React Flow để thao tác qua JS.

Base directory for this skill: C:\Users\User\.agents\skills\omicall-omiflow
Relative paths in this skill are relative to this base directory.
