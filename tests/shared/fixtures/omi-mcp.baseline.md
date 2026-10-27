# MCP OMI (`omicall-mcp`) — cài đặt, đăng nhập, bản đồ công cụ, tiết kiệm token

File dùng chung cho 4 skill: `omicall-callbot-gen-ai`, `omicall-callbot-flow`, `omicall-chatbot-gen-ai`, `omicall-omiflow` (mỗi skill giữ một bản giống nhau — sửa một bản thì chép sang các bản kia).

Package npm `omicall-mcp` của VIHAT (bản 1.3.1, server "OMICall MCP", **85 công cụ**, đã kiểm bằng `tools/list`). MCP **không** có công cụ dựng Callbot, Chatbot hay OMIFlow: phần dựng vẫn gọi API `chatbot-gateway` hoặc `campaign-v1` theo skill. MCP lo **đăng nhập, tra cứu id, kiểm thử** — những việc trước đây tốn nhiều lượt trình duyệt và token.

Nguồn: https://www.npmjs.com/package/omicall-mcp (mã nguồn https://github.com/VIHATTeam/OMICALL-MCP, giấy phép MIT). Phụ thuộc `@modelcontextprotocol/sdk`, `axios`, `zod`. **Yêu cầu Node.js 18+** (`node --version`); bản cũ hơn thì server thoát ngay khi khởi động. Kiểm tra bản mới nhất: `npm view omicall-mcp version`.

## 1. Agent tự cài và cấu hình MCP

Khi bắt đầu một tác vụ OMI, agent phải tự kiểm tra MCP OMI. Nếu chưa có, agent tự cài và cấu hình ở phạm vi người dùng; không dừng lại để đưa lệnh rồi yêu cầu người dùng tự chạy.

1. Kiểm tra các công cụ MCP đang có. Nếu gọi được `get_version` và phiên bản trả về là `1.3.x` hoặc mới hơn thì dùng luôn.
2. Lấy `domain`, email và mật khẩu từ yêu cầu hiện tại, biến môi trường hoặc cấu hình bí mật đã có. Không in lại mật khẩu/token và không ghi chúng vào repo hay file tạm. Nếu client hỗ trợ kho bí mật, biến nhập bảo mật hoặc mở rộng biến môi trường thì ưu tiên tham chiếu bí mật thay vì ghi giá trị trực tiếp. Nếu thiếu thông tin bắt buộc thì hỏi gộp đúng một lần, sau đó agent tự hoàn tất cài đặt.
3. Kiểm tra `node` và `npx`. Dùng `npx -y omicall-mcp` để gói được tải tự động khi MCP khởi chạy; không cần cài npm toàn cục.
4. Tự nhận diện **agent/client đang thực thi** qua danh mục công cụ, tiến trình hoặc CLI có trên máy. Skill không được mặc định chỉ có Codex hay Claude. Chỉ cấu hình client đang chạy ở phạm vi người dùng; mỗi môi trường khác khi dùng skill cũng phải tự thực hiện quy trình này. Đặt tên server theo domain (`OMICall-<domain>`) để nhiều tenant không ghi đè nhau.
5. Ưu tiên trình quản lý MCP gốc của client nếu có. Trước khi chạy, gọi `<cli> mcp add --help` để xác nhận cú pháp của phiên bản đang cài; các mẫu chuẩn:

| Agent/client | Tự cài ở phạm vi người dùng | Xác minh |
|---|---|---|
| Codex CLI/IDE | `codex mcp add OMICall-<domain> --env OMICALL_USERNAME=<email> --env OMICALL_PASSWORD=<mật-khẩu> --env OMICALL_DOMAIN=<domain> -- npx -y omicall-mcp` | `codex mcp list` |
| Claude Code | `claude mcp add OMICall-<domain> --scope user -e OMICALL_USERNAME=<email> -e OMICALL_PASSWORD=<mật-khẩu> -e OMICALL_DOMAIN=<domain> -- npx -y omicall-mcp` | `claude mcp list` |
| Gemini CLI | `gemini mcp add --scope user --transport stdio -e OMICALL_USERNAME=<email> -e OMICALL_PASSWORD=<mật-khẩu> -e OMICALL_DOMAIN=<domain> OMICall-<domain> npx -y omicall-mcp` | `gemini mcp list` |
| OpenCode | `opencode mcp add OMICall-<domain> --global --env OMICALL_USERNAME=<email> --env OMICALL_PASSWORD=<mật-khẩu> --env OMICALL_DOMAIN=<domain> -- npx -y omicall-mcp` | `opencode mcp list` |

6. Nếu client không có lệnh quản lý MCP, agent tự cập nhật cấu hình **phạm vi người dùng** theo định dạng mà client hỗ trợ; phải đọc và trộn với cấu hình hiện có, không ghi đè các server khác:
   - VS Code/Copilot: ưu tiên `code --add-mcp <JSON>` hoặc User Profile `mcp.json`; Copilot CLI dùng `~/.copilot/mcp-config.json`.
   - Cursor: `~/.cursor/mcp.json`.
   - Claude Desktop: `%APPDATA%\Claude\claude_desktop_config.json` (Windows) hoặc `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).
   - Windsurf: `~/.codeium/windsurf/mcp_config.json`.
   - Gemini CLI không có CLI quản lý: `~/.gemini/settings.json`.
   - Agent khác: tìm cấu hình MCP phạm vi người dùng trong tài liệu/cài đặt của chính client rồi thêm server theo schema của client. Không tạo file chứa mật khẩu trong thư mục dự án.

Mẫu phổ biến cho Cursor, Claude Desktop, Windsurf, Gemini và các client dùng `mcpServers`:
```json
{
  "mcpServers": {
    "OMICall-<domain>": {
      "command": "npx",
      "args": ["-y", "omicall-mcp"],
      "env": {
        "OMICALL_USERNAME": "<email>",
        "OMICALL_PASSWORD": "<mật-khẩu>",
        "OMICALL_DOMAIN": "<domain>"
      }
    }
  }
}
```

VS Code dùng khóa gốc `servers` và thêm `"type": "stdio"`. OpenCode v2 dùng `mcp.servers`, `type: "local"`, `command: ["npx", "-y", "omicall-mcp"]`, `environment` và `enabled: true`. Trên Windows, nếu client không chạy được `npx` trực tiếp thì dùng `command: "cmd"` với `args: ["/c", "npx", "-y", "omicall-mcp"]`.

7. Biến môi trường tuỳ chọn: `OMICALL_ENV` (mặc định `stg`), `OMICALL_TENANT_ID` (tài khoản có nhiều tenant), `OMICALL_API_KEY`.
8. Xác minh bằng danh sách/trạng thái MCP của client, sau đó gọi `get_version` và `login_omicall_mcp`. Tên công cụ có thể mang tiền tố khác nhau; agent phải dò theo hậu tố `get_version`/`login_omicall_mcp`, không hard-code một tiền tố. Nếu client chỉ nạp server mới khi khởi động lại, báo người dùng mở lại phiên một lần và tiếp tục phần việc có thể làm bằng API/giao diện trong phiên hiện tại.
9. Nếu client không hỗ trợ MCP, không cố sửa cấu hình không tồn tại; dùng API/giao diện dự phòng của skill và báo rõ giới hạn đó.

Không cài lại khi server đúng domain đã hoạt động. Nếu cấu hình cùng tên đã tồn tại nhưng sai, agent đọc cấu hình hiện tại, chỉ thay đúng server đó rồi xác minh lại.

Tên công cụ đầy đủ tuỳ client, ví dụ Claude Code dùng `mcp__<tên-server>__<tool>`, OpenCode dùng `<server>_<tool>`. Nếu công cụ đang ở dạng deferred, tải bằng cơ chế tìm công cụ của client một lần cho cả nhóm cần dùng.

## 2. Đăng nhập bằng MCP (ưu tiên số 1)
1. `login_omicall_mcp` (tham số `domain`, `tenant_id` đều tuỳ chọn; mật khẩu lấy từ cấu hình) → nếu trả danh sách nhiều tenant thì `select_tenant(tenant_id)`.
2. `get_service_package` → các module đã bật (`switchboard`, `ticket`, `integrated`, `ai`…) và hạn mức. Đọc ngay để biết thiết kế dùng được gì.
3. **Token cho API mà MCP không có** (callbot, chatbot, OMIFlow): đọc phiên MCP ở `~/.omicall-mcp/session.json` → `accessToken`, bằng `scripts/omi_session.py`. Cùng loại JWT với web, dùng làm `Authorization: Bearer` cho `chatbot-gateway-v1-stg`, `campaign-v1-stg`, `ticket-v2-stg`, `tenant-v1-stg`… Không in token ra hội thoại.
4. Phương án dự phòng (MCP vừa cài nhưng client chưa nạp lại, hoặc không có file phiên): user đăng nhập **một lần** trong browser pane → lấy token từ cookie `{domain}_omicrm_io` key `"2"`. Agent không tự gõ mật khẩu vào form hay API đăng nhập. Nếu lớp an toàn chặn việc đọc cookie thì hoàn tất cấu hình MCP theo mục 1 và yêu cầu mở lại phiên khi client bắt buộc.
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

## 5. Danh mục công cụ theo nhóm và module cần bật
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

## 6. Xử lý lỗi thường gặp
- `npm error code ETARGET` / "No matching version found": npm giữ metadata cũ sau khi gói vừa ra bản mới → xoá cache npx (`rm -rf ~/.npm/_npx`, Windows: `%LOCALAPPDATA%\npm-cache\_npx`) rồi chạy `npx omicall-mcp@latest`.
- Server ngắt ngay khi khởi động: kiểm tra Node.js 18+.
- Công cụ MCP không xuất hiện trong phiên: MCP được nạp khi mở phiên → cài xong phải mở phiên mới; kiểm tra bằng `claude mcp list` hoặc danh sách connector của ứng dụng.
- Lỗi 401 / hết phiên: gọi lại `login_omicall_mcp` (mục 2).
