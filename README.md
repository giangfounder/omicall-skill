# OMI Skills

Bộ skill dùng chung cho Claude Code và các agent khác, dùng để dựng demo và POC trên OMICall / OMICRM.

| Skill | Dùng để |
|---|---|
| `omicall-callbot-gen-ai` | Dựng Callbot Gen AI (SmartAgent): ý định, biến thu thập, phân loại, chuyển máy, kết thúc |
| `omicall-chatbot-gen-ai` | Dựng AI Chatbot (OmiBot) cho Zalo OA, Facebook, LiveTalk |
| `omicall-omiflow` | Thiết kế và dựng OMIFlow (tự động hoá: trigger, điều kiện, phiếu ghi, API, marketing…) |

## Cài đặt

### Bước 1 — Chuẩn bị
- Git, Python 3.10+ (`pip install requests`), Node.js 18+ (cho MCP OMI).
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
foreach ($n in 'omicall-callbot-gen-ai','omicall-chatbot-gen-ai','omicall-omiflow') { New-Item -ItemType Junction -Path "$dst\$n" -Target "$src\$n" }
```

**macOS / Linux**:
```bash
mkdir -p ~/.claude/skills
for n in omicall-callbot-gen-ai omicall-chatbot-gen-ai omicall-omiflow; do ln -s "$PWD/omicall-skill/$n" ~/.claude/skills/$n; done
```

Agent khác: trỏ hoặc chép 3 thư mục vào thư mục skill của agent đó (ví dụ `~/.agents/skills`, `~/.gemini/skills`).

Kiểm tra: mở Claude Code, gõ `/` và thấy `omicall-callbot-gen-ai`, `omicall-chatbot-gen-ai`, `omicall-omiflow`.

### Bước 4 — Cài MCP OMI (đăng nhập tự động, tra cứu, kiểm thử)
Mỗi người tự chạy với tài khoản của mình (mật khẩu chỉ nằm trên máy bạn):
```bash
claude mcp add OMICall-mcp --scope user -e OMICALL_USERNAME=<email> -e OMICALL_PASSWORD=<mật khẩu> -e OMICALL_DOMAIN=<domain> -- npx omicall-mcp
```
- `<domain>` là phần trước `.omicrm.io`, ví dụ `congtyabc`.
- Nhiều tenant: thêm mỗi tenant một server với tên khác, ví dụ `OMICall-congtyabc`.
- Không chạy được MCP thì skill vẫn dùng được: agent mở trang đăng nhập để bạn tự đăng nhập một lần.

### Bước 5 — Dùng
Gõ lệnh skill kèm 3 thông tin: domain, tài khoản, mô tả nghiệp vụ (file hoặc nội dung). Ví dụ:
```
/omicall-callbot-gen-ai https://congtyabc.omicrm.io  <email>  D:\tai-lieu\kich-ban.docx  dựng kịch bản Gen AI
```
Agent tự phân tích, thiết kế, dựng, lưu, kiểm tra và gửi lại link editor.

## Cập nhật
```bash
cd omicall-skill && git pull
```

## Lưu ý bảo mật
- Không commit mật khẩu, token hay thông tin tenant của khách hàng. `references/credentials.md` chỉ là mẫu.
- Agent không tự gõ mật khẩu: đăng nhập qua MCP OMI (bạn tự cấu hình) hoặc bạn tự đăng nhập trên trình duyệt.
- Agent không tự bấm Xuất bản, không xoá hay ghi đè dữ liệu của khách nếu chưa được bạn đồng ý.
