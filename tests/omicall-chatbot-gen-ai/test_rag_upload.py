# -*- coding: utf-8 -*-
"""rag_upload.py với stub HTTP chỉ bind 127.0.0.1, phát lại chuỗi phản hồi theo api-reference.md (đã làm sạch).
Phản hồi stub chỉ chứng minh script đi đúng thứ tự tài liệu ghi, không chứng minh hợp lệ với nền tảng."""
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from _util import BASE_FIXTURE, SKILL, fake_jwt, load, run


class Stub:
    def __init__(self, quota=False, duplicate=False, on_page=1, missing=False):
        self.calls = []
        self.queries = []
        self.on_page = on_page
        self.missing = missing
        self.auth = []
        self.quota = quota
        self.duplicate = duplicate
        self.polls = 0
        stub = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(n)
                path = self.path.split("?")[0]
                stub.calls.append(path)
                stub.queries.append(self.path)
                stub.auth.append(self.headers.get("Authorization") or "")
                code, body = stub.reply(path)
                raw = json.dumps(body).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        self.url = "http://127.0.0.1:%d" % self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def reply(self, path):
        if path.endswith("/file_store/put_v2"):
            return 200, {"payload": [{"object_info": {"name": "<tenant_id>/warehouse_of_knowledge_files/2026/10/<uuid>.txt",
                                                      "file_name": "kien_thuc.txt", "content_type": "text/plain"}}]}
        if path.endswith("/other/get_id_by_name"):
            return 200, {"data": ["<record_cu>"]} if self.duplicate else {"data": []}
        if path.endswith("/other/add"):
            if self.quota:
                return 400, {"status_code": 400, "message": "Đã đạt giới hạn cho phép", "payload": None}
            return 200, {"payload": {"_id": "<record_id>", "file_id": "file-<uuid>", "status": "not_training",
                                     "bots_use_file": [], "language": "vi"}}
        if "/other/training/" in path:
            return 200, {"payload": True}
        if path.endswith("/other/search"):
            q = self.queries[-1]
            page = int(q.split("page=")[1].split("&")[0]) if "page=" in q else 1
            if self.missing:
                items = [{"_id": "<record_khac_%d>" % i, "status": "completed"} for i in range(3)] if page == 1 else []
                return 200, {"payload": {"items": items}}
            if page < self.on_page:
                return 200, {"payload": {"items": [{"_id": "<record_khac_%d_%d>" % (page, i), "status": "completed"}
                                                   for i in range(10)]}}
            if page > self.on_page:
                return 200, {"payload": {"items": []}}
            self.polls += 1
            st = "completed" if self.polls >= 2 else "training"
            return 200, {"payload": {"items": [{"_id": "<record_id>", "status": st}]}}
        return 404, {"payload": None}

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


class TestRagUpload(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omi_cb_rag_")
        self.file = os.path.join(self.tmp, "Kien_Thuc.txt")
        with open(self.file, "w", encoding="utf-8") as f:
            f.write("<nội dung kiến thức mẫu>\n")
        self.tok = fake_jwt()
        self.out = os.path.join(self.tmp, "payload.json")

    def go(self, stub, *extra):
        return run("rag_upload.py", self.file, "--bot", BASE_FIXTURE, "--api-base", stub.url, "--out", self.out,
                   "--poll", "0.2", "--timeout", "10", *extra, extra_env={"OMI_TOKEN": self.tok})

    def test_api_base_non_local_refused(self):
        code, so, se = run("rag_upload.py", self.file, "--bot", BASE_FIXTURE, "--api-base", "https://example.com",
                           "--out", self.out, "--dry-run", extra_env={"OMI_TOKEN": self.tok})
        self.assertEqual(code, 2, so + se)
        self.assertIn("127.0.0.1", se)
        self.assertNotIn(self.tok, so + se)
        self.assertFalse(os.path.exists(self.out))

    def test_order_and_ref_id(self):
        s = Stub()
        try:
            code, so, se = self.go(s)
        finally:
            s.close()
        self.assertEqual(code, 0, so + se)
        self.assertEqual(s.calls[:4], ["/file_store/put_v2", "/omi_v2/warehouse_of_knowledge/other/get_id_by_name",
                                       "/omi_v2/warehouse_of_knowledge/other/add",
                                       "/omi_v2/warehouse_of_knowledge/other/training/%3Crecord_id%3E"])
        self.assertTrue(all(c.endswith("/other/search") for c in s.calls[4:]) and len(s.calls) >= 5)
        self.assertTrue(all(a == "Bearer " + self.tok for a in s.auth))
        bot = load(self.out)
        files = bot["vector_store"]["vector_store_files"]
        self.assertEqual(files[-1]["ref_id"], "<record_id>")
        self.assertNotEqual(files[-1]["ref_id"], files[-1]["file_id"])
        self.assertIn("<record_id>", bot["campaign"]["nodes"][0]["ai_analyze"]["vector_store_ids"])
        self.assertNotIn(self.tok, so + se)
        with open(self.out, encoding="utf-8") as f:
            self.assertNotIn(self.tok, f.read())
        code, vo, _ = run("validate_bot.py", self.out)
        self.assertEqual(code, 0, vo)

    def test_search_paginates_to_find_record(self):
        s = Stub(on_page=3)
        try:
            code, so, se = self.go(s)
        finally:
            s.close()
        self.assertEqual(code, 0, so + se)
        self.assertTrue(any("page=3" in q for q in s.queries), s.queries)
        self.assertIn("Training completed", so)

    def test_record_not_found_message(self):
        s = Stub(missing=True)
        try:
            code, so, se = run("rag_upload.py", self.file, "--bot", BASE_FIXTURE, "--api-base", s.url, "--out", self.out,
                               "--poll", "0.2", "--timeout", "0.5", extra_env={"OMI_TOKEN": self.tok})
        finally:
            s.close()
        self.assertEqual(code, 5, so + se)
        self.assertIn("KHÔNG THẤY", so)

    def test_out_inside_repo_refused(self):
        s = Stub()
        out = os.path.join(SKILL, "zz_rag_payload_should_not_exist.json")
        try:
            code, so, se = run("rag_upload.py", self.file, "--bot", BASE_FIXTURE, "--api-base", s.url, "--out", out,
                               extra_env={"OMI_TOKEN": self.tok})
        finally:
            s.close()
        self.assertEqual(code, 2, so + se)
        self.assertEqual(s.calls, [])
        self.assertFalse(os.path.exists(out))

    def test_dry_run_no_request(self):
        s = Stub()
        try:
            code, so, se = self.go(s, "--dry-run")
        finally:
            s.close()
        self.assertEqual(code, 0, se)
        self.assertEqual(s.calls, [])
        self.assertNotIn(self.tok, so)

    def test_quota_stops(self):
        s = Stub(quota=True)
        try:
            code, so, se = self.go(s)
        finally:
            s.close()
        self.assertNotEqual(code, 0)
        self.assertIn("quota", so + se)
        self.assertNotIn("/omi_v2/warehouse_of_knowledge/other/training/%3Crecord_id%3E", s.calls)
        self.assertNotIn(self.tok, so + se)

    def test_duplicate_name_stops(self):
        s = Stub(duplicate=True)
        try:
            code, so, se = self.go(s)
        finally:
            s.close()
        self.assertEqual(code, 3)
        self.assertEqual(len(s.calls), 2)


if __name__ == "__main__":
    unittest.main()
