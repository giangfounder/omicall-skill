"""Stub HTTP tối giản cho test omi_save.py — CHỈ bind 127.0.0.1, đếm request, phát lại dữ liệu cấu hình sẵn.

    srv = Stub(routes)          # routes: {(method, path): callable(body_obj) -> (status, json_obj)}
    srv.start(); srv.url        # http://127.0.0.1:<port>
    srv.calls                   # [(method, path, body_obj)]
    srv.stop()
Body multipart (field 'file' = JSON) được giải mã thành object; body JSON thường cũng vậy.
"""
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


def parse_body(headers, raw):
    ctype = headers.get('Content-Type', '')
    if 'multipart/form-data' in ctype:
        m = re.search(r'boundary=("?)([^";]+)\1', ctype)
        if not m:
            return None
        for part in raw.split(b'--' + m.group(2).encode()):
            if b'name="file"' in part:
                body = part.split(b'\r\n\r\n', 1)[1]
                if body.endswith(b'\r\n'):
                    body = body[:-2]
                return json.loads(body.decode('utf-8'))
        return None
    if raw:
        try:
            return json.loads(raw.decode('utf-8'))
        except ValueError:
            return raw.decode('utf-8', 'replace')
    return None


class Stub:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []
        self.auth = []
        stub = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _do(self, method):
                n = int(self.headers.get('Content-Length') or 0)
                raw = self.rfile.read(n) if n else b''
                path = urlsplit(self.path).path
                body = parse_body(self.headers, raw)
                stub.calls.append((method, path, body))
                stub.auth.append(self.headers.get('Authorization'))
                fn = stub.routes.get((method, path))
                if fn is None:
                    status, obj = 404, {'status_code': 404, 'message': 'stub: không có route %s %s' % (method, path)}
                else:
                    status, obj = fn(body)
                data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._do('GET')

            def do_POST(self):
                self._do('POST')

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), H)
        self.url = 'http://127.0.0.1:%d' % self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
