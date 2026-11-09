"""check_callin.py: phím Callbot STALE/MISSING/OK, nhóm/menu còn tồn tại, đầu số chưa gắn kịch bản; chỉ báo, không ghi.
Offline: gọi thẳng evaluate() và main() với khảo sát/danh sách kịch bản giả."""
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "omicall-assistant" / "scripts" / "check_callin.py"


def load():
    spec = importlib.util.spec_from_file_location("check_callin_t", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SCRIPTS = [
    {"id": "s1-old", "uuid": "u1", "version": 1, "is_newest_version": False, "name": "Bot A"},
    {"id": "s1-new", "uuid": "u1", "version": 2, "is_newest_version": True, "name": "Bot A"},
    {"id": "s2", "uuid": "u2", "version": 1, "is_newest_version": True, "name": "Bot B"},
]


def pbx(keys, hotlines=None, call_scripts=None):
    return {"internal_groups": [{"_id": "g1"}],
            "key_interactions": [{"_id": "m1", "name": "Menu", "keys": keys}],
            "call_scripts": call_scripts or [],
            "hotlines": hotlines or []}


def call_in(steps):
    return [{"_id": "cs1", "name": "Call in",
             "scripts": [{"order": i, "action_type": t, "action_id": a} for i, (t, a) in enumerate(steps)]}]


class TestEvaluate(unittest.TestCase):
    def setUp(self):
        self.m = load()

    def test_ok(self):
        lines, bad = self.m.evaluate(pbx([{"digit": "1", "action_type": "Callbot", "action": "s2"},
                                          {"digit": "2", "action_type": "Ring_group", "action": "g1"},
                                          {"digit": "3", "action_type": "Ivr_menu", "action": "m1"}]), SCRIPTS)
        self.assertEqual(bad, 0)
        self.assertEqual(lines[-1], "RESULT PASS")

    def test_stale_points_to_newest(self):
        lines, bad = self.m.evaluate(pbx([{"digit": "1", "action_type": "Callbot", "action": "s1-old"}]), SCRIPTS)
        self.assertEqual(bad, 1)
        text = "\n".join(lines)
        self.assertIn("STALE", text)
        self.assertIn("s1-new", text)
        self.assertIn("chờ user duyệt", text)
        self.assertEqual(lines[-1], "RESULT FAIL")

    def test_missing_bot_group_menu(self):
        lines, bad = self.m.evaluate(pbx([{"digit": "1", "action_type": "Callbot", "action": "khong-co"},
                                          {"digit": "2", "action_type": "Ring_group", "action": "g9"},
                                          {"digit": "3", "action_type": "Ivr_menu", "action": "m9"}]), SCRIPTS)
        self.assertEqual(bad, 3)
        self.assertEqual(len([l for l in lines if l.startswith("  phím") and "MISSING" in l]), 3)

    def test_hotline_without_script_is_warn_only(self):
        lines, bad = self.m.evaluate(pbx([], hotlines=[{"number": "<so>", "default_script": None},
                                                       {"number": "<so2>", "default_script": "k1"}]), SCRIPTS)
        self.assertEqual(bad, 0)
        text = "\n".join(lines)
        self.assertIn("WARN chưa gắn kịch bản", text)
        self.assertIn("kịch bản k1", text)

    def test_call_script_callbot_stale_without_ivr(self):
        # Tenant không dùng Tương tác phím: Callbot gắn thẳng vào kịch bản cuộc gọi "Call in", id cũ sau xuất bản.
        p = pbx([], hotlines=[{"number": "<so>", "default_script": "cs1"}],
                call_scripts=call_in([("Callbot", "s1-old")]))
        p["key_interactions"] = []
        lines, bad = self.m.evaluate(p, SCRIPTS)
        self.assertEqual(bad, 1)
        text = "\n".join(lines)
        self.assertIn('Kịch bản cuộc gọi "Call in"', text)
        self.assertIn("bước 0: STALE", text)
        self.assertIn("s1-new", text)
        self.assertIn('kịch bản cs1 ("Call in")', text)
        self.assertEqual(lines[-1], "RESULT FAIL")

    def test_call_script_ok_and_missing_targets(self):
        p = pbx([], call_scripts=call_in([("Callbot", "s2"), ("Ivr_menu", "m1"), ("Ring_group", "g9"),
                                          ("Callbot", "khong-co")]))
        lines, bad = self.m.evaluate(p, SCRIPTS)
        self.assertEqual(bad, 2)
        text = "\n".join(lines)
        self.assertIn("bước 0: OK", text)
        self.assertIn("bước 1: OK", text)
        self.assertIn("bước 2: MISSING  nhóm g9", text)
        self.assertIn("bước 3: MISSING", text)


class TestMainReadOnlyContext(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.tmp = Path(tempfile.mkdtemp(prefix="omi_callin_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_tenant_context_not_written(self):
        ctx = self.tmp / "tenant_context.json"
        ctx.write_text(json.dumps({"tenant": {"tenant_id": "t1"}, "khac": 1}), encoding="utf-8")
        before = ctx.read_bytes()
        seen = {}

        def fake_survey(domain, out):
            seen["out"] = out
            return {"pbx": pbx([{"digit": "1", "action_type": "Callbot", "action": "s1-old"}])}

        self.m.run_survey = fake_survey
        self.m.list_callbot_scripts = lambda d, t: SCRIPTS if t == "t1" else []
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = self.m.main(["--domain", "x", "--scratch", str(self.tmp)])
        self.assertEqual(code, 1, buf.getvalue())
        self.assertEqual(ctx.read_bytes(), before)
        self.assertNotEqual(Path(seen["out"]).name, "tenant_context.json")

    def test_missing_tenant_id_exit_2(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = self.m.main(["--domain", "x", "--scratch", str(self.tmp)])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
