# -*- coding: utf-8 -*-
"""Bot nhiều ngữ cảnh (api-reference.md mục "Bot nhiều ngữ cảnh"): X11 cạnh sót, X3 ở nút khác BEGIN, dàn ý
liệt kê Kích hoạt ngữ cảnh / Ngữ cảnh con. Fixture ghép tay, chỉ nhất quán nội bộ."""
import copy
import os
import tempfile
import unittest

from _util import BASE_FIXTURE, dump, load, run


def multi_bot():
    b = copy.deepcopy(load(BASE_FIXTURE))
    c = b["campaign"]
    c["nodes"] += [
        {"id": "<kick_id>", "node_type": "KICK_OFF_CONTEXT", "next_nodes": ["<ctx_id>"],
         "ai_analyze": {"context": "Kích hoạt khi khách muốn <chủ đề>", "type": "CUSTOM_INTENT"}},
        {"id": "<ctx_id>", "node_type": "CONTEXT", "name": "<tên ngữ cảnh>", "next_nodes": [],
         "ai_analyze": {"content": "<prompt>", "conditions": [], "api_knowledge_ids": ["<ref_lost>"]}},
    ]
    c["name_mappings"] += [
        {"id": "<kick_id>", "type": "KICK_OFF_CONTEXT", "data_type": "CUSTOM_INTENT", "content": "Kích hoạt khi khách muốn <chủ đề>"},
        {"id": "<ctx_id>", "type": "CONTEXT", "conditions": []},
    ]
    c["edges"]["connections"].append({"source": "<kick_id>", "sourceHandle": "2", "target": "<ctx_id>", "targetHandle": "1"})
    return b


class TestMultiContext(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omi_cb_mc_")

    def write(self, obj):
        return dump(obj, os.path.join(self.tmp, "bot.json"))

    def test_clean_multi_context_only_warns_lost_ref(self):
        code, out, _ = run("validate_bot.py", self.write(multi_bot()))
        self.assertEqual(code, 0, out)
        self.assertIn("WARN X3 nút CONTEXT <ctx_id>", out)
        self.assertIn("PASS X11", out)

    def test_orphan_edge_warned_and_listed(self):
        b = multi_bot()
        src = b["campaign"]["edges"]["connections"][0]  # cạnh từ BEGIN theo case có thật
        b["campaign"]["edges"]["connections"].append(dict(src, sourceHandle="<case_da_xoa>"))
        f = self.write(b)
        code, out, _ = run("validate_bot.py", f)
        self.assertEqual(code, 0, out)
        self.assertIn("WARN X11 cạnh sót", out)
        self.assertIn("<case_da_xoa>", out)
        code, out, _ = run("bot_outline.py", "--file", f)
        self.assertEqual(code, 0, out)
        self.assertIn("Cạnh sót (1)", out)
        self.assertIn("Kích hoạt ngữ cảnh (1)", out)
        self.assertIn("Ngữ cảnh con (1)", out)
        self.assertIn("(dừng ở đây)", out)


if __name__ == "__main__":
    unittest.main()
