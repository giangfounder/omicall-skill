# MCP OMI (`omicall-mcp`) — cài đặt, đăng nhập, bản đồ công cụ, tiết kiệm token

## Đọc nhanh
- **Đã có MCP** (gọi được `get_version`, bản 1.3.x trở lên): `login_omicall_mcp` → `select_tenant` (nếu nhiều tenant) → `python <thư mục skill>/scripts/omi_preflight.py --domain <domain>` (đường dẫn tuyệt đối). `route=api` thì đi đường API.
- **Chưa có MCP / chưa đăng nhập** (`route=blocked`): agent chạy nền `python <thư mục skill>/scripts/omi_login.py setup --ui --no-browser`, lấy địa chỉ ở dòng đầu kết quả rồi mở **form đăng nhập cục bộ** (domain, email, mật khẩu) ngay trong khung trình duyệt của agent, đưa ra trước mắt user (không có trình duyệt thì bỏ `--no-browser`). Sau khi hiện form, agent không đọc trang, không chụp ảnh. User điền một lần; mật khẩu đi thẳng từ form vào script (không qua hội thoại, agent không thấy), script cất vào kho bí mật hệ điều hành, tự đăng nhập MCP OMI, đăng ký server `OMICall-<domain>` không chứa mật khẩu; agent đọc dòng `OMI_LOGIN_RESULT=` rồi đi đường API ngay trong phiên. Dự phòng: `setup` không `--ui` trong terminal của user (ô nhập ẩn). Mục 2a.
- **Token hết hạn / sai tenant** (`route=login`) hoặc **script/API gặp 401**: agent TỰ chạy `omi_login.py login --domain <domain> [--tenant-id <id>]`, không hỏi user, rồi chạy lại `omi_preflight.py`.
- **Công cụ MCP báo hết phiên**: gọi lại `login_omicall_mcp`. Vẫn hỏng thì theo bảng quyết định token ngay dưới.
- **Nhiều artefact phụ thuộc nhau** (flow + bot + callbot): thứ tự đợt và cổng ở `omicall-assistant` (`orchestration.md` mục 2); sổ chung, mẫu giao việc, danh sách CẤM: `parallel.md` mục 5.
- **Đọc cấu hình tenant: API trước, ảnh chụp sau cùng** — mục 4a. Tri thức học được bằng ảnh chụp phải ghi vào reference của skill (mục 4b).
- **Công cụ MCP nào cho bước nào, danh mục theo module, tiết kiệm token**: `omi-mcp-tools.md`.

## Bảng quyết định token (duy nhất)
| Thứ tự | Nguồn token | Ai làm | Khi nào dùng |
|---|---|---|---|
| 1 | MCP OMI: `login_omicall_mcp` hoặc `omi_login.py login` → file phiên (mục 2 ý 3), script đọc bằng `scripts/omi_session.py` | agent (thông tin đăng nhập do user cất một lần bằng `omi_login.py setup`) | mặc định |
| 2 | File `OMI_TOKEN_FILE` | user tự đặt biến và file | MCP chưa cài hoặc client chưa nạp |
| 3 | Giao diện (browser pane) | user tự đăng nhập; agent dựng bằng thao tác giao diện | không có 1 và 2 |

Không đọc cookie hay token trong trang (JS, CDP, storage) dưới mọi hình thức: đây không phải một đường lấy token. Không có 1 hoặc 2 thì đi giao diện (3). Kiểm hạn và domain token: `omi_preflight.py` (không in token).

File dùng chung cho mọi skill OMI (7 skill chuyên trách và `omicall-assistant`; mỗi skill giữ một bản giống hệt; nguồn duy nhất trong repo là `shared/references/omi-mcp.md` — sửa ở đó rồi chạy `python tools/sync_shared.py` để chép sang các skill). Cài MCP cho client khác (Codex, Gemini CLI, OpenCode, Cursor, VS Code…): README mục "Cài MCP cho client khác". Node.js 18+.

## 2a. Đăng nhập một lần bằng `omi_login.py` (cách chuẩn)
User chỉ cung cấp **domain, email, mật khẩu** — một lần cho mỗi domain, trên máy của user:
0. **Cách mặc định: form cục bộ mở ngay trong agent.** Lần đầu gọi skill (`ensure` trả `need=setup`), agent chạy nền `python "<thư mục skill>/scripts/omi_login.py" setup --ui --no-browser` (form luôn trống, user tự điền). Script chỉ in địa chỉ `http://127.0.0.1:<cổng>/<mã một lần>` ở dòng đầu (chỉ nhận Host/Origin cục bộ, tự tắt sau 10 phút hoặc sau khi xong); agent mở địa chỉ đó trong khung trình duyệt của chính nó (Claude desktop: `mcp__Claude_Browser__navigate` + `show_pane`) và đưa ra trước mắt user. Agent chỉ nói user "điền form vừa mở", **không** `read_page`/`get_page_text`/chụp ảnh form (nút Hiện làm lộ mật khẩu), rồi chờ thông báo tác vụ nền xong và dòng `OMI_LOGIN_RESULT=OK|FAIL`. Không có công cụ trình duyệt thì bỏ `--no-browser` để script tự mở trình duyệt hệ thống. Phần sau (kho bí mật, đăng ký MCP, tenant) giống bước 2-3 dưới; nhiều tenant thì form hiện ô Tenant ID. User lỡ dán mật khẩu vào chat thì xử lý như bước 1.
1. Phương án dự phòng (không mở được trình duyệt, máy từ xa): agent mở terminal cho user (Claude desktop: công cụ terminal `run_in_terminal`; client khác: đưa đúng một lệnh) với `python "<thư mục skill>/scripts/omi_login.py" setup --domain <domain> --email <email>`. User gõ mật khẩu vào ô nhập ẩn. **Mật khẩu không gửi qua hội thoại**: user lỡ dán vào chat thì agent không dùng, không lặp lại, nhắc user gõ vào terminal và nên đổi mật khẩu nếu hội thoại được chia sẻ.
2. Script cất mật khẩu vào kho bí mật của hệ điều hành (Windows Credential Manager, macOS Keychain, Secret Service hoặc `keyring`), email/tenant vào `~/.omicall-mcp/accounts.json` (không bí mật), đăng nhập thử qua MCP OMI (ghi `session.json`), rồi đăng ký server MCP `OMICall-<domain>` cho Claude (CLI `claude` hoặc `~/.claude.json`) và Codex nếu có. Lệnh server là `omi_login.py serve --domain <domain>`: đọc kho bí mật rồi chạy `npx -y omicall-mcp` — cấu hình MCP không chứa mật khẩu. Server cũ cùng tên (mật khẩu trong `env`) bị thay.
3. Kết quả: `route=api` ngay trong phiên hiện tại (đi đường API bằng `omi_session.py`); công cụ MCP `OMICall-<domain>` có từ phiên kế tiếp. Mật khẩu sai → script xoá thông tin vừa cất, user chạy lại setup. Tài khoản nhiều tenant → exit 4 kèm danh sách, chạy lại với `--tenant-id`.
4. Về sau agent tự làm, không hỏi user: hết hạn hoặc 401 → `omi_login.py login --domain <domain>`; kiểm trạng thái → `omi_login.py status --domain <domain>` (không gọi mạng). User muốn xoá → `omi_login.py forget --domain <domain>`.
5. Agent chỉ chạy `setup --ui` (form do user điền); không chạy `setup` kiểu terminal thay user, không đọc, in hay chuyển mật khẩu cho subagent; subagent dùng phiên sẵn có. Không gõ mật khẩu vào form đăng nhập trên trình duyệt (kể cả Chrome MCP).
6. **Form cục bộ chỉ cất token cho script/API, không đăng nhập trang web** (✔ UI 11/2026): khung trình duyệt của agent vẫn ở màn hình đăng nhập `<domain>.omicrm.io` (có thể kèm `?redirect=`). Cần dựng bằng giao diện thì nhắn user một câu: "Anh/chị đăng nhập vào trang đang mở trong khung Trình duyệt giúp em", chờ user báo xong rồi mới `navigate` lại; agent không gõ mật khẩu. Địa chỉ giao diện: `https://<domain>.omicrm.io/<đường dẫn>` (ví dụ `/config/attribute/customer/status`, `/flow/list`, `/flow/edit/<id>`).

## 2. Đăng nhập bằng MCP (ưu tiên số 1)
1. `login_omicall_mcp` (tham số `domain`, `tenant_id` đều tuỳ chọn; mật khẩu lấy từ cấu hình) → nếu trả danh sách nhiều tenant thì `select_tenant(tenant_id)`.
2. `get_service_package` → các module đã bật (`switchboard`, `ticket`, `integrated`, `ai`…) và hạn mức. Đọc ngay để biết thiết kế dùng được gì.
3. **Token cho API mà MCP không có** (callbot, chatbot, OMIFlow): `scripts/omi_session.py` đọc `accessToken` từ file phiên: mỗi phiên Claude Code một file `~/.omicall-mcp/sessions/<CLAUDE_CODE_SESSION_ID>/.omicall-mcp/session.json` (ghi bởi `omi_login.py ensure/login`); chưa có thì đọc file của server `~/.omicall-mcp/servers/<domain>/.omicall-mcp/session.json` (ghi khi gọi công cụ `login_omicall_mcp`), luôn kiểm claim domain. Không có khoá phiên (chạy ngoài Claude Code) thì dùng file chung cũ `~/.omicall-mcp/session.json`. Cùng loại JWT với web, dùng làm `Authorization: Bearer` cho `chatbot-gateway-v1-stg`, `campaign-v1-stg`, `ticket-v2-stg`, `tenant-v1-stg`… Không in token ra hội thoại.
4. Phương án dự phòng (MCP vừa cài nhưng client chưa nạp lại, hoặc không có file phiên): theo bảng quyết định token ở đầu file — user tự đặt `OMI_TOKEN_FILE`, hoặc user đăng nhập **một lần** trong browser pane và agent làm bằng giao diện. Agent không tự gõ mật khẩu vào form hay API đăng nhập, không đọc cookie hay token trong trang. Cần MCP thì hoàn tất cấu hình theo README mục "Cài MCP cho client khác" (user tự chạy lệnh) và yêu cầu mở lại phiên khi client bắt buộc.
5. Hết phiên hoặc lỗi 401: script/API (`omi_api.py`, `omi_save.py`, `tenant_survey.py`…) → agent tự chạy `omi_login.py login --domain <domain>` rồi chạy lại lệnh; đang gọi công cụ MCP mà MCP báo hết phiên → gọi lại `login_omicall_mcp`. Đổi tenant: `logout` rồi đăng nhập với domain mới, hoặc dùng server MCP riêng cho từng tenant.
6. **Tên server MCP không bảo đảm đúng tenant** (✔ 11/2026): gói `omicall-mcp` (1.3.1) nạp `session.json` lúc khởi động và lấy `tenantId` trong đó, **ghi đè** `OMICALL_TENANT_ID`; trước bản sửa, mọi server và script dùng chung một file `~/.omicall-mcp/session.json` nên tất cả chạy nhầm cùng một tenant (tenant đăng nhập gần nhất). Từ bản sửa (omicall-skill 11/2026), `omi_login.py serve` cho mỗi domain một thư mục phiên riêng (đổi `USERPROFILE`/`HOME` của tiến trình MCP sang `~/.omicall-mcp/servers/<domain>`); server đang chạy giữ phiên cũ → **phải mở lại phiên Claude** để server khởi động lại, rồi kiểm từng server. Trước khi tin dữ liệu đọc từ MCP (kênh, phiếu, cuộc gọi, nhân viên), so `tenant_id` trong một kết quả có trường này với tenant đang làm (`omi_login.py ensure` in ra `tenant_id`; `tenant_context.json`). `list_agents` trả kèm toàn bộ quyền (hơn 100 KB dù `size` nhỏ) → để kết quả ra file rồi `grep '"tenant_id"'`, không đọc cả file. Dấu hiệu nghi: đầu số, nhân viên, cuộc gọi không khớp tenant. Lệch → bỏ số liệu của server đó, đọc bằng API (`omi_api.py`, token của `omi_login.py`) hoặc giao diện bằng chữ, báo user cấu hình lại server; mọi kết luận đã rút từ server lệch (ví dụ "chưa kết nối kênh", "chưa có phiếu") phải kiểm lại.

## 3–5. Công cụ theo bước, tiết kiệm token, danh mục công cụ
Đã chuyển sang `omi-mcp-tools.md` (đọc khi cần). Công cụ ghi chỉ chạy khi user đồng ý từng việc.

## 4a. Thứ tự nguồn khi cần biết tenant đang có gì (BẮT BUỘC)
Mỗi ảnh chụp tốn vài giây và nhiều token; giao diện dùng chung với user nên mỗi thao tác còn có rủi ro đổi form. Đi theo thứ tự, dừng ở bậc đầu tiên trả lời được:
1. **Tri thức đã ghi trong skill** (reference của skill đang dùng và skill con): màn hình nào, trường nào, lựa chọn nào — không mở lại để "xem cho chắc".
2. **`tenant_context.json` ở scratch** của phiên (đã khảo sát thì không khảo sát lại).
3. **Script đọc bằng API**: `tenant_survey.py` (thuộc tính phiếu, trạng thái, phân bổ, artefact) và `config_survey.py` (đầu số + giờ làm việc, kịch bản cuộc gọi, Tương tác phím, nhóm nội bộ/bên ngoài, lời chào, mục đích cuộc gọi, AI Assistant, tiêu chí Chat Insights, tiêu chí đánh giá). Một lệnh thay cho hàng chục lần mở trang.
4. **MCP OMI** (`get_service_package`, `list_agents`, `search_*`…). Công cụ tổng đài của MCP có thể trả 404 → dùng bậc 3.
5. **Giao diện bằng chữ**: `get_page_text` / `find` / `read_page` sau khi trang tải xong (chờ 2–3 giây; trang trống là chưa tải, không phải lỗi).
6. **Ảnh chụp** chỉ khi bậc 5 không thấy: danh sách chọn đang mở, canvas, bố cục. Chụp vùng nhỏ (`zoom`) hoặc `scale` 0.5.

Không dùng ảnh chụp để dò vị trí menu khi đã biết đường dẫn: điều hướng thẳng URL (bảng màn hình trong reference của skill).

## 4b. Ghi lại tri thức học bằng giao diện (để lần sau không chụp lại)
Ngay khi một ảnh chụp hoặc lần đọc giao diện cho ra điều skill chưa có (đường dẫn màn hình, nhãn trường, danh sách lựa chọn, quy tắc của form, endpoint thấy được, gotcha), ghi vào reference của skill phụ trách (`pbx-config.md`, `ai-insight.md`, `crm-config.md`, `ui-build-and-test.md`…) kèm nhãn `✔ UI <tháng/năm>`. Chỉ ghi năng lực nền tảng, không ghi dữ liệu khách (tên, số, id). Ghi vào repo nguồn khi user cho phép; chưa được phép thì gom vào báo cáo cuối phiên để user duyệt.

## 4c. Điều khiển giao diện mà không chụp ảnh (BẮT BUỘC khi buộc phải dựng bằng UI)
Chụp ảnh sau mỗi thao tác là lỗi đã gặp (một phiên dựng flow tốn hàng chục ảnh). Làm theo:
1. **Ngân sách ảnh**: tối đa 1 ảnh cho mỗi ngăn/hộp thoại mới mở lần đầu (để biết bố cục), `scale` 0.5; ảnh thứ hai trong cùng ngăn chỉ để `zoom` vùng nhỏ. Quá ngân sách thì dừng, chuyển sang chữ.
2. **Bấm theo `ref`, không theo toạ độ**: `find` (hoặc `read_page` filter `interactive`) ngay trước mỗi lần bấm. Toạ độ đổi mỗi lần ngăn trượt/pane đổi cỡ và gây bấm hụt (đã từng tick hụt nhân viên trong điều kiện tương tác). Hộp tick/ô chọn không hiện ở `read_page` thì `find` theo chữ hiển thị.
3. **Gộp thao tác**: `browser_batch` (tối đa 25) cho chuỗi đã biết rõ (bấm → chờ → gõ → bấm); chỉ đọc kết quả ở cuối chuỗi.
4. **Xác nhận bằng chữ, không bằng ảnh**: `get_page_text` / `find` đọc tóm tắt thẻ nút ("Không có tương tác trong 4 phút từ …"), hoặc `javascript_tool` đọc `input.value`. Ảnh chụp trễ 1–2 thao tác nên dễ gây hiểu nhầm; dùng `wait` 2 giây rồi đọc chữ.
5. **Chứng cứ cuối là API, không phải ảnh**: sau khi lưu, GET lại (`flow_outline.py --save <id>`, `filter_contacts/get_list`…) và đọc trường cần kiểm. Chỉ chụp ảnh cuối phiên khi user cần xem.
6. **Pane**: `resize_window` 1500x900 một lần đầu phiên (pane hẹp làm drawer bị cắt), nhớ trả `preset desktop` khi xong.
7. **Dựng ít nút nhất có thể trên UI**: mỗi loại nút một lần để lấy schema, phần còn lại sinh bằng script từ bản GET (xem `omicall-omiflow/references/node-catalog.md` mục 6).

## 6. Xử lý lỗi thường gặp
- `npm error code ETARGET` / "No matching version found": npm giữ metadata cũ sau khi gói vừa ra bản mới → xoá cache npx (`rm -rf ~/.npm/_npx`, Windows: `%LOCALAPPDATA%\npm-cache\_npx`) rồi chạy `npx omicall-mcp@latest`.
- Server ngắt ngay khi khởi động: kiểm tra Node.js 18+.
- Công cụ MCP không xuất hiện trong phiên: MCP được nạp khi mở phiên → cài xong phải mở phiên mới; kiểm tra bằng `claude mcp list` hoặc danh sách connector của ứng dụng.
- Lỗi 401 / hết phiên: script/API → `omi_login.py login --domain <domain>` (mục 2a); công cụ MCP → gọi lại `login_omicall_mcp` (mục 2).
