"""Lấy Bearer token OMICRM cho các API mà MCP OMI chưa có (callbot, chatbot, OMIFlow).

Thứ tự: biến môi trường OMI_TOKEN -> file OMI_TOKEN_FILE (do user tự đặt) -> phiên MCP ~/.omicall-mcp/session.json.
Không đọc cookie, không bao giờ in token. Tiền tố 'Bearer ' trong file/biến được tự bỏ.

Dùng trong script:
    from omi_session import get_token, headers, claims
    get_token(min_seconds=None, expect_domain=None)
      - min_seconds: thời gian còn hạn tối thiểu (mặc định 300 giây, ghi đè bằng env OMI_MIN_SECONDS);
      - expect_domain: domain tenant mong đợi (hoặc env OMI_DOMAIN); claim 'domain' lệch -> dừng.
      Token sắp hết hạn, sai domain hoặc không phải JWT -> SystemExit kèm việc cần làm.

Dòng lệnh (kiểm tra nhanh, không in token):
    python omi_session.py [--domain <domain>] [--min-seconds N]
In JSON {tenant_id, domain, agent_id, con_han_giay, nguon}; exit 0 khi token dùng được, 1 khi không.
"""
import argparse
import base64
import binascii
import json
import os
import sys
import time

SESSION = os.path.join(os.path.expanduser('~'), '.omicall-mcp', 'session.json')
KEYS = ('accessToken', 'access_token')
DEFAULT_MIN_SECONDS = 300
FIX_HINT = ('gọi lại login_omicall_mcp (MCP OMI), hoặc nhờ user tự cập nhật file OMI_TOKEN_FILE; '
            'chạy omi_preflight.py để biết bước kế tiếp')


def _session_path():
    return os.path.join(os.path.expanduser('~'), '.omicall-mcp', 'session.json')


def _find(obj):
    if isinstance(obj, dict):
        for k in KEYS:
            if isinstance(obj.get(k), str) and obj[k].count('.') == 2:
                return obj[k]
        for v in obj.values():
            t = _find(v)
            if t:
                return t
    elif isinstance(obj, list):
        for v in obj:
            t = _find(v)
            if t:
                return t
    return None


def _clean(tok):
    tok = (tok or '').strip()
    if tok.lower().startswith('bearer '):
        tok = tok[7:].strip()
    return tok


def find_token():
    """Trả về (token, nguồn) hoặc (None, None). Không kiểm hạn, không in token."""
    if os.environ.get('OMI_TOKEN'):
        return _clean(os.environ['OMI_TOKEN']), 'env OMI_TOKEN'
    path = os.environ.get('OMI_TOKEN_FILE')
    if path:
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                tok = _clean(f.read())
            if tok:
                return tok, 'OMI_TOKEN_FILE'
            print('CẢNH BÁO: OMI_TOKEN_FILE rỗng: %s' % path, file=sys.stderr)
        else:
            print('CẢNH BÁO: OMI_TOKEN_FILE trỏ tới file không tồn tại: %s' % path, file=sys.stderr)
    sess = _session_path()
    if os.path.exists(sess):
        try:
            with open(sess, encoding='utf-8') as f:
                tok = _find(json.load(f))
        except (OSError, ValueError):
            tok = None
            print('CẢNH BÁO: không đọc được phiên MCP %s' % sess, file=sys.stderr)
        if tok:
            return _clean(tok), 'MCP session.json'
    return None, None


def claims(tok):
    """Giải mã phần payload của JWT. Chuỗi không phải JWT -> ValueError có thông báo rõ (không IndexError)."""
    parts = _clean(tok).split('.')
    if len(parts) != 3 or not parts[1]:
        raise ValueError('token không phải JWT (cần 3 phần cách nhau bằng dấu chấm)')
    p = parts[1] + '=' * (-len(parts[1]) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(p.encode('ascii')))
    except (binascii.Error, ValueError, UnicodeError) as e:
        raise ValueError('không giải mã được payload JWT: %s' % type(e).__name__)
    if not isinstance(data, dict):
        raise ValueError('payload JWT không phải object')
    return data


def _norm_domain(d):
    d = (d or '').strip().lower()
    for pre in ('https://', 'http://'):
        if d.startswith(pre):
            d = d[len(pre):]
    d = d.split('/')[0]
    for suf in ('.omicrm.io', '.omicrm.com'):
        if d.endswith(suf):
            d = d[:-len(suf)]
    return d


def inspect(min_seconds=None, expect_domain=None):
    """Trả về dict trạng thái (không chứa token) — dùng cho omi_preflight."""
    if min_seconds is None:
        min_seconds = int(os.environ.get('OMI_MIN_SECONDS') or DEFAULT_MIN_SECONDS)
    expect = _norm_domain(expect_domain or os.environ.get('OMI_DOMAIN'))
    tok, src = find_token()
    info = {'token_ok': False, 'source': src, 'seconds_left': None, 'tenant_id': None, 'agent_id': None,
            'domain_claim': None, 'domain_match': None, 'error': None}
    if not tok:
        info['error'] = 'chưa có token'
        return info, None
    try:
        c = claims(tok)
    except ValueError as e:
        info['error'] = str(e)
        return info, None
    left = int(float(c.get('exp', 0) or 0) - time.time())
    info.update(seconds_left=left, tenant_id=c.get('tenant_id'), domain_claim=c.get('domain'), agent_id=c.get('agent_id'))
    if expect:
        info['domain_match'] = _norm_domain(c.get('domain')) == expect
    if left < min_seconds:
        info['error'] = 'token còn %d giây (< %d)' % (left, min_seconds)
    elif info['domain_match'] is False:
        info['error'] = 'token thuộc domain %r, cần %r' % (c.get('domain'), expect)
    else:
        info['token_ok'] = True
    return info, tok


def get_token(min_seconds=None, expect_domain=None):
    info, tok = inspect(min_seconds, expect_domain)
    if info['token_ok']:
        return tok
    if info['source'] is None:
        raise SystemExit('Chưa có token: ' + FIX_HINT + '.')
    raise SystemExit('Token không dùng được (%s, nguồn %s): %s.' % (info['error'], info['source'], FIX_HINT))


def headers(min_seconds=None, expect_domain=None):
    return {'Authorization': 'Bearer ' + get_token(min_seconds, expect_domain)}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Kiểm tra token OMICRM (không in token).')
    ap.add_argument('--domain', help='domain tenant mong đợi (mặc định env OMI_DOMAIN)')
    ap.add_argument('--min-seconds', type=int, help='số giây còn hạn tối thiểu (mặc định 300)')
    a = ap.parse_args(argv)
    info, _ = inspect(a.min_seconds, a.domain)
    out = {'tenant_id': info['tenant_id'], 'domain': info['domain_claim'], 'agent_id': info['agent_id'],
           'con_han_giay': info['seconds_left'],
           'nguon': info['source'], 'dung_duoc': info['token_ok']}
    if info['error']:
        out['loi'] = info['error']
        out['viec_can_lam'] = FIX_HINT
    print(json.dumps(out, ensure_ascii=False))
    return 0 if info['token_ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
