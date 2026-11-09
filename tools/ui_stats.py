"""Đo mức đi vòng của agent trong một phiên Claude Code (đọc file .jsonl của phiên, chỉ in số đếm).

  python tools/ui_stats.py <phiên.jsonl | thư mục project | tiền tố id phiên> [...] [--project <thư mục>] [--json]

Ví dụ:
  python tools/ui_stats.py ~/.claude/projects/D--Code-OMI-GEN-AI/aae981db-....jsonl
  python tools/ui_stats.py aae981db --project ~/.claude/projects/D--Code-OMI-GEN-AI

Gộp cả subagent (<id>/subagents/*.jsonl) và bỏ tin nhắn trùng (phiên "tiếp tục" chép lại lịch sử cũ, cùng uuid).
Không in nội dung tin nhắn, URL đầy đủ hay dữ liệu nhập: chỉ số đếm và đường dẫn màn hình đã thay id bằng <id>.

Chỉ số:
  active_min    thời gian làm việc: cộng khoảng giữa hai bản ghi liên tiếp, mỗi khoảng tối đa 5 phút
  tool_calls    mọi lệnh công cụ (thao tác trong browser_batch tính từng cái)
  shots         ảnh chụp/zoom; shots_scaled = số ảnh có scale
  ref_click_pct tỉ lệ cú bấm theo ref (còn lại theo toạ độ, thường phải chụp trước)
  wait_then_shot số lần "wait rồi chụp" (chờ bằng ảnh thay vì mốc chữ)
  batch_calls   số lệnh browser_batch
  scripts       số lần chạy script dựng/kiểm/lưu của skill (build_, validate_, omi_save, *_outline, *_survey, check_callin)
  shots_by_screen 5 màn hình nhiều ảnh nhất
Mốc 10 phiên dựng 10–11/2026 (trước ui-recipes.md): 1.512 ảnh, ref_click_pct ~16%, wait_then_shot ~780,
batch ~8,5% lệnh trình duyệt, ~40% ảnh ở trang danh sách.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys
from datetime import datetime

SCRIPT_KEYS = ("build_", "validate_", "omi_save", "_outline", "_survey", "check_callin", "manifest", "omi_api")
CLICKS = ("left_click", "double_click", "triple_click", "right_click")


def resolve(arg, project):
    if os.path.isfile(arg):
        return [arg]
    if os.path.isdir(arg):
        return sorted(glob.glob(os.path.join(arg, "*.jsonl")))
    if project:
        return sorted(glob.glob(os.path.join(project, arg + "*.jsonl")))
    return []


def with_subagents(paths):
    out = list(paths)
    for p in paths:
        base = os.path.splitext(p)[0]
        out += sorted(glob.glob(os.path.join(base, "subagents", "*.jsonl")))
    return out


def screen(url):
    path = re.sub(r"^https?://[^/]+", "", url or "").split("?")[0].split("#")[0]
    return re.sub(r"[0-9a-fA-F]{20,}", "<id>", path) or "?"


def items_of(tool_use):
    """Tách một tool_use thành các thao tác (name, input); browser_batch tách từng thao tác con."""
    name = tool_use.get("name", "")
    inp = tool_use.get("input") or {}
    if name.endswith("browser_batch"):
        return [((a.get("name") or ""), a.get("input") or {}) for a in inp.get("actions") or []]
    return [(name.split("__")[-1], inp)]


def analyze(paths):
    seen, recs = set(), []
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                u = o.get("uuid")
                if u:
                    if u in seen:
                        continue
                    seen.add(u)
                recs.append(o)
    ts = sorted(datetime.fromisoformat(o["timestamp"].replace("Z", "+00:00")) for o in recs if o.get("timestamp"))
    active = sum(min((b - a).total_seconds(), 300) for a, b in zip(ts, ts[1:])) / 60
    c = collections.Counter()
    by_screen = collections.Counter()
    cur = "?"
    for o in sorted((o for o in recs if o.get("timestamp")), key=lambda o: o["timestamp"]):
        if o.get("type") != "assistant":
            continue
        prev = None
        for x in (o.get("message") or {}).get("content") or []:
            if not (isinstance(x, dict) and x.get("type") == "tool_use"):
                continue
            if x.get("name", "").endswith("browser_batch"):
                c["batch_calls"] += 1
            for name, inp in items_of(x):
                c["tool_calls"] += 1
                act = inp.get("action") if name == "computer" else None
                if name == "navigate" and inp.get("url"):
                    cur = screen(str(inp["url"]))
                if act in ("screenshot", "zoom"):
                    c["shots"] += 1
                    c["shots_scaled"] += 1 if inp.get("scale") else 0
                    by_screen[cur] += 1
                    if prev == "wait":
                        c["wait_then_shot"] += 1
                if act in CLICKS:
                    c["clicks_ref" if inp.get("ref") else "clicks_coord"] += 1
                if act == "wait":
                    c["waits"] += 1
                if name in ("find", "read_page"):
                    c["find_or_read_page"] += 1
                if name == "javascript_tool":
                    c["js_reads"] += 1
                if name in ("Bash", "PowerShell"):
                    cmd = str(inp.get("command", ""))
                    c["scripts"] += 1 if any(k in cmd for k in SCRIPT_KEYS) else 0
                prev = act or name
    clicks = c["clicks_ref"] + c["clicks_coord"]
    return {
        "files": len(paths), "active_min": round(active), "tool_calls": c["tool_calls"], "shots": c["shots"],
        "shots_scaled": c["shots_scaled"], "ref_click_pct": round(100 * c["clicks_ref"] / clicks) if clicks else None,
        "clicks": clicks, "waits": c["waits"], "wait_then_shot": c["wait_then_shot"], "batch_calls": c["batch_calls"],
        "find_or_read_page": c["find_or_read_page"], "js_reads": c["js_reads"], "scripts": c["scripts"],
        "shots_by_screen": by_screen.most_common(5),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--project", help="thư mục project của Claude Code (khi đưa tiền tố id phiên)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    paths = []
    for t in a.targets:
        found = resolve(os.path.expanduser(t), os.path.expanduser(a.project) if a.project else None)
        if not found:
            print("Không tìm thấy phiên: %s" % t)
            return 2
        paths += found
    r = analyze(with_subagents(paths))
    if a.json:
        print(json.dumps(r, ensure_ascii=False))
    else:
        for k, v in r.items():
            print("%-18s %s" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
