"""Phiếu bài toán khách hàng (solution-method.md mục 1): kiểm và in mẫu Tóm tắt. Chạy offline, không mạng.

  python problem_card.py template [--mode noi|tai_lieu]   # in mẫu JSON để điền
  python problem_card.py check <problem_card.json> [--json]
  python problem_card.py render <problem_card.json>      # in mẫu "Tóm tắt" (noi) hoặc danh sách "Cần xác nhận" (tai_lieu)

check in một dòng mỗi kết quả `PASS|FAIL|WARN <mô tả>`, dòng cuối `RESULT PASS|FAIL`; exit 1 khi có FAIL.
Chế độ:
  noi       yêu cầu nói miệng, user có mặt: cần giả thuyết + độ tự tin, câu hỏi (≤4) phải kèm phỏng đoán.
  tai_lieu  tài liệu/RFP gửi khách: không đoán, không độ tự tin; ô trống = "Cần xác nhận" + câu hỏi cho khách.
"""
import argparse
import json
import re
import sys
from pathlib import Path

CXN = "Cần xác nhận"
O_KEYS = [("vao", "Vào"), ("doi_tuong", "Đối tượng"), ("luat", "Luật"), ("ra", "Ra"),
          ("rang_buoc", "Ràng buộc"), ("thanh_cong", "Thành công khi"), ("khong_lam", "Không làm")]
LABEL = dict(O_KEYS)
MAX_Q = 4
# dấu vết nội bộ không được lọt vào phần gửi khách (chế độ tài liệu)
INTERNAL = re.compile(r"(?i)(em đoán|độ tự tin|tự tin\s*\d|\d+\s*%\s*tự tin|\(đề xuất\)|ghi chú nội bộ)")


def template(mode="noi"):
    o = {k: "" for k, _ in O_KEYS}
    o["khong_lam"] = [""]
    card = {"mode": mode, "o": o, "mac_dinh": [], "phan_viec": []}
    if mode == "noi":
        card["gia_thuyet"] = {"cau": "Khách cần …", "tu_tin": 0}
        card["cau_hoi"] = [{"o": "luat", "hoi": "", "doan": ""}]
    else:
        card["can_xac_nhan"] = [{"o": "rang_buoc", "hoi": ""}]
    return card


def _blank(v):
    if isinstance(v, list):
        return not [x for x in v if isinstance(x, str) and x.strip()]
    return not (isinstance(v, str) and v.strip())


def _is_cxn(v):
    return isinstance(v, str) and v.strip().lower().startswith(CXN.lower())


def check(card):
    """Trả về list (mức, mô tả). mức: PASS/FAIL/WARN."""
    out = []
    add = lambda lv, msg: out.append((lv, msg))
    if not isinstance(card, dict):
        return [("FAIL", "phiếu phải là một object JSON")]
    mode = card.get("mode")
    if mode not in ("noi", "tai_lieu"):
        add("FAIL", "mode phải là 'noi' hoặc 'tai_lieu'")
        mode = "noi"
    o = card.get("o") or {}
    if not isinstance(o, dict):
        add("FAIL", "'o' phải là object 7 ô")
        o = {}
    cxn = []
    for k, lb in O_KEYS:
        v = o.get(k)
        if k not in o or _blank(v):
            add("FAIL", f"ô '{lb}' ({k}) trống — điền, hoặc ghi \"{CXN}\"")
        elif k == "khong_lam" and not isinstance(v, list):
            add("FAIL", "ô 'Không làm' phải là danh sách, ít nhất 1 dòng")
        elif _is_cxn(v) or (isinstance(v, list) and any(_is_cxn(x) for x in v)):
            cxn.append(k)
        else:
            add("PASS", f"ô '{lb}' đã có")
    if isinstance(o.get("khong_lam"), list) and "khong_lam" in cxn:
        add("WARN", "ô 'Không làm' đang để Cần xác nhận — nên tự đề xuất phạm vi loại trừ để khách gạt đi")

    if mode == "noi":
        gt = card.get("gia_thuyet") or {}
        if _blank(gt.get("cau")):
            add("FAIL", "thiếu giả thuyết 1 câu (gia_thuyet.cau)")
        t = gt.get("tu_tin")
        if not isinstance(t, (int, float)) or not 0 <= t <= 100:
            add("FAIL", "gia_thuyet.tu_tin phải là số 0–100")
        qs = card.get("cau_hoi") or []
        if len(qs) > MAX_Q:
            add("FAIL", f"{len(qs)} câu hỏi > {MAX_Q}: gộp hoặc để mặc định, nêu trong Tóm tắt")
        for i, q in enumerate(qs, 1):
            if _blank((q or {}).get("hoi")):
                add("FAIL", f"câu hỏi {i} trống")
            if _blank((q or {}).get("doan")):
                add("FAIL", f"câu hỏi {i} thiếu phỏng đoán 'Em đoán: …' (doan)")
        asked = {(q or {}).get("o") for q in qs}
        for k in cxn:
            if k not in asked:
                add("WARN", f"ô '{LABEL[k]}' Cần xác nhận nhưng không có câu hỏi — chấp nhận nếu không chặn việc")
        if isinstance(t, (int, float)) and t >= 90 and qs:
            add("WARN", "tự tin ≥ 90% mà vẫn hỏi — cân nhắc bỏ câu hỏi, để mặc định")
        if isinstance(t, (int, float)) and t < 70 and not qs:
            add("WARN", "tự tin < 70% mà không hỏi gì — dễ hiểu sai bài toán")
    else:
        if "gia_thuyet" in card or "cau_hoi" in card:
            add("FAIL", "chế độ tài liệu không dùng gia_thuyet/cau_hoi (không đoán trong phần gửi khách)")
        items = card.get("can_xac_nhan") or []
        have = {(x or {}).get("o") for x in items}
        for k in cxn:
            if k not in have:
                add("FAIL", f"ô '{LABEL[k]}' Cần xác nhận nhưng thiếu câu hỏi gửi khách trong can_xac_nhan")
        for i, x in enumerate(items, 1):
            q = (x or {}).get("hoi", "")
            if _blank(q):
                add("FAIL", f"can_xac_nhan {i} trống")
            elif INTERNAL.search(q):
                add("FAIL", f"can_xac_nhan {i} lộ chữ nội bộ (phỏng đoán/độ tự tin/đề xuất): {q[:60]}")
        blob = json.dumps(card.get("o", {}), ensure_ascii=False)
        if INTERNAL.search(blob):
            add("FAIL", "phiếu chế độ tài liệu có chữ nội bộ (phỏng đoán/độ tự tin)")
    if not any(lv == "FAIL" for lv, _ in out):
        add("PASS", f"phiếu hợp lệ (chế độ {mode}, {len(cxn)} ô Cần xác nhận)")
    return out


def _fmt(v):
    return "; ".join(x for x in v if x) if isinstance(v, list) else (v or "")


def render(card):
    o = card.get("o") or {}
    if card.get("mode") == "tai_lieu":
        lines = ["Các điểm cần Quý khách xác nhận:"]
        for i, x in enumerate(card.get("can_xac_nhan") or [], 1):
            lines.append(f"{i}. {x.get('hoi', '')}")
        if len(lines) == 1:
            lines.append("(không có)")
        return "\n".join(lines)
    parts = card.get("phan_viec") or []
    lines = ["Em hiểu việc cần làm như sau:",
             f"- Khi: {_fmt(o.get('vao'))}",
             f"- Hệ thống sẽ: {_fmt(o.get('luat'))}",
             f"- Kết quả: {_fmt(o.get('ra'))}",
             f"- Thành công khi: {_fmt(o.get('thanh_cong'))}",
             f"- Lần này không làm: {_fmt(o.get('khong_lam'))}",
             f"Em sẽ làm {len(parts)} phần: {'; '.join(parts)}. "
             f"Những điểm em đang để mặc định: {'; '.join(card.get('mac_dinh') or []) or 'không có'}.",
             'Anh/chị trả lời "đồng ý" để em bắt đầu, hoặc sửa giúp em dòng chưa đúng.']
    qs = card.get("cau_hoi") or []
    if qs:
        lines += ["", f"Để làm đúng ý anh/chị, em cần chốt {len(qs)} điểm. Đúng thì anh/chị chỉ cần trả lời \"đúng\":"]
        lines += [f"{i}. {q.get('hoi', '')}? Em đoán: {q.get('doan', '')}" for i, q in enumerate(qs, 1)]
    return "\n".join(lines)


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("template")
    t.add_argument("--mode", choices=["noi", "tai_lieu"], default="noi")
    c = sub.add_parser("check")
    c.add_argument("file")
    c.add_argument("--json", action="store_true", help="in kết quả dạng JSON (cho bộ chấm eval)")
    r = sub.add_parser("render")
    r.add_argument("file")
    a = ap.parse_args(argv)
    if a.cmd == "template":
        print(json.dumps(template(a.mode), ensure_ascii=False, indent=2))
        return 0
    try:
        card = _load(a.file)
    except (OSError, ValueError) as e:
        print(f"FAIL không đọc được phiếu: {e}")
        print("RESULT FAIL")
        return 1
    if a.cmd == "render":
        print(render(card))
        return 0
    res = check(card)
    ok = not any(lv == "FAIL" for lv, _ in res)
    if a.json:
        print(json.dumps({"ok": ok, "results": [{"level": lv, "msg": m} for lv, m in res]}, ensure_ascii=False))
    else:
        for lv, m in res:
            print(f"{lv} {m}")
        print(f"RESULT {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
