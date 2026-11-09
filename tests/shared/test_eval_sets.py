"""Bộ eval (offline): đủ câu kích hoạt cho mọi skill, định dạng đúng, bộ chấm routing/chất lượng chấm đúng, bộ chạy không kéo biến môi trường phiên chủ."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import claude_cli  # noqa: E402
import run_quality_eval as rq  # noqa: E402
import run_routing_eval as rr  # noqa: E402

SKILLS = sorted(p.parent.name for p in ROOT.glob("*/SKILL.md"))
GRADE_KEYS = {"mode", "max_questions", "min_confidence", "min_parts", "parts_regex_all", "o_regex",
              "o_forbid_regex", "cxn_required"}


class TestTriggerSets(unittest.TestCase):
    def test_every_skill_has_balanced_trigger_set(self):
        for s in SKILLS:
            f = ROOT / "evals" / s / "trigger.json"
            self.assertTrue(f.is_file(), "thiếu %s" % f)
            items = json.loads(f.read_text(encoding="utf-8"))
            pos = [x for x in items if x["should_trigger"] is True]
            neg = [x for x in items if x["should_trigger"] is False]
            self.assertTrue(8 <= len(pos) <= 10, "%s: %d câu nên kích hoạt (cần 8–10)" % (s, len(pos)))
            self.assertTrue(8 <= len(neg) <= 10, "%s: %d câu không kích hoạt (cần 8–10)" % (s, len(neg)))
            qs = [x["query"].strip() for x in items]
            self.assertEqual(len(qs), len(set(qs)), "%s: câu trùng" % s)
            self.assertTrue(all(qs), s)

    def test_positive_never_positive_for_two_skills(self):
        owner = {}
        for s in SKILLS:
            for x in json.loads((ROOT / "evals" / s / "trigger.json").read_text(encoding="utf-8")):
                if x["should_trigger"]:
                    self.assertNotIn(x["query"], owner, "câu là khẳng định của 2 skill: %s" % x["query"])
                    owner[x["query"]] = s


class TestQualityCases(unittest.TestCase):
    def test_cases_schema(self):
        for f in (ROOT / "evals").glob("*/evals.json"):
            d = json.loads(f.read_text(encoding="utf-8"))
            ids = [c["id"] for c in d["evals"]]
            self.assertEqual(len(ids), len(set(ids)), f)
            for c in d["evals"]:
                for k in ("prompt", "expected_output", "expectations"):
                    self.assertIn(k, c, "%s ca %s thiếu %s" % (f, c.get("id"), k))
                for p in c.get("files", []):
                    self.assertTrue((ROOT / p).is_file(), "%s: thiếu file %s" % (f, p))
                self.assertFalse(set(c.get("grade", {})) - GRADE_KEYS, "%s ca %s: khoá grade lạ" % (f, c["id"]))

    def test_grade(self):
        card = {"mode": "noi", "gia_thuyet": {"cau": "Khách cần đặt lịch qua Zalo", "tu_tin": 92},
                "o": {"vao": "Zalo OA", "doi_tuong": "khách hàng, phiếu ghi", "luat": "bot hỏi tên, SĐT, giờ",
                      "ra": "phiếu Đặt lịch giao lễ tân", "rang_buoc": "gói có chatbot",
                      "thanh_cong": "100% lịch có phiếu", "khong_lam": ["không gọi nhắc lịch"]},
                "cau_hoi": [], "phan_viec": ["chatbot Zalo", "quy trình tạo phiếu"]}
        g = {"mode": "noi", "max_questions": 1, "min_confidence": 80, "min_parts": 2,
             "parts_regex_all": ["(?i)chatbot|bot", "(?i)quy trình|flow|phiếu"], "o_regex": {"khong_lam": "(?i)nhắc"}}
        self.assertEqual(rq.grade(card, g), [])
        self.assertTrue(rq.grade(None, g))
        bad = json.loads(json.dumps(card))
        bad["o"]["khong_lam"] = ["không làm báo cáo"]
        self.assertTrue(rq.grade(bad, g))
        doc = {"mode": "tai_lieu", "o": dict(card["o"], thanh_cong="trong 4 giờ"), "can_xac_nhan": []}
        self.assertTrue(any("Cần xác nhận" in w or "nghi bịa" in w for w in
                            rq.grade(doc, {"mode": "tai_lieu", "cxn_required": ["thanh_cong"],
                                           "o_forbid_regex": {"thanh_cong": "\\d"}})))


class TestRouting(unittest.TestCase):
    def test_score(self):
        sets = {"a": [{"query": "q1", "should_trigger": True}, {"query": "q2", "should_trigger": False}],
                "b": [{"query": "q2", "should_trigger": True}]}
        picks = {"q1": ["a", "a", None], "q2": ["a", "b", "b"]}
        rep = rr.score(sets, picks, 0.5)
        self.assertEqual((rep["a"]["passed"], rep["a"]["total"]), (2, 2))
        self.assertEqual((rep["b"]["passed"], rep["b"]["total"]), (1, 1))
        picks["q2"] = ["a", "a", "b"]
        self.assertEqual(rr.score(sets, picks, 0.5)["a"]["passed"], 1)

    def test_skill_name_parsing(self):
        ev = {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "plugin:omicall-omiflow"}}]}}
        self.assertEqual([claude_cli.skill_name_of(t) for t in claude_cli.tool_uses(ev)], ["omicall-omiflow"])

    def test_clean_env_drops_host_session(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_SESSION_ID": "x", "ANTHROPIC_BASE_URL": "http://h",
                                          "CLAUDECODE": "1", "ANTHROPIC_API_KEY": "k", "PATH": os.environ.get("PATH", "")}):
            env = claude_cli.clean_env()
        self.assertNotIn("CLAUDE_CODE_SESSION_ID", env)
        self.assertNotIn("ANTHROPIC_BASE_URL", env)
        self.assertNotIn("CLAUDECODE", env)
        self.assertEqual(env.get("ANTHROPIC_API_KEY"), "k")
        self.assertEqual(env.get("OMI_SUBAGENT"), "1")

    def test_runner_is_safe_by_default(self):
        self.assertIn("--strict-mcp-config", claude_cli.run_stream.__code__.co_consts)


if __name__ == "__main__":
    unittest.main()
