# MCP OMI — tài liệu mở rộng (đọc khi cần)
Phần ít dùng tách khỏi `omi-mcp.md` để mỗi lần nạp skill không tốn token: mục 7-8 (nhiều artefact, giao việc subagent) và Phụ lục A-B (cài MCP theo client, danh mục công cụ theo module). Nội dung giữ nguyên; mục 1-6 nằm ở `omi-mcp.md`.

## 7. Dựng nhiều artefact
Bài toán gồm nhiều artefact phụ thuộc nhau (ví dụ chatbot gọi webhook flow, callbot chuyển dữ liệu sang flow, flow con):
1. **Khảo sát một lần**: `tenant_survey.py --out <scratch>/tenant_context.json` + công cụ MCP (agents, extensions, hotlines, kênh). Subagent đọc file này, không khảo sát lại tenant.
2. **Thứ tự**: flow `WEB_HOOK` lưu nháp → user duyệt xuất bản → GET lại lấy `kick_off.id` và **id mới** (xuất bản đổi id flow, xem `omicall-omiflow/SKILL.md` mục Gotchas "Xuất bản đổi id flow") → gắn URL/id vào bot hoặc callbot → test đầu-cuối khi user đồng ý.
3. **Mỗi artefact một subagent và một tiến trình ghi**; không giao hai việc cùng chạm một artefact.
4. **Tài nguyên chung của tenant chạy tuần tự** (một tiến trình tại một thời điểm): Kho tri thức NLU (mỗi lần nhập là huấn luyện lại toàn bộ), cấu hình AI Assistant, cấu hình phân bổ.
5. **Không truyền token, cookie, mật khẩu cho subagent** (kể cả qua lời giao việc, manifest, file tạm); subagent tự dùng phiên MCP sẵn có qua `omi_session.py`.
6. **Agent chính tự GET và chạy validator lại** trước khi nối artefact này vào artefact khác; không tin báo cáo của subagent khi chưa kiểm.
7. **Sổ chung `manifest.py`** (đặt `OMI_MANIFEST=<scratch>/build_manifest.json`):
   - `manifest.py init`; mỗi subagent sau khi lưu và validate: `manifest.py set <key> --owner <tên> --json '{"id":..,"uuid":..,"status":"draft","webhook_url":..,"verify":"PASS","verify_report":"<file báo cáo>","saved_at":..,"verified_at":..}'`;
   - consumer ghi kèm `"consumed_values":{"<producer>.webhook_url":"<giá trị đã gắn>"}`; đọc giá trị bằng `manifest.py get <producer>.<trường>` ngay trước khi lưu;
   - user xuất bản xong → `manifest.py stale <producer>`, GET lại rồi `set` giá trị mới; `manifest.py check` báo consumer đang trỏ giá trị cũ; `manifest.py gates` liệt kê việc chờ user duyệt;
   - manifest không chứa token hay mật khẩu (script tự từ chối).

## 8. Mẫu giao việc cho subagent
Dán khối này vào lời giao việc (điền phần trong `<>`):
```
Nạp skill <tên skill>. Artefact <key>, owner <tên subagent>. Đọc <scratch>/tenant_context.json và manifest <đường dẫn>; KHÔNG khảo sát lại tenant.
Giao diện: tabs_create một tab riêng rồi truyền tabId ở MỌI lệnh. Chờ khoảng 1 giây trước khi gõ, Ctrl+A rồi gõ,
đọc lại giá trị bằng get_page_text hoặc JS; không dùng Escape để đóng; mỗi browser_batch ≤25 thao tác;
nối cạnh bằng left_click_drag từ chấm nguồn tới chấm đích.
Sau mỗi lần Lưu: tải lại trang → GET → chạy validator của skill (mode post) → manifest.py set <key> kèm verify_report.
CẤM: xuất bản, bật flow, xoá, gắn hotline/kênh thật, gọi điện hoặc gửi tin, nhập mật khẩu, in token,
đụng artefact không phải của mình, tự đánh dấu verified cho template (extract_template --mark-verified).
Trả về: id/uuid đã GET, đường dẫn verify_report, danh sách "Cần xác nhận", việc chưa làm được và lý do.
```

## Phụ lục A — Cài và cấu hình MCP OMI theo từng client (mục 1 cũ)

Cách chuẩn là `omi_login.py setup` (mục 2a), tự đăng ký cho Claude và Codex. Phụ lục này là dự phòng cho client khác (Gemini CLI, OpenCode, Cursor, VS Code…) hoặc khi máy không có kho bí mật: thay `npx -y omicall-mcp` + `env` mật khẩu bằng lệnh `python <thư mục skill>/scripts/omi_login.py serve --domain <domain>` (không `env`) sau khi user đã chạy setup với `--client none`.

Khi bắt đầu một tác vụ OMI, agent phải tự kiểm tra MCP OMI (`get_version`, `omi_preflight.py`). Nếu chưa có, agent tự làm mọi phần không cần bí mật (nhận diện client, kiểm `node`/`npx`, xác nhận cú pháp, soạn lệnh, kiểm cấu hình sau khi cài) và đưa user đúng MỘT việc: tự chạy lệnh cài đã soạn sẵn (mật khẩu để placeholder) rồi mở phiên mới. Agent không cầm mật khẩu dạng rõ, không tự gõ mật khẩu vào lệnh, form hay API đăng nhập.

1. Kiểm tra các công cụ MCP đang có. Nếu gọi được `get_version` và phiên bản trả về là `1.3.x` hoặc mới hơn thì dùng luôn.
2. Lấy `domain` và email từ yêu cầu hiện tại. Mật khẩu không đi qua agent: lệnh soạn sẵn để `<mật khẩu>` làm placeholder, user tự thay trên máy mình; nếu client hỗ trợ kho bí mật, biến nhập bảo mật hoặc mở rộng biến môi trường thì ưu tiên tham chiếu bí mật thay vì ghi giá trị trực tiếp. Không in lại mật khẩu/token và không ghi chúng vào repo hay file tạm. Thiếu domain hoặc email thì hỏi gộp đúng một lần.
3. Kiểm tra `node` và `npx`. Dùng `npx -y omicall-mcp` để gói được tải tự động khi MCP khởi chạy; không cần cài npm toàn cục.
4. Tự nhận diện **agent/client đang thực thi** qua danh mục công cụ, tiến trình hoặc CLI có trên máy. Skill không được mặc định chỉ có Codex hay Claude. Chỉ cấu hình client đang chạy ở phạm vi người dùng; mỗi môi trường khác khi dùng skill cũng phải tự thực hiện quy trình này. Đặt tên server theo domain (`OMICall-<domain>`) để nhiều tenant không ghi đè nhau.
5. Ưu tiên trình quản lý MCP gốc của client nếu có. Trước khi chạy, gọi `<cli> mcp add --help` để xác nhận cú pháp của phiên bản đang cài; các mẫu chuẩn:

| Agent/client | Lệnh user tự chạy (agent soạn sẵn, phạm vi người dùng) | Xác minh |
|---|---|---|
| Codex CLI/IDE | `codex mcp add OMICall-<domain> --env OMICALL_USERNAME=<email> --env OMICALL_PASSWORD=<mật khẩu> --env OMICALL_DOMAIN=<domain> -- npx -y omicall-mcp` | `codex mcp list` |
| Claude Code | `claude mcp add OMICall-<domain> --scope user -e OMICALL_USERNAME=<email> -e OMICALL_PASSWORD=<mật khẩu> -e OMICALL_DOMAIN=<domain> -- npx -y omicall-mcp` | `claude mcp list` |
| Gemini CLI | `gemini mcp add --scope user --transport stdio -e OMICALL_USERNAME=<email> -e OMICALL_PASSWORD=<mật khẩu> -e OMICALL_DOMAIN=<domain> OMICall-<domain> npx -y omicall-mcp` | `gemini mcp list` |
| OpenCode | `opencode mcp add OMICall-<domain> --global --env OMICALL_USERNAME=<email> --env OMICALL_PASSWORD=<mật khẩu> --env OMICALL_DOMAIN=<domain> -- npx -y omicall-mcp` | `opencode mcp list` |

6. Nếu client không có lệnh quản lý MCP, agent tự cập nhật cấu hình **phạm vi người dùng** theo định dạng mà client hỗ trợ; phải đọc và trộn với cấu hình hiện có, không ghi đè các server khác:
   - VS Code/Copilot: ưu tiên `code --add-mcp <JSON>` hoặc User Profile `mcp.json`; Copilot CLI dùng `~/.copilot/mcp-config.json`.
   - Cursor: `~/.cursor/mcp.json`.
   - Claude Desktop: `%APPDATA%\Claude\claude_desktop_config.json` (Windows) hoặc `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).
   - Windsurf: `~/.codeium/windsurf/mcp_config.json`.
   - Gemini CLI không có CLI quản lý: `~/.gemini/settings.json`.
   - Agent khác: tìm cấu hình MCP phạm vi người dùng trong tài liệu/cài đặt của chính client rồi thêm server theo schema của client. Không tạo file chứa mật khẩu trong thư mục dự án.
   - Ô mật khẩu trong file cấu hình để placeholder `<mật khẩu>` cho user tự điền; agent không ghi mật khẩu dạng rõ.

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
