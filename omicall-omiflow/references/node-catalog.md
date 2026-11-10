# OMIFlow — Danh mục module (trigger, nút, hành động, điều kiện)

## Mục lục (đọc bảng ở đây trước; chi tiết và JSON mỗi loại ở file riêng, chỉ mở file cần)
| Mục | Nội dung | File |
|---|---|---|
| 1 | Bảng trigger | file này |
| 1a–1c | WEB_HOOK, GENERAL cuộc gọi, GENERAL phiếu ghi mới (JSON) | `node-trigger.md` |
| 2 | Bảng loại nút | file này |
| 2.1–2.6 | CONDITION, DELAY, COLLECT_INFO, DESCRIPTION, ZALO_PERSONAL_MESSAGE, MARKETING AUTOCALL (JSON) | `node-condition.md` |
| 3 | Bảng hành động | file này |
| 3.1 | ADD_TICKET (JSON) | `node-action-ticket.md` |
| 3.2–3.6, 4 | Cập nhật phiếu, PUSH_NOTIFICATION, SEND_WEBHOOK, CREATE_CUSTOM_VARIABLE, GET_RELATED; cửa sổ tương tác | `node-action-contact.md` |
| 5 | Biến dùng được trong flow | file này |
| 6 | Cấu trúc đã kiểm chứng bằng GET sau khi dựng trên editor (`name_mappings`, vỏ flow) | `node-editor-get.md` |

Danh mục này là của **nền tảng**, áp dụng cho mọi tenant (xem `concepts.md` để hiểu cơ chế đối tượng, biến, trigger). Nguồn: (1) enum và nhãn tiếng Việt trích từ mã giao diện OMICRM (bản stg, 10/2026); (2) tài liệu chính thức `omicrm.io/post/topic/omiflow-7`; (3) JSON thật của các flow đang chạy, đọc qua `GET /omi_v2/campaign/get/{id}`. Mục có nhãn **[verify JSON]** đã thấy JSON thật; **[UI đã dựng]** đã cấu hình và chạy thật qua editor (chưa có JSON mẫu, cách làm ở `ui-build-and-test.md`); mục **[enum]** đã biết công dụng nhưng chưa có JSON mẫu: khi dùng thì dựng thử một lần (hoặc Ctrl+C một nút cùng loại trên canvas để xem định dạng clipboard), GET lại để lấy schema rồi bổ sung vào đây.

Id trong ví dụ đã thay bằng `<...>`. Mã biến thật là chuỗi ngẫu nhiên 10 ký tự (ví dụ `{{MpQxWEiLis}}`).

---

## 1. Điều kiện bắt đầu (trigger)

Trigger KHÔNG phải node riêng: nó là **node `CONDITION` đầu tiên** (`is_first_node:true`), `conditions[0].type` = loại trigger. `kick_off.event` của flow lặp lại loại này, `kick_off_ids` chứa id webhook (nếu có).

| Mã (`conditions[0].type`) | Nhãn UI | Khi nào dùng | Trạng thái |
|---|---|---|---|
| `WEB_HOOK` | API | Hệ thống ngoài, Callbot, Chatbot gọi vào URL để chạy flow, truyền biến qua body | [verify JSON] |
| `GENERAL` | Điều kiện | Đối tượng (khách, phiếu, cuộc gọi, cuộc gọi AI phân tích, hội thoại) được thêm mới hoặc cập nhật và thoả thuộc tính; hoặc **sự kiện mở rộng** (cuộc gọi kết thúc, phím IVR, phiếu mới, khách quan tâm OA, đánh giá ZNS…) kèm điều kiện thuộc tính | [verify JSON] |
| `FORM` | Biểu mẫu | Khách hoàn thành hoặc sửa Biểu mẫu. Chỉ liệt kê biểu mẫu đã xuất bản | [UI đã dựng] |
| `PERIOD` | Xảy ra định kỳ | Hằng ngày, tuần, tháng; **trước hoặc sau** một thuộc tính thời gian (sinh nhật, hạn phiếu, ngày hẹn); thời điểm cụ thể | [enum] |
| `EXCEL` | Kích hoạt bằng File Excel | Chạy hàng loạt, mỗi dòng Excel là một đối tượng, định nghĩa giá trị biến | [enum] |
| `THIRD_PARTY` | Đối tác | Nhận sự kiện hoặc webhook từ đối tác tích hợp | [enum] |
| `DIRECT_CALL` | Cuộc gọi đang diễn ra | Chạy ngay trong lúc cuộc gọi diễn ra (kết hợp `HOLDING_CALL`, `TRANSFER_CALL`) | [enum] |
| `HARAVAN`, `SAPO`, `KIOTVIET`, `WOOCOMMERCE`, `SHOPIFY`, `PANCAKEPOS`, `POSBIRD`, `TPOS`, `LARK_BASE`, `EMAIL_SMTP` | Đối tác cụ thể | Sự kiện đơn hàng, khách hàng, hoá đơn: tạo mới, cập nhật, thanh toán, huỷ, giao hàng; sự kiện email | [enum] |
| `SEARCHOPT` | (nội bộ) | Dùng làm `sub_condition` khi tra đối tượng, không phải trigger | [verify JSON] |

Mô tả chính thức của các trigger (nhãn UI): ADD_CONTACT "khi có 1 khách hàng được thêm mới và thoả 1 trong các điều kiện"; CONTACT "khi khách hàng thoả các điều kiện thuộc tính"; TICKET "khi phiếu ghi được chuyển đến trạng thái nhất định"; FORM; PERIOD; EXCEL; THIRD_PARTY; WEB_HOOK; DIRECT_CALL.

## 2. Loại nút (`node_type`)

Mọi node có chung khung: `id, is_first_node, description, description_type, color, position{x,y}, node_type, conditions, actions, next_nodes, fail_next_nodes, success_next_nodes, collapse_obj, width, height`.

| `node_type` | Nhóm / nhãn UI | Vai trò | Trạng thái |
|---|---|---|---|
| `CONDITION` | Logic → Điều kiện | Rẽ nhánh theo nhiều *trường hợp*; `next_nodes` của node = nhánh "Bước tiếp theo" (else) | [verify JSON] |
| `DELAY` | Logic → Trì hoãn (Delay) | Chờ khoảng thời gian, chờ đến khung giờ, hoặc chờ đến khi thoả điều kiện | [verify JSON] |
| `RANDOM` | Logic → Random | Chia nhánh ngẫu nhiên theo tỉ lệ (A/B test kịch bản, phân tải) | [enum] |
| `AI_ANALYZE` | Logic → Phân tích thông tin | AI phân loại một đoạn nội dung theo Chủ đề hoặc Ý định đã đào tạo ở mô-đun AI, mỗi ý định một nhánh | [enum] |
| `ACTION` | Tương tác → Hành động | Chuỗi nhiều hành động chạy tuần tự (mục 3) | [verify JSON] |
| `MARKETING` | Tương tác → Marketing | Tạo phiên gửi hàng loạt: SMS, ZNS hoặc ZBS, ZCC (xin quyền gọi Zalo), Email, AutoCall, AI Callbot, Viber Business | [enum] |
| `INFO_DIALOG` / `FORM_DIALOG` / `BUTTON_DIALOG` / `VARIABLE_DIALOG` / `VIEW_DETAIL_DIALOG` / `FEATURE_DIALOG` | Tương tác → Cửa sổ tương tác | Bật cửa sổ trên màn hình nhân viên (mục 4) | INFO, FORM [verify JSON]; còn lại [enum] |
| `ZALO_PERSONAL_MESSAGE`, `ZALO_MESSAGE`, `FACEBOOK_CHAT_MESSAGE`, `FACEBOOK_POST_MESSAGE`, `LIVE_TALK_MESSAGE`, `TELEGRAM_MESSAGE`, `VIBER_MESSAGE`, `TIKTOK_BUSINESS_MESSAGE`, `WHATSAPP_BUSINESS_MESSAGE`, `EMAIL_SMTP_MESSAGE`, `MULTI_CHANNEL_MESSAGE` | Trò chuyện → từng kênh / Gửi tin nhắn chung | Gửi tin hoặc thao tác trên kênh (ví dụ Zalo cá nhân: `REQUEST_FRIEND`). Nút Zalo OA có sẵn nhánh "Trạng thái tin nhắn → Thất bại" + "Bước tiếp theo" (✔ UI 10/2026; `concepts.md` mục 6) | Zalo cá nhân [verify JSON] |
| `CHAT_GPT`, `CHATX_AI`, `OMI_BOT_AI`, `PRO_AI`, `PARTNER_AI`, `CUSTOMIZE_BOT_AI` | Trò chuyện → ChatGPT / ChatX / AI Chatbot / ProAI / Partner AI | Giao cuộc trò chuyện cho bot AI xử lý | [enum] |
| `COLLECT_INFO` | Khác → Thu thập thông tin | AI bóc Đối tượng hoặc Thực thể (SĐT, email, ngày, thực thể tự đào tạo) từ nội dung, lưu vào biến; tuỳ chọn `FROM_DEFINED_VARIABLE` gán giá trị cố định | [verify JSON] (kiểu giá trị cố định) |
| `DESCRIPTION` | Khác → Ghi chú | Ghi chú trên canvas (URL webhook, cURL mẫu, giải thích) | [verify JSON] |
| `MENU`, `CUSTOM_UI`, `DIRECT_CALL*`, `END_CALL`, `BEGIN` | (luồng gọi / bot) | Dùng trong flow cuộc gọi trực tiếp hoặc giao diện tuỳ biến | [enum] |

## 3. Hành động trong nút ACTION (`actions[].type`)

Ngăn "Hành động" trên UI có 22 mục (nhãn và mô tả chính thức):

| Mã | Nhãn UI | Mô tả chính thức | Trạng thái |
|---|---|---|---|
| `ADD_NEW_CONTACT` | Thêm khách hàng | Gán cho nhân viên cụ thể hoặc cấu hình Phân Sale. SĐT đã có → `CONTACT_EXIST`, không tạo trùng | [UI đã dựng]; runtime verify (mục 6, dòng 329-334), editor một phần |
| `UPDATE_INFO_CONTACT` | Cập nhật khách hàng | Cập nhật thuộc tính khách hàng nếu đã tồn tại (phụ trách + ghi chú log, trạng thái pipeline + ghi chú…; chỉ đổi đúng thuộc tính đã khai báo). Giá trị trùng hiện tại → `NO_CHANGE` | [UI đã dựng]; runtime verify (mục 6, dòng 329-334), editor một phần |
| `ADD_TICKET` | Tạo phiếu ghi | Dùng thuộc tính từ biểu mẫu hoặc tự định nghĩa | [verify JSON] |
| `UPDATE_INFO_TICKET` | Cập nhật phiếu ghi | Cập nhật thuộc tính phiếu ghi đã tồn tại (lưu thành các `ASSIGN_TICKET_*`) | [verify JSON] |
| `PUSH_NOTIFICATION` | Tạo thông báo | Gửi thông báo đẩy đến nhân viên hoặc nhóm | [verify JSON] |
| `PUSH_REMINDER` | Tạo nhắc nhở | Tạo lời nhắc cho nhân viên hoặc nhóm | [enum] |
| `SEND_DATA_TO_FORM` | Trả kết quả qua Biểu mẫu | Trả thông tin sau khi khách hoàn thành hoặc sửa biểu mẫu | [enum] |
| `SEND_RESPONSE_WEBHOOK_API` | Trả kết quả qua API | Trả thông tin sau khi bên thứ 3 gọi API (trả dữ liệu động cho caller) | [enum] |
| `CREATE_CUSTOM_VARIABLE` | Biến liên kết tùy chỉnh | Khai báo biến và quy định giá trị: API, ChatGPT, tính toán, ngẫu nhiên, ảnh thư mời | [verify JSON] |
| `GET_RELATED` | Gán đối tượng liên quan | Đưa đối tượng liên quan (phiếu, cuộc gọi, khách, nhân viên, hội thoại…) vào luồng | [verify JSON] |
| `UPLOAD_GOOGLE_SHEET` | Google Sheet | Ghi bảng tính với tài khoản Google đã liên kết | [enum] |
| `UPDATE_CONVERSATION` | Cập nhật cuộc trò chuyện | Cập nhật thuộc tính hội thoại đi qua flow | [enum] |
| `UPDATE_CALL_TRANSACTION` | Cập nhật lịch sử cuộc gọi | Cập nhật thuộc tính cuộc gọi đi qua flow | [enum] |
| `UPDATE_INFO_EMPLOYEE` | Cập nhật nhân viên | Cập nhật thuộc tính nhân viên | [enum] |
| `UPDATE_CUSTOM_DIALOG` | Cập nhật cửa sổ tương tác | Cập nhật thuộc tính ở Cửa sổ thông tin, Cửa sổ biểu mẫu | [enum] |
| `OMI_BOT_EVALUATION` | Cập nhật đánh giá AI Chatbot | Ghi đánh giá chất lượng AI Chatbot | [enum] |
| `SEND_WEBHOOK` | API | Gửi thông tin cho đối tác theo phương thức tự định nghĩa | [verify JSON] |
| `ADD_CLASSIFY` | Phân loại | Đánh dấu, phân loại lịch sử chiến dịch để báo cáo | [enum] |
| `TRANSFER_CALL` | Chuyển tiếp cuộc gọi | Chuyển đến nhân viên, nhóm nội bộ, nhóm bên ngoài | [enum] |
| `START_OTHER_CAMPAIGN` | Gọi đến kịch bản khác | Kích hoạt flow khác; flow đích phải là loại *phụ thuộc* | [enum] |
| `ORDER_*_ACTION` (Haravan, KiotViet, Sapo, Shopify, WooCommerce, POS Bird, TPos), `PANCAKEPOS_ACTION`, `UPDATE_LARK_BASE`, `CREATE_RECORD_LARK_BASE` | Cập nhật đối tác | Cập nhật đơn hàng, khách hàng ở đối tác | [enum] |
| `HOLDING_CALL` | Giữ cuộc gọi | Tạm giữ cuộc gọi để chờ điều kiện, hành động hoặc thông tin bên thứ 3 | [enum] |

Mã chi tiết hơn (lưu bên trong khi chọn trường trong "Cập nhật …"): `ASSIGN_TICKET_TYPE/STATUS/PRIORITY/DUE_DATE/NAME/DESCRIPTION/TAG/REPORTER/ASSIGNEE/ASSIGNEE_ALLOCATION/PIN_OBJECT/ATTRIBUTE_STRUCTURE/NOTIFY_*`, `ADD_TICKET_NOTE`, `ADD_TICKET_EVALUATION`, `ASSIGN_TAG`, `REMOVE_TAG`, `ASSIGN_ATTRIBUTE_STRUCTURE`, `REMOVE_ATTRIBUTE_STRUCTURE`, `ASSIGN_GROUP`, `ASSIGN_BUSINESS`, `ASSIGN_SALE_ALLOCATION`, `ASSIGN_USER_OWNER_ID/ALLOCATION`, `ASSIGN_RELATED_EMPLOYEE`, `ADD_CONTACT_NOTE`, `ADD_CONTACT_EVALUATION`, `ASSIGN_CALL_TRANSACTION_TAG/CALL_PURPOSE/ASSGNEE`, `ADD_CALL_TRANSACTION_NOTE`, `ASSIGN_CONVERSATION_TAG/MEMBER/ATTRIBUTE_STRUCTURE`, `ADD_CONVERSATION_NOTE`, `UPDATE_SOCIAL_CHATBOT_STATUS`, `UPDATE_SOCIAL_IS_SOLVED`, `BLOCK_CONVERSATION`, `LINK_CONTACT_CONVERSATION`, `AGENT_ASSIGN_*`, `UPDATE_VOUCHER_*`, `ASSIGN_VOUCHER_LINK_*`, `ACCEPT/REJECT_REQUEST_JOIN_GROUP(_ZLP)`, `ACTION_MINI_APP`, `ASSIGN_CUSTOM_DIALOG`, `REMOVE_CUSTOM_DIALOG`, `RE_DISTRIBUTE`.

## 5. Biến dùng được trong flow
1. **Biến trigger**: `multi_variables` của WEB_HOOK, tham chiếu `{{<field_code>}}`.
2. **Biến liên kết tùy chỉnh**: từ `CREATE_CUSTOM_VARIABLE`, khai báo ở top-level `custom_variables:[{"name","field_code"}]`.
3. **Dữ liệu thu thập** (`COLLECT_INFO` hoặc phần thu thập trong nút gửi tin): AI bóc thực thể từ nội dung hoặc câu trả lời; hoặc gán giá trị cố định (mẫu: tra API không ra tên thì gán "Khách hàng mới", rồi nhập lại nhánh chính). Biến tuỳ chỉnh và dữ liệu thu thập chỉ sống trong flow hiện tại.
4. **Biến hệ thống cuộc gọi**: `{{ct_phone_number}}`, `{{ct_transaction_id}}`, `ct_key_action`, `ct_call_status`, `ct_call_type`, `ct_sip_number`.
5. **AI Assistant** (cấu hình trường: skill con `omicall-ai-insight`): `{{ca_summarize}}` (tóm tắt cuộc gọi), `{{ca_ai_assistant}}` (kết quả phân tích, hay chèn vào mô tả phiếu).
6. **Đa kênh**: `social_*` (ví dụ `social_phone_number_linked`, `social_customer_name`, `social_zalo_shared_info_phone`…).
7. **Biến từ biểu mẫu trong cửa sổ**: `{{<field_code>}}` của `FORM_DIALOG`.

Top-level `variables` liệt kê mọi biến đã dùng (`{"name":"<code10>","type":"CUSTOM"|"COLLECT_INFO"|...}`). UI báo "N biến liên kết có vấn đề" khi văn bản tham chiếu một mã không còn được khai báo.
