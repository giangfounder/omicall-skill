# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest

from _util import BASE_FIXTURE, load, run


class TestOutline(unittest.TestCase):
    def test_outline_lists_cases_without_bearer(self):
        code, out, err = run("bot_outline.py", "--file", BASE_FIXTURE)
        self.assertEqual(code, 0, err)
        bot = load(BASE_FIXTURE)
        for c in bot["campaign"]["nodes"][0]["ai_analyze"]["conditions"]:
            self.assertIn(c["id"], out)
        self.assertIn("bot_can_not_answer", out)
        self.assertIn("customer_not_response", out)
        self.assertIn("var_sodienthoai", out)
        self.assertNotIn("Bearer", out)

    def test_skeleton_inside_repo_refused(self):
        from _util import REPO
        target = os.path.join(REPO, "tests", "omi_skeleton_should_not_exist.json")
        code, out, err = run("bot_outline.py", "--file", BASE_FIXTURE, "--testcases-skeleton", target)
        self.assertEqual(code, 2, out + err)
        self.assertFalse(os.path.exists(target))

    def test_save_masks_and_skeleton(self):
        tmp = tempfile.mkdtemp(prefix="omi_cb_out_")
        sk = os.path.join(tmp, "testcases.json")
        code, out, err = run("bot_outline.py", "--file", BASE_FIXTURE, "--save", "--out-dir", tmp,
                             "--testcases-skeleton", sk)
        self.assertEqual(code, 0, err)
        saved = [f for f in os.listdir(tmp) if f.endswith("_get.json")]
        self.assertEqual(len(saved), 1)
        with open(os.path.join(tmp, saved[0]), encoding="utf-8") as f:
            txt = f.read()
        self.assertNotIn("Bearer <access_token>", txt)
        with open(sk, encoding="utf-8") as f:
            cases = json.load(f)
        self.assertEqual({c["group"] for c in cases}, {"G%d" % i for i in range(1, 15)})
        self.assertTrue(all(c["expected"]["source"] == "Cần xác nhận" for c in cases))


if __name__ == "__main__":
    unittest.main()
