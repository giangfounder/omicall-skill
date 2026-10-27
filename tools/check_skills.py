"""Lưới an toàn cho repo skill OMI — chạy offline, chỉ đọc.

  python tools/check_skills.py [--root <repo>] [--baseline-dir <bản chụp trước khi sửa>]

In một dòng cho mỗi kết quả: `PASS|FAIL|WARN|REVIEW (<mục>) <mô tả>`; dòng cuối `RESULT PASS|FAIL`.
Exit 1 khi có FAIL, 0 khi không (WARN và REVIEW chỉ để người soát).

Các mục:
 (a) Mỗi SKILL.md có '## Đường nhanh' trong 30 dòng đầu, khối dài ≤25 dòng.
 (b) Cụm từ an toàn theo skill. Có --baseline-dir: cụm có trong baseline mà nay mất khỏi skill → FAIL.
     Không có baseline: cụm vắng mặt → FAIL.
 (c) REVIEW: bullet trong mục Rules/Gotchas/Quy tắc của baseline mà câu chuẩn hoá không còn ở đâu trong skill.
 (d) sync_shared --check (file dùng chung khớp shared/) và omi-mcp.md giống hệt ở mọi skill.
 (e) Mọi đường dẫn references/... và scripts/... nhắc trong SKILL.md đều tồn tại.
 (f) Dữ liệu nhạy cảm: SĐT VN, JWT (eyJ...), email, '<tên>.omicrm.io', '*_session.json'.
     Ngoại lệ ở tools/sensitive_allowlist.json. Mọi file credentials.md bị bỏ qua theo đường dẫn, không mở.
 (g) Không còn chuỗi '3 skill' (đã có 4 skill).
 (h) Kích thước SKILL.md so với baseline (chỉ WARN).
"""
import argparse
import glob
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

SKILLS = ["omicall-callbot-gen-ai", "omicall-callbot-flow", "omicall-chatbot-gen-ai", "omicall-omiflow"]
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache"}
SKIP_NAMES = {"credentials.md"}  # không bao giờ mở
TEXT_EXT = {".md", ".py", ".json", ".txt", ".html", ".js", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".csv", ""}

COMMON_PHRASES = ["Xuất bản", "Cần xác nhận", "mật khẩu", "uuid"]
EXTRA_PHRASES = {
    "omicall-callbot-gen-ai": ["BEGIN", "datas"],
    "omicall-chatbot-gen-ai": ["/end"],
    "omicall-omiflow": ["name_mappings", "Hoạt động"],
}

FAST_HEADING = "## Đường nhanh"
FAST_MAX_LINE = 30
FAST_MAX_LEN = 25

RE_PHONE = re.compile(r"(?<![\d.])0[35789]\d{8}(?!\d)")
RE_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{10,}")
RE_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
RE_TENANT = re.compile(r"(?<![\w{<%>$.-])([A-Za-z0-9][A-Za-z0-9-]*)\.omicrm\.io")
RE_SESSION = re.compile(r"(?<![\w.-])([\w.-]+_session\.json)")
RE_3SKILL = re.compile(r"(?<!\d)3 skill")
RE_PATH = re.compile(r"(?:(omicall-[a-z-]+)/)?((?:references|scripts)/[\w.*\-/]*[\w*]\.\w+)")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def norm(s):
    s = nfc(s).casefold()
    s = re.sub(r"[*`_>#\[\]()]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def iter_text_files(base):
    base = Path(base)
    if base.is_file():
        yield base
        return
    for p in sorted(base.rglob("*")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if not p.is_file() or p.name in SKIP_NAMES:
            continue
        if p.suffix.lower() not in TEXT_EXT:
            continue
        yield p


def read(p):
    try:
        return nfc(Path(p).read_text(encoding="utf-8"))
    except (UnicodeDecodeError, OSError):
        return None


def skill_text(skill_dir):
    parts = []
    for p in iter_text_files(skill_dir):
        t = read(p)
        if t is not None:
            parts.append(t)
    return "\n".join(parts)


def load_allowlist(path=None):
    path = Path(path) if path else TOOLS / "sensitive_allowlist.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    vals = lambda k: {str(x["value"]) for x in data.get(k, []) if isinstance(x, dict) and "value" in x}
    return {k: vals(k) for k in ("phones", "emails", "tenant_domains", "session_files", "jwt", "system_ids", "literal")}


class Report:
    def __init__(self):
        self.lines = []
        self.fails = 0

    def add(self, level, item, msg):
        if level == "FAIL":
            self.fails += 1
        line = f"{level} ({item}) {msg}"
        self.lines.append(line)
        print(line)


def check_fast_path(rep, root, skills):
    for s in skills:
        p = root / s / "SKILL.md"
        t = read(p)
        if t is None:
            rep.add("FAIL", "a", f"{s}/SKILL.md không đọc được")
            continue
        lines = t.splitlines()
        idx = next((i for i, l in enumerate(lines) if l.strip().startswith(FAST_HEADING)), None)
        if idx is None:
            rep.add("FAIL", "a", f"{s}/SKILL.md chưa có '{FAST_HEADING}'")
            continue
        if idx + 1 > FAST_MAX_LINE:
            rep.add("FAIL", "a", f"{s}/SKILL.md:{idx + 1} '{FAST_HEADING}' nằm sau dòng {FAST_MAX_LINE}")
            continue
        end = len(lines)
        for j in range(idx + 1, len(lines)):
            if re.match(r"^#{1,2} ", lines[j]):
                end = j
                break
        while end > idx + 1 and not lines[end - 1].strip():
            end -= 1
        n = end - idx
        if n > FAST_MAX_LEN:
            rep.add("FAIL", "a", f"{s}/SKILL.md:{idx + 1} khối Đường nhanh dài {n} dòng (> {FAST_MAX_LEN})")
        else:
            rep.add("PASS", "a", f"{s}/SKILL.md:{idx + 1} Đường nhanh {n} dòng")


def check_phrases(rep, root, skills, baseline):
    for s in skills:
        cur = skill_text(root / s).casefold()
        base = skill_text(baseline / s).casefold() if baseline and (baseline / s).is_dir() else None
        for ph in COMMON_PHRASES + EXTRA_PHRASES.get(s, []):
            k = nfc(ph).casefold()
            if base is not None and k not in base:
                continue
            if k in cur:
                rep.add("PASS", "b", f"{s} còn '{ph}'")
            else:
                rep.add("FAIL", "b", f"{s} mất cụm an toàn '{ph}'" + (" (có trong baseline)" if base is not None else ""))


def rule_bullets(skill_md):
    t = read(skill_md) or ""
    out, active, level = [], False, 0
    for i, line in enumerate(t.splitlines(), 1):
        m = re.match(r"^(#{1,4}) (.*)", line)
        if m:
            lv = len(m.group(1))
            if re.search(r"rules|gotchas|quy tắc|an toàn", m.group(2), re.I):
                active, level = True, lv
            elif active and lv <= level:
                active = False
            continue
        if active and re.match(r"^\s*(?:[-*]|\d+\.)\s+", line):
            body = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line)
            if len(norm(body)) >= 15:
                out.append((i, body))
    return out


def check_review(rep, root, skills, baseline):
    if not baseline:
        return
    for s in skills:
        bmd = baseline / s / "SKILL.md"
        if not bmd.is_file():
            continue
        cur = norm(skill_text(root / s))
        for i, body in rule_bullets(bmd):
            if norm(body) not in cur:
                rep.add("REVIEW", "c", f"{s}/SKILL.md:{i} (baseline) không còn nguyên câu: {body[:110]}")


def check_sync(rep, root, skills):
    try:
        import sync_shared
    except ImportError as e:
        rep.add("FAIL", "d", f"không nạp được tools/sync_shared.py: {e}")
        return
    buf = []
    n = sync_shared.check(root, out=buf.append)
    for l in buf:
        if l.startswith("FAIL"):
            rep.add("FAIL", "d", "sync_shared: " + l[5:])
    if n == 0:
        rep.add("PASS", "d", "sync_shared --check khớp")
    hashes = {}
    for s in skills:
        p = root / s / "references" / "omi-mcp.md"
        if p.is_file():
            hashes[s] = hashlib.sha256(p.read_bytes()).hexdigest()
        else:
            rep.add("FAIL", "d", f"thiếu {s}/references/omi-mcp.md")
    if len(set(hashes.values())) > 1:
        rep.add("FAIL", "d", "omi-mcp.md không giống hệt: " + ", ".join(f"{k}={v[:12]}" for k, v in hashes.items()))
    elif hashes:
        rep.add("PASS", "d", f"omi-mcp.md giống hệt ở {len(hashes)} skill")


def check_paths(rep, root, skills):
    for s in skills:
        p = root / s / "SKILL.md"
        t = read(p) or ""
        seen = set()
        for i, line in enumerate(t.splitlines(), 1):
            for m in RE_PATH.finditer(line):
                other, rel = m.group(1), m.group(2)
                if "<" in rel or "{" in rel:
                    continue
                base = root / other if other else root / s
                key = (str(base), rel)
                if key in seen:
                    continue
                seen.add(key)
                if "*" in rel:
                    ok = bool(glob.glob(str(base / rel)))
                else:
                    ok = (base / rel).exists()
                where = f"{other}/{rel}" if other else rel
                if not ok and Path(rel).name in SKIP_NAMES:
                    rep.add("WARN", "e", f"{s}/SKILL.md:{i} '{where}' chỉ có trên máy cài (không kiểm nội dung)")
                    continue
                if ok:
                    rep.add("PASS", "e", f"{s}/SKILL.md:{i} {where}")
                else:
                    rep.add("FAIL", "e", f"{s}/SKILL.md:{i} nhắc '{where}' nhưng file không tồn tại")


def scan_sensitive(root, allow, out):
    """Gọi out(rel_path, line_no, kind, value) cho mỗi phát hiện. Không mở credentials.md."""
    root = Path(root)
    for p in iter_text_files(root):
        t = read(p)
        if t is None:
            continue
        rel = p.relative_to(root).as_posix() if p != root else p.name
        for i, line in enumerate(t.splitlines(), 1):
            for m in RE_PHONE.finditer(line):
                if m.group(0) not in allow["phones"]:
                    out(rel, i, "SĐT", m.group(0))
            for m in RE_JWT.finditer(line):
                if m.group(0) not in allow["jwt"]:
                    out(rel, i, "JWT", m.group(0)[:12] + "…")
            for m in RE_EMAIL.finditer(line):
                if m.group(0) not in allow["emails"]:
                    out(rel, i, "email", m.group(0))
            for m in RE_TENANT.finditer(line):
                if m.group(1).lower() not in allow["tenant_domains"]:
                    out(rel, i, "domain tenant", m.group(0))
            for m in RE_SESSION.finditer(line):
                if m.group(1) not in allow["session_files"]:
                    out(rel, i, "file phiên", m.group(1))


def check_sensitive(rep, root, allow):
    hits = []
    scan_sensitive(root, allow, lambda *a: hits.append(a))
    for rel, i, kind, val in hits:
        rep.add("FAIL", "f", f"{rel}:{i} {kind} '{val}'")
    if not hits:
        rep.add("PASS", "f", "không thấy dữ liệu nhạy cảm ngoài allowlist")


def check_3skill(rep, root, skills):
    targets = [root / s for s in skills] + [root / "README.md", root / "shared"]
    found = False
    for base in targets:
        if not base.exists():
            continue
        for p in iter_text_files(base):
            t = read(p) or ""
            for i, line in enumerate(t.splitlines(), 1):
                if RE_3SKILL.search(line):
                    found = True
                    rep.add("FAIL", "g", f"{p.relative_to(root).as_posix()}:{i} còn chuỗi '3 skill'")
    if not found:
        rep.add("PASS", "g", "không còn '3 skill'")


def check_sizes(rep, root, skills, baseline):
    for s in skills:
        cur = root / s / "SKILL.md"
        if not cur.is_file():
            continue
        c = len((read(cur) or "").splitlines())
        if baseline and (baseline / s / "SKILL.md").is_file():
            b = len((read(baseline / s / "SKILL.md") or "").splitlines())
            lvl = "WARN" if c > b else "PASS"
            rep.add(lvl, "h", f"{s}/SKILL.md {c} dòng (baseline {b}, {c - b:+d})")
        else:
            rep.add("PASS", "h", f"{s}/SKILL.md {c} dòng")


def run(root=ROOT, baseline=None, allowlist=None):
    root = Path(root).resolve()
    baseline = Path(baseline).resolve() if baseline else None
    skills = [s for s in SKILLS if (root / s / "SKILL.md").is_file()]
    rep = Report()
    if baseline and not baseline.is_dir():
        rep.add("FAIL", "-", f"không thấy thư mục baseline {baseline}")
        baseline = None
    allow = load_allowlist(allowlist)
    check_fast_path(rep, root, skills)
    check_phrases(rep, root, skills, baseline)
    check_review(rep, root, skills, baseline)
    check_sync(rep, root, skills)
    check_paths(rep, root, skills)
    check_sensitive(rep, root, allow)
    check_3skill(rep, root, skills)
    check_sizes(rep, root, skills, baseline)
    print(f"RESULT {'FAIL' if rep.fails else 'PASS'} ({rep.fails} FAIL)")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--baseline-dir")
    ap.add_argument("--allowlist", help="mặc định tools/sensitive_allowlist.json")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rep = run(a.root, a.baseline_dir, a.allowlist)
    return 1 if rep.fails else 0


if __name__ == "__main__":
    sys.exit(main())
