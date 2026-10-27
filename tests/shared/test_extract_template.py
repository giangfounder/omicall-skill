"""Test extract_template.py trên fixtures/flow_get_sample.json (ghép từ khối [verify JSON] của omiflow node-catalog).

Lúc chạy, test cài thêm SĐT giả, 'Bearer eyJ...' giả, URL tenant giả vào bản chép (giá trị ghép từ mảnh để chính file
test không khớp bộ quét của tools/check_skills.py). Chỉ chứng minh việc che và ghép runtime/editor/edge nhất quán,
không chứng minh template hợp lệ với nền tảng.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRIPT = ROOT / "shared" / "scripts" / "extract_template.py"
FIX = HERE / "fixtures" / "flow_get_sample.json"

TRIG = "6f1c2a9e-3b4d-4c5e-8f70-1a2b3c4d5e6f"
COND = "n7d2p1q"
ACT = "n9z8y7w"
TENANT = "65a1b2c3d4e5f60718293a4b"
FAKE_PHONE = "09" + "76543210"
FAKE_JWT = "ey" + "JhbGciOiJIUzI1NiJ9" + ".ey" + "JzdWIiOiJ4In0.chukygia"
FAKE_URL = "https://" + "khachxyz" + ".omicrm.io/flow/edit/" + TENANT

RE_PHONE = re.compile(r"(?<!\d)0[35789]\d{8}(?!\d)")
RE_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


class TestExtractTemplate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="omi_tpl_"))
        doc = json.loads(FIX.read_text(encoding="utf-8"))
        act = next(n for n in doc["nodes"] if n["id"] == ACT)
        td = act["actions"][0]["data"]["ticket_detail"]
        td["name"] = "ĐĂNG KÝ MỚI - " + FAKE_PHONE
        td["description"] = "<p>Gọi lại %s, xem %s, header Authorization: Bearer %s</p>" % (FAKE_PHONE, FAKE_URL, FAKE_JWT)
        trig = next(n for n in doc["nodes"] if n["id"] == TRIG)
        trig["description"] = "Webhook cho " + FAKE_URL
        self.src = self.tmp / "get.json"
        self.src.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_x(self, node, typ, out_name, *extra):
        out = self.tmp / out_name
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--from", str(self.src), "--node", node, "--type", typ,
                            "--out", str(out), *map(str, extra)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        return p.returncode, p.stdout + p.stderr, out

    def check_clean(self, text):
        self.assertIsNone(RE_PHONE.search(text), text)
        self.assertNotIn("eyJ", text)
        self.assertIsNone(RE_UUID.search(text))
        self.assertNotIn(TENANT, text)
        self.assertNotIn("khachxyz", text)
        for real in (TRIG, COND, ACT, "k3x9q2", "c1aa", "act01x", "qwertyuiop", "asdfghjklz"):
            self.assertNotIn(real, text)

    def test_three_types_clean_and_paired(self):
        for node, typ in ((TRIG, "WEB_HOOK"), (COND, "CONDITION"), (ACT, "ADD_TICKET")):
            code, out, path = self.run_x(node, typ, typ + ".json", "--edges")
            self.assertEqual(code, 0, out)
            text = path.read_text(encoding="utf-8")
            self.check_clean(text)
            self.check_clean(out)
            t = json.loads(text)
            self.assertEqual(t["runtime"]["id"], "<node_id>")
            self.assertEqual(len(t["editor"]), 1)
            self.assertEqual(t["editor"][0]["item"]["id"], "<node_id>")
            self.assertTrue(t["edges"], "phải có edge dính vào nút")
            for e in t["edges"]:
                self.assertIn("<node_id>", (e["source"], e["target"]))
            self.assertIs(t["_meta"]["verified"], False)
            self.assertIn("Khoá đã che", out)

    def test_structure_kept(self):
        code, out, path = self.run_x(TRIG, "WEB_HOOK", "w.json", "--edges")
        self.assertEqual(code, 0, out)
        t = json.loads(path.read_text(encoding="utf-8"))
        case = t["runtime"]["conditions"][0]
        self.assertEqual(case["id"], "<case_id>")
        self.assertEqual(case["type"], "WEB_HOOK")
        d = case["data"][0]
        self.assertEqual(d["time_out"], 5000)
        self.assertIs(d["skip_time_out"], True)
        self.assertEqual(d["multi_variables"][0]["field_code"], "<code10>")
        self.assertEqual(case["next_nodes"], ["<node_id_2>"])
        self.assertIn("<case_id>", t["runtime"]["collapse_obj"])
        self.assertEqual(t["edges"][0]["sourceHandle"], "<case_id>")
        self.assertEqual(t["runtime"]["description"], "<text>")

    def test_deterministic(self):
        _, _, a = self.run_x(ACT, "ADD_TICKET", "a.json", "--edges")
        b1 = a.read_bytes()
        _, _, b = self.run_x(ACT, "ADD_TICKET", "b.json", "--edges")
        self.assertEqual(b1, b.read_bytes())

    def test_mark_verified_requires_evidence(self):
        code, out, path = self.run_x(ACT, "ADD_TICKET", "v.json", "--mark-verified")
        self.assertEqual(code, 2, out)
        self.assertFalse(path.exists())

    def test_mark_verified_with_evidence(self):
        bad = self.tmp / "bad.txt"
        bad.write_text("FAIL C1 x\nRESULT FAIL\n", encoding="utf-8")
        code, out, _ = self.run_x(ACT, "ADD_TICKET", "v0.json", "--mark-verified", "--evidence", bad)
        self.assertEqual(code, 2, out)
        ok = self.tmp / "ok.txt"
        ok.write_text("PASS C1 x\nRESULT PASS\n", encoding="utf-8")
        code, out, path = self.run_x(ACT, "ADD_TICKET", "v1.json", "--mark-verified", "--evidence", ok)
        self.assertEqual(code, 0, out)
        meta = json.loads(path.read_text(encoding="utf-8"))["_meta"]
        self.assertIs(meta["verified"], True)
        self.assertEqual(meta["source"], "GET")
        self.assertEqual(len(meta["evidence_sha256"]), 64)

    def test_residual_sensitive_exit1(self):
        # số điện thoại nằm trong một khoá lạ, dạng enum (không dấu cách) -> không bị che theo khoá -> phải bị chặn
        doc = json.loads(self.src.read_text(encoding="utf-8"))
        act = next(n for n in doc["nodes"] if n["id"] == ACT)
        act["actions"][0]["data"]["khoa_la"] = FAKE_PHONE
        self.src.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        code, out, path = self.run_x(ACT, "ADD_TICKET", "r.json")
        self.assertEqual(code, 1, out)
        self.assertIn("còn sót", out)
        self.assertFalse(path.exists())
        # không in nguyên giá trị, chỉ đường dẫn + loại + bản che bớt
        self.assertNotIn(FAKE_PHONE, out)
        self.assertIn("khoa_la", out)
        self.assertIn(FAKE_PHONE[:2] + "*", out)

    def test_id_lists_and_incoming_source_handle(self):
        code, out, path = self.run_x(ACT, "ADD_TICKET", "ids.json", "--edges")
        self.assertEqual(code, 0, out)
        t = json.loads(path.read_text(encoding="utf-8"))
        td = t["runtime"]["actions"][0]["data"]["ticket_detail"]
        self.assertTrue(td["tags"] and all(x == "<id>" for x in td["tags"]), td["tags"])
        handles = [e.get("sourceHandle") for e in t["edges"] if e.get("target") == "<node_id>"]
        self.assertTrue(handles)
        for h in handles:
            self.assertTrue(h in ("1", "2", "success_action_step", "fail_action_step", "NEXT_STEP", None)
                            or h.startswith("<case_id"), h)

    def test_reminder_only_with_mark_verified(self):
        code, out, _ = self.run_x("khong_co", "X", "u2.json")
        self.assertEqual(code, 2, out)
        self.assertNotIn("--mark-verified chỉ dùng", out)

    def test_unknown_node(self):
        code, out, _ = self.run_x("khong_co", "X", "u.json")
        self.assertEqual(code, 2, out)

    def test_out_required(self):
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--from", str(self.src), "--node", ACT, "--type", "X"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 2)


if __name__ == "__main__":
    unittest.main()
