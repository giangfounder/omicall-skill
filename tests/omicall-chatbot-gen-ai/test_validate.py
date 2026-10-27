# -*- coding: utf-8 -*-
"""validate_bot.py trên fixture ghép từ api-reference.md:90-140, :205-216, :246-262 (chỉ nhất quán nội bộ)."""
import copy
import os
import tempfile
import unittest

from _util import BASE_FIXTURE, dump, load, run


def fails(out):
    return [l.split()[1] for l in out.splitlines() if l.startswith("FAIL ")]


class TestValidate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omi_cb_val_")
        self.bot = load(BASE_FIXTURE)

    def write(self, obj, name="bot.json"):
        return dump(obj, os.path.join(self.tmp, name))

    def test_base_fixture_pass(self):
        code, out, err = run("validate_bot.py", BASE_FIXTURE)
        self.assertEqual(code, 0, out + err)
        self.assertTrue(out.strip().endswith("RESULT PASS"))
        for line in out.splitlines():
            self.assertRegex(line, r"^(PASS|FAIL|WARN) [CX]\d+ |^RESULT (PASS|FAIL)$")
        self.assertNotIn("<access_token>", out)

    def test_get_wrapper_accepted(self):
        code, out, _ = run("validate_bot.py", self.write({"status_code": 9999, "payload": self.bot}))
        self.assertEqual(code, 0, out)

    def test_intent_only_in_name_mappings(self):
        b = copy.deepcopy(self.bot)
        b["campaign"]["nodes"][0]["ai_analyze"]["conditions"] = []
        code, out, _ = run("validate_bot.py", self.write(b))
        self.assertEqual(code, 1, out)
        self.assertIn("X1", fails(out))
        self.assertIn("C3", fails(out))

    def test_system_condition_not_last(self):
        b = copy.deepcopy(self.bot)
        conds = b["campaign"]["name_mappings"][0]["conditions"]
        conds.append(conds.pop(0))  # CUSTOM_INTENT ra sau 2 điều kiện hệ thống
        code, out, _ = run("validate_bot.py", self.write(b))
        self.assertEqual(code, 1, out)
        self.assertIn("X2", fails(out))

    def test_vector_store_ids_mismatch(self):
        b = copy.deepcopy(self.bot)
        b["campaign"]["nodes"][0]["ai_analyze"]["vector_store_ids"] = ["<record_khac>"]
        code, out, _ = run("validate_bot.py", self.write(b))
        self.assertEqual(code, 1, out)
        self.assertIn("X3", fails(out))

    def test_ref_id_is_file_id(self):
        b = copy.deepcopy(self.bot)
        f = b["vector_store"]["vector_store_files"][0]
        f["ref_id"] = f["file_id"]
        b["campaign"]["nodes"][0]["ai_analyze"]["vector_store_ids"] = [f["file_id"]]
        code, out, _ = run("validate_bot.py", self.write(b))
        self.assertEqual(code, 1, out)
        self.assertIn("X3", fails(out))

    def test_sent_with_different_is_publish(self):
        sent = copy.deepcopy(self.bot)
        sent["is_publish"] = True
        code, out, _ = run("validate_bot.py", self.write(self.bot), "--mode", "post",
                           "--sent", self.write(sent, "sent.json"))
        self.assertEqual(code, 1, out)
        self.assertIn("X4", fails(out))
        self.assertIn("C7", fails(out))

    def test_post_same_as_sent_pass(self):
        code, out, _ = run("validate_bot.py", self.write(self.bot), "--mode", "post",
                           "--sent", self.write(self.bot, "sent.json"))
        self.assertEqual(code, 0, out)
        self.assertIn("PASS X4", out)

    def test_missing_edge(self):
        b = copy.deepcopy(self.bot)
        b["campaign"]["edges"]["connections"] = b["campaign"]["edges"]["connections"][:1]
        code, out, _ = run("validate_bot.py", self.write(b))
        self.assertEqual(code, 1, out)
        self.assertIn("X5", fails(out))

    def test_begin_found_by_type_not_index(self):
        b = copy.deepcopy(self.bot)
        b["campaign"]["nodes"].reverse()
        b["campaign"]["name_mappings"].reverse()
        code, out, _ = run("validate_bot.py", self.write(b))
        self.assertEqual(code, 0, out)

    def test_masked_authorization_fails(self):
        b = copy.deepcopy(self.bot)
        b["api_knowledge"][0]["headers"][1]["value"] = "***"
        code, out, _ = run("validate_bot.py", self.write(b))
        self.assertEqual(code, 1, out)
        self.assertIn("X6", fails(out))

    def test_bad_usage_exit_2(self):
        code, _, _ = run("validate_bot.py")
        self.assertEqual(code, 2)
        code, _, _ = run("validate_bot.py", os.path.join(self.tmp, "khong_co.json"))
        self.assertEqual(code, 2)


    def test_masked_webhook_header_fails_x6(self):
        b = copy.deepcopy(self.bot)
        for n in b["campaign"]["nodes"]:
            for a in n.get("actions") or []:
                if a.get("type") == "SEND_WEBHOOK":
                    a["data"]["headers"].append({"key": "Authorization", "value": "***"})
        code, out, _ = run("validate_bot.py", self.write(b))
        self.assertEqual(code, 1, out)
        self.assertIn("X6", fails(out))
        self.assertRegex(out, r"FAIL X6 .*actions\[0\]\.data\.headers\[1\]\.value")

    def test_masked_body_string_fails_x6(self):
        b = copy.deepcopy(self.bot)
        b["api_knowledge"][0]["body_json"] = '{"t":"***"}'
        code, out, _ = run("validate_bot.py", self.write(b))
        self.assertEqual(code, 1, out)
        self.assertIn("X6", fails(out))

    def test_masked_url_path_and_free_text_fail_x6(self):
        # mask_text che JWT trong đường dẫn URL / trong câu thành '***' trần -> vẫn phải FAIL X6
        for val in ("https://hook.example/***/run", "Gọi kèm ***", "***,next"):
            b = copy.deepcopy(self.bot)
            for n in b["campaign"]["nodes"]:
                for a in n.get("actions") or []:
                    if a.get("type") == "SEND_WEBHOOK":
                        a["data"]["url"] = val
            code, out, _ = run("validate_bot.py", self.write(b))
            self.assertEqual(code, 1, (val, out))
            self.assertIn("X6", fails(out), val)

    def test_markdown_bold_not_masked(self):
        b = copy.deepcopy(self.bot)
        b["system_prompt"] = "***Lưu ý***: trả lời ngắn"
        code, out, _ = run("validate_bot.py", self.write(b))
        self.assertEqual(code, 0, out)

    def test_is_publish_true_pre_warns(self):
        b = copy.deepcopy(self.bot)
        b["is_publish"] = True
        code, out, _ = run("validate_bot.py", self.write(b))
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"(?m)^WARN C7 ")

if __name__ == "__main__":
    unittest.main()
