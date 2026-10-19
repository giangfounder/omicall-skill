# OMiCall Callbot — Tenant Registry (mẫu)

KHÔNG lưu mật khẩu, token hay thông tin khách hàng vào file này (repo dùng chung). Mật khẩu do user tự nhập trong browser pane; token lấy từ cookie sau khi user đăng nhập.

| # | Domain | Login (email) | tenant_id | agent/ext | Ghi chú / script mẫu |
|---|---|---|---|---|---|
| 1 | `<domain>.omicrm.io` | `<email>` | `<tenant_id>` | `<agent_id>` | `<tên script, id, số intent>` |

## Token extraction (áp dụng chung)
- `~/.omicall-mcp/session.json` → `accessToken` (MCP login), hoặc cookie `{domain}_omicrm_io` (JSON) → key `"2"` = JWT.
- Cookie có thể URL-encode → `urllib.parse.unquote` trước khi `json.loads`; nếu HttpOnly thì dùng CDP `Network.getAllCookies`.
- Base API chung: `https://chatbot-gateway-v1-stg.omicrm.com`.
