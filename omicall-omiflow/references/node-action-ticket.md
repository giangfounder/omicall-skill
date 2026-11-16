# OMIFlow — Hành động tạo phiếu ghi ADD_TICKET (3.1)

Tách nguyên văn từ `node-catalog.md` (mục lục và bảng mã ở đó). Số mục giữ như cũ.

### 3.1 ADD_TICKET [verify JSON]
```json
{"type":"ADD_TICKET","data":{
  "ticket_detail":{"name":"ĐĂNG KÝ MỚI - {{<tenVar>}} - {{<sdtVar>}}",
    "ticket_category_id":"<categoryId>","priority":"from_topic","tags":["<tagId>"],
    "description":"<HTML được phép>","is_not_draft":true,"source":"crud",
    "assignee_config":{"sale_allocation_type":"allocate_according_to_configuration","sale_allocation_ids":["<allocId>"],
       "priority_option":{"agent_join_conv":true,"agent_of_call":true},"assign_criteria":{}}},
  "created_by":{"option":"SYSTEM"}}}
```
- `created_by.option`: `SYSTEM` hoặc `CAMPAIGN_CALLBOT_CREATOR` (người tạo = người phụ trách chiến dịch callbot).
- `priority_option`: ưu tiên nhân viên đã nghe cuộc gọi hoặc đang ở hội thoại, rồi mới đến cấu hình phân bổ.
- Phiếu vừa tạo trở thành **đối tượng phiếu ghi** của luồng: các hành động `ASSIGN_TICKET_*` sau đó áp lên phiếu này.
- ✔ GET 11/2026 (dựng UI, flow trigger API) — **giao nhân viên cụ thể + thuộc tính phiếu ngay trong ADD_TICKET** (không cần nút `ASSIGN_TICKET_ATTRIBUTE_STRUCTURE` riêng):
```json
{"ticket_detail":{"name":"<tiêu đề {{mã_biến}}>","ticket_category_id":"<categoryId>","priority":"from_topic",
  "assignee_config":{"use_topic_config":false,"sale_allocation_type":"specific_allocation",
     "sale_allocation_ids":["<contact_id nhân viên>"],"priority_option":{"agent_join_conv":false,"contact_owner":false,"agent_of_call":false}},
  "assignee_contact_ids":["<contact_id nhân viên>"],"user_id":"<user id nhân viên>","user_name":"<tên>",
  "attribute_structure":[
    {"attribute_id":"<id thuộc tính>","field_code":"<mã>","field_type":"single_text","data_format":{"type":"text"},
     "value":[{"display_value":"{{<mã biến>}}","value_type":"","data_type":"","value_id":"<id>"}]},
    {"attribute_id":"<id>","field_code":"<mã>","field_type":"multi_text",
     "value":[{"display_value":"<div ...>{{<mã biến>}}</div>","value_type":"","data_type":"","value_id":"<id>"}]}],
  "description":"<HTML>","is_not_draft":true,"source":"crud","current_status":0},
 "created_by":{"option":"SYSTEM"}}
```
  UI "Nhân viên cụ thể" lưu thành `specific_allocation` với **contact_id** nhân viên (không phải user id). Mỗi thuộc tính phiếu thêm bằng "Thêm thuộc tính" ở cuối ngăn; ô để trống vẫn lưu `display_value:""`. Thuộc tính `multi_text` lưu HTML bọc `<div>`. Giá trị cố định gõ thẳng chữ được. Kiểm sau lưu: duyệt `attribute_structure[]` theo `field_code`, ô nào `display_value` rỗng là chưa gán.

**Mô tả phiếu dạng thẻ HTML/CSS (✔ 11/2026, phiếu thật hiển thị đúng)**
- `ticket_detail.description` nhận HTML có **CSS inline**: `<div style="border:2px solid #..;border-radius:10px">`, thanh tiêu đề `background:#..;color:#fff`, `<table>` hai cột nhãn/giá trị, `<span>` dạng huy hiệu. Trang chi tiết phiếu và trình soạn mô tả đều hiển thị đúng (bảng có thể được thêm viền mặc định). Dùng mã thực thể HTML cho tiếng Việt/emoji nếu ghi qua API cho chắc.
- **HTML nằm trong GIÁ TRỊ biến bị lọc** (`<b>`, `<br>`, `\n` đều mất, chữ dính liền) → HTML phải nằm ở mẫu; nguồn gửi (bot, API ngoài) chỉ gửi dữ liệu thô, mỗi thông tin một biến webhook (ví dụ `n1..n4` nhãn, `v1..v4` giá trị).
- Muốn mỗi loại yêu cầu một mẫu (đơn hàng / khiếu nại): nguồn gửi thêm biến `type`; flow: trigger → CONDITION `CUSTOM_VARIABLE type = <giá trị>` (`node-condition.md` mục 2.1) → mỗi nhánh một ADD_TICKET với tiêu đề/mẫu riêng (nhãn cố định, không có dòng trống). Đưa giá trị màu qua biến vào thuộc tính `style` cũng chạy nhưng kém sạch hơn.
- Sửa mô tả trên UI: ô Mô tả là trình soạn rich text; gõ Enter tạo `<div>` mới mỗi dòng; Ctrl+A rồi gõ để thay toàn bộ.

**Gắn đối tượng vào phiếu vừa tạo — `ASSIGN_TICKET_PIN_OBJECT`** (✔ GET 11/2026 với cuộc gọi; hội thoại: đã lưu và xuất bản, giá trị mã hội thoại **Cần xác nhận**)
- Runtime (đặt ngay sau ADD_TICKET trong cùng nút ACTION): `{"type":"ASSIGN_TICKET_PIN_OBJECT","data":{"fix_attribute":{"pin_info":[{"action":"add","ref_type":"<call_transaction|social|contact|agent|ticket>","ref_id":"{{<mã biến>}}"}],"pin_all":{"<ref_type>":true}}}}`. Cuộc gọi: `ref_type:"call_transaction"`, `ref_id:"{{ct_transaction_id}}"`.
- Editor: phần tử `type:"UPDATE_INFO_TICKET"` trong `name_mappings[].actions`, `datas.assign[0]` `value:"ticket_attachment_object"`, `values.selectOpt` = `{"label":"social","value":"social"}` (hoặc `callHistory`/`call_transaction`), `values.content` = `{{mã biến}}`. Chép nguyên phần tử từ một flow có sẵn rồi đổi `selectOpt` và `content`. Editor hiển thị "Cập nhật phiếu ghi – Đối tượng đính kèm".
- Gắn hội thoại từ chatbot: biến Đa kênh của bot có `{{social_id}}`, `{{social_session_id}}`; biến nào là mã hội thoại (log bot: `data.target_value` khi `target_type:"SOCIAL_CONVERSATION"`): Cần xác nhận bằng một lượt chat thật rồi đối chiếu log flow.
