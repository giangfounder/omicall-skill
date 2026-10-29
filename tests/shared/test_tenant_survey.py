"""Test tenant_survey.py --replay (offline) và khuôn tenant_context.template.json.

Fixture trong survey_replay/ ghép từ khuôn trong tài liệu skill, giá trị là placeholder: chỉ chứng minh nhất quán
nội bộ, không chứng minh hợp lệ với nền tảng. attributes.json theo khuôn bộ thuộc tính đã kiểm chứng; mã kiểu danh sách vẫn giả định.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCRIPT = ROOT / "shared" / "scripts" / "tenant_survey.py"
SKILLS = ["omicall-callbot-gen-ai", "omicall-callbot-flow", "omicall-chatbot-gen-ai", "omicall-omiflow"]


class TestSurvey(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="omi_survey_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def survey(self, *extra):
        out = self.tmp / "ctx.json"
        env = {k: v for k, v in os.environ.items() if k not in ("OMI_TOKEN", "OMI_TOKEN_FILE")}
        env["PYTHONIOENCODING"] = "utf-8"
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--replay", str(HERE / "survey_replay"), "--out", str(out),
                            "--domain", "<domain>", "--tenant-id", "<tenant_id>", "--now", "2026-01-01T00:00:00", *extra],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = out.read_text(encoding="utf-8")
        return json.loads(text), text

    def test_matches_snapshot(self):
        got, _ = self.survey()
        exp = json.loads((HERE / "fixtures" / "survey_expected.json").read_text(encoding="utf-8"))
        self.assertEqual(got, exp)

    def test_unverified_not_called_by_default(self):
        got, text = self.survey()
        called = {r["key"] for r in got["_endpoints"] if r["goi"]}
        for r in got["_endpoints"]:
            if not r["verified"]:
                self.assertNotIn(r["key"], called)
                self.assertTrue(any(c.startswith(r["key"] + ":") for c in got["can_xac_nhan"]), r["key"])
            self.assertRegex(r["nguon"], r"\S+\.md:\d+")
        self.assertIn("attributes", called)
        self.assertEqual(got["_nguon"]["agents"], "MCP list_agents")
        self.assertEqual(got["agents"], [])

    def test_is_list_with_unverified(self):
        got, text = self.survey("--include-unverified")
        exp = json.loads((HERE / "fixtures" / "survey_expected_unverified.json").read_text(encoding="utf-8"))
        self.assertEqual(got, exp)
        by = {a["name"]: a for a in got["attributes"]}
        self.assertIs(by["Loại xe"]["is_list"], True)
        self.assertIs(by["Họ và tên"]["is_list"], False)
        self.assertIsNone(by["Hạng hội viên"]["is_list"])
        self.assertTrue(any("Cần xác nhận mã kiểu thật" in c for c in got["can_xac_nhan"]))

    def test_attribute_sets_flattened(self):
        got, _ = self.survey()
        by = {a["code"]: a for a in got["attributes"]}
        self.assertEqual(by["<code10_a>"]["name"], "Loại xe")  # field_name.custom
        self.assertEqual(by["<code10_a>"]["set"], "ticket/Bộ thuộc tính mặc định")
        self.assertIs(by["<code10_e>"]["is_list"], False)  # ticket_switch
        self.assertNotIn("<code10_f>", by)  # is_deleted bị bỏ

    def test_no_secrets_in_output(self):
        for extra in ((), ("--include-unverified",)):
            _, text = self.survey(*extra)
            self.assertNotIn("Authorization", text)
            self.assertNotIn("eyJ", text)

    def run_replay(self, replay_dir):
        out = self.tmp / "ctx2.json"
        env = {k: v for k, v in os.environ.items() if k not in ("OMI_TOKEN", "OMI_TOKEN_FILE")}
        env["PYTHONIOENCODING"] = "utf-8"
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--replay", str(replay_dir), "--out", str(out),
                            "--domain", "<domain>", "--tenant-id", "<tenant_id>", "--now", "2026-01-01T00:00:00"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        return p.returncode, p.stdout + p.stderr, out

    def test_all_endpoints_fail_exit4(self):
        empty = self.tmp / "replay_rong"
        empty.mkdir()
        code, out, path = self.run_replay(empty)
        self.assertEqual(code, 4, out)
        self.assertIn("không đọc được endpoint nào", out)
        self.assertFalse(path.exists())

    def test_partial_failure_warns(self):
        part = self.tmp / "replay_mot_phan"
        shutil.copytree(HERE / "survey_replay", part)
        (part / "flows.json").unlink()
        code, out, path = self.run_replay(part)
        self.assertEqual(code, 0, out)
        self.assertIn("WARN", out)
        self.assertIn("flows", out)
        self.assertIn("1 lỗi", out)
        self.assertTrue(path.exists())

    def test_template_keys_and_copies_load(self):
        tpl = json.loads((ROOT / "shared" / "references" / "tenant_context.template.json").read_text(encoding="utf-8"))
        for k in ("tenant", "survey_at", "modules_enabled", "attributes", "ticket_categories", "status_sets",
                  "sale_allocations", "agents", "extensions", "hotlines", "channels", "quota", "integrations",
                  "existing_artefacts", "can_xac_nhan"):
            self.assertIn(k, tpl)
        self.assertEqual(tpl["tenant"], {"domain": "<domain>", "tenant_id": "<tenant_id>"})
        for s in SKILLS:
            p = ROOT / s / "references" / "tenant_context.template.json"
            with open(p, encoding="utf-8") as f:
                self.assertEqual(json.load(f), tpl)


if __name__ == "__main__":
    unittest.main()
