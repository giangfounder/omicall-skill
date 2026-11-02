"""Quan hệ giữa các skill: mục 'Gọi skill liên quan' ở mọi SKILL.md khớp shared/skill-graph.json."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = sorted(p.parent.name for p in ROOT.glob("*/SKILL.md"))


class TestSkillLinks(unittest.TestCase):
    def test_generated_sections_up_to_date(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "gen_skill_links.py"), "--check"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_skill_has_outgoing_edge_and_is_reachable(self):
        g = json.loads((ROOT / "shared" / "skill-graph.json").read_text(encoding="utf-8"))
        edges, entry = g["edges"], set(g.get("entry", []))
        for s in SKILLS:
            self.assertTrue(any(e["from"] == s for e in edges), "%s không gọi skill nào" % s)
            if s in entry:
                self.assertFalse(any(e["to"] == s for e in edges), "skill cửa vào %s không được bị gọi tới" % s)
            else:
                self.assertTrue(any(e["to"] == s for e in edges), "không skill nào gọi %s" % s)

    def test_entry_reaches_every_skill(self):
        g = json.loads((ROOT / "shared" / "skill-graph.json").read_text(encoding="utf-8"))
        for en in g.get("entry", []):
            got = {e["to"] for e in g["edges"] if e["from"] == en}
            self.assertEqual(got, set(SKILLS) - {en}, en)

    def test_section_lists_exactly_the_graph_targets(self):
        edges = json.loads((ROOT / "shared" / "skill-graph.json").read_text(encoding="utf-8"))["edges"]
        for s in SKILLS:
            t = (ROOT / s / "SKILL.md").read_text(encoding="utf-8")
            m = re.search(r"skill-links:start.*?skill-links:end", t, re.S)
            self.assertIsNotNone(m, s)
            got = set(re.findall(r"\| `(omicall-[a-z-]+)` \|", m.group(0)))
            self.assertEqual(got, {e["to"] for e in edges if e["from"] == s}, s)


if __name__ == "__main__":
    unittest.main()
