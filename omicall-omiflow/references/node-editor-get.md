# OMIFlow — Cấu trúc đã kiểm chứng bằng GET sau khi dựng trên editor (mục 6)

Tách nguyên văn từ `node-catalog.md` (mục lục và bảng mã ở đó). Số mục giữ như cũ.

## 6. Cấu trúc đã kiểm chứng bằng GET sau khi dựng trên editor (10/2026) — trigger theo trạng thái khách, SLA, thu hồi

Cách học nhanh: dựng **một** flow mẫu trên editor (mỗi loại nút một lần), lưu, `GET /omi_v2/campaign/get/{id}`, rồi sinh các flow còn lại bằng script từ chính JSON đó và lưu bằng `save_draft_v2` (multipart `file`; flow mới thì bỏ `_id`, `uuid`, `created_date`, `last_updated_date` — Cần xác nhận: `omi_save.py` chỉ lưu nháp vào flow có `_id`, nên tạo vỏ flow trên UI trước, `api-reference.md` mục Lưu flow). Mỗi flow lưu **hai bản**: `nodes[]` (runtime, snake_case) và `name_mappings[]` (editor, camelCase, nút đầu loại `BEGIN`). Sửa nút phải sửa cả hai, nếu không editor hiển thị "Chưa có dữ liệu".

**Trigger Điều kiện theo trạng thái khách** (node đầu, `kick_off.event:"GENERAL"`; mỗi trường hợp một nhánh, có thể chọn nhiều trạng thái):
```json
{"id":"<case>","type":"GENERAL","operator_type":"AND","data":[{"type":"CONTACT","filter_contacts":[
  {"pos":null,"not_contain":false,"id":"<statusSetId>","index":[{"first_index":2,"second_index":[]},{"first_index":3,"second_index":[]}],"operator_type":"OR"}]}],
 "next_nodes":["<nodeId>"],"execute_for_exist":false,"iteration_config":{"is_limit":false,"number_of_times":0,"time_range":"none","apply_for_branch":false}}
```
`first_index` = số thứ tự trạng thái (bắt đầu từ 1) trong bộ trạng thái (`POST contact-v1-stg…/filter_contacts/get_list` trả `values[].index`, `values[].name`). Nút Điều kiện giữa luồng dùng cùng khối `data` (không có `iteration_config`).

**Điều kiện "Không có tương tác"** (Mở rộng → Kiểm tra tương tác khách hàng), một trường hợp có thể ghép nhiều mục `data` (AND), ví dụ "vẫn đang ở trạng thái X" + "không có tương tác":
```json
{"type":"CUSTOM","custom_data":[{"target_type":"NOT_HAVE_CONTACT_INTERACTIVE",
  "agent_option":{"assignee":true,"related":false,"system":false,"customer":false,"anonymous":false,"agent_ids":[],"agent_groups":[],"internal_groups":[],"agent_emails":[]},
  "time_range":{"value":"718","unit":"minute"},"sources":["note","call"]}]}
```
`sources`: `note`, `call`, `change_status` (bản editor ghi `call_interactive` thay cho `call`). `assignee:true` = nhân viên phụ trách khách. Cửa sổ tính lùi từ lúc nút chạy: để cửa sổ ngắn hơn trì hoãn 1–2 phút để log ghi lúc vào trạng thái không bị tính.

**Delay** (nút `DELAY`): `actions:[{"id":"<id>","type":"DELAY","data":{"type":"after","value_string":"12","unit":"hour","use_time_slot":false,"days_in_week":null}}]`, `unit`: `minute|hour|day`.

**Hành động khách hàng** (nút `ACTION`, runtime) [verify JSON — runtime; bản editor một phần]:
- `ADD_CONTACT` `{phone,email,full_name,country_code:"+84"}` (UI "Thêm khách hàng" tách thành 2 hành động) + `ASSIGN_SALE_ALLOCATION` `{ids:["<allocId>"],assign_priority:{agent_of_call:false,agent_join_conv:false},assign_criteria:{use_criteria:false,re_assign_when_match_previous:false,match_all:false,criteria:[]}}`.
- Đổi người phụ trách: `ASSIGN_USER_OWNER_ID` `{ids:["<agentContactId>"],swap_owner_to_related:false,transfer_agent_note:"<ghi chú>",assign_criteria:{...}}`.
- Đổi trạng thái: `ASSIGN_FILTER_CONTACT` `{filter_contacts:[{id:"<statusSetId>",index:1,note:"<ghi chú log>",opportunity_expired:{type:"SPECIFIC",time:""},total_deals_string:"",products:null}]}`.
- Ghi vào Mô tả khách: `ASSIGN_ATTRIBUTE_STRUCTURE` với `field_code:"note"`, `field_type:"multi_text"`, `update_types[0].type:"INSERT"`, `position:"START"`.
- Bản editor tương ứng: `UPDATE_INFO_CONTACT` `{assign:[{name:"assignUserOwner",...},{name:"assignStatus",value:"fc-<statusSetId>",targetType:"filter_contacts",values:{selectOpt:{label,value:<index>},content:"<ghi chú>",...}}]}` và `ADD_NEW_CONTACT` `{type:"ASSIGN_SALE_ALLOCATION",fullName,phone,email,selected:{value:"<allocId>"}}`.

**Cạnh (edges)**: trường hợp của CONDITION/trigger dùng `sourceHandle:<case id>`; nhánh còn lại và nút tuần tự dùng `"2"`; `targetHandle:"1"`; id cạnh `reactflow__edge-<src><handle>-<tgt>1`.

**Bẫy khi dựng bằng giao diện** (đã gặp):
- Trigger thật là thẻ trong màn "Điều kiện bắt đầu OMIFlow này" (nút đầu có tiêu đề "Điều kiện" + mô tả "Kịch bản bắt đầu khi thỏa…"). Bấm nhầm chữ "Điều kiện" bằng JS chỉ thêm một nút Điều kiện giữa luồng và trigger vẫn trống → "Kịch bản không hợp lệ".
- Nút Delay/Điều kiện cuối chuỗi không có nút kế tiếp cũng làm lưu thất bại: kết thúc bằng nút Hành động. Nút mới chưa có mục "Nút kế tiếp" trong ngăn → dùng nút "Thêm nút liền kề" trên thanh công cụ của nút (gọi bằng `.click()` JS được).
- Lưu thất bại thì editor tự mở ngăn của nút đầu tiên bị lỗi.
- Chip chọn trạng thái trong trigger là hộp tick; tick bằng `click` chuột theo `ref` (JS `click` không tick được).
- Hệ thống chặn "Xuất bản" flow (triển khai chạy thật) khi chưa được người dùng xác nhận trực tiếp trong chat.

**LiveTalk → tạo khách từ form trước chat (đã chạy thật 10/2026)**: trigger Điều kiện LiveTalk (`social_channel=widget_v2`, `social_send_by=customer`, `social_content` != "", `social_chatbot_waiting=available`, giới hạn 1 lần/đối tượng — X11: lệch quy ước mặc định, chỉ giữ nếu user yêu cầu) → ACTION `ADD_CONTACT` `{phone:"{{social_lt_phone_number}}", full_name:"{{social_customer_name}}"}` + `ASSIGN_SALE_ALLOCATION` + ghi Mô tả + `ASSIGN_FILTER_CONTACT` → `OMI_BOT_AI`. Một nhánh điều kiện nối được nhiều nút (`next_nodes` mảng + nhiều edge cùng `sourceHandle`) để chạy song song.

**Bổ sung đã kiểm chứng bằng GET sau khi dựng 17 nút (flow nhắc tương tác + thu hồi, 11/2026)**
- **Trigger nhiều trường hợp, trạng thái nhiều cấp**: mỗi trường hợp một `conditions[]` có `id` riêng, `data[0].filter_contacts[0].index` = `[{"first_index":<cấp 1>,"second_index":[<cấp 2>…]}]` (chỉ số bắt đầu từ 1, `second_index` rỗng = cả cấp 1; chọn L1 trọn gói ghi `[1,2]`). Nối nhánh bằng `conditions[i].next_nodes` + edge `sourceHandle:<case id>`; `edges.connections` của trigger dùng `style.stroke:"#00B1FF"`. Bản editor (`name_mappings`, nút `type:"BEGIN"`) ghi `children[].children[]` có `label/value/color` theo tên trạng thái và `otherDatas.limitObjPassConfig.works.value:"loop"` khi "Không giới hạn".
- **PUSH_NOTIFICATION gửi cho nhân viên phụ trách khách**: runtime `send_to_user_owner_of_contact:true`, `send_to_agent_contact:false`, `agent_contact_ids:null`; bản editor `noticeCustomer:true`, `noticeEmployee:false`, `employee:[]`. Gửi cho nhân viên cụ thể: `send_to_agent_contact:true` + `agent_contact_ids:[<id>]` (editor `noticeEmployee:true`, `employee:[{…}]`). `content` runtime là HTML thường; bản editor mã hoá ký tự có tên thực thể (`á→&aacute;`, `ê→&ecirc;`, `ì→&igrave;`…), ký tự không có tên (ạ, ệ, ư, ơ…) để nguyên.
- **CONDITION `NOT_HAVE_CONTACT_INTERACTIVE`**: bản editor `datas[0]` = `{value:"new_contact_interactive", label:"checkCustomerInteractive", targetType:"new_contact_interactive", attributeType:"EXTEND", operator:"=", interactiveType:"none", methodType:"SPECIFIC_STAFF", employeesList:[{uuid,employeeEmail:""}], sources:["call_interactive","note","change_status"], agent_option:{…}, time_range:{value,unit}}` (runtime `sources` dùng `call`). Chọn người bằng chip *Nhân viên* → tick: `agent_option.agent_ids:["<agentContactId>"]`; tick hụt thì `agent_ids:[]` và mọi cờ `false` (điều kiện vô nghĩa, vẫn lưu được).
- **ASSIGN_USER_OWNER_ID** (thu hồi): `ids:["<agentContactId>"]`, `transfer_agent_note` mã hoá thực thể như trên; bản editor `UPDATE_INFO_CONTACT.assign[0]` `{name:"assignUserOwner", tabs:[specificEmployee…], transferAgentNote, children:{…nhân viên}}`. Gán lại cho đúng người đang phụ trách → `NO_CHANGE` (vô hại).
- **Nhân bản nút bằng script**: `deepcopy` nút mẫu ở cả `nodes` và `name_mappings`, đổi `id` (10 ký tự chữ-số), `actions[].id`, `conditions[].id` (và `collapse_obj`), `position` (bước ngang 396, hàng cách 400); cạnh `reactflow__edge-<src><handle>-<tgt>1`, handle `"2"` cho nút thường, `<case id>` cho CONDITION/trigger. `validate_flow.py --mode pre` + `omi_save.py flow` đều đạt, editor mở lại hiển thị đủ.
- **Hạn mức**: thanh trên canvas ghi "Số lượng nút N / 20" (gói ví dụ); một flow 17 nút lưu được.


**Tắt chatbot của hội thoại** [verify JSON] (Hành động → Cập nhật cuộc trò chuyện → "Trạng thái Chatbot" Bật/Tắt) → runtime `{"type":"UPDATE_SOCIAL_CHATBOT_STATUS","data":{"enable_chatbot":false}}`; editor (trong `datas.assign[]` của UPDATE_CONVERSATION) `{"name":"updateSocialChatbotStatus","value":"update_social_chatbot_status","options":[{"value":"true","label":"on"},{"value":"false","label":"off"}],"kind":"assign","children":{"value":"false","label":"off"}}` (✔ GET 11/2026). Gán nhân viên cụ thể: `{"type":"ASSIGN_CONVERSATION_MEMBER","data":{"ids":["<contact id nhân viên>"],"assign_agent_option":{"agent_emails":[],"allocate_type":"SPECIFIC","agent_groups":[],"priority_agent_of_contact":false},"assign_criteria":{"use_criteria":false,"re_assign_when_match_previous":false,"match_all":false,"criteria":[]}}}`.

**Nhánh "BOT chủ động kết thúc" của `OMI_BOT_AI` cũng chạy khi khách im lặng hết thời gian chờ** (`customer_not_response.waiting_time`, mặc định 180 giây) — log 11/2026: bot trả lời đúng lúc 13:59, không có tin mới, 14:02 flow đi tiếp nhánh sau-kết-thúc. Đừng đặt chuyển nhân viên / tin "ngoài giờ" ở nhánh này nếu chỉ muốn chạy khi bot không biết; dùng ACTION gọi flow phụ thuộc trong bot.
- Phiên `OMI_BOT_AI` giữ cho tới khi bot kết thúc: tin tiếp theo của khách trong phiên không chạy lại trigger, bot trả lời luôn (kể cả sau khi flow phụ thuộc đã `RE_DISTRIBUTE`) → cần `UPDATE_SOCIAL_CHATBOT_STATUS` false khi bàn giao.
