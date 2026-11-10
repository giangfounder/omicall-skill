# Làm trên giao diện OMI mà ít chụp ảnh (chung cho mọi skill OMI)

Đọc khi một bước buộc phải làm trên giao diện (API/MCP không làm được, xem `omi-mcp.md` mục 4a). Đo 10 phiên dựng thật 10–11/2026: 1.512 ảnh, 84% cú bấm theo toạ độ (phải chụp để biết bấm đâu), ~780 lần "chờ rồi chụp", ~40% ảnh nằm ở trang danh sách chỉ để dò. Mỗi ảnh ~1.000–1.500 token và vài giây. File này cắt ba nguồn đó.

## 1. Giao thức (BẮT BUỘC, theo thứ tự)
1. **Mở thẳng bằng URL có id**, không vào trang danh sách để dò: id lấy bằng script (bảng mục 3). Trang danh sách chỉ dùng khi tạo mới.
2. **Chờ bằng mốc chữ, không bằng ảnh**: sau điều hướng hoặc bấm mở ngăn, `find "<nhãn mốc>"` (nhãn ở mục 4). Rỗng = chưa tải → `wait` 1 giây rồi `find` lại, tối đa 3 lần. Không `wait` cố định rồi chụp.
3. **Bấm theo `ref`, không theo toạ độ**: một lần `find` (hoặc `read_page` filter `interactive`) lấy ref cho cả bước, rồi **một** `browser_batch` bấm/gõ theo ref. Ref lấy trong một batch không dùng được ở thao tác sau của chính batch đó (batch viết sẵn từ đầu) → mỗi bước là 2 lệnh: tìm, rồi batch. Canvas vẽ lại hoặc trang tải lại thì ref cũ hỏng: tìm lại.
4. **Kiểm bằng chữ**: chạy đoạn JS mục 2 (chỉ đọc) để thấy ngăn/hộp thoại đang mở, giá trị từng ô, nút, thông báo lỗi, nút trên canvas. Sau khi lưu, chứng cứ là GET qua API (`flow_outline.py --save`, `script_outline.py --id`, `bot_outline.py --id`), không phải ảnh.
5. **Ảnh là bậc cuối**: chỉ khi 2–4 không trả lời được (vị trí kéo nối cạnh, bố cục canvas, danh sách chọn tự vẽ). Luôn `scale` 0.4–0.5 hoặc `zoom` vùng nhỏ. Ngân sách: **≤ 1 ảnh mỗi màn hình hoặc ngăn**; chụp tới ảnh thứ 3 trên cùng một màn hình là dấu hiệu thiếu công thức → dừng, viết công thức (mục 5) rồi làm tiếp bằng chữ.
6. **Gộp**: chuỗi đã biết (mở ngăn → gõ → chọn → Lưu lại → Xác nhận) đi trong một `browser_batch` (≤ 25 thao tác), chỉ đọc kết quả ở cuối.

Thêm hai điều (chuyển từ `omi-mcp.md` mục 4c cũ):
1. **Pane**: `resize_window` 1500x900 một lần đầu phiên (pane hẹp làm drawer bị cắt), nhớ trả `preset desktop` khi xong.
2. **Dựng ít nút nhất có thể trên UI**: mỗi loại nút một lần để lấy schema, phần còn lại sinh bằng script từ bản GET (xem `omicall-omiflow/references/node-editor-get.md`).

## 2. Đọc trạng thái giao diện bằng chữ (JS chỉ đọc)
◐ 11/2026: đã chạy đúng trên trang mẫu dựng theo lớp Ant Design và React Flow; các lớp `ant-drawer`, `ant-switch-checked`, `ant-checkbox-wrapper-checked` đã thấy trong phiên thật, còn `ant-form-item` trên form OMI: Cần xác nhận. Lần đầu dùng trên tenant thật: đối chiếu kết quả với một ảnh `scale` 0.5, khớp thì đổi dấu này thành ✔ kèm tháng. Dán nguyên vào `javascript_tool`. Không sửa trang, không đọc cookie hay storage. Trả JSON ≤ 6.000 ký tự: `layer` (tiêu đề hộp thoại/ngăn trên cùng), `fields` (nhãn = giá trị; `LỖI:` nếu ô báo lỗi), `inputs` (khi form không dùng `ant-form-item`), `buttons` (nút đang hiện, `(tắt)` nếu bị vô hiệu), `toasts` (thông báo gần nhất), `canvas` (nút React Flow: 6 ký tự cuối id + chữ trên thẻ, số cạnh).
```js
(() => {
  const vis = e => !!e && (e.offsetParent !== null || getComputedStyle(e).position === 'fixed');
  const txt = e => ((e && e.innerText) || '').replace(/\s+/g, ' ').trim();
  const out = { url: location.pathname };
  const layers = [...document.querySelectorAll('.ant-modal-wrap .ant-modal, .ant-drawer-open .ant-drawer-content, .ant-popover:not(.ant-popover-hidden), .ant-dropdown:not(.ant-dropdown-hidden)')].filter(vis);
  const top = layers[layers.length - 1];
  const root = top || document.querySelector('main') || document.body;
  out.layer = top ? (txt(top.querySelector('.ant-modal-title, .ant-drawer-title')) || top.className.split(' ')[0]) : null;
  out.fields = [...root.querySelectorAll('.ant-form-item')].filter(vis).slice(0, 40).map(fi => {
    const c = fi.querySelector('.ant-form-item-control') || fi;
    const val = [...c.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea')].map(i => i.value).filter(Boolean).join(' | ');
    const sel = [...c.querySelectorAll('.ant-select-selection-item, .ant-select-selection-item-content')].map(txt).join(', ');
    const chk = [...c.querySelectorAll('.ant-checkbox-wrapper-checked, .ant-radio-wrapper-checked, .ant-radio-button-wrapper-checked')].map(txt).join(', ');
    const sw = c.querySelector('.ant-switch') ? (c.querySelector('.ant-switch-checked') ? 'BẬT' : 'TẮT') : '';
    const err = txt(c.querySelector('.ant-form-item-explain-error'));
    return txt(fi.querySelector('.ant-form-item-label')) + ' = ' + ([val, sel, chk, sw].filter(Boolean).join(' ; ') || '(trống)') + (err ? ' | LỖI: ' + err : '');
  });
  if (!out.fields.length) out.inputs = [...root.querySelectorAll('input:not([type=hidden]), textarea')].filter(vis).slice(0, 30)
    .map(i => (i.getAttribute('placeholder') || i.getAttribute('aria-label') || i.name || i.type) + ' = ' + (i.type === 'checkbox' || i.type === 'radio' ? (i.checked ? 'chọn' : 'không') : (i.value || '(trống)')));
  out.buttons = [...root.querySelectorAll('button')].filter(vis).map(b => txt(b) + (b.disabled ? ' (tắt)' : '')).filter(s => s && s !== ' (tắt)').slice(0, 25);
  out.toasts = [...document.querySelectorAll('.ant-message-notice, .ant-notification-notice')].map(txt).filter(Boolean).slice(-3);
  const nodes = [...document.querySelectorAll('.react-flow__node')];
  if (nodes.length) out.canvas = { nodes: nodes.slice(0, 60).map(n => (n.getAttribute('data-id') || '').slice(-6) + ': ' + txt(n).slice(0, 60)), edges: document.querySelectorAll('.react-flow__edge').length };
  return JSON.stringify(out).slice(0, 6000);
})()
```
Thông báo đỏ biến mất nhanh: cài MutationObserver trước thao tác (`omicall-omiflow` `ui-build-and-test.md` mục 8).

## 3. URL thẳng (id lấy bằng script, không dò danh sách)
| Đối tượng | URL (`https://<domain>.omicrm.io` + …) | Lấy id bằng |
|---|---|---|
| Flow (sửa) | `/flow/edit/<id>` | `flow_outline.py --list` |
| Flow (tạo mới) | `/flow/create` (lưu lần đầu đổi sang `/flow/edit/<id>`) | — |
| Biểu mẫu | `/flow/form`, `/flow/form/edit/<id>` | — |
| Callbot (sửa) | `/ai/callbot/script/update/<id>` | `script_outline.py --list` hoặc `tenant_survey.py` (`callbot_scripts`) |
| Phiên gọi Callbot | `/ai/callbot/callbot-campaign/create` | — |
| Chatbot (sửa) | `/ai/bot/edit/<id>` | URL user đưa (chưa có lệnh liệt kê bot) |
| Thuộc tính Khách hàng / Phiếu ghi | `/config/attribute/customer/<tab>`, `/config/attribute/ticket/attribute` | `tenant_survey.py` |
| Bộ trạng thái khách | `/config/attribute/customer/status` | `tenant_survey.py` |
| Tương tác phím | `/config/switchboard/key-interaction/list` | `config_survey.py` |
| Quay số tự động | `/marketing/auto-call/create` | — |
Script nằm ở `<thư mục skill>/scripts/` của skill phụ trách (bảng skill trong SKILL.md, mục "Gọi skill liên quan").

## 4. Công thức theo thao tác (nhãn lấy từ các lệnh `find` đã chạy trong phiên thật 10–11/2026, chưa đi lại trọn từng chuỗi)
Nhãn là chữ hiển thị để `find`; mốc là nhãn chứng tỏ màn hình đã sẵn sàng. Nhãn lệch thì `find` theo chữ gần đúng rồi sửa dòng này (mục 5).

| Thao tác | Mốc | Chuỗi `find` → bấm theo ref | Kiểm xong |
|---|---|---|---|
| Hộp xác nhận khi lưu (flow, callbot, bot) | "Cập nhật sẽ không làm ảnh hưởng" | "Xác nhận" | `toasts` hoặc nút "Lưu lại" hết sáng; GET lại |
| Tạo vỏ flow | "Tên kịch bản" | ô "Tên kịch bản" → (Hoạt động, Không giới hạn, xoá ngày: `ui-build-and-test.md` mục 1) → thẻ trigger (Biểu mẫu (Form), Xảy ra định kỳ, Điều kiện, API, …) → "Lưu lại" → hộp "Thông tin về URL": tick, "Cập nhật" | URL thành `/flow/edit/<id>`; tiếp bằng API (`flow_outline.py --save <id>`) |
| Thêm nút trong flow | "Bước tiếp theo" | "Bước tiếp theo" → nhóm (Logic / Tương tác / Trò chuyện / Khác) → loại nút → ô trong ngăn → "Lưu lại" | JS mục 2: `canvas.nodes` có nút mới, `layer` đúng tiêu đề nút |
| Nhánh của nút Điều kiện / AI | "Thêm trường hợp" | "Thêm trường hợp" → "Trường hợp n" → điều kiện → "Lưu lại" | `fields` của ngăn |
| Callbot SmartAgent: ý định | "Ngữ cảnh bắt đầu" | "Thêm trường hợp" → "Trường hợp n" → "Biến thu thập" / "Hướng dẫn Agent" → "Cập nhật" → hộp xác nhận | `script_outline.py --id <id>` |
| Callbot: gọi API | "Dữ liệu truy vấn" | "Thêm hành động" → "Truy vấn" → "Hướng dẫn Agent lấy kết quả trả về từ API" | GET kịch bản |
| Callbot: gọi thử | "Gọi thử nghiệm" | "Gọi thử nghiệm" → "Nhập số điện thoại" (chỉ khi user đồng ý gọi) → "Đóng và lưu lại" | Lịch sử cuộc gọi qua MCP `search_calls` |
| Callbot: phiên thủ công | "Tạo phiên" | "Tạo phiên" → "Thủ công" → "Xác nhận tạo phiên" (chỉ khi user duyệt gọi) | `/ai/callbot/callbot-campaign/detail/<id>` |
| Chatbot: trường hợp gọi flow | "Ngữ cảnh bắt đầu" | "Thêm trường hợp" → "Hành động" → "Gọi đến kịch bản OMIFlow" → "Lưu lại" | `bot_outline.py --id <id>`; `validate_bot.py` X10 |
| Chatbot: trò chuyện thử | "Trò chuyện thử" | "Trò chuyện thử" → "Nhập tin nhắn" → gõ, Enter (`/end` sau mỗi lần sửa bot) | đọc câu trả lời bằng `get_page_text` |
| Thuộc tính phiếu ghi | "Bộ thuộc tính mặc định" | "Thêm thuộc tính" hoặc "Thêm mới" → ô tên ("Tối đa 256 ký tự") → kiểu trường → "Lưu lại" | `tenant_survey.py` (`attribute/get_all`) |
| Bộ trạng thái khách | "Thêm mới" | theo `omicall-crm-config` `crm-config.md` mục 1 (phân cấp) | `tenant_survey.py` |
| Tương tác phím | "Tương tác phím" | "Thêm mới" → tên ("Tối đa 48 ký tự") → phím ("[0-9] Tối đa 1 ký tự") → "Kích hoạt Webhook" | `config_survey.py` |
| Biểu mẫu | "Thêm biểu mẫu" | "Thêm biểu mẫu" → "Tên biểu mẫu" → "Thêm trường dữ liệu" → "Lưu lại" (Xuất bản = công khai: user bấm) | JS mục 2 |
| Quay số tự động | "Quay số tự động" | "Marketing" → "Quay số tự động" → "Thêm mới" | — |

Không có trong bảng: canvas kéo nối cạnh (dùng API sửa `edges` + `name_mappings`, `ui-build-and-test.md` mục 5), danh sách chọn tự vẽ (một ảnh `zoom`).

## 5. Thao tác mới chưa có công thức
Lần đầu làm: được phép tối đa 2 ảnh `scale` 0.5 để định hướng, rồi chuyển sang `find` + ref. Xong việc, thêm một dòng vào bảng mục 4 (mốc, chuỗi nhãn, cách kiểm) ở `shared/references/ui-recipes.md` của repo nguồn, không ghi tên khách hay dữ liệu thật (đoạn dưới). Lần sau không chụp lại.

**Ghi lại tri thức học bằng giao diện** (chuyển từ `omi-mcp.md` mục 4b cũ, để lần sau không chụp lại):
Ngay khi một ảnh chụp hoặc lần đọc giao diện cho ra điều skill chưa có (đường dẫn màn hình, nhãn trường, danh sách lựa chọn, quy tắc của form, endpoint thấy được, gotcha), ghi vào reference của skill phụ trách (`pbx-config.md`, `ai-insight.md`, `crm-config.md`, `ui-build-and-test.md`…) kèm nhãn `✔ UI <tháng/năm>`. Chỉ ghi năng lực nền tảng, không ghi dữ liệu khách (tên, số, id). Ghi vào repo nguồn khi user cho phép; chưa được phép thì gom vào báo cáo cuối phiên để user duyệt.
