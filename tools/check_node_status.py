"""Kiểm references/node-status.json của các skill có bảng trạng thái node — offline, chỉ đọc.

  python tools/check_node_status.py [--root <repo>] [--skill omicall-omiflow ...]

In một dòng `FAIL <mã> <skill>[<chỉ số>] <type> (<side>): <mô tả>` cho mỗi vi phạm, dòng `NGOẠI LỆ` cho dòng được
miễn có ghi lý do, rồi `Tổng theo mã: ...` và `RESULT PASS|FAIL`. Exit 1 khi có vi phạm, 0 khi không.

Mã kiểm:
 NS1 schema: mảng JSON; mỗi dòng đủ đúng 8 khoá (KEYS); side/status/builder thuộc tập cho phép (builder:
     sinh | giu_nguyen | khong | "Cần xác nhận" khi không suy được từ mã). Cùng schema ở mọi file.
 NS2 nguồn: `source` dạng `references/<file>#<đầu tiêu đề mục>` (đúng MỘT tiêu đề bắt đầu bằng chuỗi sau '#', bỏ qua
     dòng trong khối ```) hoặc kiểu cũ `references/<file>:<dòng>`; file và mục/dòng phải tồn tại, và mục (hoặc dòng đó
     cùng 3 dòng sau) phải nhắc tới loại node: một mã như ADD_TICKET, hoặc mọi từ của phần mô tả sau mã
     ('X/thuộc tính kiểu danh sách'); loại không có mã thì một từ ≥3 ký tự của tên.
 NS3 `template` khác null thì file phải tồn tại.
 NS4 trùng cặp `type` + `side` trong một file.
 NS5 `verified` phải có `verified_on`: `YYYY-MM` / `YYYY-MM-DD`, hoặc đúng chuỗi "Cần xác nhận" khi tài liệu nguồn
     không ghi ngày (không bịa ngày).
 NS6 `builder` = "sinh" thì builder của skill phải có mã cho loại đó (mọi mã của loại xuất hiện trong mã builder,
     không tính docstring; không thuộc UNSUPPORTED; hành động phải thuộc SUPPORTED_ACTIONS nếu builder khai).
     Skill không có builder: mọi dòng ghi "khong".
 NS7 `verified` mà `ui_hint` còn "Cần xác nhận" (trừ NGOAI_LE có lý do).
"""
import argparse
import ast
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS = ["type", "side", "status", "builder", "template", "source", "verified_on", "ui_hint"]
SIDES = {"runtime", "editor", "edge", "action"}
STATUSES = {"verified", "enum", "ui_only", "unverified"}
CXN = "Cần xác nhận"
BUILDERS = {"sinh", "giu_nguyen", "khong", CXN}  # CXN: không suy được từ mã builder
# skill -> builder (None: skill không có builder)
SKILLS = {"omicall-omiflow": None,
          "omicall-callbot-flow": "scripts/build_callflow.py",
          "omicall-chatbot-gen-ai": "scripts/build_bot.py",
          "omicall-callbot-gen-ai": "scripts/build_smartagent.py"}
# Dòng verified được phép kèm "Cần xác nhận" (NS7): (skill, type, side) -> lý do. Không dùng để che lỗi trạng thái.
NGOAI_LE = {
    ("omicall-chatbot-gen-ai", "RAG chain put_v2 → other/add → other/training → other/search", "action"):
        "chuỗi 4 bước đã chạy (mục nguồn); chỉ trường phụ bots_use_file sau other/add còn Cần xác nhận",
    ("omicall-callbot-gen-ai", "BEGIN", "runtime"):
        "add_v2 tối thiểu đã chạy (mục 'Bài học tenant trống'); chỉ trường mặc định khi tenant trống còn Cần xác nhận",
}
RE_DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def type_tokens(t):
    """Mã của loại node: định danh có '_' hoặc viết HOA ≥3 ký tự (bỏ phần trong ngoặc); không có thì các từ ≥3 ký tự."""
    core = re.sub(r"\([^)]*\)", " ", nfc(t))
    toks = [x for x in re.findall(r"[A-Za-z][A-Za-z0-9_*]*", core) if "_" in x or (x.isupper() and len(x) >= 3)]
    return toks, (toks or [w for w in re.findall(r"\w+", core) if len(w) >= 3])


def headings(lines):
    """[(chỉ số dòng, cấp, chữ)] của tiêu đề markdown ngoài khối ```."""
    out, fence = [], False
    for i, l in enumerate(lines):
        if l.lstrip().startswith("```"):
            fence = not fence
        elif not fence:
            m = re.match(r"^(#{1,6})\s+(.*)$", l)
            if m:
                out.append((i, len(m.group(1)), m.group(2).strip()))
    return out


def section(lines, anchor):
    """(nội dung mục có tiêu đề bắt đầu bằng anchor tới tiêu đề cùng cấp/cao hơn kế tiếp, số tiêu đề khớp)."""
    hs = headings(lines)
    hits = [k for k, (_, _, text) in enumerate(hs) if text.startswith(anchor)]
    if not hits:
        return None, 0
    i, lv, _ = hs[hits[0]]
    end = next((j for j, l2, _ in hs[hits[0] + 1:] if l2 <= lv), len(lines))
    return "\n".join(lines[i:end]), len(hits)


def mentions(text, t):
    """Có một mã của loại trong text; hoặc (loại có phần mô tả bằng chữ, ví dụ 'X/thuộc tính kiểu danh sách') mọi từ
    ≥3 ký tự của phần mô tả đều có trong text."""
    code, toks = type_tokens(t)
    low = nfc(text).lower()
    if any(x.lower() in low for x in toks):
        return True
    core = re.sub(r"\([^)]*\)", " ", nfc(t))
    for x in code:
        core = core.replace(x, " ")
    desc = [w for w in re.findall(r"\w+", core) if len(w) >= 3]
    return bool(code and desc) and all(w.lower() in low for w in desc)


def check_source(skill_dir, r, cache):
    src = r.get("source")
    if not isinstance(src, str) or not src:
        return "thiếu source"
    m = re.match(r"^(references/[^#:]+)(?:#(.+)|:(\d+))$", src)
    if not m:
        return f"source '{src}' không theo dạng file#tiêu đề hoặc file:dòng"
    f = skill_dir / m.group(1)
    if not f.is_file():
        return f"không thấy file {m.group(1)}"
    if f not in cache:
        cache[f] = nfc(f.read_text(encoding="utf-8")).split("\n")
    lines = cache[f]
    if m.group(2) is not None:
        sec, hits = section(lines, nfc(m.group(2)))
        if sec is None:
            return f"không có mục tiêu đề bắt đầu bằng '{m.group(2)}' trong {m.group(1)}"
        if hits > 1:
            return f"'{m.group(2)}' khớp {hits} tiêu đề trong {m.group(1)} (ghi dài hơn cho duy nhất)"
        if not mentions(sec, r["type"]):
            return f"mục '{m.group(2)}' không nhắc tới loại này"
        return None
    n = int(m.group(3))
    if not 1 <= n <= len(lines):
        return f"dòng {n} ngoài file ({len(lines)} dòng)"
    if not mentions("\n".join(lines[n - 1:n + 3]), r["type"]):
        return f"dòng {n} không nhắc tới loại này (nguồn lệch dòng)"
    return None


def builder_code(path):
    """(chuỗi mã không gồm docstring, UNSUPPORTED values, SUPPORTED_ACTIONS) của builder."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant):
                docs.add(id(first.value))
    parts, unsup, sup = [], set(), None
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            parts.append(node.value)
        elif isinstance(node, ast.Name):
            parts.append(node.id)
        elif isinstance(node, ast.Attribute):
            parts.append(node.attr)
        if isinstance(node, ast.Assign) and any(getattr(x, "id", "") in ("UNSUPPORTED", "SUPPORTED_ACTIONS") for x in node.targets):
            try:
                val = ast.literal_eval(node.value)
            except ValueError:
                continue
            if node.targets[0].id == "UNSUPPORTED":
                unsup |= set(val.values()) if isinstance(val, dict) else set(val)
            else:
                sup = set(val)
    return nfc("\n".join(parts)), unsup, sup


def check_builder(r, info):
    b = r.get("builder")
    if info is None:
        return None if b == "khong" else f"skill không có builder nhưng builder='{b}' (phải 'khong')"
    if b != "sinh":
        return None
    code, unsup, sup = info
    t = nfc(r["type"])
    bad = [u for u in unsup if u in t.replace(" ", "")]
    if bad:
        return f"builder dừng (UNSUPPORTED) với {bad} nhưng ghi 'sinh'"
    toks, words = type_tokens(t)
    if toks:
        miss = [x for x in toks if not re.search(r"(?<![A-Za-z0-9_])" + re.escape(x) + r"(?![A-Za-z0-9_])", code)]
    else:
        miss = [w for w in words if w.lower() not in code.lower()]
    if miss:
        return f"builder ghi 'sinh' nhưng mã builder không có {miss}"
    if sup is not None and r.get("side") == "action" and not set(toks) & sup:
        return f"hành động không thuộc SUPPORTED_ACTIONS {sorted(sup)} của builder"
    return None


def check(root=ROOT, skills=None):
    """Trả (vi phạm [(mã, skill, chỉ số, type, side, mô tả)], ngoại lệ [(skill, chỉ số, type, side, lý do)])."""
    root = Path(root)
    viol, exc = [], []
    for skill in skills or SKILLS:
        sd = root / skill
        p = sd / "references" / "node-status.json"
        if not p.is_file():
            viol.append(("NS1", skill, "-", "-", "-", "không thấy references/node-status.json"))
            continue
        try:
            rows = json.loads(p.read_text(encoding="utf-8"))
        except ValueError as e:
            viol.append(("NS1", skill, "-", "-", "-", f"JSON lỗi: {e}"))
            continue
        if not isinstance(rows, list):
            viol.append(("NS1", skill, "-", "-", "-", "gốc không phải mảng"))
            continue
        bpath = SKILLS.get(skill) and sd / SKILLS[skill]
        info = builder_code(bpath) if bpath and bpath.is_file() else None
        cache, seen = {}, {}
        for i, r in enumerate(rows):
            def add(code, msg):
                viol.append((code, skill, i, str(r.get("type")), str(r.get("side")), msg))
            if not isinstance(r, dict):
                add("NS1", "dòng không phải object")
                continue
            for k in KEYS:
                if k not in r:
                    add("NS1", f"thiếu khoá {k}")
            for k in r:
                if k not in KEYS:
                    add("NS1", f"khoá lạ {k}")
            for k, allowed in (("side", SIDES), ("status", STATUSES), ("builder", BUILDERS)):
                if k in r and r[k] not in allowed:
                    add("NS1", f"{k}='{r[k]}' ngoài {sorted(allowed)}")
            if not isinstance(r.get("type"), str):
                continue
            err = check_source(sd, r, cache)
            if err:
                add("NS2", err)
            if r.get("template") is not None and not (sd / str(r["template"])).is_file():
                add("NS3", f"không thấy template {r['template']}")
            key = (r["type"], r.get("side"))
            if key in seen:
                add("NS4", f"trùng type+side với dòng {seen[key]}")
            seen.setdefault(key, i)
            if r.get("status") == "verified":
                v = r.get("verified_on")
                if not (isinstance(v, str) and (RE_DATE.match(v) or v == CXN)):
                    add("NS5", f"verified nhưng verified_on={v!r} (cần YYYY-MM hoặc '{CXN}')")
                if CXN.casefold() in nfc(str(r.get("ui_hint", ""))).casefold():
                    reason = NGOAI_LE.get((skill, r["type"], r.get("side")))
                    if reason:
                        exc.append((skill, i, r["type"], r.get("side"), reason))
                    else:
                        add("NS7", f"verified nhưng ui_hint còn '{CXN}'")
            if "builder" in r:
                err = check_builder(r, info if bpath else None)
                if err:
                    add("NS6", err)
    return viol, exc


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--skill", action="append", choices=sorted(SKILLS), help="chỉ kiểm skill này (lặp được)")
    a = ap.parse_args(argv)
    viol, exc = check(a.root, a.skill)
    for code, skill, i, t, side, msg in viol:
        print(f"FAIL {code} {skill}[{i}] {t} ({side}): {msg}")
    for skill, i, t, side, reason in exc:
        print(f"NGOẠI LỆ NS7 {skill}[{i}] {t} ({side}): {reason}")
    counts = {}
    for v in viol:
        counts[v[0]] = counts.get(v[0], 0) + 1
    print("Tổng theo mã: " + (", ".join(f"{k} {counts[k]}" for k in sorted(counts)) or "0 vi phạm"))
    print(f"RESULT {'FAIL' if viol else 'PASS'} ({len(viol)} vi phạm)")
    return 1 if viol else 0


if __name__ == "__main__":
    sys.exit(main())
