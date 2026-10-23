"""Dựng báo cáo kiểm thử chatbot (Markdown) từ bộ câu hỏi và kết quả chấm, so sánh trước/sau tối ưu.

  python eval_report.py <testcases.json> <ket_qua_truoc.json> [<ket_qua_sau.json>] [-o report.md]

testcases.json: [{"id","group","turns":[...],"expected":{"intent","action","must","must_not","source"}}]
ket_qua_*.json: {"label":"Trước tối ưu","changes":["<thay đổi đã làm>"],
                 "results":[{"id","reply","scores":{"content","intent","grounded","tone","handoff"},
                             "critical":false,"errors":["<lỗi ngắn>"]}]}
Điểm mỗi tiêu chí 0/1/2, null = không áp dụng. Tiêu chí và ngưỡng: references/livetalk-test-optimize.md mục 5.
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


def summarize(run):
    res = run["results"]
    scores = [s for s in (case_score(r) for r in res) if s is not None]
    crit = sum(1 for r in res if r.get("critical"))
    passed = sum(1 for r in res if not r.get("critical") and (case_score(r) or 0) >= PASS)
    by_crit = {}
    for k in CRITERIA:
        vals = [r["scores"][k] for r in res if (r.get("scores") or {}).get(k) is not None]
        by_crit[k] = sum(vals) / (2 * len(vals)) if vals else None
    return {"avg": sum(scores) / len(scores) if scores else 0, "critical": crit, "passed": passed,
            "total": len(res), "by_crit": by_crit,
            "ok": crit == 0 and scores and sum(scores) / len(scores) >= PASS}


def pct(x):
    return "—" if x is None else f"{x * 100:.0f}%"


def cell(s):
    return str(s or "").replace("|", "/").replace("\n", "<br>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cases")
    ap.add_argument("runs", nargs="+")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    if len(a.runs) > 2:
        sys.exit("Tối đa 2 file kết quả (trước, sau).")
    cases = load(a.cases)
    runs = [load(p) for p in a.runs]
    idx = [{r["id"]: r for r in run["results"]} for run in runs]
    sums = [summarize(run) for run in runs]
    labels = [run.get("label") or f"Vòng {i + 1}" for i, run in enumerate(runs)]

    out = ["# Báo cáo kiểm thử chatbot", "", "## Tổng quan", "",
           "| Chỉ số | " + " | ".join(labels) + " |", "|---|" + "---|" * len(runs)]
    out.append("| Điểm trung bình | " + " | ".join(pct(s["avg"]) for s in sums) + " |")
    out.append("| Ca đạt (≥ 85%, không lỗi nghiêm trọng) | " + " | ".join(f"{s['passed']}/{s['total']}" for s in sums) + " |")
    out.append("| Lỗi nghiêm trọng | " + " | ".join(str(s["critical"]) for s in sums) + " |")
    out.append("| Kết luận | " + " | ".join("Đạt" if s["ok"] else "Chưa đạt" for s in sums) + " |")
    for k, name in CRITERIA.items():
        out.append(f"| {name} | " + " | ".join(pct(s["by_crit"][k]) for s in sums) + " |")

    groups = defaultdict(list)
    for c in cases:
        groups[c.get("group", "?")].append(c["id"])
    out += ["", "## Theo nhóm", "", "| Nhóm | Số ca | " + " | ".join(labels) + " |", "|---|---|" + "---|" * len(runs)]
    for g, ids in groups.items():
        row = []
        for ix in idx:
            sc = [s for s in (case_score(ix[i]) for i in ids if i in ix) if s is not None]
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
                row += " — | — | — |"
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
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"Đã ghi {a.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)


if __name__ == "__main__":
    main()
