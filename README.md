# OMI Skills

Bộ skill dùng chung cho Claude Code và các agent khác, dùng để dựng demo và POC trên OMICall / OMICRM.

| Skill | Dùng để |
|---|---|
| `omicall-assistant` | Cửa vào chung: hỏi việc bằng lời thường, lập kế hoạch rồi gọi đúng skill bên dưới (dùng khi chưa biết chọn skill nào) |
| `omicall-callbot-gen-ai` | Dựng Callbot Gen AI (SmartAgent): ý định, biến thu thập, phân loại, chuyển máy, kết thúc |
| `omicall-callbot-flow` | Dựng Callbot luồng cổ điển (call flow): phân tích kịch bản → chọn ý định/thực thể → sinh dữ liệu huấn luyện sát chữ STT tổng đài (≥200 câu mỗi ý định/thực thể) → nạp Kho tri thức → dựng kịch bản, kiểm tra, gọi thử |
| `omicall-chatbot-gen-ai` | Dựng AI Chatbot (OmiBot) cho Zalo OA, Facebook, LiveTalk |
| `omicall-omiflow` | Thiết kế và dựng OMIFlow (tự động hoá: trigger, điều kiện, phiếu ghi, API, marketing…) |
| `omicall-crm-config` | Skill con của omiflow: thuộc tính Khách hàng và Phiếu ghi, trường mặc định, bộ trạng thái khách, chủ đề và trạng thái phiếu, phân bổ |
| `omicall-pbx-config` | Skill con của omiflow: tổng đài — nhóm nội bộ, lời chào, Tương tác phím (IVR), kịch bản gọi vào, gắn hotline |
| `omicall-ai-insight` | Skill con của omiflow: AI Assistant, Voice Insights, Chat Insights, đánh giá cuộc gọi |

Skill con dùng được riêng (`/omicall-crm-config` …) hoặc được `omicall-omiflow` gọi khi flow thiếu cấu hình nền (bảng *Skill con* trong SKILL.md của omiflow). Cài mọi thư mục `omicall-*` để omiflow tìm thấy skill con.

## Cài đặt

### Bước 1 — Chuẩn bị
- Git, Python 3.10+ (`pip install requests openpyxl`; thêm `python-docx pymupdf` để `extract_text.py` đọc docx/pdf), Node.js 18+ (cho MCP OMI).
- Claude Code (CLI, ứng dụng desktop hoặc extension IDE).

### Bước 2 — Tải repo
```bash
git clone https://github.com/giangfounder/omicall-skill.git
```

### Bước 3 — Đưa skill vào thư mục của agent

**Windows (PowerShell)** — tạo junction để `git pull` là skill cập nhật luôn:
```powershell
$src = "$PWD\omicall-skill"; $dst = "$env:USERPROFILE\.claude\skills"
New-Item -ItemType Directory -Force $dst | Out-Null
Get-ChildItem $src -Directory -Filter 'omicall-*' | ForEach-Object { New-Item -ItemType Junction -Path "$dst\$($_.Name)" -Target $_.FullName }
```

**macOS / Linux**:
```bash
mkdir -p ~/.claude/skills
for d in "$PWD"/omicall-skill/omicall-*/; do n=$(basename "$d"); ln -s "${d%/}" ~/.claude/skills/$n; done
```

Agent khác: trỏ mọi thư mục `omicall-*` vào thư mục skill của agent đó (ví dụ `~/.agents/skills`, `~/.gemini/skills`). Lỡ chép tay cũng được: skill báo có bản mới; khi bạn đồng ý, agent chạy `self_update.py --force --link` để clone repo về `~/omicall-skill` và đổi bản chép tay thành đường dẫn (xem *Phiên bản và cập nhật*).

Kiểm tra: mở Claude Code, gõ `/` và thấy `omicall-assistant`, `omicall-callbot-gen-ai`, `omicall-callbot-flow`, `omicall-chatbot-gen-ai`, `omicall-omiflow`, `omicall-crm-config`, `omicall-pbx-config`, `omicall-ai-insight`.

### Bước 4 — Cài MCP OMI (đăng nhập tự động, tra cứu, kiểm thử)
Mỗi người tự đăng nhập với tài khoản của mình. Thường không cần làm tay: lần đầu gọi skill, agent mở form đăng nhập cục bộ cho bạn điền. Muốn làm trước thì chạy:
```bash
python omicall-skill/omicall-omiflow/scripts/omi_login.py setup --ui
```
- Form (domain, email, mật khẩu) mở ở `127.0.0.1`; mật khẩu đi thẳng vào kho bí mật của hệ điều hành (Windows Credential Manager, macOS Keychain…), không qua agent, không ghi vào file hay biến môi trường.
- Script đăng ký server MCP `OMICall-<domain>` cho Claude Code và Codex với lệnh `omi_login.py serve --domain <domain>` (đọc kho bí mật rồi chạy `npx -y omicall-mcp`): cấu hình MCP không chứa mật khẩu. Không dùng `-e OMICALL_PASSWORD=…` trong lệnh `mcp add`.
- `<domain>` là phần trước `.omicrm.io`, ví dụ `congtyabc` → server `OMICall-congtyabc`.
- Nhiều tenant: mỗi tenant một server (tên `OMICall-<domain>` khác nhau).
- Client khác (Codex, Gemini CLI, OpenCode, Cursor, VS Code…): mục *Cài MCP cho client khác* bên dưới. Cài xong mở phiên mới.
- Kiểm nhanh trong phiên: `python <thư mục skill>/scripts/omi_preflight.py --domain <domain>` (in 1 dòng JSON, không in token).
- Không chạy được MCP thì skill vẫn dùng được: agent mở trang đăng nhập để bạn tự đăng nhập một lần, hoặc bạn tự đặt biến `OMI_TOKEN_FILE`.

### Bước 5 — Dùng
Gõ lệnh skill kèm 3 thông tin: domain, tài khoản, mô tả nghiệp vụ (file hoặc nội dung). Ví dụ:
```
/omicall-callbot-gen-ai https://congtyabc.omicrm.io  <email>  D:\tai-lieu\kich-ban.docx  dựng kịch bản Gen AI
```
Agent tự phân tích, thiết kế, dựng, lưu, kiểm tra và gửi lại link editor.

Callbot luồng cổ điển (call flow):
```
/omicall-callbot-flow https://congtyabc.omicrm.io  <email>  D:\tai-lieu\kich-ban.docx  dựng call flow
```
Agent gửi bảng ý định/thực thể và file dữ liệu huấn luyện để bạn duyệt, đẩy file một lần qua Kho tri thức, dựng kịch bản trong lúc hệ thống huấn luyện, rồi gọi thử khi bạn đưa số điện thoại.

### Dựng nhiều artefact cùng lúc
Bài toán gồm nhiều phần phụ thuộc nhau (ví dụ chatbot thu SĐT → flow webhook tạo phiếu → callbot gọi lại): agent khảo sát tenant một lần (`tenant_context.json`), giao mỗi artefact cho một subagent, ghi id/URL vào sổ chung `scripts/manifest.py` và chỉ nối các phần khi đã GET và kiểm lại. Thứ tự đợt và các cổng chờ bạn (xuất bản flow, xuất bản bot, gắn số, gọi thử): `omicall-assistant/references/orchestration.md` mục 2; sổ chung, mẫu giao việc và danh sách CẤM cho subagent: `references/parallel.md` mục 5. Sau khảo sát đầu, `tenant_context.json` chỉ đọc; giá trị mới ghi qua `manifest.py` (có khoá).

## Cài MCP cho client khác
Cách chuẩn là `omi_login.py setup --ui` (Bước 4), tự đăng ký cho Claude và Codex. Mục này cho client khác (Gemini CLI, OpenCode, Cursor, VS Code…): user chạy `python <thư mục skill>/scripts/omi_login.py setup --ui --client none` (cất mật khẩu vào kho bí mật hệ điều hành, không đăng ký client nào), rồi đăng ký server MCP với lệnh `python <thư mục skill>/scripts/omi_login.py serve --domain <domain>`. Lệnh này đọc kho bí mật rồi chạy `npx -y omicall-mcp`, nên cấu hình MCP **không chứa mật khẩu**. `<thư mục skill>` là thư mục của một skill bất kỳ, ví dụ `<repo>/omicall-omiflow`.

Khi bắt đầu một tác vụ OMI, agent phải tự kiểm tra MCP OMI (`get_version`, `omi_preflight.py`). Nếu chưa có, agent tự làm mọi phần không cần bí mật (nhận diện client, kiểm `node`/`npx`, xác nhận cú pháp, soạn lệnh, kiểm cấu hình sau khi cài) và đưa user đúng MỘT việc: tự chạy lệnh cài đã soạn sẵn (mật khẩu để placeholder) rồi mở phiên mới. Agent không cầm mật khẩu dạng rõ, không tự gõ mật khẩu vào lệnh, form hay API đăng nhập.

1. Kiểm tra các công cụ MCP đang có. Nếu gọi được `get_version` và phiên bản trả về là `1.3.x` hoặc mới hơn thì dùng luôn.
2. Lấy `domain` và email từ yêu cầu hiện tại. Mật khẩu không đi qua agent: user tự điền vào form `setup --ui` (hoặc ô nhập ẩn của `setup` trong terminal), script cất vào kho bí mật của hệ điều hành. Không in lại mật khẩu/token và không ghi chúng vào repo hay file tạm. Thiếu domain hoặc email thì hỏi gộp đúng một lần.
3. Kiểm tra `node` và `npx`. Dùng `npx -y omicall-mcp` để gói được tải tự động khi MCP khởi chạy; không cần cài npm toàn cục.
4. Tự nhận diện **agent/client đang thực thi** qua danh mục công cụ, tiến trình hoặc CLI có trên máy. Skill không được mặc định chỉ có Codex hay Claude. Chỉ cấu hình client đang chạy ở phạm vi người dùng; mỗi môi trường khác khi dùng skill cũng phải tự thực hiện quy trình này. Đặt tên server theo domain (`OMICall-<domain>`) để nhiều tenant không ghi đè nhau.
5. Ưu tiên trình quản lý MCP gốc của client nếu có. Trước khi chạy, gọi `<cli> mcp add --help` để xác nhận cú pháp của phiên bản đang cài; các mẫu chuẩn:

| Agent/client | Lệnh user tự chạy (agent soạn sẵn, phạm vi người dùng) | Xác minh |
|---|---|---|
| Codex CLI/IDE | `codex mcp add OMICall-<domain> -- python <thư mục skill>/scripts/omi_login.py serve --domain <domain>` | `codex mcp list` |
| Claude Code | `claude mcp add OMICall-<domain> --scope user -- python <thư mục skill>/scripts/omi_login.py serve --domain <domain>` (thường không cần: `setup --ui` tự đăng ký) | `claude mcp list` |
| Gemini CLI | `gemini mcp add --scope user --transport stdio OMICall-<domain> python <thư mục skill>/scripts/omi_login.py serve --domain <domain>` (Cần xác nhận cú pháp) | `gemini mcp list` |
| OpenCode | `opencode mcp add OMICall-<domain> --global -- python <thư mục skill>/scripts/omi_login.py serve --domain <domain>` (Cần xác nhận cú pháp) | `opencode mcp list` |

6. Nếu client không có lệnh quản lý MCP, agent tự cập nhật cấu hình **phạm vi người dùng** theo định dạng mà client hỗ trợ; phải đọc và trộn với cấu hình hiện có, không ghi đè các server khác:
   - VS Code/Copilot: ưu tiên `code --add-mcp <JSON>` hoặc User Profile `mcp.json`; Copilot CLI dùng `~/.copilot/mcp-config.json`.
   - Cursor: `~/.cursor/mcp.json`.
   - Claude Desktop: `%APPDATA%\Claude\claude_desktop_config.json` (Windows) hoặc `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).
   - Windsurf: `~/.codeium/windsurf/mcp_config.json`.
   - Gemini CLI không có CLI quản lý: `~/.gemini/settings.json`.
   - Agent khác: tìm cấu hình MCP phạm vi người dùng trong tài liệu/cài đặt của chính client rồi thêm server theo schema của client. Không tạo file chứa mật khẩu trong thư mục dự án.
   - Cấu hình không có ô mật khẩu: lệnh server là `omi_login.py serve`, mật khẩu nằm trong kho bí mật.

Mẫu phổ biến cho Cursor, Claude Desktop, Windsurf, Gemini và các client dùng `mcpServers`:
```json
{
  "mcpServers": {
    "OMICall-<domain>": {
      "command": "python",
      "args": ["<thư mục skill>/scripts/omi_login.py", "serve", "--domain", "<domain>"]
    }
  }
}
```

VS Code dùng khóa gốc `servers` và thêm `"type": "stdio"`. OpenCode v2 dùng `mcp.servers`, `type: "local"`, `command: ["python", "<thư mục skill>/scripts/omi_login.py", "serve", "--domain", "<domain>"]` và `enabled: true`. Trên Windows, nếu client không tìm thấy `python` thì dùng đường dẫn đầy đủ tới `python.exe` hoặc `py`.

7. Biến môi trường tuỳ chọn: `OMICALL_ENV` (mặc định `stg`), `OMICALL_TENANT_ID` (tài khoản có nhiều tenant), `OMICALL_API_KEY`.
8. Xác minh bằng danh sách/trạng thái MCP của client, sau đó gọi `get_version` và `login_omicall_mcp`. Tên công cụ có thể mang tiền tố khác nhau; agent phải dò theo hậu tố `get_version`/`login_omicall_mcp`, không hard-code một tiền tố. Nếu client chỉ nạp server mới khi khởi động lại, báo người dùng mở lại phiên một lần và tiếp tục phần việc có thể làm bằng API/giao diện trong phiên hiện tại.
9. Nếu client không hỗ trợ MCP, không cố sửa cấu hình không tồn tại; dùng API/giao diện dự phòng của skill và báo rõ giới hạn đó.

Không cài lại khi server đúng domain đã hoạt động. Nếu cấu hình cùng tên đã tồn tại nhưng sai, agent đọc cấu hình hiện tại, chỉ thay đúng server đó rồi xác minh lại.

Tên công cụ đầy đủ tuỳ client, ví dụ Claude Code dùng `mcp__<tên-server>__<tool>`, OpenCode dùng `<server>_<tool>`. Nếu công cụ đang ở dạng deferred, tải bằng cơ chế tìm công cụ của client một lần cho cả nhóm cần dùng.

**Rủi ro, Cần xác nhận**: client không chạy được lệnh `python … serve` (chỉ nhận `npx -y omicall-mcp` kèm `env`) thì mật khẩu phải nằm trong biến môi trường của file cấu hình, tức là lưu dạng chữ thường trên đĩa. Không dùng cách này khi chưa hỏi user; cách thay thế (kho bí mật hoặc biến tham chiếu của chính client) cần xác nhận theo từng client.

## Phiên bản và cập nhật
- **Gọi một skill là cập nhật cả bộ**: bước đầu tiên của mọi skill là chạy `scripts/self_update.py`, tối đa 1 lần mỗi giờ cho cả bộ (`--force` để kiểm ngay). Mốc giờ ghi cả khi cập nhật lỗi, nên mất mạng không làm mỗi lần nạp skill chờ lâu. Subagent và chế độ hỏi đáp bỏ qua bước này (`--subagent` hoặc `OMI_SUBAGENT=1`).
  - Cài theo Bước 3 (junction/symlink vào bản git clone): `git pull` cả repo, báo mọi skill vừa đổi phiên bản, nhắc đọc lại SKILL.md nếu vừa đổi.
  - **Skill mới** thêm vào repo: mặc định chỉ báo. Khi bạn đồng ý, agent chạy lại với `--link` để tạo junction/symlink trong thư mục skill của agent (`~/.claude/skills`, `~/.agents/skills`, `~/.gemini/skills`, `~/.codex/skills`); mở phiên mới để thấy. Đường dẫn trỏ vào skill đã bỏ: chỉ cảnh báo, không xoá.
  - Cài bằng cách chép tay: mặc định chỉ báo khi có bản mới. Với `--link` (bạn đồng ý): clone cả repo về `~/omicall-skill`, chuyển thư mục chép tay sang `~/.cache/omicall-skill/backup/` (không xoá) rồi thay bằng đường dẫn vào bản clone. Máy không có git: chỉ báo khi có bản mới.
- Cập nhật tay: `cd omicall-skill && git pull`.
- Phiên bản từng skill nằm ở file `VERSION` (dạng MAJOR.MINOR.PATCH); lịch sử ở [CHANGELOG.md](CHANGELOG.md); mỗi bản có tag `<tên skill>/v<phiên bản>`.
- Quay về bản cũ của một skill: `git checkout omicall-omiflow/v1.4.0 -- omicall-omiflow` (thay tên skill và phiên bản).

### Phát hành bản mới (người bảo trì)
Sửa nội dung skill xong (chưa commit), ở gốc repo chạy:
```bash
python tools/release.py minor "Mô tả thay đổi" omicall-callbot-flow --push
```
- `major`: đổi quy trình/đầu vào; `minor`: thêm quy tắc, bước, script; `patch`: sửa lỗi, sửa chữ.
- Nhiều skill cùng lúc: liệt kê tên skill, hoặc `--all` khi sửa file dùng chung.
- **File dùng chung** (giữ giống hệt ở mọi skill): nguồn duy nhất nằm trong `shared/`, sửa ở đó rồi chạy `python tools/sync_shared.py` (kiểm: `--check`). Danh sách file và skill nhận bản chép: bảng `MAP` trong `tools/sync_shared.py` (nguồn duy nhất). Khối sinh trong SKILL.md, `orchestration.md`, `plan-and-approval.md` và `shared/references/parallel.md` (thứ tự đợt, cổng, quy tắc duyệt, chế độ subagent/hỏi đáp, danh sách CẤM) lấy từ `shared/skill-graph.json`: sửa ở đó, chạy `python tools/gen_skill_links.py` rồi `python tools/sync_shared.py` (kiểm: `--check` cho cả hai).
- Kiểm trước khi phát hành (chạy offline): `python tools/check_skills.py` (Đường nhanh, cụm an toàn, đường dẫn, dữ liệu nhạy cảm; thêm `--baseline-dir <bản chụp>` để so với bản trước khi sửa) và `python tools/selftest.py` (test trong `tests/`, chặn mạng). `release.py` tự từ chối khi file dùng chung lệch, `check_skills` có FAIL, hoặc git theo dõi `credentials.md` ngoài bản mẫu. Commit phát hành gồm thư mục skill được nêu, `CHANGELOG.md` và hạ tầng chung (`shared/`, `tools/`, `tests/`, `README.md`, `.gitignore`, `.gitattributes`). Sửa file dùng chung thì nên phát hành `--all`, vì `sync_shared.py` ghi bản mới vào mọi skill.
- Script tăng `VERSION`, sửa version hiển thị trong `SKILL.md` (`[vX.Y.Z]` đầu mô tả — hiện khi gõ `/`, và dòng "Phiên bản skill"), ghi dòng vào `CHANGELOG.md`, commit, gắn tag và push kèm tag.
- Khi gọi skill, câu đầu tiên agent trả lời là `Đang dùng <tên skill> v<phiên bản>`.

## Đồng bộ giữa nhiều máy
GitHub nhánh `main` là bản chuẩn duy nhất. Mỗi máy thuộc một trong hai vai trò.

**Máy chỉ dùng skill** (không cần token): cài theo Bước 3 (junction hoặc symlink vào bản git clone). Mỗi lần gọi skill, `self_update.py` tự `git pull --ff-only`. Không sửa file trong clone này; muốn sửa thì làm ở máy có vai trò sửa.

**Máy sửa skill** (ví dụ máy chủ EC2, laptop cá nhân): mỗi máy một git clone và junction/symlink vào clone đó. Máy dùng token riêng (fine-grained, chỉ repo này, quyền Contents: Read and write), không dán token vào chat hay vào repo. Đặt tác giả một lần:
```bash
git config user.name "<Họ tên>" && git config user.email <email>
git config pull.rebase true && git config rebase.autoStash true && git config fetch.prune true
```
Quy trình mỗi lần sửa, giống nhau trên mọi máy:
1. Đầu phiên: `git pull --rebase --autostash`.
2. Sửa skill, chạy `python tools/check_skills.py` và `python tools/selftest.py`.
3. Phát hành bằng `python tools/release.py <major|minor|patch> "<ghi chú>" <skill> --push`. Chỉ dùng `release.py` để commit skill. Đừng `git add -A`, vì sẽ kéo theo `credentials.md` thật hoặc file tạm. `release.py` tự kéo bản mới về trước khi tăng `VERSION`, dừng nếu tag đã có hoặc máy chưa đặt tác giả, và khi đẩy bị từ chối vì máy khác vừa đẩy thì dời commit lên trên bản mới rồi thử lại một lần.
4. Đẩy ngay sau khi phát hành, đừng để commit chưa đẩy qua đêm: máy có commit chưa đẩy sẽ không tự cập nhật được khi `main` đổi (`--ff-only` báo lỗi).

**Tránh xung đột**
- Mỗi lúc chỉ một máy sửa một skill. Hai máy sửa hai skill khác nhau thì git tự ghép.
- Xung đột thường rơi vào `VERSION` và `CHANGELOG.md`. `CHANGELOG.md` đã đặt ghép gộp (`.gitattributes`). `VERSION` xung đột nghĩa là hai máy cùng tăng một skill: giữ số cao hơn, chạy lại `release.py` cho phần của mình.
- Không `git push --force`, không sửa lịch sử đã đẩy. Cấu hình `.gitattributes` đưa mọi file về LF, nên Windows và Linux không còn khác nhau toàn file vì xuống dòng.
- Gặp xung đột khi `git pull --rebase`: sửa file báo xung đột, `git add <file>`, `git rebase --continue`. Muốn bỏ: `git rebase --abort`.

**Máy đang chép tay skill (không phải git clone)**: không chép ngược từ thư mục skill lên repo, vì sẽ ghi đè công việc từ máy khác. Chuyển sang git clone: sao lưu thư mục skill hiện có; clone repo; so sánh từng file với bản đang dùng (bỏ qua `credentials.md`) để tìm chỗ chỉ sửa riêng trên máy này; đưa các chỗ đó vào clone và phát hành bằng `release.py`; rồi thay thư mục skill bằng junction/symlink vào clone.

## Lưu ý bảo mật
- Không commit mật khẩu, token hay thông tin tenant của khách hàng. `references/credentials.md` chỉ là mẫu.
- Agent không tự gõ mật khẩu: bạn điền form `omi_login.py setup --ui` (mật khẩu vào kho bí mật hệ điều hành) hoặc tự đăng nhập trên trình duyệt. Không để mật khẩu trong biến môi trường hay file cấu hình MCP.
- Agent không tự bấm Xuất bản, không xoá hay ghi đè dữ liệu của khách nếu chưa được bạn đồng ý.
