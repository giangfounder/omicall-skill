"""Client mỏng cho API OMICRM mà MCP OMI chưa có (chatbot-gateway, campaign, tenant, ticket...).

    import omi_api
    omi_api.get('chatbot', '/callbot/script/get/<id>')
    omi_api.post_json('campaign', '/omi_v2/campaign/search?page=1&size=50', {})
    omi_api.post_multipart('chatbot', '/callbot/script/add_v2', payload)        # field 'file' = JSON blob
    omi_api.save_json(obj, out_dir=None, name='x.json')                          # luôn qua mask_secrets

- Host lấy theo bảng BASE (môi trường stg, theo tài liệu skill). Env OMI_API_BASE ghi đè MỌI host, OMI_API_BASE_<TÊN>
  (ví dụ OMI_API_BASE_CHATBOT) ghi đè một host — CHỈ dành cho stub test: chỉ nhận host 127.0.0.1/localhost/[::1]
  (host khác -> ApiError, không gửi token đi), và luôn in WARN ra stderr khi đang bật.
- Header Authorization lấy từ omi_session.headers() (kiểm hạn và domain). 401 -> ApiError 'token hết hạn -> omi_preflight'.
- `requests` chỉ được import khi thật sự gọi mạng.
- File ghi ra mặc định nằm trong env OMI_SCRATCH hoặc thư mục tạm; không ghi vào thư mục skill.
"""
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Nguồn: chatbot-gateway (callbot-gen-ai/references/api-reference.md, chatbot api-reference.md),
# campaign (omiflow/references/api-reference.md), tenant/ticket (omiflow SKILL.md Bước 0), agent (callbot-gen-ai SKILL.md),
# external/filestore (chatbot api-reference.md mục RAG).
BASE = {
    'chatbot': 'https://chatbot-gateway-v1-stg.omicrm.com',
    'campaign': 'https://campaign-v1-stg.omicrm.com',
    'tenant': 'https://tenant-v1-stg.omicrm.com',
    'ticket': 'https://ticket-v2-stg.omicrm.com',
    'agent': 'https://agent-v1-stg.omicrm.com',
    'external': 'https://external-v1-stg.omicrm.com',
    'filestore': 'https://filestore-v1-stg.omicrm.com',
}
TIMEOUT = 120
MASK = '***'
SECRET_KEY = re.compile(r'^(authorization|x-access-token|access_?token|refresh_?token|token|id_token|password|passwd|'
                        r'mat_khau|cookie|set-cookie|secret|client_secret|api_?key|x-api-key)$', re.I)
JWT = re.compile(r'eyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]*\.?[A-Za-z0-9_-]*')
BEARER = re.compile(r'(?i)\bbearer\s+(?!<)[A-Za-z0-9._~+/=-]{8,}')


class ApiError(RuntimeError):
    pass


LOCAL_HOSTS = ('127.0.0.1', 'localhost', '::1')
_warned = set()


def _override(name):
    """Env ghi đè host (chỉ cho stub test): nhận khi host là máy cục bộ, in WARN ra stderr; host khác -> ApiError."""
    val = os.environ.get(name)
    if not val:
        return None
    from urllib.parse import urlsplit
    host = (urlsplit(val).hostname or '').lower()
    if host not in LOCAL_HOSTS:
        raise ApiError('env %s trỏ tới host %r: chỉ nhận 127.0.0.1/localhost (stub test). Bỏ biến này để gọi host '
                       'thật — không gửi token tới host lạ.' % (name, host or val))
    if name not in _warned:
        _warned.add(name)
        sys.stderr.write('WARN: %s đang bật -> mọi request tới %s (chỉ dùng cho stub test)\n' % (name, val))
    return val.rstrip('/')


def base(service):
    env = _override('OMI_API_BASE') or _override('OMI_API_BASE_' + service.upper())
    if env:
        return env
    if service not in BASE:
        raise ApiError('không có host cho dịch vụ %r (có: %s)' % (service, ', '.join(BASE)))
    return BASE[service]


def url(service, path):
    if service.startswith('http://') or service.startswith('https://'):
        return service.rstrip('/') + ('/' + path.lstrip('/') if path else '')
    return base(service) + '/' + path.lstrip('/')


def _headers(expect_domain=None):
    import omi_session
    return omi_session.headers(expect_domain=expect_domain)


def _handle(r):
    if r.status_code == 401:
        raise ApiError('401: token hết hạn hoặc sai tenant -> chạy omi_preflight.py rồi đăng nhập lại (login_omicall_mcp)')
    if r.status_code >= 400:
        raise ApiError('HTTP %d: %s' % (r.status_code, mask_text(r.text[:300])))
    try:
        return r.json()
    except ValueError:
        raise ApiError('phản hồi không phải JSON: %s' % mask_text(r.text[:200]))


def _requests():
    try:
        import requests
    except ImportError:
        raise SystemExit('Thiếu thư viện requests: pip install requests')
    return requests


def get(service, path='', expect_domain=None, timeout=TIMEOUT):
    rq = _requests()
    return _handle(rq.get(url(service, path), headers=_headers(expect_domain), timeout=timeout))


def post_json(service, path, body, expect_domain=None, timeout=TIMEOUT):
    rq = _requests()
    return _handle(rq.post(url(service, path), json=body, headers=_headers(expect_domain), timeout=timeout))


def multipart_files(obj, field='file'):
    return {field: ('blob', json.dumps(obj, ensure_ascii=False).encode('utf-8'), 'application/json')}


def post_multipart(service, path, obj, field='file', expect_domain=None, timeout=TIMEOUT):
    rq = _requests()
    return _handle(rq.post(url(service, path), files=multipart_files(obj, field), headers=_headers(expect_domain),
                           timeout=timeout))


def mask_text(s):
    if not isinstance(s, str):
        return s
    s = BEARER.sub('Bearer ' + MASK, s)
    return JWT.sub(MASK, s)


def mask_secrets(obj):
    """Bản sao đã che: giá trị của khoá bí mật (Authorization, token, password, cookie...), header bí mật trong
    danh sách {key, value}, mọi chuỗi dạng JWT hoặc 'Bearer <giá trị>'. Không sửa obj gốc."""
    if isinstance(obj, dict):
        out = {}
        hk = obj.get('key') if isinstance(obj.get('key'), str) else obj.get('name') if isinstance(obj.get('name'), str) else None
        for k, v in obj.items():
            if isinstance(k, str) and SECRET_KEY.match(k) and v not in (None, '', [], {}):
                out[k] = MASK
            elif k == 'value' and hk and SECRET_KEY.match(hk) and v not in (None, ''):
                out[k] = MASK
            else:
                out[k] = mask_secrets(v)
        return out
    if isinstance(obj, list):
        return [mask_secrets(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(mask_secrets(v) for v in obj)
    return mask_text(obj)


def repo_root(skill_dir):
    """Repo nguồn chứa skill: CHỈ xét thư mục cha trực tiếp của skill (bố cục repo/<skill>/), có .git hoặc
    tools/sync_shared.py. Không đi ngược lên xa hơn (HOME có thể là repo git và chứa thư mục tạm). None nếu không phải."""
    d = os.path.dirname(os.path.abspath(skill_dir))
    if os.path.isdir(os.path.join(d, '.git')) or os.path.isfile(os.path.join(d, 'tools', 'sync_shared.py')):
        return d
    return None


def scratch_dir(out_dir=None):
    d = out_dir or os.environ.get('OMI_SCRATCH') or os.path.join(tempfile.gettempdir(), 'omi_scratch')
    d = os.path.abspath(d)
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for root in (skill_dir, repo_root(skill_dir)):
        if root and os.path.normcase(d + os.sep).startswith(os.path.normcase(root + os.sep)):
            raise SystemExit('Không ghi file vào thư mục skill hay repo skill (%s). Dùng --out-dir hoặc env OMI_SCRATCH '
                             'ở ngoài.' % root)
    os.makedirs(d, exist_ok=True)
    return d


def save_json(obj, out_dir=None, name='output.json'):
    path = os.path.join(scratch_dir(out_dir), name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(mask_secrets(obj), f, ensure_ascii=False, indent=1)
    return path


def save_text(text, out_dir=None, name='output.txt'):
    path = os.path.join(scratch_dir(out_dir), name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(mask_text(text))
    return path
