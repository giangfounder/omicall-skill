"""self_update.py: kéo cả repo, báo mọi skill đổi phiên bản, tự nối skill mới, thay bản chép tay bằng đường dẫn.
Chạy trên thư mục tạm, không gọi git hay mạng."""
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location("self_update_t", ROOT / "shared" / "scripts" / "self_update.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestSelfUpdateAll(unittest.TestCase):
    def setUp(self):
        self.su = load()
        self.tmp = Path(tempfile.mkdtemp(prefix="omi_su_"))
        self.su.CACHE = self.tmp / "cache"
        self.repo = self.tmp / "repo"
        for n, v in (("omicall-a", "1.0.0"), ("omicall-b", "2.0.0")):
            (self.repo / n).mkdir(parents=True)
            (self.repo / n / "VERSION").write_text(v, encoding="utf-8")
        (self.repo / "shared").mkdir()  # không có VERSION -> không phải skill
        self.agent = self.tmp / "agent"
        self.agent.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_repo_skills_only_versioned_omicall_dirs(self):
        self.assertEqual(self.su.repo_skills(self.repo), {"omicall-a": "1.0.0", "omicall-b": "2.0.0"})

    def test_version_changes_lists_every_skill(self):
        lines = self.su.version_changes({"omicall-a": "1.0.0", "omicall-c": "1.0.0"},
                                        {"omicall-a": "1.1.0", "omicall-b": "2.0.0"})
        text = "\n".join(lines)
        self.assertIn("omicall-a: 1.0.0 -> 1.1.0", text)
        self.assertIn("omicall-b: mới", text)
        self.assertIn("omicall-c: đã bỏ", text)

    def test_link_new_skill_and_warn_dangling(self):
        ok, err = self.su.make_link(self.agent / "omicall-a", self.repo / "omicall-a")
        self.assertTrue(ok, err)
        self.assertIn(self.agent, [Path(d) for d in self.su.agent_dirs(self.repo, extra=[self.agent])])
        (self.repo / "omicall-old").mkdir()
        self.su.make_link(self.agent / "omicall-old", self.repo / "omicall-old")
        (self.repo / "omicall-old").rmdir()
        added, warns = self.su.link_skills(self.repo, [self.agent])
        self.assertEqual([Path(a).name for a in added], ["omicall-b"])
        self.assertEqual((self.agent / "omicall-b" / "VERSION").read_text(encoding="utf-8"), "2.0.0")
        self.assertTrue(any("omicall-old" in w for w in warns), warns)
        self.assertTrue(self.su.is_link(self.agent / "omicall-b"))

    def test_agent_dir_without_link_to_repo_is_ignored(self):
        (self.agent / "omicall-a").mkdir()  # bản chép tay, không trỏ vào repo
        self.assertEqual(self.su.agent_dirs(self.repo, extra=[self.agent]), [])

    def test_replace_copy_moves_to_backup(self):
        cp = self.agent / "omicall-a"
        cp.mkdir()
        (cp / "VERSION").write_text("0.9.0", encoding="utf-8")
        (cp / "ghi-chu.txt").write_text("giữ lại", encoding="utf-8")
        self.assertFalse(self.su.is_link(cp))
        done, warns = self.su.replace_copies(self.repo, self.agent)
        self.assertEqual(len(done), 1, warns)
        self.assertTrue(self.su.is_link(cp))
        self.assertEqual((cp / "VERSION").read_text(encoding="utf-8"), "1.0.0")
        baks = list((self.su.CACHE / "backup").iterdir())
        self.assertEqual(len(baks), 1)
        self.assertEqual((baks[0] / "ghi-chu.txt").read_text(encoding="utf-8"), "giữ lại")


if __name__ == "__main__":
    unittest.main()
