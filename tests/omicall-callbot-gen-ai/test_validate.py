# -*- coding: utf-8 -*-
"""validate_smartagent.py và tts_lint.py trên fixture ghép từ api-reference.md (đã làm sạch).

Fixture chỉ chứng minh validator nhất quán nội bộ với tài liệu, KHÔNG chứng minh payload hợp lệ với nền tảng.
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cg_common import FIX, SCRIPTS, run  # noqa: E402

BAD = {
    "bad_thieu_iscustomcomp": "C3",
    "bad_system_khong_cuoi": "C2",
    "bad_canh_ve_begin": "X1",
    "bad_datas_data_dao": "X4",
    "bad_ids_rong": "X3",
    "bad_thieu_collapseobj": "C7",
    "bad_anh_hoac_chi": "X9",
    "bad_chu_so_cau_chao": "X9",
    "bad_placeholder": "X8",
    "bad_end_thieu_description": "C10",
    "bad_intent_khac_noi_end": "X6",
    "bad_bot_can_not_answer_lech": "X2",
}


class TestValidate(unittest.TestCase):
    def test_good_pass(self):
        code, out, err = run("validate_smartagent.py", os.path.join(FIX, "good.json"))
        self.assertEqual(code, 0, out + err)
        self.assertTrue(out.strip().endswith("RESULT PASS"))
        for line in out.strip().splitlines():
            self.assertRegex(line, r"^(PASS|FAIL|WARN) [CX]\d+ |^RESULT (PASS|FAIL)$")

    def test_good_post_with_sent(self):
        g = os.path.join(FIX, "good.json")
        code, out, err = run("validate_smartagent.py", g, "--mode", "post", "--sent", g)
        self.assertEqual(code, 0, out + err)
        self.assertIn("WARN C11", out)
        self.assertIn("PASS X10", out)

    def test_twelve_bad_files(self):
        files = sorted(f[:-5] for f in os.listdir(FIX) if f.startswith("bad_") and f.endswith(".json"))
        self.assertEqual(sorted(BAD), files)
        for name, code_expected in BAD.items():
            with self.subTest(name=name):
                code, out, err = run("validate_smartagent.py", os.path.join(FIX, name + ".json"))
                self.assertEqual(code, 1, out + err)
                self.assertRegex(out, r"(?m)^FAIL %s " % code_expected)
                self.assertTrue(out.strip().endswith("RESULT FAIL"))
                self.assertNotIn("Traceback", err)

    def test_four_intents_only_warn(self):
        code, out, err = run("validate_smartagent.py", os.path.join(FIX, "warn_4_intent.json"))
        self.assertEqual(code, 0, out + err)
        self.assertRegex(out, r"(?m)^WARN C1 ")
        self.assertNotRegex(out, r"(?m)^FAIL ")

    def _variant(self, mutate):
        with open(os.path.join(FIX, "good.json"), encoding="utf-8") as f:
            g = json.load(f)
        mutate(g)
        d = tempfile.mkdtemp(prefix="cg_val_")
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "v.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(g, f, ensure_ascii=False)
        return p

    def test_end_call_out_edge_fails_c6(self):
        def m(g):
            g["connections"].append({"source": "end_1", "sourceHandle": "2", "target": "clf_tu_choi", "targetHandle": "1",
                                     "id": "reactflow__edge-end_12-clf_tu_choi1", "type": "custom"})
        code, out, err = run("validate_smartagent.py", self._variant(m))
        self.assertEqual(code, 1, out + err)
        self.assertRegex(out, r"(?m)^FAIL C6 END_CALL end_1")

    def test_action_variables_missing_fails_c8(self):
        def m(g):
            g["nodes"][1]["variables"] = []
        code, out, err = run("validate_smartagent.py", self._variant(m))
        self.assertEqual(code, 1, out + err)
        self.assertRegex(out, r"(?m)^FAIL C8 ")

    def test_post_without_sent_warns_x10(self):
        code, out, err = run("validate_smartagent.py", "--mode", "post", os.path.join(FIX, "good.json"))
        self.assertEqual(code, 0, out + err)
        self.assertRegex(out, r"(?m)^WARN X10 ")

    def test_post_knowledge_lost_fails_x10(self):
        api = {"ref_id": "var_api_mau", "name": "API mau", "url": "https://api.example.invalid/x", "method": "POST",
               "headers": [{"id": "h1", "key": "Content-Type", "value": "application/json"}]}
        sent = self._variant(lambda g: g["nodes"][0]["ai_agent_config"]["knowledge"].update(apis=[copy.deepcopy(api)]))
        code, out, err = run("validate_smartagent.py", "--mode", "post", "--sent", sent, os.path.join(FIX, "good.json"))
        self.assertEqual(code, 1, out + err)
        self.assertRegex(out, r"(?m)^FAIL X10 .*var_api_mau")

    def test_usage_errors_exit_2(self):
        code, out, err = run("validate_smartagent.py")
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err)
        code, out, err = run("validate_smartagent.py", os.path.join(FIX, "khong_ton_tai.json"))
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err)

    def test_validator_is_read_only(self):
        p = os.path.join(FIX, "good.json")
        with open(p, "rb") as f:
            before = f.read()
        run("validate_smartagent.py", p)
        with open(p, "rb") as f:
            self.assertEqual(before, f.read())


class TestTtsLint(unittest.TestCase):
    def test_module(self):
        if SCRIPTS not in sys.path:
            sys.path.insert(0, SCRIPTS)
        import tts_lint
        kinds = {i["kind"] for i in tts_lint.lint_text("Gọi 0123 cho CSKH (nhé), anh hoặc chị", "t")}
        self.assertEqual(kinds, {"chu_so", "viet_tat", "ky_hieu", "anh_hoac_chi"})
        self.assertEqual(tts_lint.lint_text("Dạ em chào anh/chị, {{var_ten}} ạ.", "t"), [])
        self.assertEqual(tts_lint.lint_instruction('Tuyệt đối không nói "anh hoặc chị".', "t"), [])
        self.assertTrue(tts_lint.lint_instruction("Hãy gọi khách là anh hoặc chị.", "t"))

    def test_cli(self):
        code, out, _ = run("tts_lint.py", "--text", "Còn 2 phút")
        self.assertEqual(code, 1)
        self.assertIn("chu_so", out)
        code, out, _ = run("tts_lint.py", os.path.join(FIX, "good.json"))
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
