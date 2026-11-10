"""tenant_survey.py / config_survey.py --max-age: chạy lại khi file đích còn mới -> 0 request.

Gọi thật qua omi_api tới stub HTTP trên 127.0.0.1 (đếm request), JWT giả trong HOME tạm. Mọi route trả danh sách rỗng:
chỉ đếm request, không chứng minh khuôn dữ liệu của nền tảng.
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
SCRIPTS = ROOT / "shared" / "scripts"
sys.path.insert(0, str(HERE))
from stub_server import Stub  # noqa: E402

HAS_REQUESTS = importlib.util.find_spec("requests") is not None
DOMAIN = "congtyabc"
T0 = "2026-01-01T00:00:00"


def b64(obj):
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


def fake_jwt():
    return ".".join([b64({"alg": "HS256", "typ": "JWT"}),
                     b64({"exp": int(time.time()) + 3600, "domain": DOMAIN, "tenant_id": "tenant" + "gia01", "agent_id": "<id>"}),
                     "chuky" + "gia" + "x" * 20])


class AnyRoute(dict):
    """Mọi (method, path) đều trả 200 với danh sách rỗng."""

    def get(self, key, default=None):
        return lambda body: (200, {"payload": {"items": []}})


@unittest.skipUnless(HAS_REQUESTS, "thiếu thư viện requests (pip install requests)")
class TestSurveyMaxAge(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="omi_cache_"))
        (self.tmp / "home").mkdir()
        (self.tmp / "tok.txt").write_text("Bearer " + fake_jwt(), encoding="utf-8")
        self.stub = Stub(AnyRoute()).start()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("OMI_")}
        self.env.update(HOME=str(self.tmp / "home"), USERPROFILE=str(self.tmp / "home"), PYTHONIOENCODING="utf-8",
                        OMI_TOKEN_FILE=str(self.tmp / "tok.txt"), OMI_API_BASE=self.stub.url,
                        OMI_SCRATCH=str(self.tmp / "scratch"), NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
        (self.tmp / "scratch").mkdir()
        self.out = self.tmp / "scratch" / "tenant_context.json"

    def tearDown(self):
        self.stub.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_script(self, name, *args, domain=DOMAIN, code=0):
        dom = ["--domain", domain] if domain else []
        p = subprocess.run([sys.executable, "-B", str(SCRIPTS / name), "--out", str(self.out), *dom, *args],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.env, timeout=120)
        self.assertEqual(p.returncode, code, p.stdout + p.stderr)
        return p.stdout + p.stderr

    def count(self, name, *args):
        n = len(self.stub.calls)
        out = self.run_script(name, *args)
        return len(self.stub.calls) - n, out

    def test_rerun_within_max_age_makes_no_request(self):
        n_t, _ = self.count("tenant_survey.py", "--now", T0)
        n_c, _ = self.count("config_survey.py", "--now", T0)
        self.assertEqual((n_t, n_c), (7, 10))  # 17 request lần đầu
        n_t, out_t = self.count("tenant_survey.py", "--now", "2026-01-01T00:10:00", "--max-age", "60")
        n_c, out_c = self.count("config_survey.py", "--now", "2026-01-01T00:10:00", "--max-age", "60")
        self.assertEqual((n_t, n_c), (0, 0))
        self.assertIn("còn mới", out_t)
        self.assertIn("còn mới", out_c)
        ctx = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(ctx["survey_at"], T0)  # không ghi lại file
        self.assertEqual(ctx["config_survey_at"], T0)
        self.assertIn("pbx", ctx)

    def test_stale_file_is_surveyed_again(self):
        self.count("tenant_survey.py", "--now", T0)
        self.count("config_survey.py", "--now", T0)
        n_t, _ = self.count("tenant_survey.py", "--now", "2026-01-01T02:00:00", "--max-age", "60")
        n_c, _ = self.count("config_survey.py", "--now", "2026-01-01T02:00:00", "--max-age", "60")
        self.assertEqual((n_t, n_c), (7, 10))
        ctx = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual((ctx["survey_at"], ctx["config_survey_at"]), ("2026-01-01T02:00:00", "2026-01-01T02:00:00"))

    def test_config_survey_does_not_count_as_tenant_survey(self):
        # config_survey ghi mốc riêng: không làm tenant_survey tưởng file còn mới
        self.count("config_survey.py", "--now", T0)
        n_t, _ = self.count("tenant_survey.py", "--now", T0, "--max-age", "60")
        self.assertEqual(n_t, 7)

    def test_max_age_needs_domain_and_same_domain(self):
        self.count("tenant_survey.py", "--now", T0)
        self.count("config_survey.py", "--now", T0)
        for name in ("tenant_survey.py", "config_survey.py"):
            n = len(self.stub.calls)
            out = self.run_script(name, "--now", T0, "--max-age", "60", domain=None, code=2)
            self.assertIn("--max-age cần --domain", out)
            self.assertEqual(len(self.stub.calls), n)
        sys.path.insert(0, str(SCRIPTS))
        import config_survey, tenant_survey  # noqa: E401
        self.assertIsNone(tenant_survey.fresh_age(str(self.out), 60, "tenantkhac", T0))  # file của tenant khác: không tin
        self.assertIsNone(config_survey.fresh_age(str(self.out), 60, "tenantkhac", T0))
        self.assertIsNotNone(tenant_survey.fresh_age(str(self.out), 60, DOMAIN, T0))

    def test_without_max_age_always_calls(self):
        self.count("config_survey.py", "--now", T0)
        n_c, _ = self.count("config_survey.py", "--now", T0)
        self.assertEqual(n_c, 10)


if __name__ == "__main__":
    unittest.main()
