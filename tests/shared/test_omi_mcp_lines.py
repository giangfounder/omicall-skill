"""omi-mcp.md chỉ được sắp lại và bổ sung, không mất ý.

So với bản chụp trước khi sửa (fixtures/omi-mcp.baseline.md): mọi dòng không rỗng phải còn nguyên văn, trừ các dòng
ghi trong CHANGED (mỗi dòng ghi lý do và các cụm ý bắt buộc còn trong bản mới).
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
NEW = ROOT / "shared" / "references" / "omi-mcp.md"
BASE = HERE / "fixtures" / "omi-mcp.baseline.md"
SKILLS = ["omicall-callbot-gen-ai", "omicall-callbot-flow", "omicall-chatbot-gen-ai", "omicall-omiflow"]

# dòng baseline được phép đổi -> (lý do, cụm phải còn ở đâu đó trong bản mới)
CHANGED = {
    3: ("nguồn chung chuyển sang shared/ + tools/sync_shared.py", ["File dùng chung cho 4 skill", "sync_shared.py"]),
    9: ("§1 chuyển xuống Phụ lục A", ["Phụ lục A"]),
    11: ("agent không cầm mật khẩu: user tự chạy lệnh soạn sẵn", ["agent phải tự kiểm tra MCP OMI", "không cầm mật khẩu"]),
    14: ("mật khẩu để placeholder", ["Không in lại mật khẩu/token", "không ghi chúng vào repo hay file tạm", "kho bí mật"]),
    19: ("cột lệnh: user tự chạy", ["Lệnh user tự chạy"]),
    21: ("placeholder <mật khẩu>", ["codex mcp add OMICall-<domain>", "codex mcp list"]),
    22: ("placeholder <mật khẩu>", ["claude mcp add OMICall-<domain> --scope user", "claude mcp list"]),
    23: ("placeholder <mật khẩu>", ["gemini mcp add --scope user --transport stdio", "gemini mcp list"]),
    24: ("placeholder <mật khẩu>", ["opencode mcp add OMICall-<domain> --global", "opencode mcp list"]),
    65: ("cookie bị chặn thì dừng, theo bảng quyết định token",
         ["Phương án dự phòng", "đăng nhập **một lần**", "Agent không tự gõ mật khẩu vào form hay API đăng nhập",
          "mở lại phiên"]),
    120: ("file chép sang 4 skill: đường dẫn script tóm tắt theo từng skill, không chỉ omiflow",
          ["**Không đổ JSON lớn vào hội thoại**", "flow_outline.py", "script_outline.py", "bot_outline.py",
           "hoặc chỉ in trường cần thiết"]),
    126: ("§5 chuyển xuống Phụ lục B", ["Phụ lục B — Danh mục công cụ theo nhóm và module cần bật"]),
}


def lines(p):
    return p.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")


class TestOmiMcp(unittest.TestCase):
    def setUp(self):
        self.new = lines(NEW)
        self.text = "\n".join(self.new)

    def test_no_line_lost(self):
        newset = set(self.new)
        lost = [(i, l) for i, l in enumerate(lines(BASE), 1) if l.strip() and l not in newset and i not in CHANGED]
        self.assertEqual(lost, [], "dòng baseline bị mất: %r" % lost[:5])

    def test_changed_lines_keep_meaning(self):
        for i, (why, phrases) in CHANGED.items():
            for ph in phrases:
                self.assertIn(ph, self.text, "dòng %d (%s): thiếu cụm %r" % (i, why, ph))

    def test_header_blocks(self):
        self.assertTrue(any("Đọc nhanh" in l for l in self.new[:15]))
        start = next(i for i, l in enumerate(self.new) if l.startswith("## Đọc nhanh"))
        end = next(i for i in range(start + 1, len(self.new)) if self.new[i].startswith("## "))
        self.assertLessEqual(len([l for l in self.new[start:end] if l.strip()]), 10)
        self.assertIn("## 7. Dựng nhiều artefact", self.text)
        self.assertIn("## 8. Mẫu giao việc cho subagent", self.text)
        self.assertIn("Bảng quyết định token", self.text)

    def test_no_plain_password_and_syntax(self):
        self.assertNotIn("<mật-khẩu>`", self.text.split("## Phụ lục A")[1].split("```json")[0])
        self.assertIn("npx -y omicall-mcp", self.text)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("npx -y omicall-mcp", readme)
        self.assertIn("OMICall-<domain>", readme)
        self.assertNotRegex(self.text + readme, r"(?<!\d)3 skill")
        self.assertNotIn("cookie", self.text.split("## 2.")[0].replace("Đọc cookie bằng JS/CDP bị lớp an toàn chặn thì **dừng**", ""))

    def test_identical_in_skills(self):
        src = NEW.read_bytes()
        for s in SKILLS:
            self.assertEqual((ROOT / s / "references" / "omi-mcp.md").read_bytes(), src, s)


if __name__ == "__main__":
    unittest.main()
