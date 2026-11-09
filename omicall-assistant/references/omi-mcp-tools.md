# MCP OMI — bảng công cụ theo skill, tiết kiệm token, danh mục công cụ (đọc khi cần)
Tách khỏi `omi-mcp.md` (lõi: đăng nhập, token, thứ tự nguồn, lỗi) để mỗi lần nạp skill không tốn token. Nguồn duy nhất: `shared/references/omi-mcp-tools.md`, chép sang mọi skill bằng `tools/sync_shared.py`.

Package npm `omicall-mcp` của VIHAT (bản 1.3.1, server "OMICall MCP", **85 công cụ**, đã kiểm bằng `tools/list`). MCP **không** có công cụ dựng Callbot, Chatbot hay OMIFlow: phần dựng vẫn gọi API `chatbot-gateway` hoặc `campaign-v1` theo skill. MCP lo **đăng nhập, tra cứu id, kiểm thử** — những việc trước đây tốn nhiều lượt trình duyệt và token.

Nguồn: https://www.npmjs.com/package/omicall-mcp (mã nguồn https://github.com/VIHATTeam/OMICALL-MCP, giấy phép MIT). Phụ thuộc `@modelcontextprotocol/sdk`, `axios`, `zod`. **Yêu cầu Node.js 18+** (`node --version`); bản cũ hơn thì server thoát ngay khi khởi động. Kiểm tra bản mới nhất: `npm view omicall-mcp version`.

## 3. Công cụ nào cho bước nào

### Dùng chung (Bước 0 của mọi skill)
| Việc | Công cụ MCP |
|---|---|
| Đăng nhập, chọn tenant | `login_omicall_mcp`, `select_tenant`, `logout` |
| Gói dịch vụ, module đã bật, hạn mức | `get_service_package`, `get_balance` |
| Nhân viên (id, contact_id, email) | `list_agents`, `get_agent` |
| Máy lẻ (sip_user, uuid) | `list_extensions`, `get_extension` |
| Hotline, đầu số | `list_hotlines`, `get_hotline` |
| Kênh đa kênh đã kết nối (OA, page, widget, bot) | `get_all_channels` |
| Danh mục phiếu ghi | `get_ticket_categories` |
| Nguồn khách hàng | `get_source_contacts` |
| Webhook đã đăng ký | `list_webhooks` |

### Skill Callbot
| Bước | Công cụ |
|---|---|
| Cấu hình chuyển máy `TRANSFER_CALL` (agent id, ext, option) | `list_agents` + `list_extensions` / `get_extension` |
| Gắn kịch bản vào hotline gọi vào | `list_hotlines`, `update_hotline(inbound_script_id)` — **chỉ khi user đồng ý** |
| Gọi thử | `click_to_call(extension, hotline, phone_number)` |
| Kiểm tra sau gọi thử: transcript, tag, ghi chú | `search_calls`, `get_call_detail(transaction_id)` |
| Nghe thử giọng đọc | `text_to_speech(text, speaker_id, speed)` |
| Chiến dịch gọi tự động (IVR thường, không AI) | `autocall_by_phone` |

### Skill Chatbot
| Bước | Công cụ |
|---|---|
| Kênh gắn bot (oa_id, page_id, widget, bot_id) | `get_all_channels` |
| Tra khách theo SĐT (thay vì dựng flow tra cứu chỉ để test) | `get_contact_by_phone`, `search_contacts`, `get_contact` |
| Tạo khách mẫu để test luồng "đã có hồ sơ" | `create_contact` (dữ liệu test, xoá sau bằng `delete_contact` khi user đồng ý) |
| Xem hội thoại thật để kiểm tra bot trả lời | `search_conversations`, `get_conversation`, `search_channel_messages` |
| Gửi tin thử (Zalo, Facebook, Telegram, LiveTalk) | `send_*_message` — **chỉ khi user đồng ý**, vì gửi cho người thật |
| Chuyển hội thoại cho nhân viên | `transfer_conversation` |

### Skill OMIFlow
| Bước | Công cụ |
|---|---|
| Id cho `ADD_TICKET`, `ASSIGN_TICKET_TYPE` | `get_ticket_categories` (bộ trạng thái chưa có trong MCP → API `ticket-v2-stg/ticket/status-set/get-all`) |
| Người nhận `PUSH_NOTIFICATION`, `ASSIGN_TICKET_REPORTER` | `list_agents` (lấy `contact_id`) |
| Đầu số cho trigger `GENERAL` (`ct_sip_number`) | `list_hotlines` |
| Kênh cho nút Trò chuyện và Marketing | `get_all_channels` |
| Test trigger "cuộc gọi kết thúc" hoặc "phím IVR" | `click_to_call` rồi `search_calls` để lấy `transaction_id` |
| Kiểm tra flow đã tạo phiếu, cập nhật khách | `search_tickets`, `get_ticket`, `list_ticket_interactions`, `get_contact_by_phone` |
| Dọn dữ liệu test | `delete_ticket`, `delete_contact` — **chỉ khi user đồng ý** |

### Chưa có trong MCP → gọi API trực tiếp bằng token ở mục 2
Kịch bản callbot (`chatbot-gateway …/callbot/script/*`), chatbot (`…/bot/*`, `omiai_assistant/*`), OMIFlow (`campaign-v1 …/omi_v2/campaign/*`), bộ trạng thái phiếu, thuộc tính động (`tenant-v1 …/attribute/get_all`), phân bổ sale (`…/sale_allocation/search`), template ZNS, cấu hình AI.

## 4. Kết hợp MCP + skill để tiết kiệm token
1. **Đăng nhập bằng MCP**, không qua trình duyệt: bỏ hẳn các lượt mở trang, chụp màn hình, chờ user.
2. **Tra id bằng MCP** (JSON gọn) thay vì đọc giao diện hay tải cả trang cấu hình. Tra **một lần mỗi phiên** rồi lưu `tenant_context.json` ở scratchpad (agents, extensions, hotlines, categories, channels, package); các bước sau đọc file này.
3. **Không đổ JSON lớn vào hội thoại**: flow, kịch bản và bot có thể hàng trăm KB. Dùng script tóm tắt của skill nếu có (`scripts/*_outline.py`: `flow_outline.py` ở omiflow, `script_outline.py` ở callbot-gen-ai, `bot_outline.py` ở chatbot-gen-ai) hoặc chỉ in trường cần thiết.
4. **Đọc reference có chọn lọc**: chỉ mở mục module hoặc schema cần cho bài toán (Grep theo tên module) thay vì đọc cả file.
5. **Ưu tiên văn bản hơn ảnh**: `get_page_text`, `read_page` thay cho screenshot; nếu cần ảnh thì `scale` 0.4–0.6.
6. **Dùng lại script trong `scripts/` của skill**, không viết lại mỗi lần; script mới hữu ích thì thêm vào skill.
7. **Kiểm thử bằng MCP** (`search_calls`, `search_tickets`, `get_contact_by_phone`) thay vì mở giao diện để xem kết quả.

## Phụ lục B — Danh mục công cụ theo nhóm và module cần bật (mục 5 cũ)
Mỗi công cụ tự kiểm tra gói dịch vụ; module chưa bật trả lỗi *"Module X is not enabled in your service package."* → đọc `get_service_package` trước khi thiết kế.

| Nhóm | Module cần bật | Công cụ |
|---|---|---|
| Auth | — | `login_omicall_mcp`, `select_tenant`, `logout`, `get_balance`, `get_service_package` |
| Tổng đài (Call Center) | `switchboard` | `search_calls`, `get_call_detail`, `update_call` (tag, ghi chú), `evaluate_call`, `list_eval_criteria`, `click_to_call`; máy lẻ `list_extensions`/`get_extension`/`update_extension`/`update_extension_status`; hotline `list_hotlines`/`get_hotline`/`update_hotline`; nhóm đổ chuông `list_groups`/`create_group`/`update_group`/`delete_group`/`add_group_members`/`remove_group_members`; IVR `list_ivr`/`create_ivr`/`update_ivr`/`delete_ivr`; kịch bản gọi `list_scripts`/`create_script`/`update_script`/`delete_script`; âm thanh `list_audio`/`generate_tts_audio`/`delete_audio` |
| Gọi tự động | `switchboard` | `autocall_by_phone` (TTS, file ghi âm, IVR), `autocall_by_extension` |
| Phiếu ghi | `ticket` | `search_tickets`, `get_ticket`, `create_ticket`, `update_ticket`, `delete_ticket`, `update_ticket_status`, `create_ticket_note`/`update_ticket_note`/`delete_ticket_note`, `list_ticket_interactions`, `create_ticket_evaluation`, `get_ticket_eval_criteria`, `get_ticket_categories`, `ticket_statistics`, `transfer_tickets` |
| Đa kênh | `integrated` (+ từng kênh: `zalo`, `facebook`, `telegram`, `livetalk`…) | `search_conversations`, `get_conversation`, `get_all_channels`, `search_channel_messages`, `send_zalo_message`, `send_zalo_personal_message`, `send_facebook_message`, `send_facebook_comment`, `send_telegram_message`, `send_livetalk_message`, `mark_conversation_read`, `transfer_conversation` |
| Nhân viên, thông báo | — | `list_agents`, `get_agent`, `invite_agent`, `get_agent_pbx_info`, `list_notifications`, `count_unread_notifications`, `mark_notification_read`, `mark_all_notifications_read` |
| Webhook | — | `list_webhooks`, `register_webhook`, `destroy_webhook` (chỉ nhận HTTPS) |
| AI | `ai` | `text_to_speech` (4 giọng tiếng Việt), `register_stt_webhook` |
| Khách hàng | — | `get_contact_by_phone`, `search_contacts`, `get_contact`, `create_contact`, `delete_contact`, `get_source_contacts` |

**Công cụ ghi** (tạo/sửa/xoá IVR, nhóm, hotline, phiếu, khách, webhook; gửi tin; gọi ra; mời nhân viên) tác động lên tenant thật hoặc khách thật → chỉ chạy khi user đồng ý từng việc. Công cụ đọc (`list_*`, `get_*`, `search_*`) dùng thoải mái nhưng vẫn gom một lần mỗi phiên (mục 4).
