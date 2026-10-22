# MCP OMI (`omicall-mcp`) — cài đặt, đăng nhập, bản đồ công cụ, tiết kiệm token

File dùng chung cho 4 skill: `omicall-callbot-gen-ai`, `omicall-callbot-flow`, `omicall-chatbot-gen-ai`, `omicall-omiflow` (mỗi skill giữ một bản giống nhau — sửa một bản thì chép sang các bản kia).

Package npm `omicall-mcp` của VIHAT (bản 1.3.1, server "OMICall MCP", **85 công cụ**, đã kiểm bằng `tools/list`). MCP **không** có công cụ dựng Callbot, Chatbot hay OMIFlow: phần dựng vẫn gọi API `chatbot-gateway` hoặc `campaign-v1` theo skill. MCP lo **đăng nhập, tra cứu id, kiểm thử** — những việc trước đây tốn nhiều lượt trình duyệt và token.

## 1. Cài đặt (người dùng tự chạy — agent không điền mật khẩu)
Claude Code, phạm vi người dùng (không nằm trong repo):
```bash
claude mcp add OMICall-mcp --scope user -e OMICALL_USERNAME=<email> -e OMICALL_PASSWORD=<mật khẩu> -e OMICALL_DOMAIN=<domain> -- npx omicall-mcp
```
Biến môi trường tuỳ chọn: `OMICALL_ENV` (mặc định `stg`, khớp các gateway `*-stg.omicrm.com` trong skill), `OMICALL_TENANT_ID` (tài khoản có nhiều tenant), `OMICALL_API_KEY`.
- Claude Desktop, Cursor, VS Code, opencode: khối `mcpServers` với `"command":"npx","args":["omicall-mcp"]` và cùng các biến `env`.
- Cho phép không hỏi lại: `"permissions":{"allow":["mcp__OMICall-mcp__*"]}` trong `~/.claude/settings.json`.
- **Bảo mật**: không đặt cấu hình chứa mật khẩu trong thư mục dự án (`.mcp.json`, `mcp-config.json`) nếu thư mục đó được chia sẻ hoặc đưa lên git. Mỗi tenant cần một cấu hình riêng: đổi `OMICALL_DOMAIN` hoặc thêm server thứ hai, ví dụ `OMICall-<tenant>`.
- Kiểm tra đã cài: công cụ `get_version` trả `1.3.x`.

Tên công cụ đầy đủ tuỳ client: Claude Code `mcp__<tên-server>__<tool>` (ví dụ `mcp__OMICall-mcp__login_omicall_mcp`), opencode `<server>_<tool>` (ví dụ `omicall_login_omicall_mcp`). Nếu công cụ đang ở dạng deferred, tải bằng ToolSearch `select:` một lần cho cả nhóm cần dùng.

## 2. Đăng nhập bằng MCP (ưu tiên số 1)
1. `login_omicall_mcp` (tham số `domain`, `tenant_id` đều tuỳ chọn; mật khẩu lấy từ cấu hình) → nếu trả danh sách nhiều tenant thì `select_tenant(tenant_id)`.
2. `get_service_package` → các module đã bật (`switchboard`, `ticket`, `integrated`, `ai`…) và hạn mức. Đọc ngay để biết thiết kế dùng được gì.
3. **Token cho API mà MCP không có** (callbot, chatbot, OMIFlow): đọc phiên MCP ở `~/.omicall-mcp/session.json` → `accessToken`, bằng `scripts/omi_session.py`. Cùng loại JWT với web, dùng làm `Authorization: Bearer` cho `chatbot-gateway-v1-stg`, `campaign-v1-stg`, `ticket-v2-stg`, `tenant-v1-stg`… Không in token ra hội thoại.
4. Phương án dự phòng (MCP chưa cài, hoặc không có file phiên): user đăng nhập **một lần** trong browser pane → lấy token từ cookie `{domain}_omicrm_io` key `"2"`. Agent không tự gõ mật khẩu vào form hay API đăng nhập. Nếu lớp an toàn chặn việc đọc cookie thì đề nghị user cài MCP (mục 1), hoặc thao tác UI.
5. Hết phiên hoặc lỗi 401: gọi lại `login_omicall_mcp`. Đổi tenant: `logout` rồi đăng nhập với domain mới, hoặc dùng server MCP riêng cho từng tenant.

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
3. **Không đổ JSON lớn vào hội thoại**: flow, kịch bản và bot có thể hàng trăm KB. Dùng script tóm tắt (`omicall-omiflow/scripts/flow_outline.py`) hoặc chỉ in trường cần thiết.
4. **Đọc reference có chọn lọc**: chỉ mở mục module hoặc schema cần cho bài toán (Grep theo tên module) thay vì đọc cả file.
5. **Ưu tiên văn bản hơn ảnh**: `get_page_text`, `read_page` thay cho screenshot; nếu cần ảnh thì `scale` 0.4–0.6.
6. **Dùng lại script trong `scripts/` của skill**, không viết lại mỗi lần; script mới hữu ích thì thêm vào skill.
7. **Kiểm thử bằng MCP** (`search_calls`, `search_tickets`, `get_contact_by_phone`) thay vì mở giao diện để xem kết quả.
