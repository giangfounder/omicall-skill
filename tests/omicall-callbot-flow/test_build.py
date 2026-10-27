"""build_callflow.py: placeholder, --context, validate_spec, seed theo tên."""
import unittest

from _util import CONTEXT, SPEC_FLOW, dump, load, run, survey_context, tmpdir


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.d = tmpdir(self)

    def build(self, spec_path, *extra):
        out = self.d / "payload.json"
        if out.exists():
            out.unlink()
        code, so, se = run("build_callflow.py", spec_path, "--out", out, *extra)
        self.assertNotIn("Traceback", se + so)
        return code, so, se, out

    def test_no_context_fails_with_placeholder_count(self):
        code, so, se, out = self.build(SPEC_FLOW)
        self.assertNotEqual(code, 0)
        self.assertRegex(se, r"payload còn \d+ placeholder")
        self.assertIn("'<id>' x", se)
        self.assertFalse(out.exists(), "lỗi thì không được ghi payload")

    def test_allow_pending_writes_with_warning(self):
        code, so, se, out = self.build(SPEC_FLOW, "--allow-pending")
        self.assertEqual(code, 0, se)
        self.assertIn("CẢNH BÁO: payload còn", so)
        self.assertTrue(out.exists())

    def test_context_builds_clean(self):
        code, so, se, out = self.build(SPEC_FLOW, "--context", CONTEXT)
        self.assertEqual(code, 0, se)
        p = load(out)
        self.assertEqual(p["tenant_id"], "test_tenant_0001")
        with open(out, encoding="utf-8") as f:
            self.assertNotRegex(f.read(), r"<[^<>\n]{1,80}>")
        xfer = [a for n in p["nodes"] for a in n.get("actions") or [] if a["type"] == "TRANSFER_CALL"]
        self.assertEqual(xfer[0]["data"]["ids"], ["test_agent_01"])

    def test_survey_shape_context_builds_same(self):
        code, so, se, out = self.build(SPEC_FLOW, "--context", CONTEXT)
        self.assertEqual(code, 0, se)
        legacy = load(out)
        ctx = dump(survey_context(), self.d / "ctx_survey.json")
        code, so, se, out = self.build(SPEC_FLOW, "--context", ctx)
        self.assertEqual(code, 0, se)
        self.assertEqual(load(out), legacy, "context khuôn tenant_survey phải cho cùng payload với khuôn callbot_kb")
        self.assertIn("context không có system_intent_id — giữ giá trị trong spec", so)
        sids = {c["intent"]["code"]: c["intent"]["systemIntentId"] for o in legacy["org_nodes"]
                for c in (o.get("data") or {}).get("conditions") or [] if c.get("intent")}
        self.assertEqual(sids["omi_intent_agree"], "654c4bbfafd622652cde5a9d")
        self.assertIsNone(sids["khach_can_gap/nhan_vien_kinh_doanh"])

    def test_system_intent_without_id_fails(self):
        spec = load(SPEC_FLOW)
        spec["intents"]["omi_intent_agree"]["system_intent_id"] = "<id>"
        ctx = dump(survey_context(), self.d / "ctx_survey.json")
        code, so, se, out = self.build(dump(spec, self.d / "spec.json"), "--context", ctx)
        self.assertEqual(code, 1)
        self.assertIn("ý định hệ thống 'omi_intent_agree' thiếu system_intent_id", se)
        self.assertFalse(out.exists())

    def test_context_missing_code_fails(self):
        ctx = load(CONTEXT)
        ctx["callbot_kb"]["intents"] = [i for i in ctx["callbot_kb"]["intents"] if i["code"] != "omi_intent_angry"]
        code, so, se, out = self.build(SPEC_FLOW, "--context", dump(ctx, self.d / "ctx.json"))
        self.assertNotEqual(code, 0)
        self.assertIn("omi_intent_angry", se)

    def test_context_agent_only_raw_id_is_ambiguous(self):
        ctx = load(CONTEXT)
        ctx["agents"] = [{"_id": "test_raw_01", "ext": "100", "full_name": "Nhân viên thử"}]
        code, so, se, out = self.build(SPEC_FLOW, "--context", dump(ctx, self.d / "ctx.json"))
        self.assertNotEqual(code, 0)
        self.assertIn("Cần xác nhận", se)

    def bad(self, mutate, expect):
        s = load(SPEC_FLOW)
        mutate(s)
        code, so, se, out = self.build(dump(s, self.d / "bad.json"), "--context", CONTEXT)
        self.assertNotEqual(code, 0, so)
        self.assertIn(expect, se)
        self.assertFalse(out.exists())

    def test_next_and_branches(self):
        def m(s):
            st = next(x for x in s["steps"] if x["key"] == "XAC_NHAN")
            st["next"] = "KET"
        self.bad(m, "có cả 'next' lẫn 'branches'")

    def test_common_false_missing_nr(self):
        def m(s):
            st = next(x for x in s["steps"] if x["key"] == "HOI_THEM")
            st["common"] = False
            st["wrong_to"] = "CHUYEN"
        self.bad(m, "thiếu nr_to")

    def test_common_false_with_nr_wrong_ok(self):
        s = load(SPEC_FLOW)
        st = next(x for x in s["steps"] if x["key"] == "HOI_THEM")
        st.update({"common": False, "nr_to": "KET_NR", "wrong_to": "CHUYEN"})
        code, so, se, out = self.build(dump(s, self.d / "ok.json"), "--context", CONTEXT)
        self.assertEqual(code, 0, se)
        code, so, se = run("verify_callflow.py", out, "--context", CONTEXT)
        self.assertEqual(code, 0, so)
        self.assertIn("PASS C3", so)

    def test_route_unknown_var(self):
        def m(s):
            s["routes"] = [{"key": "R1", "name": "Theo loại", "var": "var_khong_co",
                            "cases": [{"name": "A", "values": ["1"], "to": "KET"}], "else": "KET"}]
        self.bad(m, "var 'var_khong_co' không có trong campaign_vars")

    def test_layout_bad_key(self):
        def m(s):
            s["layout"]["last_column"].append("KHONG_TON_TAI")
        self.bad(m, "layout.last_column: key 'KHONG_TON_TAI'")

    def test_branch_intent_not_declared(self):
        def m(s):
            s["steps"][0]["branches"].append({"intent": "ma_la", "to": "KET"})
        self.bad(m, "ý định 'ma_la' chưa có trong spec.intents")

    def test_seed_by_name_disjoint_ids(self):
        ids = []
        for name in ("Kịch bản A", "Kịch bản B"):
            s = load(SPEC_FLOW)
            s["name"] = name
            s.pop("seed", None)
            code, so, se, out = self.build(dump(s, self.d / "s.json"), "--context", CONTEXT)
            self.assertEqual(code, 0, se)
            ids.append({n["id"] for n in load(out)["nodes"]})
        self.assertFalse(ids[0] & ids[1])

    def test_fixed_seed_warns(self):
        s = load(SPEC_FLOW)
        s["seed"] = 1
        code, so, se, out = self.build(dump(s, self.d / "s.json"), "--context", CONTEXT)
        self.assertEqual(code, 0, se)
        self.assertIn("seed", so)


if __name__ == "__main__":
    unittest.main()
