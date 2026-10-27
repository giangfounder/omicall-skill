"""Test manifest.py (offline): khoá ghi đa tiến trình, owner, consumed_values, stale, chặn bí mật, verify_report."""
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "shared" / "scripts"
SCRIPT = SCRIPTS / "manifest.py"


def _worker(args):
    path, i = args
    sys.path.insert(0, str(SCRIPTS))
    import manifest
    for n in range(50):
        manifest.cmd_set(path, "k%d" % i, json.dumps({"n": n, "kind": "flow"}), owner="agent%d" % i)
    return i


class TestManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="omi_manifest_"))
        self.path = self.tmp / "build_manifest.json"
        self.report = self.tmp / "verify.txt"
        self.report.write_text("PASS C1 ...\nRESULT PASS\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_m(self, *args):
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--path", str(self.path), *map(str, args)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        return p.returncode, p.stdout + p.stderr

    def saved(self, key, owner, **extra):
        body = {"id": "<id_%s>" % key, "saved_at": "2026-01-01T10:00:00", "verified_at": "2026-01-01T10:01:00",
                "verify": "PASS", "verify_report": str(self.report)}
        body.update(extra)
        code, out = self.run_m("set", key, "--json", json.dumps(body), "--owner", owner)
        self.assertEqual(code, 0, out)

    def test_parallel_writers(self):
        self.assertEqual(self.run_m("init")[0], 0)
        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(8) as pool:
            done = pool.map(_worker, [(str(self.path), i) for i in range(8)])
        self.assertEqual(sorted(done), list(range(8)))
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(sorted(data["artefacts"]), ["k%d" % i for i in range(8)])
        for i in range(8):
            self.assertEqual(data["artefacts"]["k%d" % i]["n"], 49)
        self.assertFalse(Path(str(self.path) + ".lock").exists())
        self.assertEqual([p.name for p in self.tmp.iterdir() if p.name.endswith(".tmp")], [])

    def test_wrong_owner(self):
        self.saved("flow_lead", "agentA")
        code, out = self.run_m("set", "flow_lead", "--json", '{"id": "<khac>"}', "--owner", "agentB")
        self.assertEqual(code, 2)
        self.assertIn("agentA", out)
        code, out = self.run_m("get", "flow_lead.id")
        self.assertEqual(json.loads(out), "<id_flow_lead>")

    def test_consumed_value_changed(self):
        self.saved("flow_lead", "agentA", webhook_url="https://<host>/hook/<id_cu>")
        self.saved("bot", "agentB", consumed_values={"flow_lead.webhook_url": "https://<host>/hook/<id_cu>"})
        code, out = self.run_m("check")
        self.assertEqual(code, 0, out)
        self.saved("flow_lead", "agentA", webhook_url="https://<host>/hook/<id_moi>")
        code, out = self.run_m("check")
        self.assertEqual(code, 1)
        self.assertIn("FAIL bot bot <- flow_lead.webhook_url", out)

    def test_stale_producer(self):
        self.saved("flow_lead", "agentA", webhook_url="u1")
        self.saved("bot", "agentB", consumed_values={"flow_lead.webhook_url": "u1"})
        self.assertEqual(self.run_m("stale", "flow_lead")[0], 0)
        code, out = self.run_m("check")
        self.assertEqual(code, 1)
        self.assertIn("producer flow_lead đang stale", out)

    def test_refuse_secrets(self):
        jwt_like = "ey" + "JhbGciOiJIUzI1NiJ9.x.y"
        code, out = self.run_m("set", "a", "--json", json.dumps({"note": jwt_like}), "--owner", "x")
        self.assertEqual(code, 2)
        code, out = self.run_m("set", "a", "--json", json.dumps({"headers": {"Authorization": "x"}}), "--owner", "x")
        self.assertEqual(code, 2)
        code, out = self.run_m("set", "a", "--json", json.dumps({"password": "x"}), "--owner", "x")
        self.assertEqual(code, 2)
        self.assertFalse(self.path.exists() and "password" in self.path.read_text(encoding="utf-8"))

    def test_missing_report(self):
        self.saved("flow_lead", "agentA", verify_report=str(self.tmp / "khong_co.txt"))
        code, out = self.run_m("check")
        self.assertEqual(code, 1)
        self.assertIn("verify_report", out)

    def test_report_without_pass_and_order(self):
        bad = self.tmp / "bad.txt"
        bad.write_text("FAIL C2\nRESULT FAIL\n", encoding="utf-8")
        self.saved("a", "x", verify_report=str(bad))
        self.saved("b", "y", verified_at="2026-01-01T09:00:00")
        code, out = self.run_m("check")
        self.assertEqual(code, 1)
        self.assertIn("không chứa RESULT PASS", out)
        self.assertIn("verified_at", out)

    def test_gates_and_strict(self):
        self.run_m("set", "flow_lead", "--json", json.dumps({"gates": [{"name": "Xuất bản flow", "status": "pending"}]}),
                   "--owner", "main")
        code, out = self.run_m("gates")
        self.assertIn("CHỜ USER flow_lead: Xuất bản flow", out)
        self.assertEqual(self.run_m("check")[0], 0)
        self.assertEqual(self.run_m("check", "--strict")[0], 1)


if __name__ == "__main__":
    unittest.main()
