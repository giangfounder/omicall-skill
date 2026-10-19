# OMIFlow — API & schema flow

Base: `https://campaign-v1-stg.omicrm.com` (môi trường stg; bản production đổi domain tương ứng). Header `Authorization: Bearer <token>`. Token lấy theo mục *Đăng nhập* trong `SKILL.md` (cookie `{domain}_omicrm_io` → key `"2"`).

## Endpoint
| Method | Path | Mục đích | Đã thử |
|---|---|---|---|
| POST | `/omi_v2/campaign/search?page=1&size=50` body `{}` | Danh sách flow (`payload.items[]`). GET trả `invalid_param` | ✔ đọc |
| GET | `/omi_v2/campaign/get/{id}` | Chi tiết flow (nodes, edges, biến) | ✔ đọc |
| GET | `/omi_v2/campaign/get_by_uuid/{uuid}` · `/omi_v2/campaign/draft/get_by_uuid/{uuid}` | Theo uuid, bản nháp | mã UI |
| POST | `/omi_v2/campaign/add_v2` | Tạo flow mới — multipart field `file` = JSON | mã UI, chưa chạy |
| POST | `/omi_v2/campaign/update_v2/{id}` | Cập nhật (tạo phiên bản mới) — multipart `file` | mã UI, chưa chạy |
| POST | `/omi_v2/campaign/save_draft_v2` | Lưu nháp — multipart `file` | mã UI, chưa chạy |
| GET | `/campaign/update_status/{id}?status=<...>` | Bật hoặc tắt flow | mã UI |
| POST | `/omi_v2/campaign/delete/{id}` · `/omi_v2/campaign/delete_many` | Xoá | mã UI — chỉ khi user yêu cầu |
| GET | `/omi_v2/campaign/search_version` | Lịch sử phiên bản | mã UI |
| — | `/omi_v2/campaign/log/search`, `/log/route`, `/log/count_failure/{uuid}`, `/log/warning_fail`, `/action_error/retry`, `/delay_action/continue` | Lịch sử chạy, lỗi, chạy lại, tiếp tục nút Delay | mã UI |
| — | `/omi_v2/campaign/start/by/excel` | Kích hoạt bằng Excel | mã UI |
| — | `/omi_v2/campaign_node_template/search` | Kho nút đã lưu | mã UI |
| — | `report-v1-stg.omicrm.com/omi_v2/campaign/report_*` | Báo cáo (theo nút, hành động, phân loại, chi phí, webhook…) | mã UI |
| POST | `https://external-v1-stg.omicrm.com/api/campaign/webhook/{web_hook_id}` | URL kích hoạt của trigger WEB_HOOK | ✔ (skill cũ) |

Mã UI lưu flow (trích nguyên ý): `url = campaign + "omi_v2/campaign/" + (isEdit ? "update_v2/"+id : "add_v2")`; nháp → `save_draft_v2`; `FormData.append("file", <JSON blob>)`. Giống callbot: dùng Python `requests` với `files={'file': ('blob', json_bytes, 'application/json')}`.

## Đối tượng flow (top-level, rút từ GET)
```
_id, uuid, tenant_id, version, is_newest_version, is_publish, is_draft, last_publish_time,
name, description (HTML), tags, start_date, end_date, status, is_active, is_pause, is_stopped,
kick_off {event: WEB_HOOK|GENERAL|..., id: <web_hook_id>|null}, kick_off_ids [],
iteration_config {is_limit, number_of_times, time_range, apply_for_branch, unit, value, reset_date, reset_hour},
dependent_config {is_dependent, ids},           # "Phụ thuộc Flow khác" (đích của START_OTHER_CAMPAIGN)
nodes [], edges {connections: []},
variables [{name:<code10>, type: CUSTOM|COLLECT_INFO|..., is_dynamic_attribute}],
custom_variables [{name, field_code}], collect_variables, variables_with_order,
name_mappings, classifies, sale_allocations, upload_files, template_id, public_key, credit_pricing, ...
```
- `iteration_config.is_limit:true, number_of_times:2`: một đối tượng chỉ đi qua flow tối đa 2 lần (chống lặp, chống spam).
- Quota: số flow trên gói ("Thêm mới 11/20"), số nút mỗi flow ("Số lượng nút 16/20").

## Node và nhánh — DUAL (giống callbot)
Mỗi liên kết lưu **2 nơi**: trong node (`next_nodes` / `conditions[].next_nodes` / `success_next_nodes` / `fail_next_nodes`) **và** trong `edges.connections`.

| Nguồn | Field trong node | `sourceHandle` của edge |
|---|---|---|
| Trường hợp của CONDITION (kể cả trigger) | `conditions[i].next_nodes:[id]` | `<case id>` |
| "Bước tiếp theo" (else của CONDITION, hoặc nối tiếp của ACTION/DELAY/…) | `next_nodes:[id]` | `"2"` |
| Thành công của hành động (FORM_DIALOG hoàn thành, GET_RELATED tìm thấy…) | `success_next_nodes:"<id>"` (**chuỗi**, không phải mảng) | `"success_action_step"` |
| Thất bại | `fail_next_nodes:"<id>"` | `"fail_action_step"` |

Edge mẫu [verify JSON]:
```json
{"id":"reactflow__edge-<src><sourceHandle>-<tgt>1","source":"<src>","sourceHandle":"<caseId|2|success_action_step>",
 "target":"<tgt>","targetHandle":"1","type":"custom","animated":false,"hidden":false,"data":{},
 "style":{"stroke":"#1e3150","strokeWidth":3},
 "markerEnd":{"type":"arrowclosed","color":"#1e3150","width":10,"height":10,"strokeWidth":1}}
```
`collapse_obj` của CONDITION có một khoá cho mỗi case id và `"NEXT_STEP"`.

## Lưu flow (khung Python — CHƯA chạy thật, verify lần đầu trên flow nháp)
```python
import requests, json
B='https://campaign-v1-stg.omicrm.com/omi_v2/campaign/'
H={'Authorization':'Bearer '+tok}
def save(flow, flow_id=None, draft=False):
    url = B+('save_draft_v2' if draft else (f'update_v2/{flow_id}' if flow_id else 'add_v2'))
    r = requests.post(url, headers=H, files={'file':('blob', json.dumps(flow, ensure_ascii=False).encode(), 'application/json')}, timeout=120)
    return r.json()
```
An toàn: muốn sửa flow đang chạy của khách thì **GET → sao chép → sửa → lưu nháp hoặc tạo flow mới tắt sẵn**, chỉ cập nhật bản đang chạy khi user đồng ý. Không xoá và không tắt flow của khách nếu user không yêu cầu.

## Checklist kiểm tra sau khi lưu (GET lại)
1. Có đúng 1 node `is_first_node:true`, `node_type:"CONDITION"`, `conditions[0].type` = loại trigger; `kick_off.event` khớp.
2. Mọi id trong `next_nodes` / `conditions[].next_nodes` / `success_next_nodes` tồn tại trong `nodes`, và có edge tương ứng với `sourceHandle` đúng bảng trên.
3. Mọi `{{code}}` trong văn bản (tên phiếu, body API, prompt, popup) được khai báo: trigger `multi_variables`, `custom_variables`, biến thu thập, hoặc biến hệ thống. UI không còn cảnh báo "biến liên kết có vấn đề".
4. CONDITION so sánh với giá trị do AI trả về: giá trị không có khoảng trắng thừa, khớp đúng danh sách mã trong prompt.
5. Sau `ADD_TICKET` cần gắn cuộc gọi hoặc người liên quan: có `DELAY` (5–10 giây) trước `GET_RELATED` cuộc gọi (bản ghi cuộc gọi chưa có ngay).
6. Số nút ≤ quota gói; flow mới để **tắt** cho tới khi test xong.
7. Test: gọi URL webhook bằng cURL hoặc tạo sự kiện thật → tab **Lịch sử** của flow xem từng nút chạy và nhánh đã đi.
