# -*- coding: utf-8 -*-
import os
import sys
import unittest

from _util import SCRIPTS, run


class TestOmiBotLib(unittest.TestCase):
    def test_no_cookie_path(self):
        with open(os.path.join(SCRIPTS, "omi_bot_lib.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("document.cookie", src)
        self.assertNotIn("token_from_cdp", src)
        self.assertNotIn('domain in t["url"]', src)

    def test_help_offline(self):
        code, out, _ = run("omi_bot_lib.py", "--help")
        self.assertEqual(code, 0)
        self.assertIn("--domain", out)

    def test_mask_secrets(self):
        sys.path.insert(0, SCRIPTS)
        try:
            import omi_bot_lib
        finally:
            sys.path.pop(0)
        m = omi_bot_lib.mask_secrets({"headers": [{"id": "x", "key": "Authorization", "value": "Bearer abc.def.ghi"}],
                                      "token": "abc"})
        self.assertNotIn("abc.def.ghi", str(m))
        self.assertNotIn("'abc'", str(m))


if __name__ == "__main__":
    unittest.main()
