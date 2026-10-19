# -*- coding: utf-8 -*-
"""Lấy chi tiết bot OmiBot (AI Chatbot) của một tenant, lưu ra file JSON (không in token).

    python omi_bot_lib.py <bot_id> [--domain <domain>]

Token: ưu tiên phiên MCP OMI qua omi_session.py (login_omicall_mcp); dự phòng đọc cookie
`{domain}_omicrm_io` từ Chrome CDP cổng 9222 (user đã tự đăng nhập trong Chrome đó).
"""
import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request

PORT = 9222
BASE = "https://chatbot-gateway-v1-stg.omicrm.com"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def token_from_cdp(domain):
    from cdp import CDP  # cdp.py cùng thư mục
    tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/json" % PORT, timeout=5).read().decode())
    tab = next((t for t in tabs if t["type"] == "page" and domain in t["url"]), None)
    if not tab:
        raise SystemExit("Không thấy tab %s.omicrm.io trong Chrome CDP" % domain)
    c = CDP(tab["webSocketDebuggerUrl"])
    doc = c.eval_js("document.cookie") or ""
    c.close()
    for part in doc.split(";"):
        part = part.strip()
        if part.startswith(domain + "_omicrm_io="):
            return json.loads(urllib.parse.unquote(part.split("=", 1)[1]))["2"]
    raise SystemExit("Cookie chưa có token — user cần đăng nhập trước")


def get_token(domain=None):
    try:
        from omi_session import get_token as mcp_token
        return mcp_token()
    except SystemExit:
        if not domain:
            raise
        return token_from_cdp(domain)


def api(method, path, body=None, tok=None, timeout=60):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    data = None
    if body is not None and method in ("POST", "PUT"):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    with urllib.request.urlopen(req, data=data, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    bot_id = args[0]
    domain = args[args.index("--domain") + 1] if "--domain" in args else os.environ.get("OMICALL_DOMAIN")
    tok = get_token(domain)
    out = api("POST", "/omiai_assistant/get/" + bot_id, {"_id": bot_id}, tok)
    path = os.path.join(tempfile.gettempdir(), "omi_bot_%s.json" % bot_id)
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, default=str)
    print("status_code:", out.get("status_code"), "| payload keys:", list((out.get("payload") or {}).keys()), "| saved:", path)
