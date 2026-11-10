"""Test lưới an toàn: tools/sync_shared.py, tools/check_skills.py, tools/release.py preflight_checks().

Chạy trên bản chép repo trong thư mục tạm (bỏ mọi credentials.md, .git, __pycache__). Không gọi mạng.
Giá trị nhạy cảm giả được ghép lúc chạy để chính file test không khớp bộ quét.
Đặt env OMI_BASELINE_DIR=<bản chụp trước khi sửa> để chạy thêm test trên bản chụp gốc.
"""
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
SKILLS = ["omicall-callbot-gen-ai", "omicall-callbot-flow", "omicall-chatbot-gen-ai", "omicall-omiflow"]


def copy_repo(dst):
    def ignore(d, names):
        return [n for n in names if n in (".git", "__pycache__", "credentials.md") or n.endswith(".pyc")]
    shutil.copytree(ROOT, dst, ignore=ignore)
    return Path(dst)


def run_tool(script, *args):
    p = subprocess.run([sys.executable, "-B", str(TOOLS / script), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def snapshot(repo):
    """{đường dẫn tương đối: (cỡ, mtime_ns)} của mọi file trong bản chép."""
    out = {}
    for d, _, files in os.walk(repo):
        for f in files:
            p = os.path.join(d, f)
            st = os.stat(p)
            out[os.path.relpath(p, repo)] = (st.st_size, st.st_mtime_ns)
    return out


_SHARED = {}


def tearDownModule():
    if _SHARED:
        shutil.rmtree(_SHARED["tmp"], ignore_errors=True)
        _SHARED.clear()


class Base(unittest.TestCase):
    """Một bản chép repo dùng chung cho cả module (chép và lần đọc đầu file mới chép tốn vài giây mỗi lần).
    Sau mỗi test, file bị sửa/xoá được chép lại từ ROOT, file mới sinh bị xoá → test sau thấy bản sạch như chép riêng."""

    def setUp(self):
        if not _SHARED:
            tmp = Path(tempfile.mkdtemp(prefix="omi_tools_"))
            repo = copy_repo(tmp / "repo")
            _SHARED.update(tmp=tmp, repo=repo, snap=snapshot(repo))
        self.repo = _SHARED["repo"]

    def tearDown(self):
        repo, snap = _SHARED["repo"], _SHARED["snap"]
        cur = snapshot(repo)
        for rel in set(cur) - set(snap):
            os.remove(repo / rel)
        for rel, st in snap.items():
            if cur.get(rel) != st:
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel, repo / rel)
                s2 = os.stat(repo / rel)
                snap[rel] = (s2.st_size, s2.st_mtime_ns)


class TestSyncShared(Base):
    def test_check_ok_on_copy(self):
        code, out = run_tool("sync_shared.py", "--check", "--root", self.repo)
        self.assertEqual(code, 0, out)
        self.assertIn("RESULT PASS", out)

    def test_one_byte_change_detected(self):
        p = self.repo / "omicall-omiflow" / "references" / "omi-mcp.md"
        b = bytearray(p.read_bytes())
        b[-1] = (b[-1] + 1) % 256 or 65
        p.write_bytes(bytes(b))
        code, out = run_tool("sync_shared.py", "--check", "--root", self.repo)
        self.assertEqual(code, 1, out)
        self.assertIn("omicall-omiflow/references/omi-mcp.md", out)
        self.assertNotIn("FAIL lệch omicall-callbot-flow/references/omi-mcp.md", out)

    def test_sync_repairs(self):
        p = self.repo / "omicall-callbot-flow" / "scripts" / "omi_session.py"
        p.write_text("# hỏng\n", encoding="utf-8")
        code, out = run_tool("sync_shared.py", "--dry-run", "--root", self.repo)
        self.assertEqual(p.read_text(encoding="utf-8"), "# hỏng\n")
        self.assertIn("SẼ CHÉP", out)
        run_tool("sync_shared.py", "--root", self.repo)
        code, out = run_tool("sync_shared.py", "--check", "--root", self.repo)
        self.assertEqual(code, 0, out)


class TestCheckSkills(Base):
    def test_synthetic_sensitive_and_3skill(self):
        fake_phone = "09" + "87654321"
        fake_jwt = "ey" + "J" + "hbGciOiJIUzI1NiJ9abcdef"
        f = self.repo / "omicall-omiflow" / "references" / "concepts.md"
        f.write_text(f.read_text(encoding="utf-8") + f"\nSĐT {fake_phone} token {fake_jwt}\nbản giống hệt trong {3} skill OMI\n"
                     + "khach" + "xyz.omi" + "crm.io và foo" + "_session.json\n", encoding="utf-8")
        n = len(f.read_text(encoding="utf-8").splitlines())
        code, out = run_tool("check_skills.py", "--root", self.repo)
        self.assertEqual(code, 1)
        self.assertIn(f"FAIL (f) omicall-omiflow/references/concepts.md:{n - 2} SĐT", out)
        self.assertIn(f"FAIL (f) omicall-omiflow/references/concepts.md:{n - 2} JWT", out)
        self.assertIn(f"omicall-omiflow/references/concepts.md:{n} domain tenant", out)
        self.assertIn(f"omicall-omiflow/references/concepts.md:{n} file phiên", out)
        self.assertIn(f"FAIL (g) omicall-omiflow/references/concepts.md:{n - 1}", out)
        self.assertNotIn(fake_jwt, out)  # không in nguyên token

    def test_phrase_removed_fails(self):
        skill = self.repo / "omicall-omiflow"
        for p in skill.rglob("*"):
            if p.is_file() and p.suffix in (".md", ".py", ".json") and p.name != "credentials.md":
                t = p.read_text(encoding="utf-8")
                t2 = re.sub(r"(?i)cần xác nhận", "", t)
                if t2 != t:
                    p.write_text(t2, encoding="utf-8")
        code, out = run_tool("check_skills.py", "--root", self.repo, "--baseline-dir", ROOT)
        self.assertEqual(code, 1)
        self.assertIn("FAIL (b) omicall-omiflow mất cụm an toàn 'Cần xác nhận'", out)
        self.assertNotIn("FAIL (b) omicall-callbot-flow", out)

    def test_credentials_file_ignored(self):
        fake_phone = "09" + "11222333"
        for s in ("omicall-callbot-gen-ai", "omicall-omiflow"):
            (self.repo / s / "references" / "credentials.md").write_text(f"| tenant | {fake_phone} |\n", encoding="utf-8")
        code, out = run_tool("check_skills.py", "--root", self.repo)
        self.assertNotIn("credentials.md:", out)
        self.assertNotIn(fake_phone, out)

    def test_missing_script_path_fails(self):
        md = self.repo / "omicall-omiflow" / "SKILL.md"
        md.write_text(md.read_text(encoding="utf-8") + "\nChạy `scripts/khong_ton_tai_xyz.py`.\n", encoding="utf-8")
        code, out = run_tool("check_skills.py", "--root", self.repo)
        self.assertIn("FAIL (e) omicall-omiflow/SKILL.md", out)
        self.assertIn("scripts/khong_ton_tai_xyz.py", out)

    @unittest.skipUnless(os.environ.get("OMI_BASELINE_DIR"), "đặt OMI_BASELINE_DIR=<bản chụp gốc> để chạy")
    def test_original_snapshot(self):
        snap = Path(os.environ["OMI_BASELINE_DIR"])
        code, out = run_tool("check_skills.py", "--root", snap)
        self.assertEqual(code, 1)
        self.assertRegex(out, r"FAIL \(a\) omicall-\S+/SKILL.md chưa có '## Đường nhanh'")
        self.assertIn("FAIL (f) omicall-callbot-gen-ai/references/api-reference.md:133", out)
        self.assertIn("FAIL (f) omicall-chatbot-gen-ai/references/api-reference.md:32", out)
        self.assertIn("FAIL (g)", out)


class TestSharedCopyRestore(Base):
    def test_restore_after_mutation(self):
        p = self.repo / "omicall-omiflow" / "SKILL.md"
        p.write_text("# hỏng\n", encoding="utf-8")
        (self.repo / "omicall-omiflow" / "references" / "credentials.md").write_text("x\n", encoding="utf-8")
        gone = self.repo / "omicall-callbot-flow" / "references" / "node-status.json"
        gone.unlink()
        self.tearDown()
        self.assertEqual(p.read_bytes(), (ROOT / "omicall-omiflow" / "SKILL.md").read_bytes())
        self.assertFalse((self.repo / "omicall-omiflow" / "references" / "credentials.md").exists())
        self.assertTrue(gone.is_file())
        self.assertEqual(snapshot(self.repo), _SHARED["snap"])


NS_DOC = """# Tài liệu
## 1. Hành động
| `ADD_CLASSIFY` | Phân loại |
| `TRANSFER_CALL` | Chuyển máy, Ring_group |
### 1.1 ADD_CLASSIFY [verify JSON]
```json
# không phải tiêu đề
```
## 2. Khác
Không nhắc loại nào.
"""
NS_BUILDER = '''"""Builder giả. Docstring nhắc HOLDING_CALL nhưng không tính."""
SUPPORTED_ACTIONS = ("ADD_CLASSIFY", "TRANSFER_CALL")
UNSUPPORTED = {"ring_group": "Ring_group"}
def build():
    return {"type": "ADD_CLASSIFY"}, {"type": "TRANSFER_CALL", "actionType": "Extension"}
'''


def ns_row(**kw):
    r = {"type": "ADD_CLASSIFY", "side": "action", "status": "enum", "builder": "sinh", "template": None,
         "source": "references/doc.md#1.1 ADD_CLASSIFY", "verified_on": None, "ui_hint": "-"}
    r.update(kw)
    return r


class TestCheckNodeStatus(unittest.TestCase):
    """tools/check_node_status.py trên skill giả trong thư mục tạm (không đụng dữ liệu thật)."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(TOOLS))
        try:
            cls.cns = importlib.import_module("check_node_status")
        finally:
            sys.path.remove(str(TOOLS))

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="omi_ns_"))
        for skill in ("omicall-callbot-flow", "omicall-omiflow"):
            (self.tmp / skill / "references").mkdir(parents=True)
            (self.tmp / skill / "scripts").mkdir()
            (self.tmp / skill / "references" / "doc.md").write_text(NS_DOC, encoding="utf-8")
        (self.tmp / "omicall-callbot-flow" / "scripts" / "build_callflow.py").write_text(NS_BUILDER, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_ns(self, rows, skill="omicall-callbot-flow"):
        p = self.tmp / skill / "references" / "node-status.json"
        p.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        viol, exc = self.cns.check(self.tmp, [skill])
        return sorted(v[0] for v in viol), viol, exc

    def test_clean_rows_pass(self):
        codes, viol, _ = self.run_ns([
            ns_row(status="verified", verified_on="2026-11"),
            ns_row(type="TRANSFER_CALL Extension", source="references/doc.md#1. Hành động", verified_on=None),
            ns_row(type="ADD_CLASSIFY (cũ)", side="runtime", builder="khong", source="references/doc.md:3"),
            ns_row(type="TRANSFER_CALL Ring_group", builder="khong", source="references/doc.md#1. Hành động",
                   status="verified", verified_on="Cần xác nhận")])
        self.assertEqual(codes, [], viol)

    def test_each_code(self):
        codes, viol, _ = self.run_ns([
            ns_row(source="references/doc.md#9. Không có"),                    # NS2 mục không tồn tại
            ns_row(type="PUSH_NOTIFICATION", builder="khong",
                   source="references/doc.md#2. Khác"),                        # NS2 mục không nhắc loại
            ns_row(type="ADD_CLASSIFY (b)", source="references/doc.md#không phải tiêu đề"),             # NS2 dòng '#' trong khối ``` không tính
            ns_row(type="X_Y", source="references/doc.md:2", builder="khong"), # NS2 dòng lệch (kiểu cũ)
            ns_row(type="ADD_CLASSIFY", side="editor", template="references/templates/khong_co.json"),  # NS3
            ns_row(type="ADD_CLASSIFY", side="editor"),                         # NS4 trùng type+side
            ns_row(type="TRANSFER_CALL Ring_group", source="references/doc.md#1. Hành động"),  # NS6 UNSUPPORTED
            ns_row(type="ACTION/HOLDING_CALL", source="references/doc.md#1. Hành động"),       # NS2 + NS6 không có mã
            ns_row(type="TRANSFER_CALL", side="editor", source="references/doc.md#1. Hành động",
                   status="verified", verified_on=None),                       # NS5
            ns_row(type="TRANSFER_CALL", side="runtime", source="references/doc.md#1. Hành động", status="verified",
                   verified_on="2026-11", ui_hint="trường phụ: Cần xác nhận"),  # NS7
        ])
        self.assertEqual(codes.count("NS2"), 5, viol)
        self.assertEqual([c for c in codes if c != "NS2"], ["NS3", "NS4", "NS5", "NS6", "NS6", "NS7"], viol)

    def test_schema_and_no_builder(self):
        row = ns_row(builder="sinh")
        del row["verified_on"]
        codes, viol, _ = self.run_ns([row, ns_row(side="edge", builder="khong", extra=1)], skill="omicall-omiflow")
        msgs = [v[5] for v in viol]
        self.assertIn("thiếu khoá verified_on", msgs)
        self.assertIn("khoá lạ extra", msgs)
        self.assertTrue(any("skill không có builder" in m for m in msgs), msgs)  # omiflow: builder phải 'khong'

    def test_ns7_exception_listed_not_failed(self):
        key = next(iter(self.cns.NGOAI_LE))
        skill, t, side = key
        (self.tmp / skill / "references").mkdir(parents=True, exist_ok=True)
        (self.tmp / skill / "references" / "doc.md").write_text(f"# x\n## {t}\n{t}\n", encoding="utf-8")
        codes, viol, exc = self.run_ns([ns_row(type=t, side=side, builder="khong", status="verified", verified_on="2026-11",
                                               source=f"references/doc.md#{t}", ui_hint="phụ: Cần xác nhận")], skill=skill)
        self.assertNotIn("NS7", codes, viol)
        self.assertEqual(len(exc), 1)

    def test_cli_exit_codes(self):
        self.run_ns([ns_row()])
        code, out = run_tool("check_node_status.py", "--root", self.tmp, "--skill", "omicall-callbot-flow")
        self.assertEqual(code, 0, out)
        self.assertIn("RESULT PASS", out)
        self.run_ns([ns_row(source="references/doc.md#9. Không có")])
        code, out = run_tool("check_node_status.py", "--root", self.tmp, "--skill", "omicall-callbot-flow")
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL NS2 omicall-callbot-flow[0]", out)
        self.assertIn("Tổng theo mã: NS2 1", out)


class TestReleasePreflight(Base):
    def _release(self):
        sys.path.insert(0, str(TOOLS))
        try:
            return importlib.import_module("release")
        finally:
            sys.path.remove(str(TOOLS))

    def test_mismatch_stops_before_git(self):
        rel = self._release()
        p = self.repo / "omicall-chatbot-gen-ai" / "scripts" / "cdp.py"
        p.write_text(p.read_text(encoding="utf-8") + "\n# lệch\n", encoding="utf-8")
        fake = mock.Mock()
        errs = rel.preflight_checks(root=self.repo, run=fake)
        self.assertTrue(errs)
        self.assertIn("omicall-chatbot-gen-ai/scripts/cdp.py", errs[0])
        fake.assert_not_called()

    def test_untracked_credentials_path_refused(self):
        rel = self._release()

        def fake_run(cmd, **kw):
            if cmd[0] == "git" and "ls-files" in cmd:
                return subprocess.CompletedProcess(cmd, 0, "omicall-omiflow/references/credentials.md\n", "")
            if cmd[0] == "git":
                return subprocess.CompletedProcess(cmd, 0, "", "")
            return subprocess.CompletedProcess(cmd, 0, "RESULT PASS\n", "")
        errs = rel.preflight_checks(root=self.repo, run=mock.Mock(side_effect=fake_run))
        self.assertTrue(any("omicall-omiflow/references/credentials.md" in e for e in errs), errs)

    def test_template_credentials_allowed_when_clean(self):
        rel = self._release()
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            if cmd[0] == "git" and "ls-files" in cmd:
                return subprocess.CompletedProcess(cmd, 0, "\n".join(sorted(rel.TEMPLATE_CREDENTIALS)) + "\n", "")
            if cmd[0] == "git":
                return subprocess.CompletedProcess(cmd, 0, "", "")
            return subprocess.CompletedProcess(cmd, 0, "RESULT PASS\n", "")
        errs = rel.preflight_checks(root=self.repo, run=fake_run)
        self.assertEqual(errs, [])
        self.assertFalse(any(c[0] == "git" and ("commit" in c or "add" in c or "tag" in c) for c in calls))


if __name__ == "__main__":
    unittest.main()


class TestHelpNoSideEffects(unittest.TestCase):
    """--help của tools/ và self_update.py chỉ in hướng dẫn, exit 0, không gọi git/mạng; cờ lạ -> exit 2."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="omi_help_"))
        self.env = dict(os.environ, HOME=str(self.tmp), USERPROFILE=str(self.tmp), PYTHONIOENCODING="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_py(self, script, *args):
        p = subprocess.run([sys.executable, "-B", str(script), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=self.env, cwd=str(self.tmp), timeout=60)
        return p.returncode, p.stdout + p.stderr

    def test_selftest_help(self):
        code, out = self.run_py(ROOT / "tools" / "selftest.py", "--help")
        self.assertEqual(code, 0, out)
        self.assertNotIn("RESULT", out)

    def test_release_help(self):
        code, out = self.run_py(ROOT / "tools" / "release.py", "--help")
        self.assertEqual(code, 0, out)
        self.assertIn("release.py", out)

    def test_self_update_help_and_bad_args(self):
        script = ROOT / "shared" / "scripts" / "self_update.py"
        code, out = self.run_py(script, "--help")
        self.assertEqual(code, 0, out)
        self.assertIn("--force", out)
        code, out = self.run_py(script, "--khong-co")
        self.assertEqual(code, 2, out)
        self.assertFalse((self.tmp / ".cache" / "omicall-skill").exists(), "không được chạy kiểm cập nhật")

    def test_self_update_refuses_without_version(self):
        # shared/ không có VERSION -> dừng trước khi gọi git hay mạng
        code, out = self.run_py(ROOT / "shared" / "scripts" / "self_update.py")
        self.assertEqual(code, 2, out)
        self.assertIn("VERSION", out)
        self.assertFalse((self.tmp / ".cache" / "omicall-skill").exists())
