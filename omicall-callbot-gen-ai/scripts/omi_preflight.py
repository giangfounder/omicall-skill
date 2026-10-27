"""B0 của Đường nhanh: chọn đường làm việc (API / giao diện / chờ user) trong ~10 giây, không gọi mạng.

  python <thư mục skill>/scripts/omi_preflight.py --domain <domain> [--min-minutes 5]

In đúng 1 dòng JSON:
  {token_ok, source, minutes_left, domain_claim, domain_match, node_available, npx_available,
   mcp_session_file, route: api|ui|blocked, next_step}
- route=api     : token dùng được cho domain này -> đi đường API (omi_save.py, *_outline.py ...). Exit 0.
- route=ui      : có token nhưng hết hạn / sai domain / hỏng -> gọi lại login_omicall_mcp (+ select_tenant) rồi chạy
                  lại lệnh này; chưa làm được thì dựng bằng giao diện. Exit 3.
- route=blocked : không có nguồn token nào -> đưa user đúng MỘT việc (tự chạy lệnh mcp add đã soạn sẵn với
                  placeholder rồi mở phiên mới, HOẶC tự đặt OMI_TOKEN_FILE). Trong lúc chờ, làm tiếp phần offline. Exit 3.
Không in token, không đọc cookie, không nhận mật khẩu.
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omi_session  # noqa: E402


def mcp_add_command(domain):
    d = domain or '<domain>'
    """Lệnh mẫu cho Claude Code. Client khác có cú pháp khác (Codex --env, Gemini đặt tên ở cuối + --transport stdio,
    OpenCode --global --env): mẫu ở references/omi-mcp.md Phụ lục A."""
    return ('claude mcp add OMICall-%s --scope user -e OMICALL_USERNAME=<email> -e OMICALL_PASSWORD=<mật khẩu> '
            '-e OMICALL_DOMAIN=%s -- npx -y omicall-mcp' % (d, d))


def decide(domain, min_minutes=5):
    info, _tok = omi_session.inspect(min_seconds=int(min_minutes * 60), expect_domain=domain)
    left = info['seconds_left']
    out = {
        'token_ok': info['token_ok'],
        'source': info['source'],
        'minutes_left': None if left is None else round(left / 60.0, 1),
        'domain_claim': info['domain_claim'],
        'domain_match': info['domain_match'],
        'node_available': bool(shutil.which('node')),
        'npx_available': bool(shutil.which('npx')),
        'mcp_session_file': os.path.exists(omi_session._session_path()),
    }
    if info['token_ok']:
        out['route'] = 'api'
        out['next_step'] = ('Đi đường API: tenant_survey.py -> dựng payload -> validate -> omi_save.py. '
                            'Token chỉ dùng trong script, không in ra hội thoại.')
    elif info['source']:
        out['route'] = 'ui'
        out['next_step'] = ('Token không dùng được (%s). Nếu công cụ MCP OMI có trong phiên: gọi login_omicall_mcp '
                            '(+ select_tenant đúng domain %s) rồi chạy lại omi_preflight.py. Nếu không: user tự cập nhật '
                            'file OMI_TOKEN_FILE, hoặc dựng bằng giao diện (user tự đăng nhập trên trình duyệt).'
                            % (info['error'], domain or '<domain>'))
    else:
        out['route'] = 'blocked'
        out['next_step'] = ('Cần user làm MỘT việc rồi mở phiên mới: (a) user tự chạy lệnh mcp add của client đang dùng — '
                            'Claude Code: `%s`; client khác (Codex, Gemini CLI, OpenCode...): mẫu lệnh ở '
                            'references/omi-mcp.md Phụ lục A (cú pháp khác nhau, không chỉ đổi tên CLI); user tự điền '
                            '<email> và <mật khẩu> trên máy mình; cần Node.js 18+ — hoặc '
                            '(b) user tự đặt biến OMI_TOKEN_FILE trỏ tới file chứa token. Agent không cầm mật khẩu. '
                            'Trong lúc chờ: làm tiếp phần offline (extract_text, phân tích, spec).'
                            % mcp_add_command(domain))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--domain', required=True, help='domain tenant (phần trước .omicrm.io)')
    ap.add_argument('--min-minutes', type=float, default=5, help='số phút còn hạn tối thiểu (mặc định 5)')
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    out = decide(omi_session._norm_domain(a.domain), a.min_minutes)
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out['route'] == 'api' else 3


if __name__ == '__main__':
    sys.exit(main())
