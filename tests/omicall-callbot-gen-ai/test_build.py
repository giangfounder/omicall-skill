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

    # --- collect + confirm (agent-config-guide mục 4: không gửi/ghi dữ liệu trước khi khách xác nhận)
    def conds(self, payload):
        return {c.get("name") or c["id"]: c for c in payload["nodes"][0]["ai_agent_config"]["ai_analyze"]["conditions"]}

    def legacy_spec(self):
        s = self.spec()
        s["intents"] = [it for it in s["intents"] if it["kind"] != "confirm"]
        col = next(it for it in s["intents"] if it["kind"] == "collect")
        col.pop("confirm_by")
        col["classify_labels"] = ["Có nhu cầu"]
        return s

    def test_example_collect_confirm(self):
        code, out, err = self.build(SPEC, "--new", "--out", self.p("o.json"))
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("WARN X14", out)
        self.assertNotRegex(out, r"(?m)^WARN X13 ")
        p = self.load_out()
        c = self.conds(p)
        col, conf = c["Khách có nhu cầu"], c["Khách xác nhận thông tin"]
        self.assertIsNone(col["next_node"])
        self.assertEqual([s["variables_code"] for s in col["action_steps"]], [["var_ten", "var_nhu_cau"]])
        self.assertIsNone(conf["action_steps"])
        begin = p["nodes"][0]["id"]
        self.assertFalse([e for e in p["connections"] if e["source"] == begin and e["sourceHandle"] == col["id"]])
        tgt = next(n for n in p["nodes"] if n["id"] == conf["next_node"])
        self.assertTrue(any(a.get("type") == "ADD_CLASSIFY" for a in tgt["actions"]))
        self.assertEqual([v["field_code"] for v in tgt["variables"]], ["var_ten", "var_nhu_cau"])
        org = next(o for o in p["org_nodes"] if o["id"] == tgt["id"])
        self.assertEqual([v["variable"] for v in org["data"]["variables"]], ["var_ten", "var_nhu_cau"])
        self.assertTrue([e for e in p["connections"] if e["source"] == begin and e["sourceHandle"] == conf["id"] and e["target"] == tgt["id"]])
        # chỉ một node phân loại có nhãn "Có nhu cầu" (collect không có node riêng)
        clf = [n for n in p["nodes"] if any(a.get("type") == "ADD_CLASSIFY" and "Có nhu cầu" in a["data"]["ids"] for a in n.get("actions") or [])]
        self.assertEqual(len(clf), 1)

    def test_confirm_by_on_collect_side_only(self):
        s = self.spec()
        next(it for it in s["intents"] if it["kind"] == "confirm").pop("confirms")
        code, out, err = self.build(self.write("s.json", s), "--new", "--out", self.p("o.json"))
        self.assertEqual(code, 0, out + err)
        self.assertIsNone(self.conds(self.load_out())["Khách có nhu cầu"]["next_node"])

    def test_legacy_collect_still_builds_with_warn(self):
        code, out, err = self.build(self.write("s.json", self.legacy_spec()), "--new", "--out", self.p("o.json"))
        self.assertEqual(code, 0, out + err)
        self.assertRegex(out, r"(?m)^WARN X14 .*Khách có nhu cầu.*trước khi khách xác nhận")
        self.assertIsNotNone(self.conds(self.load_out())["Khách có nhu cầu"]["next_node"])

    def test_duplicate_names_without_confirm_still_build(self):
        s = self.legacy_spec()
        s["intents"].insert(2, {"name": "Khách bận", "kind": "handled", "content": "Khách nói đang bận việc khác, ví dụ: anh đang bận chút."})
        code, out, err = self.build(self.write("s.json", s), "--new", "--out", self.p("o.json"))
        self.assertEqual(code, 0, out + err)

    def test_confirm_bad_reference_exit_2(self):
        s = self.spec()
        next(it for it in s["intents"] if it["kind"] == "confirm")["confirms"] = "khong_co"
        code, out, err = self.build(self.write("s.json", s), "--new", "--out", self.p("o.json"))
        self.assertEqual(code, 2, out + err)
        self.assertIn("confirms", err)
        self.assertNotIn("Traceback", err)

    def test_confirmed_collect_with_labels_exit_2(self):
        s = self.spec()
        next(it for it in s["intents"] if it["kind"] == "collect")["classify_labels"] = ["Có nhu cầu"]
        code, out, err = self.build(self.write("s.json", s), "--new", "--out", self.p("o.json"))
        self.assertEqual(code, 2, out + err)
        self.assertIn("ý định xác nhận", err)

    # --- --new không mang file RAG của base
    def base_with_files(self):
        with open(BASE, encoding="utf-8") as f:
            b = json.load(f)
        files = [{"url": "https://files.example.invalid/a.pdf", "id": "f1", "name": "a.pdf"}]
        b["nodes"][0]["ai_agent_config"]["knowledge"]["files"] = files
        ob = next(o for o in b["org_nodes"] if o["id"] == b["nodes"][0]["id"])
        ob["data"]["selectedTraining"] = json.loads(json.dumps(files))
        ob["data"]["typeTrainingFile"] = "file"
        return b

    def begin_org(self, p):
        return next(o for o in p["org_nodes"] if o["id"] == p["nodes"][0]["id"])["data"]

    def test_new_drops_base_rag_files(self):
        code, out, err = self.build(SPEC, "--new", "--out", self.p("o.json"), base=self.write("b.json", self.base_with_files()))
        self.assertEqual(code, 0, out + err)
        p = self.load_out()
        self.assertEqual(p["nodes"][0]["ai_agent_config"]["knowledge"]["files"], [])
        d = self.begin_org(p)
        self.assertEqual(d["selectedTraining"], [])
        self.assertNotIn("typeTrainingFile", d)
        self.assertIn("không chép 1 file RAG", out)

    def test_new_keeps_spec_rag_files(self):
        s = self.spec()
        s["knowledge"] = {"files": [{"id": "f2", "name": "b.pdf", "other_wok_id": "rec_1"}]}
        code, out, err = self.build(self.write("s.json", s), "--new", "--out", self.p("o.json"), base=self.write("b.json", self.base_with_files()))
        self.assertEqual(code, 0, out + err)
        p = self.load_out()
        self.assertEqual([f["id"] for f in p["nodes"][0]["ai_agent_config"]["knowledge"]["files"]], ["f2"])
        d = self.begin_org(p)
        self.assertEqual([f["id"] for f in d["selectedTraining"]], ["f2"])
        self.assertEqual(d["typeTrainingFile"], "other")

    def test_rag_upload_dry_run_uses_put_v2(self):
        f = self.p("faq.txt")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("Câu hỏi mẫu")
        code, out, err = run("rag_upload.py", f, "--base", BASE, "--out", self.p("r.json"), "--dry-run")
        self.assertEqual(code, 0, out + err)
        self.assertIn("/file_store/put_v2?business_type=callbot_recording_file", out)
        self.assertIn("file_0=faq.txt", out)

    def test_update_keeps_base_rag_files(self):
        code, out, err = self.build(SPEC, "--update", "--out", self.p("o.json"), base=self.write("b.json", self.base_with_files()))
        self.assertEqual(code, 0, out + err)
        p = self.load_out()
        self.assertEqual([f["id"] for f in p["nodes"][0]["ai_agent_config"]["knowledge"]["files"]], ["f1"])
        d = self.begin_org(p)
        self.assertEqual([f["id"] for f in d["selectedTraining"]], ["f1"])
        self.assertEqual(d["typeTrainingFile"], "file")


if __name__ == "__main__":
    unittest.main()
