# -*- coding: utf-8 -*-
"""Kiểm tài liệu omicall-chatbot-gen-ai (CB3) offline. Không mở bất kỳ credentials.md nào.
OMI_BASELINE_DIR=<snapshot repo trước khi sửa> → so khối ```json``` và cụm từ an toàn với baseline."""
import hashlib
import json
import os
import re
import unittest

from _util import SKILL

SHARED_SCRIPTS = {"self_update.py", "omi_session.py", "omi_preflight.py", "omi_api.py", "omi_save.py",
                  "tenant_survey.py", "manifest.py", "extract_text.py", "extract_template.py", "cdp.py"}
# id bot thật đã gỡ khỏi tài liệu: chỉ lưu sha256, không ghi giá trị vào repo
REMOVED_ID_SHA256 = {"253e85cc361d87f04d095b6828edeb7f6f5af06b34aac9a9a0315fd73d395865"}
UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
SAFETY = ["Xuất bản", "Cần xác nhận", "mật khẩu", "uuid", "/end"]


def skill_files(root):
    for d, _, fs in os.walk(root):
        if "__pycache__" in d:
            continue
        for f in fs:
            if f == "credentials.md" or not f.endswith((".md", ".json", ".py")):
                continue
            yield os.path.join(d, f)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def json_blocks(text):
    return re.findall(r"```json\n(.*?)```", text, re.S)


class TestDocs(unittest.TestCase):
    def setUp(self):
        self.skill_md = read(os.path.join(SKILL, "SKILL.md"))
        self.lines = self.skill_md.splitlines()

    def test_fast_path_block(self):
        idx = next(i for i, l in enumerate(self.lines) if l.strip() == "## Đường nhanh")
        self.assertLess(idx, 30)
        end = next((j for j in range(idx + 1, len(self.lines)) if self.lines[j].startswith("#")), len(self.lines))
        block = [l for l in self.lines[idx:end] if l.strip()]
        self.assertLessEqual(len(block), 20)
        upd = next(i for i, l in enumerate(self.lines) if l.startswith("## Bước bắt buộc: cập nhật skill"))
        self.assertLess(upd, idx)

    def test_safety_phrases_present(self):
        allt = "\n".join(read(p) for p in skill_files(SKILL))
        for ph in SAFETY:
            self.assertIn(ph, allt, ph)

    def test_paths_in_skill_md_exist(self):
        for m in set(re.findall(r"(references/[A-Za-z0-9_.-]+|scripts/[A-Za-z0-9_]+\.py)", self.skill_md)):
            if m == "references/credentials.md":
                self.fail("SKILL.md còn trỏ credentials.md")
            if os.path.basename(m) in SHARED_SCRIPTS and not os.path.exists(os.path.join(SKILL, m)):
                continue  # file dùng chung do owner shared tạo/đồng bộ
            self.assertTrue(os.path.exists(os.path.join(SKILL, m)), m)

    def test_no_sensitive_or_stale(self):
        bad = []
        for p in skill_files(SKILL):
            t = read(p)
            for pat in (r"(?<!\d)0[35789]\d{8}(?!\d)", r"eyJ[A-Za-z0-9_-]{10,}", r"[A-Za-z0-9_-]*_session\.json",
                        r"input\[name=password\]", r"Credentials registry",
                        r"\b3 skill"):
                for m in re.finditer(pat, t):
                    bad.append("%s: %s" % (os.path.relpath(p, SKILL), m.group(0)))
            for m in re.finditer(UUID, t):
                if hashlib.sha256(m.group(0).lower().encode("ascii")).hexdigest() in REMOVED_ID_SHA256:
                    bad.append("%s: id bot thật đã gỡ (%s…)" % (os.path.relpath(p, SKILL), m.group(0)[:4]))
            for m in re.finditer(r"([\w{}<>%-]+)\.omicrm\.io", t):
                if m.group(1) not in ("<domain>", "{domain}", "%s", "<tên>", "{d}"):
                    bad.append("%s: %s" % (os.path.relpath(p, SKILL), m.group(0)))
        self.assertEqual(bad, [])

    def test_specific_fixes(self):
        self.assertIn("other/training", self.skill_md)
        rag = self.skill_md[self.skill_md.index("## Bước 6"):self.skill_md.index("## Bước 7")]
        self.assertIn("other/training", rag)
        q = self.skill_md[self.skill_md.index("## Truy vấn API"):self.skill_md.index("# Quy ước biên soạn")]
        self.assertRegex(q, r"24 giờ")
        self.assertNotIn("tra cứu/hỏi thông tin→RAG", self.skill_md)
        gotchas = read(os.path.join(SKILL, "references", "ui-gotchas.md"))
        self.assertNotIn("Luôn đóng bằng nút X", gotchas)
        self.assertIn("vùng mờ", gotchas)
        api = read(os.path.join(SKILL, "references", "api-reference.md"))
        self.assertNotIn("đang xác minh qua captor)", api)
        self.assertIn("Cần xác nhận", api[api.index("## RAG"):api.index("## Bot object")])
        crm = read(os.path.join(SKILL, "references", "crm-integration.md"))
        self.assertNotIn("status_code:200", crm.replace(" ", ""))
        self.assertNotIn("!= 200", crm)

    def test_node_status(self):
        with open(os.path.join(SKILL, "references", "node-status.json"), encoding="utf-8") as f:
            rows = json.load(f)
        keys = {"type", "side", "status", "template", "source", "verified_on", "ui_hint"}
        for r in rows:
            self.assertEqual(set(r), keys, r)
            self.assertIn(r["side"], ("runtime", "editor", "edge", "action"))
            self.assertIn(r["status"], ("verified", "enum", "ui_only", "unverified"))
            path, line = r["source"].rsplit(":", 1)
            full = os.path.join(SKILL, path)
            self.assertTrue(os.path.exists(full), path)
            self.assertLessEqual(int(line), len(read(full).splitlines()), r["source"])
        st = {r["type"]: r["status"] for r in rows}
        for t in ("SEND_MESSAGE (Gửi tin nhắn chung)", "END (Kết thúc trò chuyện)", "Chuyển nhân viên",
                  "KICK_OFF_CONTEXT (Kích hoạt ngữ cảnh)"):
            self.assertEqual(st[t], "ui_only")
        self.assertTrue(any("OMI_BOT_AI" in r["ui_hint"] for r in rows if r["type"].startswith("ACTION SEND_WEBHOOK")))

    def test_spec_example_loads(self):
        with open(os.path.join(SKILL, "references", "spec-bot.example.json"), encoding="utf-8") as f:
            json.load(f)

    @unittest.skipUnless(os.environ.get("OMI_BASELINE_DIR"), "đặt OMI_BASELINE_DIR để so với baseline")
    def test_json_blocks_vs_baseline(self):
        base = os.path.join(os.environ["OMI_BASELINE_DIR"], "omicall-chatbot-gen-ai")
        for p in skill_files(SKILL):
            if not p.endswith(".md"):
                continue
            rel = os.path.relpath(p, SKILL)
            bp = os.path.join(base, rel)
            old = set()
            if os.path.exists(bp):
                for b in json_blocks(read(bp)):
                    old.add(b)
            for b in json_blocks(read(p)):
                if b in old:
                    continue  # khối không đổi
                try:
                    json.loads(b)
                except ValueError:
                    self.fail("%s: khối ```json``` mới/sửa không parse được:\n%s" % (rel, b[:200]))
        if os.path.exists(os.path.join(base, "SKILL.md")):
            allt = "\n".join(read(p) for p in skill_files(SKILL))
            oldt = "\n".join(read(p) for p in skill_files(base))
            for ph in SAFETY:
                if ph in oldt:
                    self.assertIn(ph, allt, ph)


if __name__ == "__main__":
    unittest.main()
