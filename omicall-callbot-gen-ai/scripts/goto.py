# -*- coding: utf-8 -*-
"""Mở trình biên tập Callbot cho user xem realtime trên Chrome CDP (port 9222).

  python goto.py <script_id> [--domain <domain>] [--port 9222]

- domain mặc định lấy từ phiên (omi_session, không in token);
- chọn tab có URL chứa '/ai/callbot/script/' đúng domain; không có thì tab bất kỳ cùng domain;
- điều hướng bằng scripts/cdp.py (cần `pip install websocket-client`) và đọc phản hồi Page.navigate.
--help không gọi mạng.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def utf8_stdout():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def pick_tab(tabs, domain):
    host = "%s.omicrm.io" % domain
    same = []
    for t in tabs:
        if t.get("type") != "page":
            continue
        try:
            h = urllib.parse.urlparse(t.get("url") or "").hostname
        except ValueError:
            continue
        if h == host:
            same.append(t)
    for t in same:
        if "/ai/callbot/script/" in (t.get("url") or ""):
            return t
    return same[0] if same else None


def main(argv=None):
    utf8_stdout()
    ap = argparse.ArgumentParser(description="Điều hướng tab OMiCRM tới trình biên tập Callbot (Chrome CDP).")
    ap.add_argument("script_id", help="id kịch bản (lấy id mới nhất sau mỗi lần lưu)")
    ap.add_argument("--domain", help="tên miền tenant, phần trước .omicrm.io (mặc định lấy từ phiên MCP)")
    ap.add_argument("--port", type=int, default=9222, help="cổng remote debugging của Chrome")
    a = ap.parse_args(argv)

    domain = a.domain
    if not domain:
        from omi_session import claims, get_token
        domain = claims(get_token()).get("domain")
    if not domain:
        print("Không xác định được domain; truyền --domain <domain>", file=sys.stderr)
        return 2
    url = "https://%s.omicrm.io/ai/callbot/script/update/%s?lng=vi" % (domain, urllib.parse.quote(str(a.script_id), safe=""))

    try:
        raw = urllib.request.urlopen("http://127.0.0.1:%d/json" % a.port, timeout=5).read().decode("utf-8")
        tabs = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        print("Không kết nối được Chrome CDP ở cổng %d: %s" % (a.port, e), file=sys.stderr)
        return 1
    tab = pick_tab(tabs, domain)
    if not tab:
        print("Không có tab nào của %s.omicrm.io trong Chrome CDP" % domain, file=sys.stderr)
        return 1
    try:
        import cdp
    except ImportError as e:
        print("Thiếu thư viện cho cdp.py (%s): pip install websocket-client" % e, file=sys.stderr)
        return 1
    cdp.PORT = a.port
    c = cdp.CDP(tab["webSocketDebuggerUrl"])
    try:
        res = c.call("Page.navigate", {"url": url})
    except Exception as e:  # noqa: BLE001
        print("Page.navigate lỗi: %s" % e, file=sys.stderr)
        return 1
    finally:
        c.close()
    if isinstance(res, dict) and res.get("errorText"):
        print("Page.navigate lỗi: %s" % res["errorText"], file=sys.stderr)
        return 1
    print("navigated to: %s" % url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
