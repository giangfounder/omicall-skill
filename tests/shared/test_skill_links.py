"""Quan hệ giữa các skill và các khối sinh từ shared/skill-graph.json (gen_skill_links.py)."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = sorted(p.parent.name for p in ROOT.glob("*/SKILL.md"))
GEN = ROOT / "tools" / "gen_skill_links.py"


def run_gen(root, *args):
    r = subprocess.run([sys.executable, "-B", str(GEN), "--root", str(root), *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


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


class TestGeneratorOnCopy(unittest.TestCase):
    """Chạy generator ở chế độ ghi trên bản chép repo (thư mục tạm), không đụng repo thật."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omi_gen_"))
        cls.repo = cls.tmp / "repo"

        def ignore(d, names):
            return [n for n in names if n in (".git", "__pycache__", "credentials.md", "tests") or n.endswith(".pyc")]
        shutil.copytree(ROOT, cls.repo, ignore=ignore)
        cls.code, cls.out = run_gen(cls.repo)
        cls.g = json.loads((cls.repo / "shared" / "skill-graph.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def read(self, rel):
        return (self.repo / rel).read_text(encoding="utf-8")

    def test_write_then_check_is_idempotent(self):
        self.assertEqual(self.code, 0, self.out)
        code, out = run_gen(self.repo, "--check")
        self.assertEqual(code, 0, out)
        code, out = run_gen(self.repo)
        self.assertNotIn("GHI", out)

    def test_dry_run_writes_nothing(self):
        p = self.repo / "omicall-omiflow" / "SKILL.md"
        before = p.read_bytes()
        p.write_bytes(before.replace("- Mục 2–6:".encode(), b"- Muc cu:"))
        try:
            code, out = run_gen(self.repo, "--dry-run")
            self.assertIn("SẼ GHI omicall-omiflow/SKILL.md", out)
            self.assertIn(b"- Muc cu:", p.read_bytes())
        finally:
            p.write_bytes(before)

    def test_foreign_heading_in_start_region_is_error(self):
        # không xoá im lặng mục người khác chèn giữa "Bước bắt buộc" và "Đường nhanh"
        p = self.repo / "omicall-pbx-config" / "SKILL.md"
        before = p.read_bytes()
        p.write_bytes(before.replace("## Bắt đầu và cách trao đổi (BẮT BUỘC)".encode(),
                                     "## Mục riêng\nnội dung\n\n## Bắt đầu và cách trao đổi (BẮT BUỘC)".encode()))
        try:
            code, out = run_gen(self.repo, "--check")
            self.assertEqual(code, 1)
            self.assertIn("Mục riêng", out)
        finally:
            p.write_bytes(before)

    def test_skill_md_headings_version_and_mode(self):
        for s in SKILLS:
            t = self.read(f"{s}/SKILL.md")
            lines = t.split("\n")
            heads = [l for l in lines if l.startswith("## ")]
            self.assertEqual(heads[0], "## Bước bắt buộc: cập nhật skill", s)
            fast = lines.index("## Đường nhanh")
            self.assertLess(fast, 30, s)
            prev = max(i for i in range(fast) if lines[i].startswith("## "))
            if s in self.g["entry"]:
                self.assertEqual(lines[prev], "## Bước bắt buộc: cập nhật skill", s)
            else:
                self.assertEqual(lines[prev], "## Bắt đầu và cách trao đổi (BẮT BUỘC)", s)
            ver = self.read(f"{s}/VERSION").strip()
            self.assertIn("dùng v%s)" % ver, t, s)
            self.assertIn("**Chế độ subagent / hỏi đáp**", t, s)
            self.assertEqual(t.count("## Bước bắt buộc: cập nhật skill"), 1, s)

    def test_skill_md_size_limits(self):
        sys.path.insert(0, str(ROOT / "tests" / "shared"))
        import test_skill_ux as ux
        for s in SKILLS:
            n = len((self.repo / s / "SKILL.md").read_bytes())
            lim = ux.LIMIT["builder" if s in ux.BUILDERS else "entry" if s in self.g["entry"] else "other"]
            self.assertLessEqual(n, lim, "%s/SKILL.md %d byte > %d sau khi sinh" % (s, n, lim))

    def test_orchestration_waves_and_gates(self):
        t = self.read("omicall-assistant/references/orchestration.md")
        for gid in ("xuat_ban_flow", "xuat_ban_bot", "gan_so", "goi_thu"):
            self.assertIn("`%s`" % gid, t)
        self.assertLess(t.index("User xuất bản flow"), t.index("3 Nối"))
        self.assertLess(t.index("3 Nối"), t.index("User xuất bản bot/callbot"))
        self.assertLess(t.index("User xuất bản bot/callbot"), t.index("5 Gắn và thử"))
        self.assertIn("chỉ dùng kết quả sau cổng **User xuất bản flow**", t)

    def test_plan_and_approval_rules(self):
        t = self.read("omicall-assistant/references/plan-and-approval.md")
        self.assertIn("**Đọc**", t)
        self.assertIn("duyệt từng mục", t)
        self.assertIn("`training/reset`", t)
        self.assertIn("callbot-flow: bảng ý định/thực thể", t)
        self.assertNotIn("một lượt duyệt", t)
        self.assertNotIn("đọc tài khoản thật lần đầu", t)

    def test_parallel_has_single_forbidden_list_and_template(self):
        t = self.read("shared/references/parallel.md")
        self.assertEqual(t.count("**CẤM cho subagent**"), 1)
        self.assertIn("CẤM: xuất bản", t)
        self.assertIn("Chế độ subagent / hỏi đáp", t)
        for f in ("omicall-assistant/references/orchestration.md", "shared/references/omi-mcp-extra.md"):
            self.assertNotIn("CẤM: xuất bản", self.read(f), f)

    def test_check_flags_drift(self):
        p = self.repo / "omicall-assistant" / "references" / "plan-and-approval.md"
        before = p.read_bytes()
        p.write_bytes(before.replace("duyệt từng mục".encode(), b"duyet gop"))
        try:
            code, out = run_gen(self.repo, "--check")
            self.assertEqual(code, 1)
            self.assertIn("plan-and-approval.md", out)
        finally:
            p.write_bytes(before)

    def test_unknown_gate_is_error(self):
        g = json.loads((self.repo / "shared" / "skill-graph.json").read_text(encoding="utf-8"))
        bad = self.tmp / "bad"
        shutil.copytree(self.repo, bad)
        g["edges"][0]["can_cong"] = "khong_co"
        (bad / "shared" / "skill-graph.json").write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")
        code, out = run_gen(bad, "--check")
        self.assertEqual(code, 1)
        self.assertIn("khong_co", out)


if __name__ == "__main__":
    unittest.main()
