"""Tài liệu omicall-callbot-flow: Đường nhanh, tham chiếu, node-status, checklist khớp validator, dữ liệu nhạy cảm."""
import json
import re
import unittest

from _util import REFS, SKILL, SPEC_FLOW, load

# File dùng chung do owner 'shared' tạo/đồng bộ — có thể chưa có khi chạy test của skill này.
SHARED = {"references/omi-mcp.md", "references/tenant_context.template.json", "scripts/self_update.py",
          "scripts/omi_session.py", "scripts/omi_preflight.py", "scripts/omi_api.py", "scripts/omi_save.py",
          "scripts/tenant_survey.py", "scripts/manifest.py", "scripts/extract_text.py", "scripts/extract_template.py"}


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


class TestDocs(unittest.TestCase):
    def setUp(self):
        self.skill = read(SKILL / "SKILL.md")
        self.lines = self.skill.splitlines()

    def test_fast_path_block(self):
        idx = [i for i, l in enumerate(self.lines) if l.strip() == "## Đường nhanh"]
        self.assertEqual(len(idx), 1)
        self.assertLess(idx[0], 30)
        end = next(i for i in range(idx[0] + 1, len(self.lines)) if self.lines[i].startswith("## "))
        block = [l for l in self.lines[idx[0] + 1:end] if l.strip()]
        self.assertLessEqual(len(block), 20)
        self.assertIn("verify_callflow.py", "\n".join(block))
        prev = max(i for i, l in enumerate(self.lines[:idx[0]]) if l.startswith("## "))
        self.assertIn("Bước bắt buộc: cập nhật skill", self.lines[prev])

    def test_skill_md_greps(self):
        self.assertNotIn("credentials.md", self.skill)
        self.assertIn("verify_callflow.py", self.skill)
        self.assertIn("## Bảo trì skill", self.skill)
        self.assertNotIn("3 skill", self.skill)
        b2 = self.skill.split("### Bước 2")[1].split("### Bước 3")[0]
        b3 = self.skill.split("### Bước 3")[1].split("### Bước 4")[0]
        self.assertIn("user duyệt", b2)
        self.assertIn("user duyệt", b3)

    def test_paths_in_skill_md_exist(self):
        missing = []
        for p in sorted(set(re.findall(r"\b((?:references|scripts)/[\w.\-]+\.(?:md|json|py))", self.skill))):
            if not (SKILL / p).exists() and p not in SHARED:
                missing.append(p)
        self.assertEqual(missing, [])

    def test_api_reference(self):
        api = read(REFS / "api-reference.md")
        for ln in api.splitlines():
            if re.search(r"ADD_TICKET|ADD_CONTACT|HOLDING_CALL", ln):
                self.assertNotIn("omicall-callbot-gen-ai", ln)
        checklist = api.split("## 6.")[1]
        codes = re.findall(r"\*\*(C\d)\*\*", checklist)
        self.assertEqual(codes, [f"C{i}" for i in range(1, 8)])
        ver = read(SKILL / "scripts" / "verify_callflow.py")
        for c in codes:
            self.assertIn(f'"{c}"', ver)

    def test_node_status(self):
        rows = load(REFS / "node-status.json")
        self.assertTrue(rows)
        for r in rows:
            self.assertEqual(set(r), {"type", "side", "status", "template", "source", "verified_on", "ui_hint"})
            self.assertIn(r["side"], ("runtime", "editor", "edge", "action"))
            self.assertIn(r["status"], ("verified", "enum", "ui_only", "unverified"))
            f, line = r["source"].rsplit(":", 1)
            n = len(read(SKILL / f).splitlines())
            self.assertTrue(1 <= int(line) <= n, r["source"])
        st = {r["type"]: r["status"] for r in rows if r["side"] != "editor"}
        for t in ("STAFF", "CONDITION/INTENT", "CONDITION/CUSTOMER_NOT_RESPONSE", "CONDITION/CUSTOMER_RESPONSE_WRONG",
                  "CONDITION/FROM_SYSTEM EQUAL", "ACTION/ADD_CLASSIFY", "ACTION/TRANSFER_CALL Extension"):
            self.assertEqual(st[t], "verified", t)
        for t in ("CONDITION/KEYWORD", "CONDITION/CUSTOMER_RESPONSE", "ACTION/TRANSFER_CALL Ring_group",
                  "ACTION/ADD_TICKET", "ACTION/ADD_CONTACT", "ACTION/HOLDING_CALL"):
            self.assertIn(st[t], ("enum", "unverified"), t)

    def test_context_key_and_post_check_doc(self):
        sk = read(SKILL / "SKILL.md")
        self.assertIn("kho_tri_thuc", sk)
        self.assertNotIn("callbot_kb", sk, "SKILL.md chỉ nêu một khoá Kho tri thức (kho_tri_thuc, khuôn tenant_survey)")
        self.assertNotIn("omicrm.io/ai/callbot", sk, "link editor phải theo đuôi miền của tenant (io|com)")
        # omi_save.py nay chuyền --context/--base cho verify_callflow; SKILL.md phải dặn truyền --context
        self.assertIn("Quên `--context`", sk)
        self.assertIn("--base-version", sk)
        ver = read(SKILL / "scripts" / "verify_callflow.py")
        self.assertIn("--base-version", ver)

    def test_spec_examples_load(self):
        s = load(SPEC_FLOW)
        self.assertIn("Cần xác nhận", s["_ghi_chu_id"])
        json.loads(read(REFS / "spec-training.example.json"))

    def test_no_sensitive_data(self):
        pats = [re.compile(r"(?<!\d)0[35789]\d{8}(?!\d)"), re.compile(r"eyJ[A-Za-z0-9_-]{10,}"),
                re.compile(r"\b(?!chatbot-gateway|cdn)[a-z0-9-]+\.omicrm\.io\b"), re.compile(r"\w+_session\.json")]
        hits = []
        for p in SKILL.rglob("*"):
            if not p.is_file() or p.name == "credentials.md" or p.suffix not in (".md", ".json", ".py"):
                continue
            rel = p.relative_to(SKILL).as_posix()
            if rel in SHARED:
                continue
            for i, ln in enumerate(read(p).splitlines(), 1):
                for rx in pats:
                    if rx.search(ln):
                        hits.append(f"{rel}:{i}")
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
