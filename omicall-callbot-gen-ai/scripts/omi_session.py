"""Lấy Bearer token OMICRM cho các API mà MCP OMI chưa có (callbot, chatbot, OMIFlow).

Thứ tự: biến môi trường OMI_TOKEN -> file OMI_TOKEN_FILE -> phiên MCP ~/.omicall-mcp/session.json.
Không bao giờ in token. Dùng:
    from omi_session import get_token, headers
    python omi_session.py            # kiểm tra: in tenant_id, domain, hạn dùng (không in token)
"""
import base64
import json
import os
import sys
import time

SESSION = os.path.join(os.path.expanduser('~'), '.omicall-mcp', 'session.json')
KEYS = ('accessToken', 'access_token')


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


def get_token():
    if os.environ.get('OMI_TOKEN'):
        return os.environ['OMI_TOKEN'].strip()
    path = os.environ.get('OMI_TOKEN_FILE')
    if path and os.path.exists(path):
        return open(path, encoding='utf-8').read().strip()
    if os.path.exists(SESSION):
        tok = _find(json.load(open(SESSION, encoding='utf-8')))
        if tok:
            return tok
    raise SystemExit('Chưa có token: gọi login_omicall_mcp (MCP OMI) hoặc đặt OMI_TOKEN_FILE.')


def claims(tok):
    p = tok.split('.')[1]
    p += '=' * (-len(p) % 4)
    return json.loads(base64.urlsafe_b64decode(p))


def headers():
    return {'Authorization': 'Bearer ' + get_token()}


if __name__ == '__main__':
    c = claims(get_token())
    left = int(c.get('exp', 0) - time.time())
    print(json.dumps({'tenant_id': c.get('tenant_id'), 'domain': c.get('domain'),
                      'agent_id': c.get('agent_id'), 'con_han_giay': left}, ensure_ascii=False))
    sys.exit(0 if left > 0 else 1)
