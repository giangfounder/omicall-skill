# -*- coding: utf-8 -*-
"""build_smartagent.py trên spec mẫu và base.json.

base.json là fixture ghép từ các khối JSON trong references/api-reference.md (đã làm sạch): test này
CHỈ KIỂM NHẤT QUÁN NỘI BỘ giữa builder, validator và tài liệu, KHÔNG chứng minh payload hợp lệ với nền tảng.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cg_common import HERE, SKILL, run  # noqa: E402

SPEC = os.path.join(SKILL, "references", "spec-smartagent.example.json")
BASE = os.path.join(HERE, "base.json")


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="cg_build_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def p(self, name):
        return os.path.join(self.d, name)

    def write(self, name, obj):
        with open(self.p(name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
        return self.p(name)

    def spec(self):
        with open(SPEC, encoding="utf-8") as f:
            return json.load(f)

    def build(self, spec_path, *extra, base=BASE):
        args = [spec_path]
        if base:
            args += ["--base", base]
        return run("build_smartagent.py", *(args + list(extra)))

    def test_example_validates_and_is_deterministic(self):
        code, out, err = self.build(SPEC, "--new", "--out", self.p("a.json"))
        self.assertEqual(code, 0, out + err)
        self.assertIn("RESULT PASS", out)
        code2, out2, err2 = run("validate_smartagent.py", self.p("a.json"))
        self.assertEqual(code2, 0, out2 + err2)
        code, out, err = self.build(SPEC, "--new", "--out", self.p("b.json"))
        self.assertEqual(code, 0, out + err)
        with open(self.p("a.json"), "rb") as fa, open(self.p("b.json"), "rb") as fb:
            self.assertEqual(fa.read(), fb.read())
        with open(self.p("a.json"), encoding="utf-8") as f:
            payload = json.load(f)
        for k in ("id", "uuid", "public_key", "_ghi_chu"):
            self.assertNotIn(k, payload)

    def test_unverified_kind_exit_2(self):
        s = self.spec()
        s["intents"].append({"name": "Gửi thông tin", "kind": "webhook", "content": "Khách muốn nhận thông tin qua tin nhắn."})
        code, out, err = self.build(self.write("s.json", s), "--new", "--out", self.p("o.json"))
        self.assertEqual(code, 2)
        self.assertIn("SEND_WEBHOOK", err)
        self.assertNotIn("Traceback", err)
        self.assertFalse(os.path.exists(self.p("o.json")))

    def test_missing_base_exit_2(self):
        code, out, err = self.build(SPEC, "--new", "--out", self.p("o.json"), base=None)
        self.assertEqual(code, 2)
        self.assertIn("--base", err)
        self.assertNotIn("Traceback", err)

    def test_update_without_uuid_exit_2(self):
        with open(BASE, encoding="utf-8") as f:
            b = json.load(f)
        b.pop("uuid")
        code, out, err = self.build(SPEC, "--update", "--out", self.p("o.json"), base=self.write("b.json", b))
        self.assertEqual(code, 2)
        self.assertIn("uuid", err)
        self.assertNotIn("Traceback", err)

    def test_update_keeps_id_uuid(self):
        code, out, err = self.build(SPEC, "--update", "--out", self.p("o.json"))
        self.assertEqual(code, 0, out + err)
        with open(self.p("o.json"), encoding="utf-8") as f:
            payload = json.load(f)
        self.assertTrue(payload.get("id") and payload.get("uuid"))

    def base_with_api(self, header_value="application/json", header_key="Content-Type"):
        with open(BASE, encoding="utf-8") as f:
            b = json.load(f)
        b["nodes"][0]["ai_agent_config"]["knowledge"]["apis"] = [{
            "ref_id": "var_api_mau", "name": "API mau", "url": "https://api.example.invalid/tra-cuu", "method": "POST",
            "headers": [{"id": "h1", "key": header_key, "value": header_value}], "body_type": "raw", "body_json": "{}",
            "variables": None, "prompt": "", "query_prompt": "", "param_type": "json", "time_out": 60,
            "api_response_guide": [], "retrieve_data": None}]
        return b

    def load_out(self):
        with open(self.p("o.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_example_spec_has_no_empty_apis(self):
        self.assertNotIn("apis", (self.spec().get("knowledge") or {}))

    def test_update_keeps_base_apis_when_spec_empty(self):
        s = self.spec()
        s["knowledge"] = {"apis": []}
        base = self.write("b.json", self.base_with_api())
        code, out, err = self.build(self.write("s.json", s), "--update", "--out", self.p("o.json"), base=base)
        self.assertEqual(code, 0, out + err)
        apis = self.load_out()["nodes"][0]["ai_agent_config"]["knowledge"]["apis"]
        self.assertEqual([a["ref_id"] for a in apis], ["var_api_mau"])
        self.assertEqual(apis[0]["headers"][0]["value"], "application/json")
        self.assertIn("giữ nguyên 1 api", out)
        self.assertNotIn("WARN X12", out)

    def test_update_replace_apis_reports_ref_ids(self):
        s = self.spec()
        s["knowledge"] = {"apis": [{"ref_id": "var_api_moi", "name": "API moi", "url": "https://api.example.invalid/moi",
                                    "method": "POST", "headers": []}]}
        base = self.write("b.json", self.base_with_api())
        code, out, err = self.build(self.write("s.json", s), "--update", "--out", self.p("o.json"), base=base)
        self.assertEqual(code, 0, out + err)
        self.assertIn("bỏ ref_id ['var_api_mau']", out)
        self.assertIn("thêm ref_id ['var_api_moi']", out)

    def test_shrink_warning_x12(self):
        if os.path.join(SKILL, "scripts") not in sys.path:
            sys.path.insert(0, os.path.join(SKILL, "scripts"))
        import build_smartagent as bs
        b = self.base_with_api()
        b["nodes"][0]["ai_agent_config"]["knowledge"]["files"] = [{"url": "https://files.example.invalid/a.pdf", "id": "f1", "name": "a.pdf"}]
        payload = json.loads(json.dumps(b))
        self.assertEqual(bs.shrink_warnings(b, payload), [])
        payload["nodes"][0]["ai_agent_config"]["knowledge"] = {"apis": [], "files": []}
        w = bs.shrink_warnings(b, payload)
        self.assertTrue(any(x.startswith("WARN X12 knowledge.apis") for x in w), w)
        self.assertTrue(any(x.startswith("WARN X12 knowledge.files") for x in w), w)

    def test_masked_base_refused(self):
        base = self.write("b.json", self.base_with_api(header_value="***", header_key="Authorization"))
        code, out, err = self.build(SPEC, "--update", "--out", self.p("o.json"), base=base)
        self.assertEqual(code, 2, out + err)
        self.assertIn("***", err)
        self.assertNotIn("Traceback", err)
        self.assertFalse(os.path.exists(self.p("o.json")))

    def test_new_drops_publish_and_server_fields(self):
        base = self.write("b.json", self.base_with_api())
        code, out, err = self.build(SPEC, "--new", "--out", self.p("o.json"), base=base)
        self.assertEqual(code, 0, out + err)
        payload = self.load_out()
        self.assertIs(payload["is_publish"], False)
        for k in ("version", "created_date", "created_by", "last_updated_date", "last_updated_by"):
            self.assertNotIn(k, payload)
        self.assertEqual(payload["nodes"][0]["ai_agent_config"]["knowledge"]["apis"], [])
        self.assertIn("is_publish", out)
        self.assertIn("không chép 1 api", out)

    def test_update_keeps_is_publish_and_version(self):
        with open(BASE, encoding="utf-8") as f:
            b = json.load(f)
        code, out, err = self.build(SPEC, "--update", "--out", self.p("o.json"))
        self.assertEqual(code, 0, out + err)
        payload = self.load_out()
        self.assertEqual(payload["is_publish"], b["is_publish"])
        self.assertEqual(payload["version"], b["version"])

    def test_out_inside_skill_refused(self):
        target = os.path.join(SKILL, "khong_duoc_ghi.json")
        code, out, err = self.build(SPEC, "--new", "--out", target)
        self.assertEqual(code, 2, out + err)
        self.assertFalse(os.path.exists(target))
        self.assertNotIn("Traceback", err)

    def test_out_inside_repo_refused(self):
        repo = os.path.dirname(SKILL)
        if not os.path.isfile(os.path.join(repo, "tools", "sync_shared.py")):
            self.skipTest("không chạy trong repo nguồn")
        target = os.path.join(repo, "tests", "khong_duoc_ghi_%d.json" % os.getpid())
        code, out, err = self.build(SPEC, "--new", "--out", target)
        self.assertEqual(code, 2, out + err)
        self.assertFalse(os.path.exists(target))

    def test_anh_hoac_chi_fails_validation(self):
        s = self.spec()
        s["start_call"] = "Dạ em chào anh hoặc chị, em gọi từ công ty mẫu."
        code, out, err = self.build(self.write("s.json", s), "--new", "--out", self.p("o.json"))
        self.assertEqual(code, 1, out + err)
        self.assertRegex(out, r"(?m)^FAIL X9 ")
        self.assertIn("RESULT FAIL", out)

    def test_base_without_classify_sample_exit_2(self):
        with open(BASE, encoding="utf-8") as f:
            b = json.load(f)
        drop = {n["id"] for n in b["nodes"] if any(a.get("type") == "ADD_CLASSIFY" for a in n.get("actions") or [])}
        b["nodes"] = [n for n in b["nodes"] if n["id"] not in drop]
        b["org_nodes"] = [n for n in b["org_nodes"] if n["id"] not in drop]
        b["connections"] = [c for c in b["connections"] if c["target"] not in drop]
        code, out, err = self.build(SPEC, "--new", "--out", self.p("o.json"), base=self.write("b.json", b))
        self.assertEqual(code, 2)
        self.assertIn("ADD_CLASSIFY", err)
        self.assertIn("extract_template", err)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
