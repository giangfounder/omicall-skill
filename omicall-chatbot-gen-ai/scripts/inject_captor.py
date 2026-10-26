# -*- coding: utf-8 -*-
"""Inject a fetch/XHR captor into the chatbot editor page to learn request/response schemas.

    python inject_captor.py [domain]   # domain mặc định lấy từ phiên MCP (omi_session.py)
"""
import os, sys, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # cdp.py, omi_session.py cùng thư mục
from cdp import CDP

if len(sys.argv) > 1:
    domain = sys.argv[1]
else:
    from omi_session import claims, get_token
    domain = claims(get_token()).get('domain')

tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=5).read().decode())
tab = next((t for t in tabs if t["type"] == "page" and "%s.omicrm.io" % domain in t["url"]), None)
if not tab:
    sys.exit("Không thấy tab %s.omicrm.io trong Chrome CDP cổng 9222" % domain)

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