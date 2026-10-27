# OMIFlow — API & schema flow

Base: `https://campaign-v1-stg.omicrm.com` (môi trường stg; bản production đổi domain tương ứng). Header `Authorization: Bearer <token>`. Token lấy bằng `scripts/omi_session.py` (phiên MCP OMI hoặc `OMI_TOKEN_FILE` do user đặt); kiểm trước bằng `scripts/omi_preflight.py --domain <domain>`. Không đọc cookie lấy token (mục *Đăng nhập* trong `SKILL.md`).

Loại nút nào đã có JSON kiểm chứng: `references/node-status.json`. Cách học schema mới: dựng 1 nút bằng UI → GET → `scripts/extract_template.py` → agent chính hoặc user duyệt.

## Endpoint
| Method | Path | Mục đích | Đã thử |
|---|---|---|---|
| POST | `/omi_v2/campaign/search?page=1&size=50` body `{}` | Danh sách flow (`payload.items[]`). GET trả `invalid_param` | ✔ đọc |
| GET | `/omi_v2/campaign/get/{id}` | Chi tiết flow (nodes, edges, biến) | ✔ đọc |
| GET | `/omi_v2/campaign/get_by_uuid/{uuid}` · `/omi_v2/campaign/draft/get_by_uuid/{uuid}` | Theo uuid, bản nháp | mã UI |
| POST | `/omi_v2/campaign/add_v2` | Tạo flow mới — multipart field `file` = JSON | mã UI, chưa chạy → không dùng |
| POST | `/omi_v2/campaign/update_v2/{id}` | Cập nhật (tạo phiên bản mới) — multipart `file` | mã UI, chưa chạy → không dùng |
| POST | `/omi_v2/campaign/save_draft_v2` | Lưu nháp — multipart `file` = toàn bộ object GET (giữ `_id`) đã sửa `nodes`/`edges`/`custom_variables`; trả `status_code` 9999 + payload | ✔ (10/2026, flow chưa xuất bản) |
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

## Node và nhánh — DUAL: nodes + edges + name_mappings
Flow lưu ba phần phải khớp nhau: `nodes[]` (runtime, snake_case), `edges.connections[]` (cạnh), `name_mappings[]` (bản editor, camelCase, nút đầu loại `BEGIN` — `node-catalog.md` mục 6). Sửa nút phải sửa cả `nodes` lẫn `name_mappings`, nếu không editor hiện "Chưa có dữ liệu"; schema chi tiết của `name_mappings` chưa có mẫu kiểm chứng (Cần xác nhận, lấy từ GET thật).

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

## Lưu flow — chỉ `save_draft_v2` trên flow nháp
Đã chạy thật (10/2026): `save_draft_v2` với toàn bộ object GET của flow nháp (giữ `_id`). `add_v2` / `update_v2` chỉ thấy trong mã UI, **chưa chạy** → script không dùng. Đường chuẩn: `scripts/omi_save.py flow payload.json --domain <domain>` (validate pre → POST → GET lại → validate post → diff; không có cờ xuất bản). Khung tối thiểu khi tự viết:
```python
import requests, json
B='https://campaign-v1-stg.omicrm.com/omi_v2/campaign/'
H={'Authorization':'Bearer '+tok}
def save_draft(flow):  # flow phải có _id của flow nháp
    r = requests.post(B+'save_draft_v2', headers=H, files={'file':('blob', json.dumps(flow, ensure_ascii=False).encode(), 'application/json')}, timeout=120)
    return r.json()
```
Flow mới: tạo vỏ trên UI để có `_id` nháp, rồi lưu nháp vào đó. Vỏ chỉ có trigger có thể lưu thất bại (trigger là nút `CONDITION`; nút Điều kiện cuối chuỗi không có nút kế tiếp làm lưu thất bại, `node-catalog.md` mục 6; validator cũng báo X3) → vỏ nên gồm trigger + ít nhất một nút Hành động; cách tối thiểu để lưu được vỏ: Cần xác nhận. (`node-catalog.md` mục 6 có ghi lưu flow mới bằng `save_draft_v2` sau khi bỏ `_id`: Cần xác nhận, script không làm.)

An toàn: muốn sửa flow đang chạy của khách thì **GET → sao chép → sửa → lưu nháp hoặc tạo flow mới chưa xuất bản**, chỉ cập nhật bản đang chạy khi user đồng ý. Không xoá và không tắt flow của khách nếu user không yêu cầu.

## Checklist kiểm tra sau khi lưu (GET lại)
Chạy tự động: `python <thư mục skill>/scripts/validate_flow.py <GET.json> --mode post --sent payload.json [--context tenant_context.json] [--quota N]` (trước khi lưu: `--mode pre`). Mã `[Cn]`/`[Xn]` dưới đây trùng mã trong output của validator.
1. **[C1]** Có đúng 1 node `is_first_node:true`, `node_type:"CONDITION"`, `conditions[0].type` = loại trigger; `kick_off.event` khớp.
2. **[C2]** Mọi id trong `next_nodes` / `conditions[].next_nodes` / `success_next_nodes` / `fail_next_nodes` tồn tại trong `nodes`, và có edge tương ứng với `sourceHandle` đúng bảng trên **[X1]** (khớp hai chiều: không thiếu edge, không thừa edge). `success_next_nodes`/`fail_next_nodes` là chuỗi, `next_nodes` là mảng **[X2]**. Không có nút mồ côi (không đi tới được từ trigger) **[X7]**.
3. **[C3]** Mọi `{{code}}` trong văn bản (tên phiếu, body API, prompt, popup) được khai báo: trigger `multi_variables`, `custom_variables`, biến thu thập, biến form, hoặc biến hệ thống; dùng **mã**, không dùng tên biến **[X4]**. UI không còn cảnh báo "biến liên kết có vấn đề".
4. **[C4]** CONDITION so sánh với giá trị do AI trả về: giá trị không có khoảng trắng thừa, khớp đúng danh sách mã trong prompt **[X5]**.
5. **[C5]** Sau `ADD_TICKET` cần gắn cuộc gọi hoặc người liên quan: có `DELAY` (5–10 giây) trước `GET_RELATED` cuộc gọi (bản ghi cuộc gọi chưa có ngay) **[X6]**.
6. **[C6]** Số nút ≤ quota gói; flow mới chỉ lưu nháp, **chưa xuất bản** cho tới khi test xong và user duyệt (giữ quy ước Hoạt động của user, `SKILL.md` Rule 3; nháp có chạy hay không: Cần xác nhận). Validator kiểm "chưa xuất bản" ở mode post (thiếu `is_publish` → WARN Cần xác nhận) và cảnh báo khi payload mode pre có `is_publish=true`; không kiểm Hoạt động/tắt.
7. **[C7]** Test: gọi URL webhook bằng cURL hoặc tạo sự kiện thật (khi user đồng ý) → tab **Lịch sử** của flow xem từng nút chạy và nhánh đã đi. Validator không thay được bước này.
8. **[X3]** Nút cuối chuỗi không phải `DELAY` hoặc `CONDITION` (lưu sẽ thất bại; kết thúc bằng nút Hành động — `node-catalog.md` mục 6).
9. **[X8]** Thuộc tính khách kiểu danh sách (`is_list` trong `tenant_context.json`) không nhận biến: rẽ nhánh theo giá trị, mỗi nhánh gán một giá trị cố định.
10. **[X9]** `name_mappings` có đủ bản editor cho các nút trong `nodes` (`node-catalog.md` mục 6); phần tử chép nguyên từ bản GET của nút cùng loại, không tự viết. Hiện chỉ WARN vì chưa có template editor kiểm chứng; không đối chiếu được id thì WARN "Cần xác nhận", không PASS.
11. **[X10]** Bản GET khớp bản đã gửi (id nút, số edge) — mode post với `--sent`.
