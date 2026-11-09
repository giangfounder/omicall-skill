"""Eval chất lượng đa model cho bước hiểu bài toán (phiếu bài toán) — chạy offline, dừng ở cổng xin duyệt.

  python tools/run_quality_eval.py --dry-run
  python tools/run_quality_eval.py --model haiku --model sonnet --model opus --runs 1 --out evals/results
  python tools/run_quality_eval.py --model sonnet --case 3              # một ca

Nguồn ca: evals/<skill>/evals.json (định dạng skill-creator + khối "grade"). Mỗi lượt:
  1. thư mục tạm có .claude/ rỗng; chép files của ca vào ./evals_files/;
  2. `claude -p "/<skill> <prompt> + lời dặn chế độ đánh giá"` — không MCP, chỉ Skill/Read/Write/Glob/Grep và
     Bash cho riêng problem_card.py (mọi lệnh khác bị từ chối), nên không thể đăng nhập hay ghi lên tenant;
  3. chấm ./problem_card.json bằng shared/scripts/problem_card.py check + các điều kiện trong "grade";
  4. ghi token, chi phí, thời gian từ sự kiện result.
Kết quả cùng một ca trên Haiku/Sonnet/Opus cho thấy cách viết skill có giữ chất lượng khi đổi model không.
"""
import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ROOT / "shared" / "scripts"))
import claude_cli  # noqa: E402
import problem_card as pc  # noqa: E402

EVAL_SUFFIX = (
    "\n\n[Chế độ đánh giá offline] Không có tài khoản OMI: bỏ qua bước cập nhật skill, đăng nhập và khảo sát tài khoản. "
    "Chỉ làm bước hiểu bài toán (references/solution-method.md mục 1) rồi dừng ở bước xin duyệt, không dựng gì. "
    "Ghi phiếu bài toán theo định dạng của scripts/problem_card.py vào file ./problem_card.json "
    "(thư mục hiện tại), kiểm bằng problem_card.py check, rồi trả lời user như bình thường.")
TOOLSET = ("Skill", "Read", "Write", "Glob", "Grep", "Bash")
ALLOWED = ["Skill", "Read", "Write", "Glob", "Grep", "Bash(python *problem_card.py*)"]


def load_cases(root=ROOT, only_skill=None):
    out = []
    for f in sorted((root / "evals").glob("*/evals.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        sk = d.get("skill_name") or f.parent.name
        if only_skill and sk not in only_skill:
            continue
        for c in d.get("evals", []):
            if "grade" in c:
                out.append((sk, c))
    return out


def _text(v):
    return " ; ".join(v) if isinstance(v, list) else str(v or "")


def grade(card, g):
    """Trả về list lý do trượt (rỗng = đạt)."""
    if card is None:
        return ["không có ./problem_card.json"]
    why = [f"problem_card: {m}" for lv, m in pc.check(card) if lv == "FAIL"]
    o = card.get("o") or {}
    if g.get("mode") and card.get("mode") != g["mode"]:
        why.append(f"mode {card.get('mode')} ≠ {g['mode']}")
    qs = card.get("cau_hoi") or []
    if "max_questions" in g and len(qs) > g["max_questions"]:
        why.append(f"{len(qs)} câu hỏi > {g['max_questions']}")
    conf = (card.get("gia_thuyet") or {}).get("tu_tin")
    if "min_confidence" in g and not (isinstance(conf, (int, float)) and conf >= g["min_confidence"]):
        why.append(f"độ tự tin {conf} < {g['min_confidence']}")
    parts = card.get("phan_viec") or []
    if len(parts) < g.get("min_parts", 0):
        why.append(f"{len(parts)} phần việc < {g['min_parts']}")
    pj = " ; ".join(map(str, parts))
    for rx in g.get("parts_regex_all", []):
        if not re.search(rx, pj):
            why.append(f"phần việc thiếu /{rx}/")
    for k, rx in (g.get("o_regex") or {}).items():
        if not re.search(rx, _text(o.get(k))):
            why.append(f"ô {k} không khớp /{rx}/: {_text(o.get(k))[:60]}")
    for k, rx in (g.get("o_forbid_regex") or {}).items():
        if re.search(rx, _text(o.get(k))):
            why.append(f"ô {k} có /{rx}/ (nghi bịa): {_text(o.get(k))[:60]}")
    for k in g.get("cxn_required", []):
        if not pc._is_cxn(o.get(k)) and not (isinstance(o.get(k), list) and any(pc._is_cxn(x) for x in o[k])):
            why.append(f"ô {k} phải là \"{pc.CXN}\" (tài liệu không nói)")
    return why


def run_case(claude, skill, case, model, timeout):
    cwd = claude_cli.sandbox_dir("omi_qeval_")
    fdir = cwd / "evals_files"
    for f in case.get("files", []):
        src = ROOT / f
        if src.is_file():
            fdir.mkdir(exist_ok=True)
            shutil.copyfile(src, fdir / src.name)
    prompt = f"/{skill} {case['prompt']}{EVAL_SUFFIX}"
    r = claude_cli.run_stream(claude, prompt, model=model, tools=TOOLSET, cwd=cwd, timeout=timeout,
                              extra_args=["--allowedTools", *ALLOWED])
    stray = []
    for ev in r["events"]:
        for tu in claude_cli.tool_uses(ev):
            if tu.get("name") == "Write":
                p = str((tu.get("input") or {}).get("file_path", ""))
                if not p.replace("\\", "/").endswith("problem_card.json"):
                    stray.append(p)
    card = None
    pf = cwd / "problem_card.json"
    if pf.is_file():
        try:
            card = json.loads(pf.read_text(encoding="utf-8"))
        except ValueError:
            card = None
    why = grade(card, case["grade"])
    if stray:
        why.append(f"ghi file ngoài phiếu: {stray[:3]}")
    res = r.get("result") or {}
    usage = res.get("usage") or {}
    if not r["events"]:
        why = ["không chạy được claude: " + (r.get("stderr") or "")[:200]]
    elif res.get("is_error"):
        why = ["claude báo lỗi: " + str(res.get("result"))[:200]]
    return {"id": case["id"], "pass": not why, "why": why, "seconds": r["seconds"], "timed_out": r["timed_out"],
            "cost_usd": res.get("total_cost_usd"), "turns": res.get("num_turns"),
            "tokens_in": (usage.get("input_tokens") or 0) + (usage.get("cache_read_input_tokens") or 0)
            + (usage.get("cache_creation_input_tokens") or 0),
            "tokens_out": usage.get("output_tokens")}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", action="append")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--case", type=int, action="append", help="chỉ ca id này")
    ap.add_argument("--skill", action="append")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--claude")
    ap.add_argument("--out")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    cases = [(s, c) for s, c in load_cases(only_skill=set(a.skill) if a.skill else None)
             if not a.case or c["id"] in a.case]
    models = a.model or [None]
    print(f"{len(cases)} ca · {a.runs} lượt · {len(models)} model → {len(cases) * a.runs * len(models)} lần gọi claude -p")
    if a.dry_run or not cases:
        return 0
    claude = claude_cli.find_claude(a.claude)
    if not claude:
        print("Không tìm thấy claude: thêm --claude <đường dẫn> hoặc đặt CLAUDE_BIN")
        return 2
    report = {"started": time.strftime("%Y-%m-%d %H:%M"), "models": {}}
    for m in models:
        name = m or "(mặc định)"
        rows = []
        for s, c in cases:
            for _ in range(a.runs):
                r = run_case(claude, s, c, m, a.timeout)
                r["skill"] = s
                rows.append(r)
                mark = "✓" if r["pass"] else "✗"
                print(f"[{name}] {mark} {s} ca {c['id']} · {r['seconds']}s · in {r['tokens_in']} out {r['tokens_out']}"
                      + ("" if r["pass"] else " · " + " | ".join(r["why"][:3])))
        ok = sum(r["pass"] for r in rows)
        secs = [r["seconds"] for r in rows]
        toks = [r["tokens_in"] + (r["tokens_out"] or 0) for r in rows if r["tokens_in"]]
        report["models"][name] = {"passed": ok, "total": len(rows), "rows": rows,
                                  "avg_seconds": round(sum(secs) / len(secs), 1) if secs else None,
                                  "avg_tokens": round(sum(toks) / len(toks)) if toks else None}
    print("\n| model | đạt | TB giây | TB token |\n|---|---|---|---|")
    for k, v in report["models"].items():
        print(f"| {k} | {v['passed']}/{v['total']} | {v['avg_seconds']} | {v['avg_tokens']} |")
    if a.out:
        d = Path(a.out)
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"quality-{time.strftime('%Y%m%d-%H%M')}.json"
        p.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Đã ghi {p}")
    return 0 if all(v["passed"] == v["total"] for v in report["models"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
