# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

from _util import dump, run

FULL = {"content": 2, "intent": 2, "grounded": 2, "tone": 2, "handoff": None}


class TestEvalReport(unittest.TestCase):
    def setUp(self):
        t = tempfile.mkdtemp(prefix="omi_cb_eval_")
        cases = [{"id": "G1-01", "group": "G1", "turns": ["<tin>"], "expected": {"action": "trả lời"}},
                 {"id": "G2-01", "group": "G2", "turns": ["<tin>"], "expected": {"action": "trả lời"}},
                 {"id": "G3-01", "group": "G3", "turns": ["<tin>"], "expected": {"action": "thu biến"}}]
        self.cases = dump(cases, os.path.join(t, "testcases.json"))
        self.one = dump({"label": "Trước", "results": [{"id": "G1-01", "reply": "<trả lời>", "scores": FULL,
                                                        "critical": False, "errors": []}]}, os.path.join(t, "r1.json"))
        self.all = dump({"label": "Sau", "results": [{"id": i, "reply": "<trả lời>", "scores": FULL, "critical": False,
                                                      "errors": []} for i in ("G1-01", "G2-01", "G3-01")]},
                        os.path.join(t, "r3.json"))

    def test_out_inside_repo_refused(self):
        from _util import REPO
        target = os.path.join(REPO, "tests", "omi_eval_should_not_exist.md")
        code, out, err = run("eval_report.py", self.cases, self.all, "-o", target)
        self.assertEqual(code, 2, out + err)
        self.assertFalse(os.path.exists(target))

    def test_missing_cases_count_as_fail(self):
        code, out, err = run("eval_report.py", self.cases, self.one)
        self.assertEqual(code, 0, err)
        self.assertIn("thiếu 2 ca", out)
        self.assertNotIn("Đạt", out)
        self.assertIn("1/3", out)

    def test_strict_exit_1(self):
        code, out, _ = run("eval_report.py", self.cases, self.one, "--strict")
        self.assertEqual(code, 1)
        self.assertIn("thiếu 2 ca", out)

    def test_complete_run_passes(self):
        code, out, _ = run("eval_report.py", self.cases, self.all, "--strict")
        self.assertEqual(code, 0)
        self.assertIn("Đạt", out)


if __name__ == "__main__":
    unittest.main()
