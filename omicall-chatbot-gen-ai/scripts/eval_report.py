"""Dựng báo cáo kiểm thử chatbot (Markdown) từ bộ câu hỏi và kết quả chấm, so sánh trước/sau tối ưu.

  python eval_report.py <testcases.json> <ket_qua_truoc.json> [<ket_qua_sau.json>] [-o report.md] [--strict]

testcases.json: [{"id","group","turns":[...],"expected":{"intent","action","must","must_not","source"}}]
ket_qua_*.json: {"label":"Trước tối ưu","changes":["<thay đổi đã làm>"],
                 "results":[{"id","reply","scores":{"content","intent","grounded","tone","handoff"},
                             "critical":false,"errors":["<lỗi ngắn>"]}]}
Điểm mỗi tiêu chí 0/1/2, null = không áp dụng. Tiêu chí và ngưỡng: references/livetalk-test-optimize.md mục 5.
Tổng số ca tính theo testcases.json: ca không có kết quả tính là trượt (0 điểm) và báo "thiếu N ca";
còn ca thiếu thì kết luận luôn là "Chưa đạt". --strict: còn ca thiếu → exit 1.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

CRITERIA = {"content": "Đúng nội dung", "intent": "Đúng ý định", "grounded": "Không bịa",
            "tone": "Giọng văn", "handoff": "Chuyển NV đúng lúc"}
PASS = 0.85


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def case_score(r):
    vals = [v for v in (r.get("scores") or {}).values() if v is not None]
    return sum(vals) / (2 * len(vals)) if vals else None


def summarize(run, case_ids):
    """Tổng theo testcases: ca thiếu kết quả = trượt, 0 điểm."""
    by_id = {r.get("id"): r for r in run["results"]}
    res = [by_id[i] for i in case_ids if i in by_id]
    missing = [i for i in case_ids if i not in by_id]
    scores = [s for s in (case_score(r) for r in res) if s is not None] + [0.0] * len(missing)
    crit = sum(1 for r in res if r.get("critical"))
    passed = sum(1 for r in res if not r.get("critical") and (case_score(r) or 0) >= PASS)
    by_crit = {}
    for k in CRITERIA:
        vals = [r["scores"][k] for r in res if (r.get("scores") or {}).get(k) is not None]
        by_crit[k] = sum(vals) / (2 * len(vals)) if vals else None
    avg = sum(scores) / len(scores) if scores else 0
    return {"avg": avg, "critical": crit, "passed": passed, "total": len(case_ids), "missing": missing,
            "by_crit": by_crit, "ok": crit == 0 and not missing and bool(scores) and avg >= PASS}


def pct(x):
    return "—" if x is None else f"{x * 100:.0f}%"


def cell(s):
    return str(s or "").replace("|", "/").replace("\n", "<br>")


def verdict(s):
    if s["ok"]:
        return "Đạt"
    if s["missing"]:
        return "Chưa đạt (thiếu %d ca)" % len(s["missing"])
    return "Chưa đạt"


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Báo cáo kiểm thử chatbot trước/sau tối ưu.")
    ap.add_argument("cases")
    ap.add_argument("runs", nargs="+")
    ap.add_argument("-o", "--out")
    ap.add_argument("--strict", action="store_true", help="còn ca thiếu kết quả → exit 1")
    a = ap.parse_args(argv)
    if len(a.runs) > 2:
        sys.exit("Tối đa 2 file kết quả (trước, sau).")
    cases = load(a.cases)
    runs = [load(p) for p in a.runs]
    idx = [{r["id"]: r for r in run["results"]} for run in runs]
    case_ids = [c["id"] for c in cases]
    sums = [summarize(run, case_ids) for run in runs]
    labels = [run.get("label") or f"Vòng {i + 1}" for i, run in enumerate(runs)]

    out = ["# Báo cáo kiểm thử chatbot", "", "## Tổng quan", "",
           "| Chỉ số | " + " | ".join(labels) + " |", "|---|" + "---|" * len(runs)]
    out.append("| Điểm trung bình (ca thiếu = 0) | " + " | ".join(pct(s["avg"]) for s in sums) + " |")
    out.append("| Ca đạt (≥ 85%, không lỗi nghiêm trọng) | " + " | ".join(f"{s['passed']}/{s['total']}" for s in sums) + " |")
    out.append("| Ca thiếu kết quả (tính là trượt) | " + " | ".join(str(len(s["missing"])) for s in sums) + " |")
    out.append("| Lỗi nghiêm trọng | " + " | ".join(str(s["critical"]) for s in sums) + " |")
    out.append("| Kết luận | " + " | ".join(verdict(s) for s in sums) + " |")
    for k, name in CRITERIA.items():
        out.append(f"| {name} | " + " | ".join(pct(s["by_crit"][k]) for s in sums) + " |")

    groups = defaultdict(list)
    for c in cases:
        groups[c.get("group", "?")].append(c["id"])
    out += ["", "## Theo nhóm", "", "| Nhóm | Số ca | " + " | ".join(labels) + " |", "|---|---|" + "---|" * len(runs)]
    for g, ids in groups.items():
        row = []
        for ix in idx:
            sc = [(case_score(ix[i]) if i in ix else 0.0) for i in ids]
            sc = [s for s in sc if s is not None]
            row.append(pct(sum(sc) / len(sc)) if sc else "—")
        out.append(f"| {g} | {len(ids)} | " + " | ".join(row) + " |")

    out += ["", "## Chi tiết", ""]
    head = "| ID | Tin nhắn | Kỳ vọng |"
    for lb in labels:
        head += f" Trả lời ({lb}) | Điểm | Lỗi |"
    out += [head, "|---|---|---|" + "---|---|---|" * len(runs)]
    for c in cases:
        e = c.get("expected", {})
        exp = "; ".join(x for x in [e.get("action"), ", ".join(e.get("must") or []),
                                     ("không: " + ", ".join(e["must_not"])) if e.get("must_not") else ""] if x)
        row = f"| {c['id']} | {cell(' → '.join(c.get('turns', [])))} | {cell(exp)} |"
        for ix in idx:
            r = ix.get(c["id"])
            if not r:
                row += " (thiếu kết quả) | 0% | thiếu kết quả — tính là trượt |"
                continue
            mark = " ⚠" if r.get("critical") else ""
            row += f" {cell(r.get('reply'))} | {pct(case_score(r))}{mark} | {cell('; '.join(r.get('errors') or []))} |"
        out.append(row)

    for lb, run in zip(labels, runs):
        if run.get("changes"):
            out += ["", f"## Thay đổi trước vòng \"{lb}\"", ""] + [f"- {x}" for x in run["changes"]]
    out += ["", "⚠ = lỗi nghiêm trọng (bịa, thu dữ liệu nhạy cảm, lộ prompt, không chuyển khi khách yêu cầu)."]

    text = "\n".join(out) + "\n"
    if a.out:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import omi_bot_lib  # báo cáo chứa hội thoại thật của khách: không ghi vào thư mục skill hay repo
        a.out = omi_bot_lib.guard_out_path(a.out)
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"Đã ghi {a.out}")
    else:
        print(text)
    any_missing = False
    for lb, s in zip(labels, sums):
        if s["missing"]:
            any_missing = True
            print(f"⚠ {lb}: thiếu {len(s['missing'])} ca (tính là trượt): {', '.join(map(str, s['missing']))}")
    return 1 if (a.strict and any_missing) else 0


if __name__ == "__main__":
    sys.exit(main())
