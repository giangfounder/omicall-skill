"""Test omi_session.py và omi_preflight.py (offline, HOME tạm, JWT giả ghép lúc chạy)."""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "shared" / "scripts"


def b64(obj):
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


def fake_jwt(exp_in=3600, domain="congtyabc", tenant_id="<tenant_id>"):
    return ".".join([b64({"alg": "HS256", "typ": "JWT"}),
                     b64({"exp": int(time.time()) + exp_in, "domain": domain, "tenant_id": tenant_id, "agent_id": "<id>"}),
                     "chuky" + "gia"])


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="omi_sess_"))
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.env = {k: v for k, v in os.environ.items()
                    if k not in ("OMI_TOKEN", "OMI_TOKEN_FILE", "OMI_DOMAIN", "OMI_MIN_SECONDS")}
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), PYTHONIOENCODING="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def token_file(self, content):
        p = self.tmp / "tok.txt"
        p.write_text(content, encoding="utf-8")
        self.env["OMI_TOKEN_FILE"] = str(p)

    def run_py(self, *args):
        p = subprocess.run([sys.executable, "-B", *map(str, args)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=self.env, cwd=str(self.tmp))
        return p.returncode, p.stdout, p.stderr

    def preflight(self, domain="congtyabc"):
        code, out, err = self.run_py(SCRIPTS / "omi_preflight.py", "--domain", domain)
        lines = [l for l in out.splitlines() if l.strip()]
        self.assertEqual(len(lines), 1, out)
        return code, json.loads(lines[0]), out, err


class TestPreflight(Base):
    def test_ok_route_api(self):
        tok = fake_jwt()
        self.token_file(tok)
        code, j, out, err = self.preflight()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(j["route"], "api")
        self.assertTrue(j["token_ok"])
        self.assertTrue(j["domain_match"])
        self.assertNotIn(tok, out + err)
        self.assertNotIn(tok.split(".")[1], out + err)

    def test_expired(self):
        self.token_file(fake_jwt(exp_in=-10))
        code, j, out, _ = self.preflight()
        self.assertEqual(code, 3)
        self.assertFalse(j["token_ok"])
        self.assertNotEqual(j["route"], "api")

    def test_near_expiry_below_threshold(self):
        self.token_file(fake_jwt(exp_in=120))
        code, j, _, _ = self.preflight()
        self.assertEqual(code, 3)

    def test_domain_mismatch(self):
        self.token_file(fake_jwt(domain="tenantkhac"))
        code, j, _, _ = self.preflight("congtyabc")
        self.assertEqual(code, 3)
        self.assertIs(j["domain_match"], False)

    def test_no_token_blocked(self):
        code, j, out, _ = self.preflight()
        self.assertEqual(code, 3)
        self.assertEqual(j["route"], "blocked")
        self.assertIn("omi_login.py\" setup --domain congtyabc", j["next_step"])
        self.assertIn("ô nhập ẩn", j["next_step"])
        self.assertIn("Phụ lục A", j["next_step"])
        self.assertNotIn("<cli>", j["next_step"])
        self.assertFalse(j["credential_stored"])
        self.assertIn("OMI_TOKEN_FILE", j["next_step"])
        self.assertNotIn("cookie", j["next_step"].lower())
        self.assertFalse(j["mcp_session_file"])

    def test_missing_token_file_warns(self):
        self.env["OMI_TOKEN_FILE"] = str(self.tmp / "khong_co.txt")
        code, j, out, err = self.preflight()
        self.assertEqual(j["route"], "blocked")
        self.assertIn("không tồn tại", err)

    def test_bearer_prefix(self):
        self.token_file("Bearer " + fake_jwt())
        code, j, _, _ = self.preflight()
        self.assertEqual(code, 0)
        self.assertEqual(j["route"], "api")

    def test_mcp_session_file(self):
        d = self.home / ".omicall-mcp"
        d.mkdir()
        (d / "session.json").write_text(json.dumps({"x": {"accessToken": fake_jwt()}}), encoding="utf-8")
        code, j, _, _ = self.preflight()
        self.assertEqual(code, 0)
        self.assertEqual(j["source"], "MCP session.json")
        self.assertTrue(j["mcp_session_file"])


class TestSession(Base):
    def test_not_jwt_clear_message(self):
        self.token_file("abc")
        code, out, err = self.run_py(SCRIPTS / "omi_session.py")
        self.assertEqual(code, 1)
        self.assertIn("không phải JWT", out)
        self.assertNotIn("Traceback", out + err)
        code, j, out2, err2 = self.preflight()
        self.assertEqual(j["route"], "ui")
        self.assertNotIn("Traceback", out2 + err2)

    def test_get_token_systemexit_not_traceback(self):
        self.token_file("abc")
        code, out, err = self.run_py("-c", f"import sys; sys.path.insert(0, r'{SCRIPTS}'); import omi_session; omi_session.get_token()")
        self.assertNotEqual(code, 0)
        self.assertNotIn("Traceback", err)
        self.assertIn("Token không dùng được", err)

    def test_headers_backward_compatible(self):
        tok = fake_jwt()
        self.token_file(tok)
        code, out, err = self.run_py("-c", f"import sys; sys.path.insert(0, r'{SCRIPTS}'); import omi_session; "
                                           "h = omi_session.headers(); c = omi_session.claims(omi_session.get_token()); "
                                           "print(h['Authorization'].startswith('Bearer '), c['domain'])")
        self.assertEqual(code, 0, err)
        self.assertEqual(out.split(), ["True", "congtyabc"])

    def test_env_min_seconds(self):
        self.token_file(fake_jwt(exp_in=600))
        self.env["OMI_MIN_SECONDS"] = "900"
        code, out, err = self.run_py(SCRIPTS / "omi_session.py")
        self.assertEqual(code, 1)
        self.env["OMI_MIN_SECONDS"] = "60"
        code, out, err = self.run_py(SCRIPTS / "omi_session.py")
        self.assertEqual(code, 0, out + err)

    def test_help(self):
        code, out, _ = self.run_py(SCRIPTS / "omi_session.py", "--help")
        self.assertEqual(code, 0)
        code, out, _ = self.run_py(SCRIPTS / "omi_preflight.py", "--help")
        self.assertEqual(code, 0)


class TestMask(unittest.TestCase):
    def test_mask_secrets(self):
        sys.path.insert(0, str(SCRIPTS))
        try:
            import omi_api
        finally:
            sys.path.remove(str(SCRIPTS))
        tok = fake_jwt()
        obj = {"headers": {"Authorization": "Bearer " + tok}, "token": tok, "note": "x Bearer " + tok,
               "knowledge": {"apis": [{"headers": [{"key": "Authorization", "value": "Bearer abcdefgh12345"},
                                                   {"key": "Content-Type", "value": "application/json"}]}]}}
        m = json.dumps(omi_api.mask_secrets(obj))
        self.assertNotIn(tok, m)
        self.assertNotIn("abcdefgh12345", m)
        self.assertIn("application/json", m)
        self.assertEqual(obj["token"], tok)  # không sửa bản gốc


if __name__ == "__main__":
    unittest.main()
