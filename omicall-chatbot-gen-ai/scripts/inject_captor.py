# -*- coding: utf-8 -*-
"""Gắn bộ ghi fetch/XHR vào trang editor chatbot (Chrome CDP) để học schema request/response từ thao tác UI.

    python inject_captor.py [domain] [--cdp http://127.0.0.1:9222]   # domain mặc định lấy từ phiên MCP (omi_session.py)

Bộ ghi lưu vào `window.__omiCaps` (tối đa ~200 mục; url, body, response đã cắt ngắn) cho các URL
omiai_assistant / omiai_v2 / chatbot-gateway / training. Bí mật được che TRƯỚC khi lưu (hàm push):
  - khoá JSON khớp SECRET_KEY_RE (authorization, token, secret, api key, password, cookie) → '***';
    cặp header dạng {"key"/"name": <khoá bí mật>, "value": ...} → value '***';
  - chuỗi JWT `eyJ...` ở bất kỳ đâu (body, response, url) → '***';
  - văn bản không phải JSON (FormData, query string): `<khoá bí mật>: ...` / `<khoá bí mật>=...` → '***'.
Che theo mẫu nên không bảo đảm tuyệt đối: vẫn không dán nguyên __omiCaps vào tài liệu/repo.

Chỉ nối Chrome CDP trên 127.0.0.1/localhost; không đọc cookie hay token từ trang.
Exit: 0 xong; 1 không nối được CDP / không thấy tab; 2 sai cách gọi.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # cdp.py, omi_session.py cùng thư mục

# Nguồn regex dùng chung cho Python (test) và JS (nhúng vào SNIFF) — sửa ở đây là đổi cả hai.
SECRET_KEY_RE = r"authorization|token|secret|api[_-]?key|password|cookie"
JWT_RE = r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]*)?"
# `<khoá bí mật>: giá trị` / `<khoá bí mật>=giá trị` trong văn bản thường (FormData, query string); bỏ qua "Bearer ".
KV_RE = r"((?:" + SECRET_KEY_RE + r")[\w-]*[\"']?\s*[:=]\s*[\"']?)(?:bearer\s+)?[^\s&\"',;}]+"
MASK = "***"


def redact_text(s):
    """Bản Python của redactText trong SNIFF (để test): JSON thì che theo khoá, không phải JSON thì che JWT + khoá=giá trị."""
    if not isinstance(s, str) or not s:
        return s
    try:
        obj = json.loads(s)
    except ValueError:
        obj = None
    if isinstance(obj, (dict, list)):
        return json.dumps(redact_obj(obj), ensure_ascii=False, separators=(",", ":"))
    s = re.sub(JWT_RE, MASK, s)
    return re.sub(KV_RE, lambda m: m.group(1) + MASK, s, flags=re.I)


def redact_obj(o):
    if isinstance(o, list):
        return [redact_obj(v) for v in o]
    if isinstance(o, dict):
        out = {}
        pair_secret = any(isinstance(o.get(k), str) and re.search(SECRET_KEY_RE, o[k], re.I) for k in ("key", "name"))
        for k, v in o.items():
            if re.search(SECRET_KEY_RE, str(k), re.I) or (pair_secret and k == "value"):
                out[k] = MASK
            else:
                out[k] = redact_obj(v)
        return out
    if isinstance(o, str):
        return redact_text(o)
    return o


SNIFF = r"""
(() => {
  if (window.__omiCapsInjected) return {already:true};
  window.__omiCaps = [];
  const want = u => /omiai_assistant|omiai_v2|chatbot-gateway|training/i.test(u) && !/\.png|\.svg|\.js|\.css|\.woff/.test(u);
  const SK = new RegExp(%(sk)s, 'i');
  const JWT = new RegExp(%(jwt)s, 'g');
  const KV = new RegExp(%(kv)s, 'gi');
  const M = '***';
  const redactObj = o => {
    if (Array.isArray(o)) return o.map(redactObj);
    if (o && typeof o === 'object') {
      const pair = ['key', 'name'].some(k => typeof o[k] === 'string' && SK.test(o[k]));
      const out = {};
      for (const k of Object.keys(o)) out[k] = (SK.test(k) || (pair && k === 'value')) ? M : redactObj(o[k]);
      return out;
    }
    return typeof o === 'string' ? redactText(o) : o;
  };
  const redactText = s => {
    if (typeof s !== 'string' || !s) return s;
    let obj = null;
    try { obj = JSON.parse(s); } catch(e) {}
    if (obj && typeof obj === 'object') return JSON.stringify(redactObj(obj));
    return s.replace(JWT, M).replace(KV, (m, p1) => p1 + M);
  };
  const push = (kind, url, body, resp) => {
    try {
      if (window.__omiCaps.length > 200) window.__omiCaps.shift();
      // che bí mật trên bản đầy đủ rồi mới cắt (cắt trước có thể làm hỏng JSON và lọt giá trị)
      window.__omiCaps.push({t: Date.now(), kind, url: redactText(String(url||'')).slice(0,300),
        body: redactText(String(body||'')).slice(0,300000), resp: redactText(String(resp||'')).slice(0,300000)});
    } catch(e) {}
  };
  window.__omiRedact = redactText;
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
""" % {"sk": json.dumps(SECRET_KEY_RE), "jwt": json.dumps(JWT_RE), "kv": json.dumps(KV_RE)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gắn bộ ghi fetch/XHR (đã che bí mật) vào trang editor chatbot qua "
                                             "Chrome CDP (127.0.0.1).")
    ap.add_argument("domain", nargs="?", help="domain tenant (<domain>.omicrm.io); bỏ trống → lấy từ phiên MCP")
    ap.add_argument("--cdp", default="http://127.0.0.1:9222", help="địa chỉ CDP, chỉ chấp nhận 127.0.0.1/localhost")
    a = ap.parse_args(argv)
    if (urlparse(a.cdp).hostname or "") not in ("127.0.0.1", "localhost"):
        ap.error("--cdp chỉ được trỏ tới 127.0.0.1/localhost")

    if a.domain:
        domain = a.domain
    else:
        from omi_session import claims, get_token
        domain = claims(get_token()).get('domain')
    if not domain:
        print("Không xác định được domain — truyền domain làm tham số", file=sys.stderr)
        return 1

    try:
        tabs = json.loads(urllib.request.urlopen(a.cdp.rstrip("/") + "/json", timeout=5).read().decode())
    except (urllib.error.URLError, OSError, ValueError) as e:
        print("Không nối được Chrome CDP ở %s (%s) — mở Chrome với --remote-debugging-port=9222 rồi chạy lại"
              % (a.cdp, type(e).__name__), file=sys.stderr)
        return 1
    host = "%s.omicrm.io" % domain.strip().lower()
    # so khớp đúng hostname, không dùng kiểu `domain in url` (tránh khớp nhầm tenant có tên chứa domain)
    tab = next((t for t in tabs if t.get("type") == "page" and (urlparse(t.get("url", "")).hostname or "") == host), None)
    if not tab:
        print("Không thấy tab %s.omicrm.io trong Chrome CDP %s" % (domain, a.cdp), file=sys.stderr)
        return 1

    from cdp import CDP
    c = CDP(tab["webSocketDebuggerUrl"])
    print("INJECT:", c.eval_js(SNIFF))
    print("count:", c.eval_js("(window.__omiCaps||[]).length"))
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
