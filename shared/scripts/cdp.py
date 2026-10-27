# -*- coding: utf-8 -*-
"""Minimal CDP driver using websocket-client: find omicrm tab, navigate, evaluate JS.

call() có hạn chót (mặc định 30 giây, đổi bằng tham số timeout): hết hạn -> TimeoutError; socket đóng -> ConnectionError.
Chỉ bỏ qua thông điệp không phải JSON; mọi lỗi khác được ném ra (không lặp vô hạn).
"""
import json, time, urllib.request, websocket

PORT = 9222
DEFAULT_TIMEOUT = 30


def _tabs():
    return json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=5).read().decode())


def find_omicrm_tab():
    for t in _tabs():
        if t['type'] == 'page' and 'omicrm.io' in t['url']:
            return t
    return None


class CDP:
    def __init__(self, ws_url, timeout=DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.ws = websocket.create_connection(ws_url, timeout=timeout,
                                              suppress_origin=True, enable_multithread=False)
        self.next_id = 1

    def call(self, method, params=None, timeout=None):
        mid = self.next_id
        self.next_id += 1
        msg = {"id": mid, "method": method}
        if params:
            msg["params"] = params
        deadline = time.monotonic() + (timeout or self.timeout or DEFAULT_TIMEOUT)
        self.ws.send(json.dumps(msg))
        timeout_exc = getattr(websocket, 'WebSocketTimeoutException', None)
        closed_exc = getattr(websocket, 'WebSocketConnectionClosedException', None)
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError('CDP %s: quá hạn chờ phản hồi' % method)
            try:
                self.ws.settimeout(left)
            except Exception:
                pass
            try:
                raw = self.ws.recv()
            except Exception as e:
                if timeout_exc is not None and isinstance(e, timeout_exc):
                    raise TimeoutError('CDP %s: quá hạn chờ phản hồi' % method)
                if closed_exc is not None and isinstance(e, closed_exc):
                    raise ConnectionError('CDP %s: websocket đã đóng' % method)
                raise
            if raw is None or raw == '' or raw == b'':
                raise ConnectionError('CDP %s: websocket đã đóng (nhận chuỗi rỗng)' % method)
            try:
                data = json.loads(raw)
            except ValueError:
                continue  # chỉ bỏ qua thông điệp không phải JSON
            if not isinstance(data, dict):
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