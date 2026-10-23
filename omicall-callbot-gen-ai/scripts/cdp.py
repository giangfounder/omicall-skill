# -*- coding: utf-8 -*-
"""Minimal CDP driver using websocket-client: find omicrm tab, navigate, evaluate JS."""
import json, urllib.request, websocket

PORT = 9222


def _tabs():
    return json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=5).read().decode())


def find_omicrm_tab():
    for t in _tabs():
        if t['type'] == 'page' and 'omicrm.io' in t['url']:
            return t
    return None


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=30,
                                              suppress_origin=True, enable_multithread=False)
        self.next_id = 1

    def call(self, method, params=None):
        mid = self.next_id
        self.next_id += 1
        msg = {"id": mid, "method": method}
        if params:
            msg["params"] = params
        self.ws.send(json.dumps(msg))
        while True:
            try:
                data = json.loads(self.ws.recv())
            except Exception:
                continue
            if data.get('id') == mid:
                if 'error' in data:
                    raise RuntimeError(data['error'])
                return data.get('result', {})

    def navigate(self, url):
        self.call('Page.navigate', {'url': url})

    def eval_js(self, expr, as_promise=False):
        r = self.call('Runtime.evaluate', {
            'expression': expr, 'returnByValue': True, 'awaitPromise': as_promise})
        if r.get('exceptionDetails'):
            return 'ERR: ' + json.dumps(r['exceptionDetails'], ensure_ascii=False)
        return r.get('result', {}).get('value')

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass