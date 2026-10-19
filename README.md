# OMI Skills

Bộ skill dùng chung cho Claude Code / agent, phục vụ dựng demo và POC trên OMiCALL / OMiCRM.

| Skill | Dùng để |
|---|---|
| `omicall-callbot-gen-ai` | Dựng Callbot Gen AI (SmartAgent): intent, biến thu thập, phân loại, kết thúc, lưu qua API |
| `omicall-chatbot-gen-ai` | Dựng AI Chatbot (OmiBot) cho Zalo OA, Facebook, LiveTalk |
| `omicall-omiflow` | Workflow Builder (OMIFlow) |
| `ai-chatbot-builder` | Playbook chung thiết kế chatbot, mẫu prompt và intent |

## Cài đặt
Chép từng thư mục skill vào thư mục skill của agent, ví dụ `~/.claude/skills/` (Claude Code) hoặc `~/.agents/skills/`.

## Lưu ý bảo mật
- Không commit mật khẩu, token hay thông tin tenant của khách hàng. File `references/credentials.md` chỉ là mẫu.
- Đăng nhập luôn do người dùng tự thực hiện trong trình duyệt.
