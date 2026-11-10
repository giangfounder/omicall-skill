# OMIFlow — API & schema flow

Base: `https://campaign-v1-stg.omicrm.com` (host đã dùng thật; host production khác hay không: Cần xác nhận, chưa có bằng chứng). Header `Authorization: Bearer <token>`. Token lấy bằng `scripts/omi_session.py` (phiên MCP OMI hoặc `OMI_TOKEN_FILE` do user đặt); kiểm trước bằng `scripts/omi_preflight.py --domain <domain>`. Không đọc cookie lấy token (mục *Đăng nhập* trong `SKILL.md`).

Loại nút nào đã có JSON kiểm chứng: `references/node-status.json`. Cách học schema mới: dựng 1 nút bằng UI → GET → `scripts/extract_template.py` → agent chính hoặc user duyệt.

## Endpoint
| Method | Path | Mục đích | Đã thử |
|---|---|---|---|
| POST | `/omi_v2/campaign/search?page=1&size=50` body `{}` | Danh sách flow (`payload.items[]`). GET trả `invalid_param` | ✔ đọc |
| GET | `/omi_v2/campaign/get/{id}` | Chi tiết flow (nodes, edges, biến) | ✔ đọc |
| GET | `/omi_v2/campaign/get_by_uuid/{uuid}` · `/omi_v2/campaign/draft/get_by_uuid/{uuid}` | Theo uuid, bản nháp | mã UI |
| POST | `/omi_v2/campaign/add_v2` | Tạo flow mới — multipart field `file` = JSON | ✔ 11/2026 nhưng tạo luôn bản **ĐÃ xuất bản** → chỉ khi user duyệt (mục *Tạo flow mới bằng `add_v2`*) |
| POST | `/omi_v2/campaign/update_v2/{id}` | Cập nhật (tạo phiên bản mới) — multipart `file` | mã UI, chưa kiểm chứng → không dùng |
| POST | `/omi_v2/campaign/save_draft_v2` | Lưu nháp — multipart `file` = toàn bộ object GET (giữ `_id`) đã sửa `nodes`/`edges`/`custom_variables`; trả `status_code` 9999 + payload | ✔ (10/2026, flow chưa xuất bản) |
| GET | `/campaign/update_status/{id}?status=<...>` | Bật hoặc tắt flow | mã UI |
| POST | `/omi_v2/campaign/delete/{id}` · `/omi_v2/campaign/delete_many` | Xoá | mã UI — chỉ khi user yêu cầu |
| GET | `/omi_v2/campaign/search_version` | Lịch sử phiên bản | mã UI |
| — | `/omi_v2/campaign/log/search`, `/log/route`, `/log/count_failure/{uuid}`, `/log/warning_fail`, `/action_error/retry`, `/delay_action/continue` | Lịch sử chạy, lỗi, chạy lại, tiếp tục nút Delay. `log/search` ✔ 10/2026: `POST ?page=1&size=50` body `{}` trả mọi flow, mỗi item có `campaign_id`, `campaign_name`, `total_credit`, `credit_counts[]` (`concepts.md` mục 6a); lọc theo `campaign_id` trong body không ăn (Cần xác nhận tên trường lọc) | mã UI |
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
- `iteration_config.is_limit:true, number_of_times:2`: một đối tượng chỉ đi qua flow tối đa 2 lần (giao diện mặc định như vậy). Quy ước skill: `is_limit:false` (X11); đặt giới hạn là lệch quy ước mặc định, chỉ giữ nếu user yêu cầu.
- Quota: số flow trên gói ("Thêm mới 11/20"), số nút mỗi flow ("Số lượng nút 16/20").

## Node và nhánh — DUAL: nodes + edges + name_mappings
Flow lưu ba phần phải khớp nhau: `nodes[]` (runtime, snake_case), `edges.connections[]` (cạnh), `name_mappings[]` (bản editor, camelCase, nút đầu loại `BEGIN` — `node-editor-get.md` mục 6). Sửa nút phải sửa cả `nodes` lẫn `name_mappings`, nếu không editor hiện "Chưa có dữ liệu"; schema chi tiết của `name_mappings` chưa có mẫu kiểm chứng (Cần xác nhận, lấy từ GET thật).

Mỗi liên kết lưu **2 nơi**: trong node (`next_nodes` / `conditions[].next_nodes` / `success_next_nodes` / `fail_next_nodes`) **và** trong `edges.connections`.

| Nguồn | Field trong node | `sourceHandle` của edge |
|---|---|---|
| Trường hợp của CONDITION (kể cả trigger) | `conditions[i].next_nodes:[id]` | `<case id>` |
| "Bước tiếp theo" (else của CONDITION, hoặc nối tiếp của ACTION/DELAY/…) | `next_nodes:[id]` | `"2"` |
| Thành công của hành động (FORM_DIALOG hoàn thành, GET_RELATED tìm thấy…) | `success_next_nodes:"<id>"` (**chuỗi**, không phải mảng) | `"success_action_step"` |
| Thất bại | `fail_next_nodes:"<id>"` | `"fail_action_step"` |
| Nút AI Chatbot (`OMI_BOT_AI`): nhánh "BOT chủ động kết thúc" | `next_nodes:[id]` | id trường hợp kết thúc (= `ai_analyze.customer_not_response.id`), **không** phải `"2"` (✔ UI 10/2026; `validate_flow.py` X1 đã nhận) |

Edge mẫu [verify JSON]:
```json
{"id":"reactflow__edge-<src><sourceHandle>-<tgt>1","source":"<src>","sourceHandle":"<caseId|2|success_action_step>",
 "target":"<tgt>","targetHandle":"1","type":"custom","animated":false,"hidden":false,"data":{},
 "style":{"stroke":"#1e3150","strokeWidth":3},
 "markerEnd":{"type":"arrowclosed","color":"#1e3150","width":10,"height":10,"strokeWidth":1}}
```
`collapse_obj` của CONDITION có một khoá cho mỗi case id và `"NEXT_STEP"`.

## Lưu flow — chỉ `save_draft_v2` trên flow nháp
Đã chạy thật (10/2026): `save_draft_v2` với toàn bộ object GET của flow nháp (giữ `_id`). Script không dùng `add_v2` (✔ 11/2026 nhưng tạo luôn bản ĐÃ xuất bản, mục *Tạo flow mới bằng `add_v2`*) và `update_v2` (chưa kiểm chứng). Đường chuẩn: `scripts/omi_save.py flow payload.json --domain <domain>` (validate pre → POST → GET lại → validate post → diff; không có cờ xuất bản). Khung tối thiểu khi tự viết:
```python
import requests, json
B='https://campaign-v1-stg.omicrm.com/omi_v2/campaign/'
H={'Authorization':'Bearer '+tok}
def save_draft(flow):  # flow phải có _id của flow nháp
    r = requests.post(B+'save_draft_v2', headers=H, files={'file':('blob', json.dumps(flow, ensure_ascii=False).encode(), 'application/json')}, timeout=120)
    return r.json()
```
**Vỏ flow tối thiểu và lần "Lưu lại" đầu** (mục duy nhất; nơi khác trỏ về đây):
- Flow mới: tạo vỏ trên UI để có `_id` nháp (lưu lần đầu đổi URL sang `/flow/edit/<id>`), rồi lưu nháp vào đó bằng `omi_save.py flow`.
- Vỏ đã lưu được (✔ UI 11/2026): trigger + vài nút, kết thúc bằng nút Hành động, kể cả khi nhánh mặc định của nút Điều kiện chưa nối. Nút cuối là `CONDITION`/`DELAY` làm lưu thất bại (X3, `node-editor-get.md` mục 6). Vỏ chỉ có trigger có lưu được không: Cần xác nhận.
- Lần "Lưu lại" đầu: một lần (✔ UI 11/2026) thấy sau đó editor chỉ còn "Xuất bản", nút thêm sau không lên server; ghi chép khác (10/2026) vẫn Lưu lại nhiều lần trên flow nháp. Khi nào bị khoá: Cần xác nhận. Đường an toàn: dựng đủ nút trước lần lưu đầu, hoặc sửa tiếp bằng `omi_save.py flow` (lưu nháp vào `_id`). Agent không bấm Xuất bản để lưu.
- `node-editor-get.md` (mục 6) có ghi lưu flow mới bằng `save_draft_v2` sau khi bỏ `_id`: Cần xác nhận, script không làm.

An toàn: muốn sửa flow đang chạy của khách thì **GET → sao chép → sửa → lưu nháp hoặc tạo flow mới chưa xuất bản**, chỉ cập nhật bản đang chạy khi user đồng ý. Không xoá và không tắt flow của khách nếu user không yêu cầu.

## Checklist kiểm tra sau khi lưu (GET lại)
Chạy tự động: `python <thư mục skill>/scripts/validate_flow.py <GET.json> --mode post --sent payload.json [--context tenant_context.json] [--quota N]` (trước khi lưu: `--mode pre`). Mã `[Cn]`/`[Xn]` dưới đây trùng mã trong output của validator.
1. **[C1]** Có đúng 1 node `is_first_node:true`, `node_type:"CONDITION"`, `conditions[0].type` = loại trigger; `kick_off.event` khớp.
2. **[C2]** Mọi id trong `next_nodes` / `conditions[].next_nodes` / `success_next_nodes` / `fail_next_nodes` tồn tại trong `nodes`, và có edge tương ứng với `sourceHandle` đúng bảng trên **[X1]** (khớp hai chiều: không thiếu edge, không thừa edge). `success_next_nodes`/`fail_next_nodes` là chuỗi, `next_nodes` là mảng **[X2]**. Không có nút mồ côi (không đi tới được từ trigger) **[X7]**.
3. **[C3]** Mọi `{{code}}` trong văn bản (tên phiếu, body API, prompt, popup) được khai báo: trigger `multi_variables`, `custom_variables`, biến thu thập, biến form, hoặc biến hệ thống; dùng **mã**, không dùng tên biến **[X4]**. UI không còn cảnh báo "biến liên kết có vấn đề".
4. **[C4]** CONDITION so sánh với giá trị do AI trả về: giá trị không có khoảng trắng thừa, khớp đúng danh sách mã trong prompt **[X5]**.
5. **[C5]** Sau `ADD_TICKET` cần gắn cuộc gọi hoặc người liên quan: có `DELAY` (5–10 giây) trước `GET_RELATED` cuộc gọi (bản ghi cuộc gọi chưa có ngay) **[X6]**.
6. **[C6]** Số nút ≤ quota gói; flow mới chỉ lưu nháp, **chưa xuất bản** cho tới khi test xong và user duyệt (giữ quy ước Hoạt động của user, `SKILL.md` Rule 3; nháp có chạy hay không: Cần xác nhận). Validator kiểm "chưa xuất bản" ở mode post (thiếu `is_publish` → WARN Cần xác nhận) và cảnh báo khi payload mode pre có `is_publish=true`; quy ước mặc định (Hoạt động, Không giới hạn lượt, không khoảng hiệu lực) kiểm ở **[X11]**.
7. **[C7]** Test: gọi URL webhook bằng cURL hoặc tạo sự kiện thật (khi user đồng ý) → tab **Lịch sử** của flow xem từng nút chạy và nhánh đã đi. Validator không thay được bước này.
8. **[X3]** Nút cuối chuỗi không phải `DELAY` hoặc `CONDITION` (lưu sẽ thất bại; kết thúc bằng nút Hành động — `node-editor-get.md`).
9. **[X8]** Thuộc tính khách kiểu danh sách (`is_list` trong `tenant_context.json`) không nhận biến: rẽ nhánh theo giá trị, mỗi nhánh gán một giá trị cố định.
10. **[X9]** `name_mappings` có đủ bản editor cho các nút trong `nodes` (`node-editor-get.md`); phần tử chép nguyên từ bản GET của nút cùng loại, không tự viết. Hiện chỉ WARN vì chưa có template editor kiểm chứng; không đối chiếu được id thì WARN "Cần xác nhận", không PASS.
11. **[X10]** Bản GET khớp bản đã gửi (id nút, số edge) — mode post với `--sent`.
12. **[X11]** Quy ước mặc định mọi flow (trừ khi user nói khác): Hoạt động, Không giới hạn lượt (`iteration_config.is_limit=false`), không đặt khoảng hiệu lực (`start_date`/`end_date` null). WARN khi `iteration_config.is_limit=true`, `start_date` hoặc `end_date` khác null, `is_pause` hoặc `is_stopped` = true (thiếu trường coi như null; không đọc `status`/`is_active` vì chưa rõ giá trị) — lệch quy ước mặc định, chỉ giữ nếu user yêu cầu. Giao diện mặc định ngược lại (hạn +7 ngày, giới hạn 2 lượt; `ui-build-and-test.md` mục 1).

## Ghi chú vận hành đã gặp (11/2026)
- `flow_outline.py --save <id>` ghi vào thư mục scratch: đặt `OMI_SCRATCH=<thư mục>` trước (tham số sau `--save` là **id flow**, không phải đường dẫn file); in ra đường dẫn file.
- Danh sách flow: `POST campaign-v1-stg…/omi_v2/campaign/search?page=1&size=50` body `{}`. Bộ trạng thái khách: `POST contact-v1-stg…/filter_contacts/get_list` body `{}` (`payload.items[].values[].second_level[]`). Cả hai gọi được qua `omi_api.post_json('<service>', '<path>', {})`.
- Flow tạo mới trên UI lưu xong có `_id` nháp (`is_draft:true`, `is_publish:false`); `omi_save.py flow` lưu đè được ngay và tự GET + validate post.


## Tạo flow mới bằng `add_v2` (✔ chạy 11/2026 — tạo luôn bản ĐÃ xuất bản)
Mục duy nhất về `add_v2`/`update_v2`. **Cảnh báo**: `add_v2` không tạo nháp mà tạo luôn bản đã xuất bản (chạy thật theo sự kiện) → chỉ gọi khi user đã duyệt cho đúng flow đó; `omi_save.py` cố ý không dùng. `update_v2/{id}`: chỉ thấy trong mã UI, chưa kiểm chứng → không dùng.
- `POST /omi_v2/campaign/add_v2` multipart `file` = JSON nhân bản từ GET một flow có sẵn, bỏ `_id, uuid, public_key, version, versions, created_date, last_updated_date, create_by, last_update_by, last_publish_time, executed, execute_amount, tenant_id`; đặt `name`, `is_publish:false`, `dependent_config`, `start_date/end_date:null`. Giữ nguyên id nút/cạnh/`name_mappings` của flow nguồn được.
- Kết quả `status_code 9999`, payload có `_id`, `uuid` mới, **`version:1`, `is_publish:true`** (add_v2 tạo luôn bản đã xuất bản, không phải nháp) → chỉ dùng khi user đã duyệt cho chạy, hoặc flow phụ thuộc (không tự chạy theo sự kiện).
- Đường nhanh tạo flow phụ thuộc gọi từ bot: nhân bản flow có trigger Đa kênh, trigger chỉ giữ `social_channel`, bỏ nút `OMI_BOT_AI`, `dependent_config:{"is_dependent":true}` → add_v2 → `validate_flow.py --mode pre` PASS trước khi gửi.
- Id nháp / id phiên bản / URL webhook sau khi sửa hoặc xuất bản: mục *Ba loại id và URL webhook*. Flow phụ thuộc được gọi qua bot chạy với đối tượng `SOCIAL_CONVERSATION` đúng hội thoại (log `target_value` = id hội thoại), `RE_DISTRIBUTE` SUCCESS (✔ 11/2026).

## Ba loại id và URL webhook (✔ GET 11/2026)
Mục duy nhất về id flow và URL webhook; nơi khác chỉ trỏ về đây.
- **Id bản nháp cố định**: `flow_outline.py --list` trả id này (`is_draft:true`), không đổi qua các lần xuất bản; GET id này ra nội dung mới nhất kèm `versions[]`. Dùng id này để lưu nháp (`omi_save.py flow`) và ghi manifest.
- **Id phiên bản**: mỗi lần Xuất bản (user bấm) sinh id phiên bản mới, `versions[]` thêm một dòng, URL editor nhảy sang `/flow/edit/<id phiên bản>` → không giữ URL editor cũ, mở flow từ danh sách. User hay người khác xuất bản trên UI cũng làm id phiên bản tăng.
- **Id webhook `kick_off.id`**: URL kích hoạt `https://external-v1-stg.omicrm.com/api/campaign/webhook/{kick_off.id}`; **giữ nguyên qua các lần xuất bản**, chỉ đổi khi tạo lại trigger hoặc làm mới URL. Luôn xem lại được bằng GET (không cần chép lúc hộp "Thông tin về URL" hiện). Cần xác nhận: URL có sinh mới ở lần lưu đầu hay ở mỗi lần lưu còn hiện hộp "Thông tin về URL" hay không.
- Ghi chép cũ, Cần xác nhận: sửa flow đã xuất bản rồi bấm "Cập nhật" từng thấy id nháp = `_id` bản xuất bản + 1 (cùng `uuid`) và `GET /get/<id xuất bản>` vẫn trả bản cũ; chưa đối chiếu với quy luật "id nháp cố định" ở trên.
- **Trước khi giao hoặc gắn** (báo cáo, gắn webhook Tương tác phím, gắn vào bot, ghi manifest, ghi chú chứa URL): chạy `flow_outline.py --list` rồi GET lại `kick_off.id`; không dựa vào id/URL trong tài liệu bàn giao hay ảnh chụp.
