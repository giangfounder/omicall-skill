"""omi-mcp.md chỉ được sắp lại và bổ sung, không mất ý.

So với bản chụp trước khi sửa (fixtures/omi-mcp.baseline.md): mọi dòng không rỗng phải còn nguyên văn trong tập
omi-mcp.md (lõi) + omi-mcp-extra.md (chỉ dẫn cho skill điều phối) + omi-mcp-tools.md (bảng công cụ, tiết kiệm token,
danh mục) + README.md (cài MCP cho client khác), trừ các dòng ghi trong CHANGED (mỗi dòng ghi lý do và các cụm ý bắt
buộc còn trong bản mới).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
NEW = ROOT / "shared" / "references" / "omi-mcp.md"
EXTRA = ROOT / "shared" / "references" / "omi-mcp-extra.md"  # chỉ dẫn cho skill điều phối (assistant)
TOOLS = ROOT / "shared" / "references" / "omi-mcp-tools.md"  # mục 3-5 cũ: công cụ theo bước, tiết kiệm token, danh mục
README = ROOT / "README.md"  # phụ lục A cũ: cài MCP cho client khác (cấu hình không chứa mật khẩu)
BASE = HERE / "fixtures" / "omi-mcp.baseline.md"
sys.path.insert(0, str(ROOT / "tools"))
import sync_shared  # noqa: E402

CORE_MAX = 17000  # byte; lõi omi-mcp.md nạp ở mọi skill (21,5 KB trước đợt 3; phần còn lại là quy tắc an toàn)
NO_PW = ["không chứa mật khẩu"]

# dòng baseline được phép đổi -> (lý do, cụm phải còn ở đâu đó trong bản mới)
CHANGED = {
    3: ("nguồn chung ở shared/ + tools/sync_shared.py; dùng cho mọi skill (7 skill chuyên trách + assistant)",
        ["File dùng chung cho mọi skill OMI", "7 skill chuyên trách", "sync_shared.py"]),
    9: ("§1 chuyển xuống Phụ lục A, rồi sang README", ["Cài MCP cho client khác"]),
    11: ("agent không cầm mật khẩu: user tự chạy lệnh soạn sẵn", ["agent phải tự kiểm tra MCP OMI", "không cầm mật khẩu"]),
    14: ("mật khẩu vào kho bí mật qua form setup --ui",
         ["Không in lại mật khẩu/token", "không ghi chúng vào repo hay file tạm", "kho bí mật"]),
    19: ("cột lệnh: user tự chạy", ["Lệnh user tự chạy"]),
    21: ("lệnh server omi_login.py serve, không mật khẩu", ["codex mcp add OMICall-<domain>", "codex mcp list"]),
    22: ("lệnh server omi_login.py serve, không mật khẩu", ["claude mcp add OMICall-<domain> --scope user", "claude mcp list"]),
    23: ("lệnh server omi_login.py serve, không mật khẩu", ["gemini mcp add --scope user --transport stdio", "gemini mcp list"]),
    24: ("lệnh server omi_login.py serve, không mật khẩu", ["opencode mcp add OMICall-<domain> --global", "opencode mcp list"]),
    39: ("JSON mẫu: lệnh python omi_login.py serve", ['"command": "python"']),
    40: ("JSON mẫu: lệnh python omi_login.py serve", ['"serve", "--domain", "<domain>"']),
    41: ("JSON mẫu không còn khối env mật khẩu", NO_PW),
    42: ("JSON mẫu không còn khối env mật khẩu", NO_PW),
    43: ("JSON mẫu không còn khối env mật khẩu", NO_PW),
    44: ("JSON mẫu không còn khối env mật khẩu", NO_PW),
    45: ("JSON mẫu không còn khối env mật khẩu", NO_PW),
    51: ("VS Code/OpenCode: lệnh python omi_login.py serve", ["VS Code dùng khóa gốc `servers`", "OpenCode v2 dùng `mcp.servers`"]),
    64: ("file phiên tách theo phiên Claude Code và theo server (omicall-mcp ghi đè tenant từ session.json, 11/2026)",
         ["**Token cho API mà MCP không có**", "omi_session.py", "sessions/<CLAUDE_CODE_SESSION_ID>",
          "servers/<domain>", "Không in token ra hội thoại"]),
    65: ("không đọc cookie/token trong trang (C5), theo bảng quyết định token",
         ["Phương án dự phòng", "đăng nhập **một lần**", "Agent không tự gõ mật khẩu vào form hay API đăng nhập",
          "không đọc cookie hay token trong trang", "mở lại phiên"]),
    66: ("401 của script/API → omi_login.py login; công cụ MCP hết phiên → login_omicall_mcp",
         ["gọi lại `login_omicall_mcp`", "omi_login.py login --domain <domain>"]),
    147: ("401 của script/API → omi_login.py login; công cụ MCP hết phiên → login_omicall_mcp",
          ["gọi lại `login_omicall_mcp`", "omi_login.py login --domain <domain>"]),
    120: ("file chép sang mọi skill: đường dẫn script tóm tắt theo từng skill, không chỉ omiflow",
          ["**Không đổ JSON lớn vào hội thoại**", "flow_outline.py", "script_outline.py", "bot_outline.py",
           "hoặc chỉ in trường cần thiết"]),
    126: ("§5 chuyển xuống Phụ lục B (nay ở omi-mcp-tools.md)", ["Phụ lục B — Danh mục công cụ theo nhóm và module cần bật"]),
}


def lines(p):
    return p.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")


class TestOmiMcp(unittest.TestCase):
    def setUp(self):
        self.core = lines(NEW)
        self.new = self.core + lines(EXTRA) + lines(TOOLS) + lines(README)
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
        self.assertTrue(any("Đọc nhanh" in l for l in self.core[:15]))
        start = next(i for i, l in enumerate(self.core) if l.startswith("## Đọc nhanh"))
        end = next(i for i in range(start + 1, len(self.core)) if self.core[i].startswith("## "))
        self.assertLessEqual(len([l for l in self.core[start:end] if l.strip()]), 10)
        core = "\n".join(self.core)
        for h in ("## 2a.", "## 2. Đăng nhập bằng MCP", "## 4a.", "## 4b.", "## 4c.", "## 6. Xử lý lỗi"):
            self.assertIn(h, core, "mục được skill khác trỏ tới phải còn trong lõi")
        self.assertIn("## 7. Dựng nhiều artefact", self.text)
        self.assertIn("## 8. Mẫu giao việc cho subagent", self.text)
        self.assertIn("Bảng quyết định token", core)
        self.assertLessEqual(len(NEW.read_bytes()), CORE_MAX)

    def test_no_plain_password_and_syntax(self):
        readme = README.read_text(encoding="utf-8")
        self.assertNotRegex(self.text, r"OMICALL_PASSWORD=<")
        self.assertNotIn('"OMICALL_PASSWORD"', self.text)
        self.assertIn("npx -y omicall-mcp", "\n".join(self.core))
        self.assertIn("npx -y omicall-mcp", readme)
        self.assertIn("OMICall-<domain>", readme)
        self.assertIn("omi_login.py serve --domain <domain>", readme)
        self.assertIn("setup --ui", readme)
        self.assertNotRegex(self.text, r"(?<!\d)[34] skill")
        head = "\n".join(self.core).split("## 2a.")[0]
        self.assertNotIn("cookie", head.replace("Không đọc cookie hay token trong trang", ""))

    def test_401_rule_unified(self):
        core = "\n".join(self.core)
        self.assertIn("script/API gặp 401", core)
        self.assertIn("Công cụ MCP báo hết phiên", core)

    def test_identical_in_skills(self):
        for rel in ("references/omi-mcp.md", "references/omi-mcp-tools.md", "references/omi-mcp-extra.md"):
            src = (ROOT / "shared" / rel).read_bytes()
            for s in sync_shared.MAP[rel]:
                self.assertEqual((ROOT / s / rel).read_bytes(), src, s)


if __name__ == "__main__":
    unittest.main()
