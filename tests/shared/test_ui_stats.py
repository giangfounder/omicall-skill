"""tools/ui_stats.py (đếm ảnh, cú bấm theo ref/toạ độ, wait rồi chụp, gộp subagent, bỏ bản ghi trùng)
và ui-recipes.md (khối giao diện có trong mọi SKILL.md, đoạn JS chỉ đọc). Offline."""
import importlib.util
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location("ui_stats_t", ROOT / "tools" / "ui_stats.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def rec(uuid, ts, tools):
    return {"uuid": uuid, "type": "assistant", "timestamp": ts,
            "message": {"content": [{"type": "tool_use", "name": n, "input": i} for n, i in tools]}}


C = "mcp__Claude_Browser__computer"


class TestUiStats(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.tmp = Path(tempfile.mkdtemp(prefix="omi_uistats_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, path, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")

    def test_counts_dedup_and_subagents(self):
        main = self.tmp / "abc123.jsonl"
        rows = [
            rec("1", "2026-11-09T01:00:00Z", [("mcp__Claude_Browser__navigate", {"url": "https://<domain>.omicrm.io/flow/edit/6af1299b2f65010ec1d9db15?lng=vi"})]),
            rec("2", "2026-11-09T01:00:10Z", [(C, {"action": "wait", "duration": 2}), (C, {"action": "screenshot"})]),
            rec("3", "2026-11-09T01:00:20Z", [(C, {"action": "left_click", "coordinate": [1, 2]}),
                                             (C, {"action": "left_click", "ref": "ref_5"})]),
            rec("4", "2026-11-09T01:30:00Z", [("mcp__Claude_Browser__browser_batch", {"actions": [
                {"name": "computer", "input": {"action": "left_click", "ref": "ref_7"}},
                {"name": "computer", "input": {"action": "screenshot", "scale": 0.5}}]})]),
            rec("5", "2026-11-09T01:30:05Z", [("Bash", {"command": "python scripts/validate_flow.py p.json"})]),
        ]
        self.write(main, rows + [rows[1]])  # bản ghi trùng uuid (phiên tiếp tục) không đếm lại
        self.write(self.tmp / "abc123" / "subagents" / "a.jsonl",
                   [rec("9", "2026-11-09T01:31:00Z", [(C, {"action": "zoom", "region": [0, 0, 1, 1]})])])
        r = self.m.analyze(self.m.with_subagents([str(main)]))
        self.assertEqual(r["files"], 2)
        self.assertEqual(r["shots"], 3)
        self.assertEqual(r["shots_scaled"], 1)
        self.assertEqual(r["wait_then_shot"], 1)
        self.assertEqual(r["clicks"], 3)
        self.assertEqual(r["ref_click_pct"], 67)
        self.assertEqual(r["batch_calls"], 1)
        self.assertEqual(r["scripts"], 1)
        self.assertEqual(r["shots_by_screen"][0], ("/flow/edit/<id>", 3))
        self.assertLessEqual(r["active_min"], 6)  # khoảng 29 phút giữa hai bản ghi chỉ tính 5 phút

    def test_prefix_resolve_and_missing(self):
        self.write(self.tmp / "abc123-x.jsonl", [rec("1", "2026-11-09T01:00:00Z", [])])
        self.assertEqual(len(self.m.resolve("abc123", str(self.tmp))), 1)
        self.assertEqual(self.m.main(["khongco", "--project", str(self.tmp)]), 2)


class TestUiRecipes(unittest.TestCase):
    def test_every_skill_reads_ui_recipes(self):
        skills = sorted(p.parent for p in ROOT.glob("omicall-*/SKILL.md"))
        self.assertTrue(skills)
        for s in skills:
            text = (s / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("references/ui-recipes.md", text, s.name)
            self.assertTrue((s / "references" / "ui-recipes.md").is_file(), s.name)

    def test_js_reader_is_read_only(self):
        text = (ROOT / "shared" / "references" / "ui-recipes.md").read_text(encoding="utf-8")
        js = re.search(r"```js\n(.*?)```", text, re.S).group(1)
        for bad in ("document.cookie", "localStorage", "sessionStorage", ".click(", "fetch(", "XMLHttpRequest",
                    ".value =", ".value=", "innerHTML =", "dispatchEvent", "submit("):
            self.assertNotIn(bad, js, bad)
        self.assertIn("JSON.stringify(out).slice(0, 6000)", js)

    def test_brief_template_asks_for_screenshot_count(self):
        g = json.loads((ROOT / "shared" / "skill-graph.json").read_text(encoding="utf-8"))
        self.assertIn("ui-recipes.md", g["giao_dien"])
        brief = "\n".join(g["mau_giao_viec"])
        self.assertIn("ui-recipes.md", brief)
        self.assertIn("số ảnh đã chụp", brief)


if __name__ == "__main__":
    unittest.main()
