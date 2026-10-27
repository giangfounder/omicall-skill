"""Test omi_save.py với stub HTTP trên 127.0.0.1 (phát lại fixture, đếm request) và JWT giả trong HOME tạm.

Fixture save_*.json ghép từ khuôn có sẵn trong tài liệu skill, giá trị placeholder: chỉ chứng minh omi_save chạy đúng
trình tự (token, new/update, guard version, validator pre/post, che token), KHÔNG chứng minh hợp lệ với nền tảng.
Validator được thay bằng script giả qua env OMI_VALIDATOR_OVERRIDE (chỉ dùng trong test).
"""
import base64
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRIPT = ROOT / "shared" / "scripts" / "omi_save.py"
FIX = HERE / "fixtures"
sys.path.insert(0, str(HERE))
from stub_server import Stub  # noqa: E402

HAS_REQUESTS = importlib.util.find_spec("requests") is not None
TENANT = "tenant" + "gia01"
DOMAIN = "congtyabc"

FAKE_VALIDATOR = r'''
import json, os, sys
args = sys.argv[1:]
mode = args[args.index("--mode") + 1] if "--mode" in args else "pre"
json.load(open(args[0], encoding="utf-8"))
if mode == "post" and os.environ.get("FAKE_POST_FAIL") == "1":
    print("FAIL C1 bản GET thiếu trường (giả lập)")
    print("RESULT FAIL")
    sys.exit(1)
print("PASS C1 giả lập mode %s" % mode)
print("RESULT PASS")
'''


def b64(obj):
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


def fake_jwt():
    return ".".join([b64({"alg": "HS256", "typ": "JWT"}),
                     b64({"exp": int(time.time()) + 3600, "domain": DOMAIN, "tenant_id": TENANT, "agent_id": "<id>"}),
                     "chuky" + "gia" + "x" * 20])


def load(name):
    obj = json.loads((FIX / name).read_text(encoding="utf-8"))
    obj.pop("_ghi_chu", None)
    return obj


@unittest.skipUnless(HAS_REQUESTS, "thiếu thư viện requests (pip install requests)")
class TestOmiSave(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="omi_save_"))
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.out = self.tmp / "out"
        self.token = fake_jwt()
        (self.tmp / "tok.txt").write_text("Bearer " + self.token, encoding="utf-8")
        val = self.tmp / "fake_validator.py"
        val.write_text(FAKE_VALIDATOR, encoding="utf-8")
        self.server_version = 3
        self.saved = {}
        self.stub = Stub(self.routes()).start()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("OMI_")}
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), PYTHONIOENCODING="utf-8",
                        OMI_TOKEN_FILE=str(self.tmp / "tok.txt"), OMI_API_BASE=self.stub.url,
                        OMI_VALIDATOR_OVERRIDE=str(val), OMI_TEST_MODE="1", OMI_SCRATCH=str(self.tmp / "scratch"),
                        NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")

    def tearDown(self):
        self.stub.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------- stub ----------
    def routes(self):
        test = self

        def add_v2(body):
            obj = dict(body or {})
            obj["id"] = "idmoi01"
            obj["uuid"] = obj.get("uuid") or "uuidmoi01"
            obj["version"] = (obj.get("version") or 0) + 1
            test.saved["idmoi01"] = obj
            return 200, {"status_code": 9999, "payload": {"id": "idmoi01", "version": obj["version"]}}

        def get_new(body):
            return 200, {"status_code": 9999, "payload": test.saved.get("idmoi01")}

        def list_by_tenant(body):
            cur = load("save_callbot.json")
            cur["version"] = test.server_version
            return 200, {"status_code": 9999, "payload": [cur]}

        return {
            ("POST", "/callbot/script/add_v2"): add_v2,
            ("GET", "/callbot/script/get/idmoi01"): get_new,
            ("GET", "/callbot/script/list-by-tenant/" + TENANT): list_by_tenant,
        }

    # ---------- helpers ----------
    def write(self, name, obj):
        p = self.tmp / name
        p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return p

    def run_save(self, *args, **env):
        e = dict(self.env)
        e.update(env)
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args), "--domain", DOMAIN,
                            "--out-dir", str(self.out)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=e, cwd=str(self.tmp))
        return p.returncode, p.stdout + p.stderr

    def assert_no_token(self, out):
        self.assertNotIn(self.token, out)
        self.assertNotIn(self.token.split(".")[1], out)
        if self.out.is_dir():
            for f in self.out.rglob("*"):
                if f.is_file():
                    t = f.read_text(encoding="utf-8", errors="replace")
                    self.assertNotIn(self.token, t, f.name)
                    self.assertNotIn(self.token.split(".")[1], t, f.name)

    # ---------- (a) ----------
    def test_a_save_new_ok(self):
        p = self.write("cb.json", load("save_callbot.json"))
        code, out = self.run_save("callbot", p, "--new")
        self.assertEqual(code, 0, out)
        self.assertIn("idmoi01", out)
        self.assertIn("[post] RESULT PASS", out)
        sent = [c for c in self.stub.calls if c[1] == "/callbot/script/add_v2"]
        self.assertEqual(len(sent), 1)
        for k in ("id", "uuid", "public_key"):
            self.assertNotIn(k, sent[0][2], "--new phải xoá %s" % k)
        self.assertTrue(all(a == "Bearer " + self.token for a in self.stub.auth))
        self.assert_no_token(out)

    # ---------- (b) ----------
    def test_b_version_guard(self):
        base = load("save_callbot.json")  # version 3
        self.server_version = 5
        p = self.write("cb.json", base)
        b = self.write("base.json", base)
        code, out = self.run_save("callbot", p, "--update", "--confirm-update", "--base", b)
        self.assertEqual(code, 3, out)
        self.assertIn("VERSION LỆCH", out)
        self.assertIn("version: base 3, hiện tại 5", out)
        self.assertFalse(any(c[1] == "/callbot/script/add_v2" for c in self.stub.calls))
        self.assert_no_token(out)

    def test_b2_update_same_version_saves(self):
        base = load("save_callbot.json")
        p = self.write("cb.json", base)
        code, out = self.run_save("callbot", p, "--update", "--confirm-update", "--base", p)
        self.assertEqual(code, 0, out)
        self.assertIn("list_hotlines", out)

    # ---------- (c) ----------
    def test_c_post_validator_fail(self):
        p = self.write("cb.json", load("save_callbot.json"))
        code, out = self.run_save("callbot", p, "--new", FAKE_POST_FAIL="1")
        self.assertEqual(code, 1, out)
        self.assertIn("[post] RESULT FAIL", out)
        self.assertIn("[pre] RESULT PASS", out)
        self.assert_no_token(out)

    # ---------- (d) ----------
    def test_d_dry_run_no_request(self):
        p = self.write("cb.json", load("save_callbot.json"))
        code, out = self.run_save("callbot", p, "--new", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.stub.calls, [])
        self.assertIn("DRY-RUN", out)
        self.assertIn("Bearer ***", out)
        self.assert_no_token(out)

    # ---------- (f) ----------
    def test_f_publish_flag_rejected(self):
        p = self.write("cb.json", load("save_callbot.json"))
        code, out = self.run_save("callbot", p, "--new", "--publish")
        self.assertEqual(code, 2, out)
        self.assertIn("unrecognized arguments", out)
        self.assertEqual(self.stub.calls, [])

    # ---------- (g) ----------
    def test_g_flow_without_id(self):
        flow = load("save_flow.json")
        flow.pop("_id")
        p = self.write("flow.json", flow)
        code, out = self.run_save("flow", p)
        self.assertEqual(code, 2, out)
        self.assertIn("_id", out)
        self.assertEqual(self.stub.calls, [])

    # ---------- (h) ----------
    def test_h_update_requires_uuid(self):
        cb = load("save_callbot.json")
        cb.pop("uuid")
        p = self.write("cb.json", cb)
        code, out = self.run_save("callbot", p, "--update", "--confirm-update")
        self.assertEqual(code, 2, out)
        self.assertIn("uuid", out)
        self.assertEqual(self.stub.calls, [])

    def test_h_update_requires_confirm(self):
        p = self.write("cb.json", load("save_callbot.json"))
        code, out = self.run_save("callbot", p, "--update")
        self.assertEqual(code, 2, out)
        self.assertIn("--confirm-update", out)
        self.assertEqual(self.stub.calls, [])

    def test_missing_validator_exit2(self):
        p = self.write("cb.json", load("save_callbot.json"))
        code, out = self.run_save("callbot", p, "--new", OMI_VALIDATOR_OVERRIDE=str(self.tmp / "khong_co.py"))
        self.assertEqual(code, 2, out)
        self.assertFalse(any(c[1] == "/callbot/script/add_v2" for c in self.stub.calls))

    # ---------- giá trị đã che ----------
    def test_masked_payload_refused_flow(self):
        flow = load("save_flow.json")
        flow["nodes"].append({"id": "<id>", "type": "API_CALL",
                              "data": {"headers": [{"key": "Authorization", "value": "Bearer ***"}]}})
        p = self.write("flow.json", flow)
        code, out = self.run_save("flow", p)
        self.assertEqual(code, 2, out)
        self.assertIn("đã che", out)
        self.assertIn("headers[0].value", out)
        self.assertEqual(self.stub.calls, [])

    def test_masked_payload_refused_callbot(self):
        cb = load("save_callbot.json")
        cb["variables"] = [{"name": "api_key", "api_key": "***"}]
        p = self.write("cb.json", cb)
        code, out = self.run_save("callbot", p, "--new")
        self.assertEqual(code, 2, out)
        self.assertIn("đã che", out)
        self.assertEqual(self.stub.calls, [])

    def test_validator_sees_unmasked_payload(self):
        """Validator pre/post phải nhận bản CHƯA che (bí mật thật đi đúng vào validator, file lưu lại vẫn che)."""
        secret = "Bearer " + "abcdefghijk12345"
        cb = load("save_callbot.json")
        cb["headers"] = [{"key": "Authorization", "value": secret}]
        p = self.write("cb.json", cb)
        val = self.tmp / "need_raw.py"
        val.write_text(
            "import json, sys\n"
            "t = open(sys.argv[1], encoding='utf-8').read()\n"
            "ok = %r in t and '***' not in t\n"
            "print(('PASS' if ok else 'FAIL') + ' X6 validator nhận bản chưa che')\n"
            "print('RESULT ' + ('PASS' if ok else 'FAIL'))\n"
            "sys.exit(0 if ok else 1)\n" % secret, encoding="utf-8")
        code, out = self.run_save("callbot", p, "--new", OMI_VALIDATOR_OVERRIDE=str(val))
        self.assertEqual(code, 0, out)
        self.assertIn("[pre] RESULT PASS", out)
        self.assertIn("[post] RESULT PASS", out)
        for f in self.out.rglob("*.json"):
            self.assertNotIn(secret, f.read_text(encoding="utf-8"), f.name)

    # ---------- đọc payload ----------
    def test_payload_missing_or_invalid_exit2(self):
        code, out = self.run_save("callbot", self.tmp / "khong_co.json", "--new", "--dry-run")
        self.assertEqual(code, 2, out)
        self.assertIn("không đọc được payload", out)
        bad = self.tmp / "hong.json"
        bad.write_text("{khong phai json", encoding="utf-8")
        code, out = self.run_save("callbot", bad, "--new", "--dry-run")
        self.assertEqual(code, 2, out)
        self.assertIn("không đọc được payload", out)
        p = self.write("cb.json", load("save_callbot.json"))
        code, out = self.run_save("callbot", p, "--update", "--confirm-update", "--base", self.tmp / "khong_co.json")
        self.assertEqual(code, 2, out)
        self.assertIn("không đọc được --base", out)
        self.assertEqual(self.stub.calls, [])

    def test_new_refuses_is_publish_true(self):
        cb = load("save_callbot.json")
        cb["is_publish"] = True
        p = self.write("cb.json", cb)
        code, out = self.run_save("callbot", p, "--new", "--dry-run")
        self.assertEqual(code, 2, out)
        self.assertIn("is_publish:true", out)
        self.assertEqual(self.stub.calls, [])

    def test_masked_bare_star_in_text_refused(self):
        # mask_text che JWT trong câu / trong đường dẫn URL thành '***' trần -> vẫn phải chặn
        for val in ("Gọi kèm ***", "***,next", "https://hook.example/***/run"):
            cb = load("save_callbot.json")
            cb["description"] = val
            p = self.write("cb.json", cb)
            code, out = self.run_save("callbot", p, "--new", "--dry-run")
            self.assertEqual(code, 2, val + " | " + out)
            self.assertIn("đã che", out)

    def test_markdown_bold_not_masked(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import omi_save
        self.assertEqual(omi_save.masked_paths({"t": "Lưu ý: ***Quan trọng*** nhé"}), [])
        self.assertEqual(omi_save.masked_paths({"t": "a **** b"}), [])

    def test_editor_url_keeps_suffix(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import omi_save
        t = omi_save.KINDS["callbot"]["editor"]
        self.assertIn("<domain>.omicrm.com/", omi_save.editor_url(t, "<domain>.omicrm.com", "<domain>", "x"))
        self.assertIn("<domain>.omicrm.io/", omi_save.editor_url(t, "<domain>", "<domain>", "x"))

    # ---------- env chỉ dùng cho test ----------
    def test_validator_override_needs_test_mode(self):
        p = self.write("cb.json", load("save_callbot.json"))
        code, out = self.run_save("callbot", p, "--new", "--dry-run", OMI_TEST_MODE="")
        self.assertEqual(code, 2, out)
        self.assertIn("OMI_TEST_MODE", out)

    def test_validator_override_warns(self):
        p = self.write("cb.json", load("save_callbot.json"))
        code, out = self.run_save("callbot", p, "--new", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("WARN: OMI_VALIDATOR_OVERRIDE", out)

    def test_api_base_non_local_refused(self):
        p = self.write("cb.json", load("save_callbot.json"))
        code, out = self.run_save("callbot", p, "--new", OMI_API_BASE="https://example.invalid")
        self.assertEqual(code, 4, out)
        self.assertIn("chỉ nhận 127.0.0.1/localhost", out)
        self.assertEqual(self.stub.calls, [])
        self.assert_no_token(out)


CHATBOT_SAVE = ROOT / "omicall-chatbot-gen-ai" / "scripts" / "omi_save.py"


@unittest.skipUnless(CHATBOT_SAVE.is_file() and (CHATBOT_SAVE.parent / "validate_bot.py").is_file(),
                     "chưa có omicall-chatbot-gen-ai/scripts/{omi_save,validate_bot}.py (chạy tools/sync_shared.py)")
class TestOmiSaveRealValidator(unittest.TestCase):
    """omi_save + validate_bot.py thật (không override, dry-run, không gọi mạng): header Authorization thật trong
    api_knowledge không được báo nhầm X6 vì validator nhận bản chưa che; payload còn '***' thì bị chặn."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="omi_save_real_"))
        home = self.tmp / "home"
        home.mkdir()
        (self.tmp / "tok.txt").write_text("Bearer " + fake_jwt(), encoding="utf-8")
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("OMI_")}
        self.env.update(HOME=str(home), USERPROFILE=str(home), PYTHONIOENCODING="utf-8",
                        OMI_TOKEN_FILE=str(self.tmp / "tok.txt"), OMI_SCRATCH=str(self.tmp / "scratch"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_bot(self, bot):
        p = self.tmp / "bot.json"
        p.write_text(json.dumps(bot, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([sys.executable, "-B", str(CHATBOT_SAVE), "bot", str(p), "--domain", DOMAIN, "--dry-run",
                            "--out-dir", str(self.tmp / "out")], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=self.env, cwd=str(self.tmp))
        return r.returncode, r.stdout + r.stderr

    def bot_with_header(self, value):
        bot = load("save_bot.json")
        bot["api_knowledge"] = [{"name": "tra_cuu", "method": "GET", "url": "https://<domain>/api",
                                 "headers": [{"key": "Authorization", "value": value}]}]
        return bot

    def test_real_header_not_flagged_x6(self):
        secret = "Bearer " + "abcdefghijk12345"
        code, out = self.run_bot(self.bot_with_header(secret))
        self.assertNotIn("FAIL X6", out)
        # X8 chỉ báo khi header KHÔNG phải bản che -> chứng minh validator nhận bản chưa che
        self.assertIn("WARN X8", out)
        self.assertNotIn("abcdefghijk12345", out)
        self.assertIn(code, (0, 1), out)  # fixture tối giản có thể FAIL mục khác (C3), không liên quan X6
        for f in (self.tmp / "out").rglob("*"):
            if f.is_file():
                self.assertNotIn("abcdefghijk12345", f.read_text(encoding="utf-8"), f.name)

    def test_masked_header_refused(self):
        code, out = self.run_bot(self.bot_with_header("Bearer ***"))
        self.assertEqual(code, 2, out)
        self.assertIn("đã che", out)


class TestOmiSaveStatic(unittest.TestCase):
    def test_no_publish_or_campaign_add_v2(self):
        t = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("publish_v2", t)
        for line in t.splitlines():
            self.assertFalse("campaign" in line and "add_v2" in line, line)
            self.assertNotIn("update_v2/", line)


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(HAS_REQUESTS, "thiếu thư viện requests (pip install requests)")
class TestOmiSaveRealValidator(unittest.TestCase):
    """Dry-run đầu-cuối với validator THẬT của skill (không OMI_VALIDATOR_OVERRIDE), payload có bí mật.

    Dùng bản omi_save.py đã sync trong omicall-omiflow/scripts (validator validate_flow.py nằm cùng thư mục) và fixture
    tests/omicall-omiflow/fixtures/flow_basic.json (ghép từ khối [verify JSON] của tài liệu omiflow): chỉ chứng minh
    nhất quán nội bộ, không chứng minh nền tảng chấp nhận payload.
    """
    SECRET = "PLAINSECRET" + "VALUE987"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="omi_save_real_"))
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.out = self.tmp / "out"
        self.token = fake_jwt()
        (self.tmp / "tok.txt").write_text("Bearer " + self.token, encoding="utf-8")
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("OMI_")}
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), PYTHONIOENCODING="utf-8",
                        OMI_TOKEN_FILE=str(self.tmp / "tok.txt"), OMI_API_BASE="http://127.0.0.1:9",
                        OMI_SCRATCH=str(self.tmp / "scratch"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_flow_dry_run_real_validator(self):
        script = ROOT / "omicall-omiflow" / "scripts" / "omi_save.py"
        flow = json.loads((ROOT / "tests" / "omicall-omiflow" / "fixtures" / "flow_basic.json").read_text(encoding="utf-8"))
        flow["_test_headers"] = [{"key": "x-api-key", "value": self.SECRET},
                                 {"key": "Authorization", "value": "Bearer " + self.SECRET}]
        p = self.tmp / "flow.json"
        p.write_text(json.dumps(flow, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([sys.executable, "-B", str(script), "flow", str(p), "--domain", DOMAIN, "--dry-run",
                            "--out-dir", str(self.out)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=self.env, cwd=str(self.tmp))
        out = r.stdout + r.stderr
        self.assertEqual(r.returncode, 0, out)
        self.assertIn("[pre] RESULT PASS", out)
        self.assertIn("DRY-RUN: POST", out)
        self.assertIn("Không gửi request nào", out)
        self.assertNotIn(self.SECRET, out)
        self.assertNotIn(self.token, out)
        sent = list(self.out.glob("flow_*_sent.json"))
        self.assertEqual(len(sent), 1, list(self.out.iterdir()))
        for f in self.out.rglob("*"):
            if f.is_file():
                t = f.read_text(encoding="utf-8", errors="replace")
                self.assertNotIn(self.SECRET, t, f.name)
                self.assertNotIn(self.token, t, f.name)
