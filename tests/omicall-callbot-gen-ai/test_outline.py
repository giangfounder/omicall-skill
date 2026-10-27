# -*- coding: utf-8 -*-
"""script_outline.py --file chạy offline trên fixture (ghép từ tài liệu, chỉ kiểm nhất quán nội bộ)."""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cg_common import FIX, run  # noqa: E402


class TestOutline(unittest.TestCase):
    def test_file_lists_all_intents(self):
        g = os.path.join(FIX, "good.json")
        code, out, err = run("script_outline.py", "--file", g)
        self.assertEqual(code, 0, err)
        with open(g, encoding="utf-8") as f:
            s = json.load(f)
        for c in s["nodes"][0]["ai_agent_config"]["ai_analyze"]["conditions"]:
            if c["type"] == "CUSTOM_INTENT":
                self.assertIn(c["name"], out)
        self.assertNotIn("Authorization", out)

    def test_api_headers_masked(self):
        with open(os.path.join(FIX, "good.json"), encoding="utf-8") as f:
            s = json.load(f)
        s["nodes"][0]["ai_agent_config"]["knowledge"]["apis"] = [{
            "ref_id": "var_tra_cuu", "name": "Tra cứu mẫu", "url": "https://api.example.invalid/tra-cuu", "method": "POST",
            "headers": [{"id": "h1", "key": "Authorization", "value": "Bearer bi-mat-gia"}],
            "body_type": "raw", "body_json": "{}", "query_prompt": "", "param_type": "json", "time_out": 60}]
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "s.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(s, f, ensure_ascii=False)
            code, out, err = run("script_outline.py", "--file", p)
            self.assertEqual(code, 0, err)
            self.assertNotIn("bi-mat-gia", out)
            self.assertNotIn("Authorization", out)
            self.assertIn("Tra cứu mẫu", out)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_mask_keeps_plain_headers(self):
        from _cg_common import SCRIPTS
        if SCRIPTS not in sys.path:
            sys.path.insert(0, SCRIPTS)
        import script_outline
        obj = {"headers": [{"id": "h1", "key": "Content-Type", "value": "application/json"},
                           {"id": "h2", "key": "Authorization", "value": "Bearer bi-mat-gia-1234"}],
               "max_tokens": 100, "token": "bi-mat"}
        m = script_outline.mask(obj)
        self.assertEqual(m["headers"][0]["value"], "application/json")
        self.assertEqual(m["headers"][1]["value"], "***")
        self.assertEqual(m["max_tokens"], 100)
        self.assertEqual(m["token"], "***")

    def test_no_args_usage(self):
        code, out, err = run("script_outline.py")
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
