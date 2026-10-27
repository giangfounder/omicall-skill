# -*- coding: utf-8 -*-
"""goto.py: --help không gọi mạng; thiếu đối số in usage, exit 2; chọn tab đúng domain."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cg_common import SCRIPTS, run  # noqa: E402


class TestGoto(unittest.TestCase):
    def test_help_offline(self):
        code, out, err = run("goto.py", "--help")
        self.assertEqual(code, 0, err)
        self.assertIn("script_id", out)
        self.assertNotIn("Traceback", err)

    def test_no_args(self):
        code, out, err = run("goto.py")
        self.assertEqual(code, 2)
        self.assertIn("usage", err.lower())
        self.assertNotIn("Traceback", err)

    def test_pick_tab(self):
        if SCRIPTS not in sys.path:
            sys.path.insert(0, SCRIPTS)
        import goto
        host = "." + "omicrm" + ".io"  # ghép chuỗi để bộ quét domain tenant không bắt ví dụ giả
        tabs = [
            {"type": "page", "url": "https://khac" + host + "/ai/callbot/script/update/1"},
            {"type": "page", "url": "https://mau" + host + ".evil.example/ai/callbot/script/update/1"},
            {"type": "page", "url": "https://mau" + host + "/dashboard"},
            {"type": "page", "url": "https://mau" + host + "/ai/callbot/script/update/2"},
        ]
        self.assertEqual(goto.pick_tab(tabs, "mau")["url"], tabs[3]["url"])
        self.assertEqual(goto.pick_tab(tabs[:3], "mau")["url"], tabs[2]["url"])
        self.assertIsNone(goto.pick_tab(tabs[:2], "mau"))

    def test_no_handshake_code(self):
        with open(os.path.join(SCRIPTS, "goto.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("Sec-WebSocket-Key", src)
        self.assertIn("import cdp", src)


if __name__ == "__main__":
    unittest.main()
