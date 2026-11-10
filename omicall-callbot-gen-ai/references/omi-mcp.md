# MCP OMI (`omicall-mcp`) — cài đặt, đăng nhập, bản đồ công cụ, tiết kiệm token

## Đọc nhanh
- **Đã có MCP** (gọi được `get_version`, bản 1.3.x trở lên): `login_omicall_mcp` → `select_tenant` (nếu nhiều tenant) → `python <thư mục skill>/scripts/omi_preflight.py --domain <domain>` (đường dẫn tuyệt đối). `route=api` thì đi đường API.
- **Chưa có MCP / chưa đăng nhập** (`route=blocked`): agent chạy nền `python <thư mục skill>/scripts/omi_login.py setup --ui --no-browser`, lấy địa chỉ ở dòng đầu kết quả rồi mở **form đăng nhập cục bộ** (domain, email, mật khẩu) ngay trong khung trình duyệt của agent, đưa ra trước mắt user (không có trình duyệt thì bỏ `--no-browser`). Sau khi hiện form, agent không đọc trang, không chụp ảnh. User điền một lần; mật khẩu đi thẳng từ form vào script (không qua hội thoại, agent không thấy), script cất vào kho bí mật hệ điều hành, tự đăng nhập MCP OMI, đăng ký server `OMICall-<domain>` không chứa mật khẩu; agent đọc dòng `OMI_LOGIN_RESULT=` rồi đi đường API ngay trong phiên. Dự phòng: `setup` không `--ui` trong terminal của user (ô nhập ẩn). Các bước: `omi-login.md` mục 2a.
- **Token hết hạn / sai tenant** (`route=login`) hoặc **script/API gặp 401**: agent TỰ chạy `omi_login.py login --domain <domain> [--tenant-id <id>]`, không hỏi user, rồi chạy lại `omi_preflight.py`.
- **Công cụ MCP báo hết phiên**: gọi lại `login_omicall_mcp`. Vẫn hỏng thì theo bảng quyết định token ngay dưới.
- **Mật khẩu**: không nhận qua chat, không gõ, không đọc hay chụp form, không in hay chuyển cho subagent; user lỡ dán vào chat thì không dùng, không nhắc lại, khuyên đổi (`omi-login.md` mục 2a).
- **Dữ liệu đọc từ MCP**: kiểm `tenant_id` của server với tenant đang làm trước khi tin (tên server không bảo đảm đúng tenant; `omi-login.md` mục 2 ý 6).
- **Nhiều artefact phụ thuộc nhau** (flow + bot + callbot): thứ tự đợt và cổng ở `omicall-assistant` (`orchestration.md` mục 2); sổ chung, mẫu giao việc: `parallel.md` mục 5; danh sách CẤM: `parallel-brief.md`.
- **Đọc cấu hình tenant: API trước, ảnh chụp sau cùng** — mục 4a. Tri thức học được bằng ảnh chụp phải ghi vào reference của skill (`ui-recipes.md` mục 5).
- **Công cụ MCP nào cho bước nào, danh mục theo module, tiết kiệm token**: `omi-mcp-tools.md`.

## Bảng quyết định token (duy nhất)
| Thứ tự | Nguồn token | Ai làm | Khi nào dùng |
|---|---|---|---|
| 1 | MCP OMI: `login_omicall_mcp` hoặc `omi_login.py login` → file phiên (`omi-login.md` mục 2 ý 3), script đọc bằng `scripts/omi_session.py` | agent (thông tin đăng nhập do user cất một lần bằng `omi_login.py setup`) | mặc định |
| 2 | File `OMI_TOKEN_FILE` | user tự đặt biến và file | MCP chưa cài hoặc client chưa nạp |
| 3 | Giao diện (browser pane) | user tự đăng nhập; agent dựng bằng thao tác giao diện | không có 1 và 2 |

Không đọc cookie hay token trong trang (JS, CDP, storage) dưới mọi hình thức: đây không phải một đường lấy token. Không có 1 hoặc 2 thì đi giao diện (3). Kiểm hạn và domain token: `omi_preflight.py` (không in token).

File dùng chung cho mọi skill OMI (7 skill chuyên trách và `omicall-assistant`; mỗi skill giữ một bản giống hệt; nguồn duy nhất trong repo là `shared/references/omi-mcp.md` — sửa ở đó rồi chạy `python tools/sync_shared.py` để chép sang các skill). Cài MCP cho client khác (Codex, Gemini CLI, OpenCode, Cursor, VS Code…): README mục "Cài MCP cho client khác". Node.js 18+.

## 3–5. Công cụ theo bước, tiết kiệm token, danh mục công cụ
Đã chuyển sang `omi-mcp-tools.md` (đọc khi cần). Công cụ ghi chỉ chạy khi user đồng ý từng việc.

## 4a. Thứ tự nguồn khi cần biết tenant đang có gì (BẮT BUỘC)
Mỗi ảnh chụp tốn vài giây và nhiều token; giao diện dùng chung với user nên mỗi thao tác còn có rủi ro đổi form. Đi theo thứ tự, dừng ở bậc đầu tiên trả lời được:
1. **Tri thức đã ghi trong skill** (reference của skill đang dùng và skill con): màn hình nào, trường nào, lựa chọn nào — không mở lại để "xem cho chắc".
2. **`tenant_context.json` ở scratch** của phiên (đã khảo sát thì không khảo sát lại).
3. **Script đọc bằng API**: `tenant_survey.py` (thuộc tính phiếu, trạng thái, phân bổ, artefact) và `config_survey.py` (đầu số + giờ làm việc, kịch bản cuộc gọi, Tương tác phím, nhóm nội bộ/bên ngoài, lời chào, mục đích cuộc gọi, AI Assistant, tiêu chí Chat Insights, tiêu chí đánh giá). Một lệnh thay cho hàng chục lần mở trang. Chạy lại: thêm `--max-age <phút> --domain <domain>` để bỏ qua khi file còn mới và đúng domain (0 request).
4. **MCP OMI** (`get_service_package`, `list_agents`, `search_*`…). Công cụ tổng đài của MCP có thể trả 404 → dùng bậc 3.
5. **Giao diện bằng chữ**: `get_page_text` / `find` / `read_page` sau khi trang tải xong (chờ bằng `find` mốc chữ: rỗng thì `wait` 1 giây rồi tìm lại, tối đa 3 lần; trang trống là chưa tải, không phải lỗi). Đọc trạng thái form/ngăn/canvas: JS chỉ đọc ở `ui-recipes.md` mục 2.
6. **Ảnh chụp** chỉ khi bậc 5 không thấy: danh sách chọn đang mở, canvas, bố cục. Chụp vùng nhỏ (`zoom`) hoặc `scale` 0.5.

Không dùng ảnh chụp để dò vị trí menu khi đã biết đường dẫn: điều hướng thẳng URL (bảng màn hình trong reference của skill).

## 6. Xử lý lỗi thường gặp
- `npm error code ETARGET` / "No matching version found": npm giữ metadata cũ sau khi gói vừa ra bản mới → xoá cache npx (`rm -rf ~/.npm/_npx`, Windows: `%LOCALAPPDATA%\npm-cache\_npx`) rồi chạy `npx omicall-mcp@latest`.
- Server ngắt ngay khi khởi động: kiểm tra Node.js 18+.
- Công cụ MCP không xuất hiện trong phiên: MCP được nạp khi mở phiên → cài xong phải mở phiên mới; kiểm tra bằng `claude mcp list` hoặc danh sách connector của ứng dụng.
- Lỗi 401 / hết phiên: script/API → `omi_login.py login --domain <domain>` (`omi-login.md` mục 2a); công cụ MCP → gọi lại `login_omicall_mcp` (`omi-login.md` mục 2).
