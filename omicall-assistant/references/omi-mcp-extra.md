# MCP OMI — tài liệu mở rộng cho skill có điều phối (chỉ chép cho `omicall-assistant`)
Các phần trước đây nằm ở đây đã về nguồn duy nhất của từng loại tri thức; file này chỉ còn chỉ đường để tham chiếu cũ không gãy.

## 7. Dựng nhiều artefact
- Thứ tự đợt, cổng của user (xuất bản flow, xuất bản bot, gắn số, gọi thử) và cạnh "bot cần URL flow đã xuất bản": `orchestration.md` mục 2 (sinh từ `shared/skill-graph.json`).
- Khảo sát một lần, `tenant_context.json` chỉ đọc sau đợt 0, sổ chung `manifest.py`, giới hạn song song: `parallel.md` mục 3 và 5.

## 8. Mẫu giao việc cho subagent
Mẫu giao việc, mẫu trả về và danh sách CẤM: **chỉ ở** `parallel.md` mục 5.

## Phụ lục A — Cài và cấu hình MCP OMI theo từng client
Đã chuyển sang README của repo, mục "Cài MCP cho client khác" (cấu hình MCP không chứa mật khẩu: lệnh server là `omi_login.py serve`).

## Phụ lục B — Danh mục công cụ theo nhóm và module cần bật
Đã chuyển sang `omi-mcp-tools.md`.
