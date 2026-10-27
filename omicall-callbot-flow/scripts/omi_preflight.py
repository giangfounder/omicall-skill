"""B0 của Đường nhanh: chọn đường làm việc (API / giao diện / chờ user) trong ~10 giây, không gọi mạng.

  python <thư mục skill>/scripts/omi_preflight.py --domain <domain> [--min-minutes 5]

In đúng 1 dòng JSON:
  {token_ok, source, minutes_left, domain_claim, domain_match, credential_stored, node_available, npx_available,
   mcp_session_file, route: api|login|ui|blocked, next_step}
- route=api     : token dùng được cho domain này -> đi đường API (omi_save.py, *_outline.py ...). Exit 0.
- route=login   : token hết hạn / sai tenant / chưa có, nhưng user đã cất thông tin đăng nhập (omi_login.py setup)
                  -> agent TỰ chạy `omi_login.py login --domain <domain>` rồi chạy lại lệnh này. Exit 3.
- route=ui      : có token hỏng/hết hạn, chưa cất thông tin đăng nhập -> gọi login_omicall_mcp nếu MCP có trong
                  phiên; không thì user chạy omi_login.py setup (một lần). Exit 3.
- route=blocked : không có nguồn token nào -> user chạy `omi_login.py setup --domain <domain>` trong terminal của
                  mình (nhập mật khẩu ở ô ẩn, một lần). Trong lúc chờ, làm tiếp phần offline. Exit 3.
Không in token, không đọc cookie, không nhận mật khẩu.
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omi_session  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def setup_command(domain):
    d = domain or '<domain>'
    return 'python "%s" setup --domain %s' % (os.path.join(HERE, 'omi_login.py'), d)


def credential_stored(domain):
    if not domain:
        return False
    try:
        import omi_login
        return bool(omi_login.cred_load(domain)[1])
    except Exception:
        return False


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
    out['credential_stored'] = stored = credential_stored(domain)
    if info['token_ok']:
        out['route'] = 'api'
        out['next_step'] = ('Đi đường API: tenant_survey.py -> dựng payload -> validate -> omi_save.py. '
                            'Token chỉ dùng trong script, không in ra hội thoại.')
    elif stored:
        out['route'] = 'login'
        out['next_step'] = ('Agent tự chạy `python "%s" login --domain %s` (thông tin đăng nhập lấy từ kho bí mật, '
                            'không hỏi user) rồi chạy lại omi_preflight.py. Lỗi đăng nhập thì báo user chạy lại '
                            'setup: `%s`.' % (os.path.join(HERE, 'omi_login.py'), domain or '<domain>',
                                              setup_command(domain)))
    elif info['source']:
        out['route'] = 'ui'
        out['next_step'] = ('Token không dùng được (%s). Nếu công cụ MCP OMI có trong phiên: gọi login_omicall_mcp '
                            '(+ select_tenant đúng domain %s) rồi chạy lại omi_preflight.py. Nếu không: user chạy '
                            'một lần trong terminal `%s` để agent tự đăng nhập từ đó về sau.'
                            % (info['error'], domain or '<domain>', setup_command(domain)))
    else:
        out['route'] = 'blocked'
        out['next_step'] = ('Cần user làm MỘT việc: chạy trong terminal `%s`, nhập email và mật khẩu ở ô nhập ẩn '
                            '(mật khẩu cất vào kho bí mật của hệ điều hành, không qua hội thoại). Script tự đăng nhập '
                            'MCP OMI và đăng ký server MCP; agent đi đường API ngay trong phiên này. Client có công cụ '
                            'mở terminal thì agent mở sẵn lệnh này cho user. Cần Node.js 18+. Dự phòng: lệnh mcp add '
                            'theo references/omi-mcp.md Phụ lục A, hoặc user tự đặt OMI_TOKEN_FILE. '
                            'Trong lúc chờ: làm tiếp phần offline (extract_text, phân tích, spec).'
                            % setup_command(domain))
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
