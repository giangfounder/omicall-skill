# -*- coding: utf-8 -*-
"""build_bot.py trên base fixture (ghép từ api-reference.md, chỉ nhất quán nội bộ) + spec mẫu references/spec-bot.example.json."""
import copy
import os
import tempfile
import unittest

from _util import BASE_FIXTURE, SKILL, dump, load, run

SPEC = os.path.join(SKILL, "references", "spec-bot.example.json")


class TestBuildBot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omi_cb_build_")

    def build(self, spec_path, out_name="payload.json", base=BASE_FIXTURE):
        out = os.path.join(self.tmp, out_name)
        code, so, se = run("build_bot.py", spec_path, "--base", base, "--out", out)
        return code, so, se, out

    def test_example_spec_validates(self):
        code, so, se, out = self.build(SPEC)
        self.assertEqual(code, 0, so + se)
        self.assertIn("RESULT PASS", so)
        bot = load(out)
        self.assertEqual(bot["_id"], load(BASE_FIXTURE)["_id"])
        self.assertEqual(bot["is_publish"], load(BASE_FIXTURE)["is_publish"])
        types = [c["type"] for c in bot["campaign"]["name_mappings"][0]["conditions"]]
        self.assertEqual(types[-2:], ["bot_can_not_answer", "customer_not_response"])
        code, so, _ = run("validate_bot.py", out)
        self.assertEqual(code, 0, so)

    def test_deterministic_bytes(self):
        _, _, _, o1 = self.build(SPEC, "p1.json")
        _, _, _, o2 = self.build(SPEC, "p2.json")
        with open(o1, "rb") as f1, open(o2, "rb") as f2:
            self.assertEqual(f1.read(), f2.read())

    def test_rebuild_on_own_output_is_stable(self):
        _, _, _, o1 = self.build(SPEC, "p1.json")
        code, so, se, o2 = self.build(SPEC, "p2.json", base=o1)
        self.assertEqual(code, 0, so + se)
        self.assertEqual(len(load(o1)["campaign"]["nodes"]), len(load(o2)["campaign"]["nodes"]))
        self.assertEqual(len(load(o1)["campaign"]["edges"]["connections"]),
                         len(load(o2)["campaign"]["edges"]["connections"]))

    def _spec_with_step(self, step_type):
        spec = load(SPEC)
        spec["intents"][2]["then"] = {"type": step_type}
        return dump(spec, os.path.join(self.tmp, "spec_%s.json" % step_type))

    def test_ui_only_types_exit_2(self):
        for t in ("end", "handoff", "send_message", "kick_off_context"):
            code, so, se, _ = self.build(self._spec_with_step(t))
            self.assertEqual(code, 2, t)
            self.assertIn(t, se)
            self.assertIn("làm UI", se)

    def test_nested_ui_only_exit_2(self):
        spec = load(SPEC)
        spec["intents"][0]["then"]["when_collected"]["then"] = {"type": "end"}
        code, _, se, _ = self.build(dump(spec, os.path.join(self.tmp, "nested.json")))
        self.assertEqual(code, 2)
        self.assertIn("end", se)

    def test_system_intent_exit_2(self):
        spec = load(SPEC)
        spec["intents"][2]["intent_code"] = "omi_intent_phone"
        code, _, se, _ = self.build(dump(spec, os.path.join(self.tmp, "sys.json")))
        self.assertEqual(code, 2)
        self.assertIn("CUSTOM_INTENT", se)

    def test_missing_template_exit_2(self):
        base = load(BASE_FIXTURE)
        base["campaign"]["nodes"] = [n for n in base["campaign"]["nodes"]
                                     if not any(a.get("type") == "START_OTHER_CAMPAIGN" for a in n.get("actions") or [])]
        conds = base["campaign"]["nodes"][0]["ai_analyze"]["conditions"]
        base["campaign"]["nodes"][0]["ai_analyze"]["conditions"] = [c for c in conds if c["id"] != "<case_2>"]
        b = dump(base, os.path.join(self.tmp, "base_no_flow.json"))
        code, _, se, _ = self.build(SPEC, base=b)
        self.assertEqual(code, 2)
        self.assertIn("START_OTHER_CAMPAIGN", se)

    def test_unknown_key_exit_2(self):
        spec = copy.deepcopy(load(SPEC))
        spec["publish"] = True
        code, _, se, _ = self.build(dump(spec, os.path.join(self.tmp, "pub.json")))
        self.assertEqual(code, 2)


    def _webhooks(self, bot):
        return [(n["id"], a) for n in bot["campaign"]["nodes"] for a in n.get("actions") or []
                if a.get("type") == "SEND_WEBHOOK" and n["id"] != "<action_node_id>"]

    def test_new_webhook_does_not_inherit_template_headers(self):
        base = load(BASE_FIXTURE)
        for n in base["campaign"]["nodes"]:
            for a in n.get("actions") or []:
                if a.get("type") == "SEND_WEBHOOK":
                    a["data"]["url"] = "https://partner-a.example/hook"
                    a["data"]["headers"].append({"key": "X-Secret", "value": "SECRET_A"})
        b = dump(base, os.path.join(self.tmp, "base_hdr.json"))
        spec = load(SPEC)
        spec["intents"][0]["then"]["when_collected"]["then"]["url"] = "https://other-b.example/hook"
        spec["intents"][0]["then"]["when_collected"]["then"].pop("headers", None)
        code, so, se, out = self.build(dump(spec, os.path.join(self.tmp, "spec_hdr.json")), base=b)
        self.assertEqual(code, 0, so + se)
        hooks = self._webhooks(load(out))
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0][1]["data"]["url"], "https://other-b.example/hook")
        self.assertEqual(hooks[0][1]["data"]["headers"], [{"key": "Content-Type", "value": "application/json"}])
        self.assertNotIn("SECRET_A", so + se)

    def test_webhook_editor_template_not_cloned(self):
        # mẫu editor TỔNG HỢP chỉ để test: build_bot không được chép URL/header cũ sang editor của node mới
        base = load(BASE_FIXTURE)
        base["campaign"]["name_mappings"].append(
            {"id": "<action_node_id>", "type": "ACTION",
             "actions": [{"type": "SEND_WEBHOOK", "datas": {"url": "https://partner-a.example/hook",
                                                            "bodyJson": {"text": "{}"}}}]})
        b = dump(base, os.path.join(self.tmp, "base_ed.json"))
        code, so, se, out = self.build(SPEC, base=b)
        self.assertEqual(code, 0, so + se)
        bot = load(out)
        nid = self._webhooks(bot)[0][0]
        self.assertFalse([m for m in bot["campaign"]["name_mappings"] if m.get("id") == nid])
        self.assertIn("dựng/kiểm nút trên UI", so)

    def test_out_inside_skill_or_repo_refused(self):
        for d in (SKILL, os.path.dirname(SKILL)):
            out = os.path.join(d, "zz_payload_should_not_exist.json")
            code, _, se = run("build_bot.py", SPEC, "--base", BASE_FIXTURE, "--out", out)
            self.assertEqual(code, 2, se)
            self.assertFalse(os.path.exists(out))

if __name__ == "__main__":
    unittest.main()
