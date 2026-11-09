"""Đánh giá kích hoạt skill (routing) trên các skill OMI đã cài thật — đo description có gọi đúng skill không.

  python tools/run_routing_eval.py --dry-run                         # chỉ in số lượt chạy dự kiến
  python tools/run_routing_eval.py --model sonnet --runs 1 --limit 2  # chạy thử nhỏ
  python tools/run_routing_eval.py --model haiku --model sonnet --model opus --runs 3 --out evals/results
  python tools/run_routing_eval.py --pairs --model sonnet           # chỉ các câu "suýt giống" giữa skill anh em

Nguồn câu hỏi: evals/<skill>/trigger.json (định dạng của skill-creator: [{"query", "should_trigger"}]).
Khác run_eval.py của skill-creator: không tạo lệnh tạm cạnh tranh với skill thật; mỗi câu chạy một lần cho mọi skill,
ghi lại skill omicall-* nào được gọi ĐẦU TIÊN (hoặc không gọi skill nào). Một câu là "đạt" với skill S khi:
  should_trigger=true  → tỉ lệ chọn S ≥ ngưỡng (mặc định 0.5)
  should_trigger=false → tỉ lệ chọn S < ngưỡng
An toàn: không MCP, chỉ công cụ Skill, dừng ngay khi thấy lời gọi Skill đầu tiên (xem tools/claude_cli.py).
Yêu cầu: skill omicall-* đã cài vào ~/.claude/skills (junction tới repo này).
"""
import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import claude_cli  # noqa: E402

PREFIX = "omicall-"
# cặp dễ nhầm: --pairs chỉ chạy câu phủ định của skill này mà là câu khẳng định của skill kia
PAIRS = [("omicall-callbot-flow", "omicall-callbot-gen-ai"), ("omicall-chatbot-gen-ai", "omicall-callbot-gen-ai")]


def load_sets(root=ROOT, only=None):
    sets = {}
    for f in sorted((root / "evals").glob("*/trigger.json")):
        sk = f.parent.name
        if only and sk not in only:
            continue
        sets[sk] = json.loads(f.read_text(encoding="utf-8"))
    return sets


def pair_queries(sets):
    """Câu phủ định của skill X mà rõ ràng thuộc skill anh em Y (nhắc tới mảng của Y) — nơi description dễ nhầm nhất.
    Lấy kèm câu khẳng định của cả hai skill trong cặp có câu như vậy để đo cả hai chiều."""
    keep = set()
    for a, b in PAIRS:
        if a in sets and b in sets:
            keep |= {it["query"] for it in sets[a] + sets[b]}
    return keep


def first_skill(run):
    for ev in run["events"]:
        for tu in claude_cli.tool_uses(ev):
            n = claude_cli.skill_name_of(tu)
            if n:
                return n
    return None


def _stop(ev):
    return any(claude_cli.skill_name_of(tu) for tu in claude_cli.tool_uses(ev))


def run_one(claude, query, model, timeout):
    cwd = claude_cli.sandbox_dir()
    r = claude_cli.run_stream(claude, query, model=model, tools=("Skill",), cwd=cwd, timeout=timeout, stop=_stop)
    err = None
    if not r["events"]:
        err = (r.get("stderr") or "không có output").strip()[:300]
    return {"chosen": first_skill(r), "timed_out": r["timed_out"], "seconds": r["seconds"], "error": err}


def score(sets, picks, threshold):
    """picks: query -> list chosen. Trả về {skill: {passed,total,fails:[...]}}."""
    rep = {}
    for sk, items in sets.items():
        fails, passed, total = [], 0, 0
        for it in items:
            ch = picks.get(it["query"])
            if not ch:
                continue
            total += 1
            rate = sum(1 for c in ch if c == sk) / len(ch)
            ok = rate >= threshold if it["should_trigger"] else rate < threshold
            passed += ok
            if not ok:
                fails.append({"query": it["query"], "should_trigger": it["should_trigger"], "rate": round(rate, 2),
                              "chosen": dict(Counter(c or "(không skill)" for c in ch))})
        rep[sk] = {"passed": passed, "total": total, "fails": fails}
    return rep


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", action="append", help="lặp lại để so nhiều model (haiku, sonnet, opus hoặc id đầy đủ)")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--skill", action="append", help="chỉ đánh giá skill này (lặp lại được)")
    ap.add_argument("--pairs", action="store_true", help="chỉ câu thuộc các cặp skill dễ nhầm")
    ap.add_argument("--limit", type=int, default=0, help="chỉ N câu đầu (chạy thử)")
    ap.add_argument("--claude", help="đường dẫn claude.exe")
    ap.add_argument("--out", help="thư mục ghi results-<thời gian>.json")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    sets = load_sets(only=set(a.skill) if a.skill else None)
    if not sets:
        print("Không có evals/*/trigger.json")
        return 2
    queries = list(dict.fromkeys(it["query"] for items in sets.values() for it in items))
    if a.pairs:
        keep = pair_queries(sets)
        queries = [q for q in queries if q in keep]
    if a.limit:
        queries = queries[:a.limit]
    models = a.model or [None]
    n = len(queries) * a.runs * len(models)
    print(f"{len(sets)} skill · {len(queries)} câu · {a.runs} lượt · {len(models)} model → {n} lần gọi claude -p")
    if a.dry_run:
        return 0
    claude = claude_cli.find_claude(a.claude)
    if not claude:
        print("Không tìm thấy claude: thêm --claude <đường dẫn claude.exe> hoặc đặt CLAUDE_BIN")
        return 2

    all_out = {"started": time.strftime("%Y-%m-%d %H:%M"), "runs": a.runs, "threshold": a.threshold, "models": {}}
    for m in models:
        picks, errors = defaultdict(list), []
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            fut = {ex.submit(run_one, claude, q, m, a.timeout): q for q in queries for _ in range(a.runs)}
            for f in as_completed(fut):
                q = fut[f]
                try:
                    r = f.result()
                except Exception as e:  # noqa: BLE001
                    r = {"chosen": None, "error": str(e)[:300]}
                if r.get("error"):
                    errors.append({"query": q, "error": r["error"]})
                    continue
                picks[q].append(r["chosen"])
        rep = score(sets, picks, a.threshold)
        name = m or "(mặc định)"
        all_out["models"][name] = {"skills": rep, "errors": errors}
        tp = sum(v["passed"] for v in rep.values())
        tt = sum(v["total"] for v in rep.values())
        print(f"\n## Model {name}: {tp}/{tt} đạt" + (f" · {len(errors)} lượt lỗi" if errors else ""))
        for sk, v in rep.items():
            if v["total"]:
                print(f"- {sk}: {v['passed']}/{v['total']}")
            for x in v["fails"]:
                kind = "phải gọi" if x["should_trigger"] else "không được gọi"
                print(f"    ✗ ({kind}) {x['query'][:80]} → {x['chosen']}")
        if errors:
            print(f"    lỗi đầu tiên: {errors[0]['error']}")
    if len(models) > 1:
        print("\n## So sánh model (đạt/tổng)")
        print("| skill | " + " | ".join(all_out["models"]) + " |")
        print("|---|" + "---|" * len(models))
        for sk in sets:
            row = [f"{all_out['models'][k]['skills'][sk]['passed']}/{all_out['models'][k]['skills'][sk]['total']}"
                   for k in all_out["models"]]
            print(f"| {sk} | " + " | ".join(row) + " |")
    if a.out:
        d = Path(a.out)
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"routing-{time.strftime('%Y%m%d-%H%M')}.json"
        p.write_text(json.dumps(all_out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nĐã ghi {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
