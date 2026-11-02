"""Giữ skill gọn và lời nói với user dễ hiểu: giới hạn kích thước SKILL.md, khung trao đổi chung, không thuật ngữ trong mẫu câu."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = sorted(p.parent.name for p in ROOT.glob("*/SKILL.md"))
BUILDERS = ["omicall-callbot-gen-ai", "omicall-callbot-flow", "omicall-chatbot-gen-ai", "omicall-omiflow"]
ENTRY = json.loads((ROOT / "shared" / "skill-graph.json").read_text(encoding="utf-8")).get("entry", [])
# byte; nâng ngưỡng chỉ khi có lý do, chi tiết chuyển sang references/playbook.md
LIMIT = {"builder": 12000, "entry": 5000, "other": 10000}
JARGON = ["flow", "node", "webhook", "payload", "json", "api", "tenant", "intent", "ivr", "token", "mcp",
          "prompt", "trigger", "draft", "endpoint", "schema"]


def kind(s):
    return "builder" if s in BUILDERS else "entry" if s in ENTRY else "other"


class TestSkillUx(unittest.TestCase):
    def test_skill_md_size(self):
        for s in SKILLS:
            n = len((ROOT / s / "SKILL.md").read_bytes())
            self.assertLessEqual(n, LIMIT[kind(s)], "%s/SKILL.md %d byte > %d" % (s, n, LIMIT[kind(s)]))

    def test_every_skill_uses_shared_conversation(self):
        for s in SKILLS:
            t = (ROOT / s / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("references/conversation.md", t, s)
            self.assertTrue((ROOT / s / "references" / "conversation.md").is_file(), s)

    def test_builders_point_to_playbook(self):
        for s in BUILDERS:
            self.assertIn("references/playbook.md", (ROOT / s / "SKILL.md").read_text(encoding="utf-8"), s)
            self.assertTrue((ROOT / s / "references" / "playbook.md").is_file(), s)

    def test_user_facing_templates_have_no_jargon(self):
        t = (ROOT / "shared" / "references" / "conversation.md").read_text(encoding="utf-8")
        blocks = re.findall(r"<!-- loi-user:start -->(.*?)<!-- loi-user:end -->", t, re.S)
        self.assertTrue(blocks, "conversation.md thiếu khối loi-user")
        for b in blocks:
            for w in JARGON:
                self.assertIsNone(re.search(r"(?i)\b%s\b" % re.escape(w), b), "mẫu câu cho user có thuật ngữ '%s'" % w)


if __name__ == "__main__":
    unittest.main()
