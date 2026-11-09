# -*- coding: utf-8 -*-
"""inject_captor.py: che bí mật trước khi lưu vào window.__omiCaps (offline, không nối CDP)."""
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from _util import SCRIPTS, fake_jwt, run


def load_captor():
    spec = importlib.util.spec_from_file_location("inject_captor", os.path.join(SCRIPTS, "inject_captor.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # import không chạy argparse/CDP (logic nằm trong main())
    return mod


class TestCaptorRedact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_captor()
        cls.jwt = fake_jwt()

    def test_secret_keys_masked_in_json(self):
        body = json.dumps({"access_token": self.jwt, "refreshToken": "abc", "client_secret": "s1",
                           "api_key": "k1", "apiKey": "k2", "Password": "p", "Cookie": "c=1",
                           "name": "giữ nguyên", "nested": {"Authorization": "Bearer xyz"}})
        out = json.loads(self.m.redact_text(body))
        for k in ("access_token", "refreshToken", "client_secret", "api_key", "apiKey", "Password", "Cookie"):
            self.assertEqual(out[k], "***", k)
        self.assertEqual(out["nested"]["Authorization"], "***")
        self.assertEqual(out["name"], "giữ nguyên")

    def test_header_pair_value_masked(self):
        body = json.dumps({"headers": [{"id": "h1", "key": "Authorization", "value": "Bearer " + self.jwt},
                                       {"id": "h2", "key": "Content-Type", "value": "application/json"}]})
        out = json.loads(self.m.redact_text(body))
        self.assertEqual(out["headers"][0]["value"], "***")
        self.assertEqual(out["headers"][1]["value"], "application/json")

    def test_jwt_in_free_text_and_url(self):
        for s in ("lỗi: phiên " + self.jwt + " hết hạn",
                  "https://x.example/api?jwt=" + self.jwt + "&page=1",
                  "[FormData]\naccess_token: Bearer " + self.jwt + "\nfile_0: [Blob]",
                  "https://x.example/api?apiKey=abc123&page=1"):
            out = self.m.redact_text(s)
            self.assertNotIn(self.jwt, out, s)
            self.assertNotIn("abc123", out, s)
            self.assertIn("***", out, s)
        self.assertIn("page=1", self.m.redact_text("https://x.example/api?apiKey=abc123&page=1"))

    def test_jwt_inside_json_string_value(self):
        out = self.m.redact_text(json.dumps({"payload": {"note": "dùng " + self.jwt}}))
        self.assertNotIn(self.jwt, out)

    def test_plain_text_untouched(self):
        s = '{"system_prompt":"Xin chào","items":[1,2]}'
        self.assertEqual(json.loads(self.m.redact_text(s)), json.loads(s))
        self.assertEqual(self.m.redact_text("không có gì bí mật"), "không có gì bí mật")

    def test_help_offline(self):
        code, so, se = run("inject_captor.py", "--help")
        self.assertEqual(code, 0, se)

    def test_non_local_cdp_refused(self):
        code, _, se = run("inject_captor.py", "demo", "--cdp", "http://10.0.0.1:9222")
        self.assertEqual(code, 2, se)

    @unittest.skipUnless(shutil.which("node"), "cần node để chạy JS của captor")
    def test_js_push_masks_before_storing(self):
        jwt = self.jwt
        req = json.dumps({"headers": [{"key": "Authorization", "value": "Bearer " + jwt}], "api_key": "k1",
                          "name": "bot"})
        resp = json.dumps({"status_code": 9999, "payload": {"access_token": jwt, "tenant": "t"}})
        harness = """
const RESP = %(resp)s;
globalThis.window = {
  fetch: (u, o) => Promise.resolve({clone() { return {text: () => Promise.resolve(RESP)}; }}),
  XMLHttpRequest: function() {},
};
window.XMLHttpRequest.prototype = {open() {}, send() {}};
globalThis.FormData = class {};
const r = eval(%(sniff)s);
window.fetch('https://gw.example/chatbot-gateway/save?token=%(jwt)s', {body: %(req)s}).then(() =>
  setTimeout(() => console.log(JSON.stringify({r, caps: window.__omiCaps})), 20));
""" % {"resp": json.dumps(resp), "sniff": json.dumps(self.m.SNIFF), "jwt": jwt, "req": json.dumps(req)}
        d = tempfile.mkdtemp(prefix="omi_cb_captor_")
        p = os.path.join(d, "h.js")
        with open(p, "w", encoding="utf-8") as f:
            f.write(harness)
        out = subprocess.run(["node", p], capture_output=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr.decode("utf-8", "replace"))
        text = out.stdout.decode("utf-8")
        data = json.loads(text)
        self.assertEqual(data["r"], {"ok": True})
        self.assertEqual([c["kind"] for c in data["caps"]], ["fetch", "fetch-resp"])
        self.assertNotIn(jwt, text)
        self.assertNotIn("k1", text)
        body = json.loads(data["caps"][0]["body"])
        self.assertEqual(body["headers"][0]["value"], "***")
        self.assertEqual(body["name"], "bot")
        self.assertEqual(json.loads(data["caps"][1]["resp"])["payload"]["access_token"], "***")
        self.assertIn("token=***", data["caps"][0]["url"])


if __name__ == "__main__":
    unittest.main()
