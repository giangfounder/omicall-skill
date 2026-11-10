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
