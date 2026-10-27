"""Test offline cho omicall-omiflow/scripts/flow_outline.py (--file, --help). Không gọi mạng.

Bốn biến thể "từng crash" được ghép từ fixtures/flow_basic.json (khối [verify JSON] của tài liệu):
thiếu position, kick_off=None, multi_variables thiếu field_code, position.x=''.
"""
import base64
import http.server
import json
import os
import subprocess
import threading
import time
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRIPT = os.path.join(ROOT, 'omicall-omiflow', 'scripts', 'flow_outline.py')
FIXTURE = os.path.join(HERE, 'fixtures', 'flow_basic.json')

SITECUSTOMIZE = r'''
import os, socket
_orig = socket.socket.connect
def _blocked(self, addr, *a, **k):
    if isinstance(addr, tuple) and addr[0] in ("127.0.0.1", "localhost"):
        return _orig(self, addr, *a, **k)
    with open(os.environ["NET_LOG"], "a") as f:
        f.write(repr(addr) + "\n")
    raise OSError("mạng bị chặn trong test")
socket.socket.connect = _blocked
'''


def load_base():
    with open(FIXTURE, encoding='utf-8') as f:
        return json.load(f)


class FlowOutlineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        site = os.path.join(self.tmp.name, 'site')
        os.makedirs(site)
        with open(os.path.join(site, 'sitecustomize.py'), 'w', encoding='utf-8') as f:
            f.write(SITECUSTOMIZE)
        self.netlog = os.path.join(self.tmp.name, 'net.log')
        self.env = dict(os.environ, PYTHONPATH=site, NET_LOG=self.netlog, NO_NETWORK='1',
                        PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1',
                        OMI_TOKEN_FILE=os.path.join(self.tmp.name, 'khong_co_token'))
        self.env.pop('OMI_TOKEN', None)

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *args):
        return subprocess.run([sys.executable, '-B', SCRIPT, *args], capture_output=True, text=True,
                              encoding='utf-8', env=self.env, timeout=60)

    def write(self, name, obj):
        p = os.path.join(self.tmp.name, name)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False)
        return p

    def assert_no_network(self):
        self.assertFalse(os.path.exists(self.netlog), 'có kết nối mạng ngoài ý muốn')

    def test_help_offline(self):
        r = self.run_script('--help')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('--file', r.stdout)
        self.assert_no_network()

    def test_sitecustomize_really_blocks(self):
        r = subprocess.run([sys.executable, '-B', '-c', 'import socket; socket.create_connection(("192.0.2.1", 80), 1)'],
                           capture_output=True, text=True, env=self.env, timeout=30)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(os.path.exists(self.netlog))

    def test_crash_fixtures(self):
        variants = {}
        f = load_base()
        f['nodes'][1].pop('position')
        variants['thieu_position'] = f
        f = load_base()
        f['kick_off'] = None
        variants['kick_off_none'] = f
        f = load_base()
        f['nodes'][0]['conditions'][0]['data'][0]['multi_variables'][0].pop('field_code')
        variants['thieu_field_code'] = f
        f = load_base()
        f['nodes'][2]['position']['x'] = ''
        variants['position_x_rong'] = f
        for name, flow in variants.items():
            with self.subTest(name):
                r = self.run_script('--file', self.write(name + '.json', flow))
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertNotIn('Traceback', r.stderr)
                self.assertIn('TRIGGER', r.stdout)
        self.assert_no_network()

    def test_content(self):
        flow = load_base()
        ticket = flow['nodes'][3]
        ticket['actions'].insert(0, {'id': '<a_gpt>', 'type': 'CREATE_CUSTOM_VARIABLE', 'data': {
            'type': 'CHAT_GPT', 'config_variables': [{'type': 'CHAT_GPT', 'config': {'multi_variables': [
                {'field_code': '<code_intent>', 'field_name': 'intent', 'chat_gpt_model': 'gpt-4o-mini',
                 'content': 'Phân loại {{<code_status>}}. Trả về DUY NHẤT mã.'}]}}]}})
        ticket['actions'].append({'id': '<a_ci>', 'type': 'COLLECT_INFO', 'data': {'content': 'Khách hàng mới', 'variables': [
            {'variable_code': '<code_ten>', 'variable_name': 'Tên khách', 'variable_value': 'Khách hàng mới',
             'option': 'FROM_DEFINED_VARIABLE'}]}})
        ticket['actions'][1]['data']['ticket_detail']['name'] = 'YÊU CẦU - {{<code_ten>}} - <id>'
        flow['nodes'].append({'id': '<node_orphan>', 'node_type': 'ACTION', 'actions': [], 'next_nodes': ['GHOST']})
        r = self.run_script('--file', self.write('content.json', {'payload': flow}))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout
        self.assertIn('intent (gpt-4o-mini)', out)
        self.assertIn('Phân loại {{status}}', out)
        self.assertIn('{{Tên khách}}', out)          # COLLECT_INFO variable_code -> tên
        self.assertIn('<id>', out)                   # short() không xoá placeholder
        self.assertNotIn('<p>', out)                 # nhưng vẫn bỏ thẻ HTML
        self.assertIn('GHOST', out)
        self.assertIn('nút mồ côi', out)
        self.assert_no_network()

    def _stub(self, handler_fn):
        hits = []

        class H(http.server.BaseHTTPRequestHandler):
            def _do(self):
                n = int(self.headers.get('Content-Length') or 0)
                if n:
                    self.rfile.read(n)
                hits.append(self.path)
                code, body = handler_fn(self.path)
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            do_GET = do_POST = _do

            def log_message(self, *a):
                pass

        srv = http.server.HTTPServer(('127.0.0.1', 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        seg = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip('=')
        self.env['OMI_TOKEN'] = seg({'alg': 'none'}) + '.' + seg({'exp': int(time.time()) + 3600}) + '.x'
        self.env['OMI_FLOW_API_BASE'] = f'http://127.0.0.1:{srv.server_port}/omi_v2/campaign'
        return hits

    def test_401_and_pagination(self):
        try:
            import requests  # noqa: F401
        except ImportError:
            self.skipTest('thiếu requests')
        self._stub(lambda path: (401, {'message': 'unauthorized'}))
        r = self.run_script('<id>')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('401', r.stderr)
        self.assertNotIn('Traceback', r.stderr)
        self.assertNotIn(self.env['OMI_TOKEN'], r.stdout + r.stderr)

        def pages(path):
            page = int(path.split('page=')[1].split('&')[0])
            items = [{'_id': f'<id{page}_{i}>', 'name': 'x', 'version': 1} for i in range(100 if page == 1 else 3)]
            return 200, {'status_code': 9999, 'payload': {'items': items}}
        hits = self._stub(pages)
        r = self.run_script('--list')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(r.stdout.strip().splitlines()), 103)
        self.assertEqual(len(hits), 2)
        self.assert_no_network()

    def test_save_to_scratch(self):
        try:
            import requests  # noqa: F401
        except ImportError:
            self.skipTest('thiếu requests')
        flow = load_base()
        self._stub(lambda path: (200, {'status_code': 9999, 'payload': flow}))
        scratch = os.path.join(self.tmp.name, 'scratch')
        os.makedirs(scratch)
        self.env['OMI_SCRATCH'] = scratch
        r = self.run_script('--save', 'abc')
        self.assertEqual(r.returncode, 0, r.stderr)
        p = r.stdout.strip().splitlines()[-1]
        self.assertTrue(os.path.abspath(p).startswith(os.path.abspath(scratch)), p)
        with open(p, encoding='utf-8') as f:
            saved = f.read()
        self.assertNotIn(self.env['OMI_TOKEN'], saved + r.stdout)
        self.assertEqual(json.loads(saved)['name'], flow['name'])
        self.assert_no_network()

    def test_bad_file(self):
        r = self.run_script('--file', os.path.join(self.tmp.name, 'khong_co.json'))
        self.assertEqual(r.returncode, 2)
        self.assertNotIn('Traceback', r.stderr)
        r = self.run_script('--file', self.write('arr.json', []))
        self.assertEqual(r.returncode, 2)
        self.assertNotIn('Traceback', r.stderr)

    def test_malformed_ids(self):
        flow = load_base()
        flow['nodes'][1]['id'] = ['x']
        flow['nodes'][0]['next_nodes'] = [['y']]
        r = self.run_script('--file', self.write('bad_ids.json', flow))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('Traceback', r.stderr)
        self.assertIn('CẢNH BÁO', r.stdout)


if __name__ == '__main__':
    unittest.main()
