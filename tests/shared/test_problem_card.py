"""Test problem_card.py (offline): 7 ô, chế độ nói (giả thuyết, câu hỏi kèm phỏng đoán) và chế độ tài liệu (không lộ chữ nội bộ)."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "shared" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import problem_card as pc  # noqa: E402

GOOD_NOI = {
    "mode": "noi",
    "gia_thuyet": {"cau": "Khách cần ghi nhận cuộc gọi ngoài giờ để sáng hôm sau gọi lại", "tu_tin": 75},
    "o": {"vao": "cuộc gọi vào số tổng đài ngoài giờ", "doi_tuong": "khách hàng, cuộc gọi",
          "luat": "ngoài 8h–17h thì tạo phiếu gọi lại", "ra": "phiếu gọi lại giao nhóm CSKH",
          "rang_buoc": "Cần xác nhận", "thanh_cong": "mọi cuộc gọi nhỡ ngoài giờ có phiếu trước 8h",
          "khong_lam": ["không gọi ra tự động"]},
    "cau_hoi": [{"o": "rang_buoc", "hoi": "Giờ làm việc có gồm thứ Bảy không", "doan": "có, 8h–12h"}],
    "mac_dinh": ["giờ làm việc 8h–17h"], "phan_viec": ["giờ làm việc", "quy trình tạo phiếu"],
}
GOOD_DOC = {
    "mode": "tai_lieu",
    "o": {"vao": "hotline", "doi_tuong": "khách hàng", "luat": "Cần xác nhận", "ra": "phiếu ghi",
          "rang_buoc": "Cần xác nhận", "thanh_cong": "Cần xác nhận", "khong_lam": ["Cần xác nhận"]},
    "can_xac_nhan": [{"o": "luat", "hoi": "Cuộc gọi được chia cho bộ phận nào?"},
                     {"o": "rang_buoc", "hoi": "Hệ thống hiện tại cần kết nối là gì?"},
                     {"o": "thanh_cong", "hoi": "Chỉ tiêu nào dùng để nghiệm thu?"},
                     {"o": "khong_lam", "hoi": "Hạng mục nào nằm ngoài phạm vi đợt này?"}],
}


def levels(card):
    return [lv for lv, _ in pc.check(card)]


class TestProblemCard(unittest.TestCase):
    def test_good_cards_pass(self):
        self.assertNotIn("FAIL", levels(GOOD_NOI))
        self.assertNotIn("FAIL", levels(GOOD_DOC))

    def test_template_has_all_seven_boxes(self):
        for m in ("noi", "tai_lieu"):
            self.assertEqual(set(pc.template(m)["o"]), {k for k, _ in pc.O_KEYS})

    def test_missing_out_of_scope_fails(self):
        c = copy.deepcopy(GOOD_NOI)
        c["o"]["khong_lam"] = []
        self.assertIn("FAIL", levels(c))

    def test_question_without_guess_fails(self):
        c = copy.deepcopy(GOOD_NOI)
        c["cau_hoi"][0]["doan"] = ""
        self.assertIn("FAIL", levels(c))

    def test_more_than_four_questions_fails(self):
        c = copy.deepcopy(GOOD_NOI)
        c["cau_hoi"] = [{"o": "luat", "hoi": "q%d" % i, "doan": "d"} for i in range(5)]
        self.assertIn("FAIL", levels(c))

    def test_doc_mode_rejects_guess_and_confidence(self):
        c = copy.deepcopy(GOOD_DOC)
        c["can_xac_nhan"][0]["hoi"] = "Chia cho bộ phận nào? Em đoán: CSKH"
        self.assertIn("FAIL", levels(c))
        c = copy.deepcopy(GOOD_DOC)
        c["gia_thuyet"] = {"cau": "x", "tu_tin": 50}
        self.assertIn("FAIL", levels(c))

    def test_doc_mode_unknown_needs_customer_question(self):
        c = copy.deepcopy(GOOD_DOC)
        c["can_xac_nhan"] = c["can_xac_nhan"][1:]
        self.assertIn("FAIL", levels(c))

    def test_render_noi_has_scope_and_explicit_yes(self):
        t = pc.render(GOOD_NOI)
        self.assertIn("Lần này không làm", t)
        self.assertIn("Thành công khi", t)
        self.assertIn('"đồng ý"', t)
        self.assertIn("Em đoán:", t)

    def test_render_doc_has_no_internal_words(self):
        t = pc.render(GOOD_DOC)
        self.assertIsNone(pc.INTERNAL.search(t))

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            good, bad = Path(d) / "g.json", Path(d) / "b.json"
            good.write_text(json.dumps(GOOD_NOI, ensure_ascii=False), encoding="utf-8")
            bad.write_text(json.dumps({"mode": "noi", "o": {}}), encoding="utf-8")
            run = lambda f: subprocess.run([sys.executable, str(SCRIPTS / "problem_card.py"), "check", str(f), "--json"],
                                           capture_output=True, text=True, encoding="utf-8")
            r = run(good)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertTrue(json.loads(r.stdout)["ok"])
            self.assertEqual(run(bad).returncode, 1)


if __name__ == "__main__":
    unittest.main()
