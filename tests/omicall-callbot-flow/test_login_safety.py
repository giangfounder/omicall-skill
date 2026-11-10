"""Tài liệu omicall-callbot-flow: đăng nhập qua form --ui, không đọc cookie/token trong trang, cổng duyệt training/reset,
một nguồn cho API nhân viên và nhãn upload_excel, nguồn node-status trỏ đúng dòng, khối Python trong browser-snippets
gọi đúng hàm có thật. Chỉ kiểm file của riêng skill (bỏ qua bản chép từ shared/)."""
import ast
import re
import sys
import unittest

from _util import REFS, SKILL, load
from test_docs import SHARED, read

BANNED = ["document.cookie", "_omicrm_", "atob(", "window.__t", "Set-Clipboard", "__pasteBox", "__payload"]


def own_files(suffixes=(".md", ".json", ".py")):
    out = []
    for p in sorted(SKILL.rglob("*")):
        if not p.is_file() or p.suffix not in suffixes or "__pycache__" in p.parts:
            continue
        rel = p.relative_to(SKILL).as_posix()
        if rel not in SHARED:
            out.append((rel, read(p)))
    return out


def section(text, start, stop_prefix):
    lines = text.splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith(start))
    j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith(stop_prefix)), len(lines))
    return "\n".join(lines[i:j])


class TestLoginSafety(unittest.TestCase):
    def test_no_cookie_or_token_js(self):
        hits = []
        for rel, txt in own_files():
            for n, ln in enumerate(txt.splitlines(), 1):
                for b in BANNED:
                    if b in ln:
                        hits.append("%s:%d %s" % (rel, n, b))
                if "cookie" in ln.lower() and "không" not in ln.lower():
                    hits.append("%s:%d cookie (không phải câu cấm)" % (rel, n))
        self.assertEqual(hits, [])

    def test_login_points_to_ui_form(self):
        rx = re.compile(r'(?<!")\bsetup\b(?!")')
        bad = []
        for rel, txt in own_files((".md",)):
            for n, ln in enumerate(txt.splitlines(), 1):
                if "omi_login.py" in ln and rx.search(ln) and "--ui" not in ln and "dự phòng" not in ln:
                    bad.append("%s:%d" % (rel, n))
        self.assertEqual(bad, [])
        skill = read(SKILL / "SKILL.md")
        rule6 = next(l for l in section(skill, "## Rules", "## ").splitlines() if l.startswith("6. "))
        self.assertIn("setup --ui", rule6)
        self.assertIn("cookie", rule6)
        self.assertIn("omi_login.py login", rule6)
        contract = section(read(REFS / "playbook.md"), "## Input contract", "## ")
        self.assertIn("setup --ui", contract)

    def test_training_reset_gate(self):
        skill = read(SKILL / "SKILL.md")
        fast = section(skill, "## Đường nhanh", "## ")
        b4 = section(read(REFS / "playbook.md"), "### Bước 4", "### ")
        for blk in (fast, b4):
            self.assertIn("training/reset", blk)
            self.assertIn("hỏi user riêng", blk)
            self.assertIn("total_items == 0", blk)
        self.assertIn("user đồng ý riêng", read(REFS / "data-rules.md"))

    def test_agent_api_single_source(self):
        lines = [(rel, ln) for rel, txt in own_files((".md", ".json")) for ln in txt.splitlines() if "get_all_agent" in ln]
        self.assertEqual(len(lines), 1, lines)
        self.assertEqual(lines[0][0], "references/playbook.md")
        self.assertIn("Cần xác nhận", lines[0][1])
        for rel, txt in own_files((".md", ".json")):
            self.assertNotIn("agent-v1-stg", txt, rel)

    def test_upload_excel_single_label(self):
        api = read(REFS / "api-reference.md")
        row = next(l for l in api.splitlines() if "`callbot/training/upload_excel`" in l)
        self.assertIn("Kiểm chứng qua giao diện; gọi trực tiếp bằng API: chưa", row)
        for rel, txt in own_files((".md", ".json")):
            for ln in txt.splitlines():
                if ln == row:
                    continue
                if "upload_excel" in ln and "upload_excel/status" not in ln:
                    self.assertNotRegex(ln, r"(?i)đã kiểm chứng|chưa kiểm chứng", rel)
        fast = section(read(SKILL / "SKILL.md"), "## Đường nhanh", "## ")
        self.assertIn("api-reference.md` §2", fast)

    def test_omi_save_doc_claims(self):
        api = read(REFS / "api-reference.md")
        self.assertNotIn("chưa truyền `--context`", api)
        save = read(SKILL / "scripts" / "omi_save.py")
        self.assertIn("vextra = ['--context', a.context]", save)
        self.assertIn("post_extra += ['--base', a.base]", save)

    def test_node_status_source_line_matches_type(self):
        bad = []
        sys.path.insert(0, str(SKILL.parent / "tools"))
        try:
            import check_node_status as cns
        finally:
            sys.path.pop(0)
        for r in load(REFS / "node-status.json"):
            # nguồn dạng file#tiêu đề: mục được trỏ phải nhắc mã của loại (ví dụ CUSTOMER_RESPONSE_WRONG)
            f, anchor = r["source"].split("#", 1)
            sec, hits = cns.section(read(SKILL / f).splitlines(), anchor)
            key = r["type"].split(" ")[0].rsplit("/", 1)[-1]
            if hits != 1 or key.lower() not in sec.lower():
                bad.append("%s -> %s" % (r["type"], r["source"]))
        self.assertEqual(bad, [])

    def test_snippet_python_calls_exist(self):
        doc = read(REFS / "browser-snippets.md")
        blocks = re.findall(r"```python\n(.*?)```", doc, re.S)
        self.assertGreaterEqual(len(blocks), 3)
        defs = {}
        for mod in ("omi_api", "omi_session"):
            defs[mod] = set(re.findall(r"^def (\w+)", read(SKILL / "scripts" / (mod + ".py")), re.M))
        used = set()
        for b in blocks:
            for node in ast.walk(ast.parse(b)):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in defs:
                    used.add((node.value.id, node.attr))
        self.assertTrue(used)
        missing = sorted("%s.%s" % u for u in used if u[1] not in defs[u[0]])
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
