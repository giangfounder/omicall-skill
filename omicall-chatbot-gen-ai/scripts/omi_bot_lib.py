# -*- coding: utf-8 -*-
"""Read oanhtesting session token from Chrome cookie, save to file, fetch omi bot detail."""
import os, tempfile, sys, json, time, urllib.request, urllib.parse, websocket

PORT = 9222
BOT_ID = "6ab9d5fc82ddf2619521d99a"
TENANT_ID = "6ab9d2c8949dfc02813731e6"
BASE = "https://chatbot-gateway-v1-stg.omicrm.com"


def get_cookie():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # cdp.py cùng thư mục
    from cdp import CDP
    tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/json" % PORT, timeout=5).read().decode())
    tab = None
    for t in tabs:
        if t["type"] == "page" and "oanhtesting" in t["url"]:
            tab = t
            break
    c = CDP(tab["webSocketDebuggerUrl"])
    doc = c.eval_js("document.cookie") or ""
    c.close()
    for part in doc.split(";"):
        part = part.strip()
        if part.startswith("oanhtesting_omicrm_io="):
            raw = urllib.parse.unquote(part.split("=", 1)[1])
            return json.loads(raw)
    return None


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
    ck = get_cookie()
    tok = ck["2"]
    json.dump({"token": tok, "tenant_id": TENANT_ID, "agent_id": ck.get("6ab9d2c9949dfc0281373201", ""),
               "contact_id": "6ab9d2d00cc4e3120f97c662"},
              open(os.path.join(tempfile.gettempdir(), "oanh_session.json"), "w", encoding="utf-8"))
    print("saved token len", len(tok))
    out = api("POST", "/omiai_assistant/get/" + BOT_ID, {"_id": BOT_ID}, tok)
    json.dump(out, open(os.path.join(tempfile.gettempdir(), "oanh_bot.json"), "w", encoding="utf-8"), ensure_ascii=False, default=str)
    print("GET bot detail status_code:", out.get("status_code"), "| payload keys:", list((out.get("payload") or {}).keys()))