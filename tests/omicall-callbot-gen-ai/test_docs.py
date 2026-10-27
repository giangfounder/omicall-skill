# -*- coding: utf-8 -*-
"""Kiểm tài liệu của omicall-callbot-gen-ai sau CG3 (offline, chỉ đọc). Bỏ qua mọi credentials.md theo đường dẫn."""
import hashlib
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cg_common import SKILL  # noqa: E402

# Chuỗi cấm dạng văn bản (không phải dữ liệu khách).
FORBIDDEN = [
    "HỎI LẠI user",
    "Network.getAllCookies",
    "Credentials registry",
    "3 skill",
]
# Dữ liệu khách thật đã xoá khỏi skill (SĐT, 2 tên trường nghiệp vụ, hậu tố webhookId của tenant):
# chỉ lưu (độ dài, sha256) để test không chứa lại chính dữ liệu đó.
FORBIDDEN_SHA256 = [
    (10, "d0ea87591a6f5626baf380738b25d0648df535e29bb80878406ac12effcf5179"),
    (7, "31c7e92eb483732cc8123a914c2ba4d5e7c44107df1c2dc5a4506f38a145a9dd"),
    (9, "5b5d65717bd5f8d6eff4e6999f5803a047bd1a0a5de2aefc26a833d2e43dd5f7"),
    (20, "906c895dcbcd03ddc8c9776913c3a3e0a064287792b1483997141b55fdd0824c"),
]
assert len(FORBIDDEN) + len(FORBIDDEN_SHA256) == 8, "danh sách chuỗi cấm bị gộp hoặc mất phần tử"
SAFETY = ["Xuất bản", "Cần xác nhận", "mật khẩu", "uuid", "BEGIN", "datas"]


def skill_text_files():
    for root, dirs, files in os.walk(SKILL):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f == "credentials.md":
                continue  # bản mẫu, không mở
            if f.endswith((".md", ".json", ".py")):
                yield os.path.join(root, f)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


class TestDocs(unittest.TestCase):
    def setUp(self):
        self.skill_md = read(os.path.join(SKILL, "SKILL.md"))
        self.lines = self.skill_md.splitlines()

    def test_forbidden_strings_gone(self):
        for p in skill_text_files():
            t = read(p)
            for s in FORBIDDEN:
                with self.subTest(file=os.path.relpath(p, SKILL), s=s):
                    self.assertNotIn(s, t)

    def test_forbidden_hashes_gone(self):
        lens = {n for n, _ in FORBIDDEN_SHA256}
        want = {h for _, h in FORBIDDEN_SHA256}
        tok = re.compile(r"[A-Za-z0-9_]+")
        for p in skill_text_files():
            found = set()
            for m in tok.finditer(read(p)):
                w = m.group(0)
                for n in lens:
                    for i in range(0, len(w) - n + 1):
                        h = hashlib.sha256(w[i:i + n].encode("utf-8")).hexdigest()
                        if h in want:
                            found.add(h)
            with self.subTest(file=os.path.relpath(p, SKILL)):
                self.assertFalse(found, "còn dữ liệu khách (sha256) %s" % sorted(found))

    def test_safety_phrases_kept(self):
        allt = "\n".join(read(p) for p in skill_text_files() if p.endswith(".md"))
        for s in SAFETY:
            self.assertIn(s, allt)

    def test_fast_path_block(self):
        idx = [i for i, l in enumerate(self.lines) if l.strip() == "## Đường nhanh"]
        self.assertEqual(len(idx), 1)
        start = idx[0]
        self.assertLess(start, 30)
        nxt = next(i for i in range(start + 1, len(self.lines)) if self.lines[i].startswith("## "))
        self.assertLessEqual(len([l for l in self.lines[start:nxt] if l.strip()]), 20)
        prev = max(i for i in range(start) if self.lines[i].startswith("## "))
        self.assertTrue(self.lines[prev].startswith("## Bắt đầu: hỏi domain"))
        prev2 = max(i for i in range(prev) if self.lines[i].startswith("## "))
        self.assertTrue(self.lines[prev2].startswith("## Bước bắt buộc"))
        self.assertIn("## Bảo trì skill", self.skill_md)

    def test_no_relative_script_paths(self):
        self.assertIsNone(re.search(r"python scripts/", self.skill_md))

    def test_begin_rule_single_bullet(self):
        self.assertEqual(self.skill_md.count("Cấm nối ngược về BEGIN"), 1)
        self.assertEqual(self.skill_md.count("không có cạnh đi ra"), 1)
        full = [l for l in self.lines if "connection" in l and "BEGIN" in l and "next_node" in l and "null" in l]
        self.assertEqual(len(full), 1, full)
        self.assertIn("hỏi lại một lần", full[0])

    def test_referenced_paths_exist(self):
        for m in sorted(set(re.findall(r"(references/[\w.\-]+|scripts/[\w\-]+\.py)", self.skill_md))):
            with self.subTest(path=m):
                self.assertTrue(os.path.exists(os.path.join(SKILL, m)), m)

    def test_node_status(self):
        rows = json.loads(read(os.path.join(SKILL, "references", "node-status.json")))
        self.assertIsInstance(rows, list)
        keys = {"type", "side", "status", "template", "source", "verified_on", "ui_hint"}
        types = " ".join(r["type"] for r in rows)
        for name in ("CUSTOM_INTENT", "bot_can_not_answer", "TRANSFER_CALL Extension", "ADD_CLASSIFY", "END_CALL",
                     "knowledge.apis", "PUSH_NOTIFICATION", "SEND_WEBHOOK", "START_OTHER_CAMPAIGN", "Ring_group", "RAG upload"):
            self.assertIn(name, types)
        for r in rows:
            with self.subTest(type=r.get("type")):
                self.assertEqual(set(r), keys)
                self.assertIn(r["side"], ("runtime", "editor", "edge", "action"))
                self.assertIn(r["status"], ("verified", "enum", "ui_only", "unverified"))
                self.assertIsNone(r["template"])
                rel, ln = r["source"].rsplit(":", 1)
                path = os.path.join(SKILL, rel)
                self.assertTrue(os.path.exists(path), r["source"])
                n = len(read(path).splitlines())
                self.assertTrue(1 <= int(ln) <= n, r["source"])
        for t in ("PUSH_NOTIFICATION", "SEND_WEBHOOK", "START_OTHER_CAMPAIGN"):
            self.assertNotEqual(next(r for r in rows if r["type"] == t)["status"], "verified")

    def test_api_json_blocks_load(self):
        t = read(os.path.join(SKILL, "references", "api-reference.md"))
        sec = t.split("## Cấu hình API cho agent", 1)[1].split("\n## ", 1)[0]
        blocks = re.findall(r"```json\n(.*?)\n```", sec, re.S)
        self.assertTrue(blocks)
        for b in blocks:
            obj = json.loads(b)
            self.assertIn("<so_dien_thoai>", obj["body_json"])


if __name__ == "__main__":
    unittest.main()
