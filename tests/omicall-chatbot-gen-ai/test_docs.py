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


def shared_copies():
    """Đường dẫn (tương đối trong skill) của file chép từ shared/ — sửa ở shared/, không sửa ở đây."""
    import importlib.util
    tool = os.path.join(os.path.dirname(SKILL), "tools", "sync_shared.py")
    if not os.path.isfile(tool):
        return set()
    spec = importlib.util.spec_from_file_location("_sync_shared_for_test", tool)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {rel for rel, skills in mod.MAP.items() if os.path.basename(SKILL) in skills}


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
        # Bước 6, Truy vấn API: chi tiết theo bước nằm ở references/playbook.md
        pb = read(os.path.join(SKILL, "references", "playbook.md"))
        self.assertIn("other/training", pb)
        rag = pb[pb.index("## Bước 6"):pb.index("## Bước 7")]
        self.assertIn("other/training", rag)
        q = pb[pb.index("## Truy vấn API"):pb.index("# Quy ước biên soạn")]
        self.assertRegex(q, r"24 giờ")
        self.assertNotIn("tra cứu/hỏi thông tin→RAG", self.skill_md)
        gotchas = read(os.path.join(SKILL, "references", "ui-gotchas.md"))
        self.assertNotIn("Luôn đóng bằng nút X", gotchas)
        self.assertIn("vùng mờ", gotchas)
        api = read(os.path.join(SKILL, "references", "api-reference.md"))
        self.assertNotIn("đang xác minh qua captor)", api)
        self.assertIn("Cần xác nhận", api[api.index("## RAG"):api.index("## Bot object")])
        # captor chỉ còn ở scripts/inject_captor.py (có che bí mật), không chép code trong tài liệu
        self.assertNotIn("window.fetch=function", api.replace(" ", ""))
        self.assertIn("scripts/inject_captor.py", api)
        # START_OTHER_CAMPAIGN: chỉ một schema runtime (data.ids); không còn dòng ghi runtime là datas.selected
        self.assertNotIn('actions:[{type:"START_OTHER_CAMPAIGN", datas:', api)
        self.assertNotIn("bot không biết thì im lặng, chuyển nhân viên", api)
        # nhánh "BOT chủ động kết thúc" cũng chạy khi khách im lặng → không gợi ý rẽ khung giờ ở đó
        self.assertNotIn("flow rẽ `TIME_FRAME` sau nút `OMI_BOT_AI`", gotchas)
        # Hướng A (token tĩnh 24 giờ) không còn là mặc định
        self.assertNotIn("Hướng A (mặc định)", pb)
        self.assertNotIn("Hướng A (khuyên dùng)", read(os.path.join(SKILL, "references", "crm-integration.md")))
        spec = read(os.path.join(SKILL, "references", "spec-bot.example.json"))
        self.assertNotIn("Bearer <access_token>", spec)
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
        for t in ("SEND_MESSAGE (Gửi tin nhắn chung)", "END (Kết thúc trò chuyện)",
                  "KICK_OFF_CONTEXT (Kích hoạt ngữ cảnh)"):
            self.assertEqual(st[t], "ui_only")
        # chuyển nhân viên = ACTION START_OTHER_CAMPAIGN gọi flow phụ thuộc, không phải nút giao diện
        self.assertEqual(st["Chuyển nhân viên"], "verified")
        # source trỏ đúng dòng (theo số dòng nên dễ lệch khi sửa tài liệu): kiểm vài dòng mốc
        anchors = {"Chuyển nhân viên": "huyển nhân viên", "ACTION START_OTHER_CAMPAIGN": "START_OTHER_CAMPAIGN",
                   "ACTION SEND_WEBHOOK": "SEND_WEBHOOK", "OMI_BOT_COLLECT_INFO": "collect_variables",
                   "INTENT (ý định hệ thống)": "omi_intent_phone", "api_knowledge (Truy vấn)": "API Knowledge"}
        for r in rows:
            if r["type"] in anchors:
                path, line = r["source"].rsplit(":", 1)
                text = read(os.path.join(SKILL, path)).splitlines()[int(line) - 1]
                self.assertIn(anchors[r["type"]], text, r["source"])
        self.assertTrue(any("OMI_BOT_AI" in r["ui_hint"] for r in rows if r["type"].startswith("ACTION SEND_WEBHOOK")))

    def test_consistency_round2(self):
        """Đợt dọn mâu thuẫn: một hệ chấm, một cách đăng nhập, một nguồn cho prompt/`/end`/24 giờ."""
        own = {os.path.relpath(p, SKILL).replace(os.sep, "/"): read(p) for p in skill_files(SKILL)}
        shared = shared_copies()
        mine = {k: v for k, v in own.items() if k not in shared}
        # 1 hệ chấm (G1–G14): không còn thang 12 tình huống ở file của skill này (test-cases.md là bản chép shared/)
        self.assertEqual([k for k, v in mine.items() if "n/12" in v], [])
        self.assertIn("G1–G14", self.skill_md)
        # đăng nhập: một cách (form cục bộ --ui); terminal chỉ dự phòng
        pb = own["references/playbook.md"]
        self.assertIn("setup --ui", self.skill_md)
        self.assertIn("setup --ui", pb)
        self.assertNotIn("setup --domain <domain> --email", pb)
        # attribute_structure là mảng
        for k in ("references/omicall-public-api.md", "references/crm-integration.md"):
            self.assertNotRegex(own[k], r'"attribute_structure":\s*\{', k)
            self.assertNotIn("object hay mảng", own[k], k)
        # prompt chính: một mục nguồn trong api-reference, UI mapping không còn gán Ngữ cảnh bắt đầu = system_prompt
        api = own["references/api-reference.md"]
        self.assertEqual(api.count("## Prompt chính"), 1)
        self.assertNotIn('"Ngữ cảnh bắt đầu" (= `system_prompt`)', api)
        self.assertNotIn("System Prompt nằm ở top-level `system_prompt`", pb)
        # nút gọi flow: một schema runtime (data.ids); datas.selected chỉ là editor
        self.assertEqual(len(re.findall(r'"data":\{"ids":\["<flow uuid>"\]\}', api)), 1)
        self.assertNotIn('actions:[{type:"START_OTHER_CAMPAIGN", datas:', api)
        # chuyển nhân viên: flow phụ thuộc, không phải nút giao diện; bot không im lặng
        for k, v in mine.items():
            self.assertNotIn("handoff/chuyển nhân viên, kick_off_context", v, k)
            self.assertNotIn("bot không biết thì im lặng", v, k)
        # OMI_BOT_AI: chỉ ghi nhận với SEND_WEBHOOK, không suy rộng cho mọi hành động
        self.assertNotIn("hành động trong kịch bản bot có thể không chạy", pb)
        # crm-integration không chép lại OMIFlow (trỏ sang skill omicall-omiflow)
        crm = own["references/crm-integration.md"]
        self.assertNotIn("## OMIFlow —", crm)
        self.assertNotIn("## Kiến trúc chuẩn: 2 OMIFlow", crm)
        self.assertIn("omicall-omiflow", crm)
        # quy tắc gốc `/end` chỉ ở playbook Gotchas; SKILL.md không nhắc lại chi tiết "không bật lại"
        self.assertEqual(pb.count("**`/end` (quy tắc gốc"), 1)
        self.assertNotIn("không bật lại bot", self.skill_md)
        # tham chiếu sai: mục playbook không còn trỏ về SKILL.md
        for k in ("references/ui-gotchas.md", "references/livetalk-test-optimize.md", "references/api-reference.md"):
            self.assertNotRegex(own[k], r"SKILL\.md\)? ?(Gotchas \"Editor|mục \"(Đăng nhập an toàn|Bảo trì skill)\")", k)
        self.assertNotIn("Verifed", api)
        self.assertNotIn("Camera:", api)

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
