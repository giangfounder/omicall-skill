# -*- coding: utf-8 -*-
"""Inject a fetch/XHR captor into the chatbot editor page to learn request/response schemas.

    python inject_captor.py [domain] [--cdp http://127.0.0.1:9222]   # domain mặc định lấy từ phiên MCP (omi_session.py)

Chỉ nối Chrome CDP trên 127.0.0.1 (cổng 9222 mặc định); không đọc cookie hay token từ trang.
Exit: 0 xong; 1 không nối được CDP / không thấy tab; 2 sai cách gọi.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # cdp.py, omi_session.py cùng thư mục

ap = argparse.ArgumentParser(description="Gắn bộ ghi fetch/XHR vào trang editor chatbot qua Chrome CDP (127.0.0.1).")
ap.add_argument("domain", nargs="?", help="domain tenant (<domain>.omicrm.io); bỏ trống → lấy từ phiên MCP")
ap.add_argument("--cdp", default="http://127.0.0.1:9222", help="địa chỉ CDP, chỉ chấp nhận 127.0.0.1/localhost")
a = ap.parse_args()
if (urlparse(a.cdp).hostname or "") not in ("127.0.0.1", "localhost"):
    ap.error("--cdp chỉ được trỏ tới 127.0.0.1/localhost")

if a.domain:
    domain = a.domain
else:
    from omi_session import claims, get_token
    domain = claims(get_token()).get('domain')
if not domain:
    sys.exit("Không xác định được domain — truyền domain làm tham số")

try:
    tabs = json.loads(urllib.request.urlopen(a.cdp.rstrip("/") + "/json", timeout=5).read().decode())
except (urllib.error.URLError, OSError, ValueError) as e:
    print("Không nối được Chrome CDP ở %s (%s) — mở Chrome với --remote-debugging-port=9222 rồi chạy lại"
          % (a.cdp, type(e).__name__), file=sys.stderr)
    sys.exit(1)
host = "%s.omicrm.io" % domain.strip().lower()
# so khớp đúng hostname, không dùng kiểu `domain in url` (tránh khớp nhầm tenant có tên chứa domain)
tab = next((t for t in tabs if t.get("type") == "page" and (urlparse(t.get("url", "")).hostname or "") == host), None)
if not tab:
    sys.exit("Không thấy tab %s.omicrm.io trong Chrome CDP %s" % (domain, a.cdp))

from cdp import CDP
c = CDP(tab["webSocketDebuggerUrl"])
sniff = r"""
(() => {
  if (window.__omiCapsInjected) return {already:true};
  window.__omiCaps = [];
  const want = u => /omiai_assistant|omiai_v2|chatbot-gateway|training/i.test(u) && !/\.png|\.svg|\.js|\.css|\.woff/.test(u);
  const push = (kind, url, body, resp) => {
    try {
      if (window.__omiCaps.length > 200) window.__omiCaps.shift();
      window.__omiCaps.push({t: Date.now(), kind, url: url.slice(0,300), body: (body||'').slice(0,300000), resp: (resp||'').slice(0,300000)});
    } catch(e) {}
  };
  const ofetch = window.fetch;
  window.fetch = function(u, o) {
    try {
      const url = typeof u === 'string' ? u : (u && u.url) || '';
      if (want(url)) {
        if (o && o.body) {
          let b = typeof o.body === 'string' ? o.body : '';
          try { if (o.body instanceof FormData) { b = '[FormData]'; for (const kv of o.body.entries()) b += '\n' + kv[0] + ': ' + (typeof kv[1]==='string'? kv[1].slice(0,300) : '['+kv[1].constructor.name+']'); } } catch(e){}
          push('fetch', url, b);
        }
        return ofetch.apply(this, arguments).then(r => {
          const c2 = r.clone();
          c2.text().then(t => { try { push('fetch-resp', url, null, t); } catch(e){} }).catch(()=>{});
          return r;
        });
      }
    } catch(e) {}
    return ofetch.apply(this, arguments);
  };
  const oXhr = window.XMLHttpRequest.prototype.open;
  window.XMLHttpRequest.prototype.open = function(m, url) {
    this.__u = url; this.__m = m;
    return oXhr.apply(this, arguments);
  };
  const oSend = window.XMLHttpRequest.prototype.send;
  window.XMLHttpRequest.prototype.send = function(body) {
    try {
      const url = this.__u || '';
      if (want(url)) {
        let b = body;
        try { if (body instanceof FormData) { b = '[FormData]'; for (const kv of body.entries()) b += '\n' + kv[0] + ': ' + (typeof kv[1]==='string'? kv[1].slice(0,300) : '['+kv[1].constructor.name+']'); } } catch(e){}
        push('xhr', url, typeof b === 'string' ? b : String(b));
        this.addEventListener('load', () => { try { push('xhr-resp', url, null, this.responseText); } catch(e){} });
      }
    } catch(e) {}
    return oSend.apply(this, arguments);
  };
  window.__omiCapsInjected = true;
  return {ok:true};
})()
"""
print("INJECT:", c.eval_js(sniff))
print("count:", c.eval_js("(window.__omiCaps||[]).length"))
c.close()