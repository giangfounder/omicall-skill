"""verify_callflow.py: hợp đồng output và các mã C1..C7 trên payload dựng từ spec mẫu."""
import tempfile
import unittest

from _util import CONTEXT, SPEC_FLOW, dump, load, run, survey_context, tmpdir


class TestVerify(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._d = tempfile.TemporaryDirectory()
        cls.payload = f"{cls._d.name}/payload.json"
        code, so, se = run("build_callflow.py", SPEC_FLOW, "--out", cls.payload, "--context", CONTEXT)
        assert code == 0, se

    @classmethod
    def tearDownClass(cls):
        cls._d.cleanup()

    def verify(self, path, *extra):
        code, so, se = run("verify_callflow.py", path, *extra)
        self.assertNotIn("Traceback", so + se)
        lines = [ln for ln in so.splitlines() if ln.strip()]
        for ln in lines:
            self.assertRegex(ln, r"^(PASS|FAIL|WARN) [CX]\d+ |^RESULT (PASS|FAIL)$")
        self.assertTrue(lines[-1].startswith("RESULT "))
        return code, so

    def mutated(self, fn):
        p = load(self.payload)
        fn(p)
        return dump(p, tmpdir(self) / "m.json")

    def test_self_post_pass(self):
        code, so = self.verify(self.payload, "--sent", self.payload, "--context", CONTEXT, "--mode", "post")
        self.assertEqual(code, 0, so)
        self.assertTrue(so.rstrip().endswith("RESULT PASS"))
        for c in ("C1", "C2", "C3", "C4", "C5", "C6", "C7"):
            self.assertIn(f"PASS {c} ", so)

    def test_drop_connection_fails_c7(self):
        def cut(p):
            i = next(i for i, e in enumerate(p["connections"]) if e["sourceHandle"] != "COLLECT_INFO")
            p["connections"].pop(i)
        code, so = self.verify(self.mutated(cut))
        self.assertEqual(code, 1)
        self.assertIn("FAIL C7", so)

    def test_bare_anh_chi_fails_c6(self):
        def f(p):
            st = next(n for n in p["nodes"] if n["node_type"] == "STAFF")
            st["template_content"] += " Anh/chị nghe rõ không ạ"
        code, so = self.verify(self.mutated(f))
        self.assertEqual(code, 1)
        self.assertIn("FAIL C6", so)

    def test_transfer_without_ids_fails_c5(self):
        def f(p):
            for n in p["nodes"]:
                for a in n.get("actions") or []:
                    if a["type"] == "TRANSFER_CALL":
                        a["data"]["ids"] = []
        code, so = self.verify(self.mutated(f))
        self.assertIn("FAIL C5", so)

    def test_missing_nr_fails_c3(self):
        def f(p):
            nr = {n["id"] for n in p["nodes"] if n.get("condition_type") == "CUSTOMER_NOT_RESPONSE"}
            st = next(n for n in p["nodes"] if n["node_type"] == "STAFF" and set(n.get("next_nodes") or []) & nr)
            st["next_nodes"] = [t for t in st["next_nodes"] if t not in nr]
        code, so = self.verify(self.mutated(f))
        self.assertIn("FAIL C3", so)

    def test_unknown_intent_fails_c4(self):
        def f(p):
            c = next(n for n in p["nodes"] if n.get("intent_code"))
            c["intent_code"] = "ma_la"
        code, so = self.verify(self.mutated(f), "--context", CONTEXT)
        self.assertIn("FAIL C4 ý định 'ma_la'", so)

    def test_sent_count_mismatch(self):
        def f(p):
            p["nodes"].append({"id": "x1", "node_type": "ACTION", "actions": []})
            p["org_nodes"].append({"id": "x1", "type": "ACTION", "data": {}})
        code, so = self.verify(self.mutated(f), "--sent", self.payload, "--mode", "post")
        self.assertIn("FAIL X5", so)

    def test_get_wrapper_and_version(self):
        sent = load(self.payload)
        sent.update({"id": "test_id_1", "uuid": "test_uuid_1", "version": 3})
        got = dict(sent, version=3, is_newest_version=True)
        d = tmpdir(self)
        code, so = self.verify(dump({"status_code": 9999, "payload": got}, d / "g.json"), "--sent", dump(sent, d / "s.json"),
                               "--mode", "post")
        self.assertIn("FAIL C7 version không tăng", so)

    def _update_pair(self, get_version):
        sent = load(self.payload)
        sent.update({"id": "test_id_1", "uuid": "test_uuid_1"})  # payload cập nhật thật: có id+uuid, không có version
        got = dict(sent, version=get_version, is_newest_version=True)
        d = tmpdir(self)
        return d, dump(got, d / "g.json"), dump(sent, d / "s.json")

    def test_version_not_increased_vs_base_fails(self):
        d, g, s = self._update_pair(1)
        base = dump(dict(load(s), version=1), d / "base.json")
        code, so = self.verify(g, "--sent", s, "--mode", "post", "--base", base)
        self.assertEqual(code, 1)
        self.assertIn("FAIL C7 version không tăng (1 → 1)", so)
        code, so = self.verify(g, "--sent", s, "--mode", "post", "--base-version", "2")
        self.assertIn("FAIL C7 version không tăng (2 → 1)", so)

    def test_version_increased_passes(self):
        d, g, s = self._update_pair(2)
        code, so = self.verify(g, "--sent", s, "--mode", "post", "--base-version", "1")
        self.assertEqual(code, 0, so)
        self.assertIn("PASS C7 version tăng (1 → 2)", so)

    def test_version_unknown_base_warns(self):
        d, g, s = self._update_pair(1)
        code, so = self.verify(g, "--sent", s, "--mode", "post")
        self.assertIn("WARN C7 chưa kiểm được version tăng", so)

    def test_non_object_elements_fail_cleanly(self):
        def f(p):
            p["nodes"].append("str")
            p["org_nodes"].append(None)
            p["connections"].append(1)
        code, so = self.verify(self.mutated(f))
        self.assertEqual(code, 1)
        self.assertIn("FAIL X1 phần tử không phải object (str)", so)
        self.assertIn("[org_nodes[", so)

    def test_bad_content_exit1(self):
        d = tmpdir(self)
        for name, text in (("l.json", "[1, 2]"), ("bad.json", "{khong phai json")):
            (d / name).write_text(text, encoding="utf-8")
            code, so = self.verify(d / name)
            self.assertEqual(code, 1, name)
            self.assertIn("FAIL X0", so)

    def test_survey_shape_context(self):
        d = tmpdir(self)
        ctx = dump(survey_context(), d / "ctx.json")
        code, so = self.verify(self.payload, "--context", ctx)
        self.assertEqual(code, 0, so)
        self.assertIn("PASS C4 11 mã ý định, 2 mã thực thể", so)
        self.assertIn("PASS C4 huấn luyện mới nhất SUCCESS", so)
        self.assertIn("WARN C4 context thiếu system_intent_id", so)

    def test_null_system_intent_id_fails_c4(self):
        def f(p):
            for o in p["org_nodes"]:
                for c in (o.get("data") or {}).get("conditions") or []:
                    if (c.get("intent") or {}).get("code") == "omi_intent_agree":
                        c["intent"]["systemIntentId"] = None
        code, so = self.verify(self.mutated(f), "--context", CONTEXT)
        self.assertEqual(code, 1)
        self.assertIn("FAIL C4 editor: ý định hệ thống omi_intent_agree systemIntentId None", so)

    def test_placeholder_fails(self):
        def f(p):
            p["tenant_id"] = "<tenant_id>"
        code, so = self.verify(self.mutated(f))
        self.assertIn("FAIL X3", so)

    def test_bad_usage_exit2(self):
        code, so, se = run("verify_callflow.py", "khong_ton_tai.json")
        self.assertEqual(code, 2)
        code, so, se = run("verify_callflow.py")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
