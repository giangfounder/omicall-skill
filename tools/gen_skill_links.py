"""Sinh các khối dùng chung từ shared/skill-graph.json (nguồn duy nhất) vào tài liệu skill.

  python tools/gen_skill_links.py                # ghi/cập nhật mọi khối
  python tools/gen_skill_links.py --check        # chỉ kiểm: exit 1 khi khối thiếu/lệch hoặc cạnh trỏ skill không tồn tại
  python tools/gen_skill_links.py --dry-run      # in file sẽ ghi, không ghi
  python tools/gen_skill_links.py --root <repo>  # mặc định: thư mục cha của tools/

Khối sinh ra:
  1. Mọi SKILL.md, đoạn từ '## Bước bắt buộc: cập nhật skill' tới trước '## Đường nhanh': bước cập nhật skill
     (phiên bản dự phòng lấy từ VERSION), dòng "Chế độ subagent / hỏi đáp" (khoá `modes`) và, với skill không phải
     cửa vào, mục '## Bắt đầu và cách trao đổi (BẮT BUỘC)'.
  2. Mọi SKILL.md, giữa dấu skill-links: mục 'Gọi skill liên quan' (khoá `edges`; thứ tự ngắn từ `waves`).
     Chưa có thì chèn ngay sau mục '## Tư duy chức năng'.
  3. omicall-assistant/references/orchestration.md, giữa <!-- gen:waves -->: bảng đợt kèm cổng (khoá `waves`, `gates`).
  4. omicall-assistant/references/plan-and-approval.md, giữa <!-- gen:gates -->: quy tắc duyệt và danh sách cổng
     (khoá `approval`, `gates`).
  5. shared/references/parallel.md, giữa <!-- gen:modes --> và <!-- gen:cam -->: chế độ subagent/hỏi đáp, danh sách
     CẤM và mẫu giao việc (khoá `modes`, `cam_subagent`, `mau_giao_viec`). Sau khi ghi phải chạy
     `python tools/sync_shared.py` để chép parallel.md sang các skill.
Không gọi mạng. Ghi giữ kiểu xuống dòng của file.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START = "<!-- skill-links:start (sinh từ shared/skill-graph.json bằng tools/gen_skill_links.py, đừng sửa tay) -->"
END = "<!-- skill-links:end -->"
ANCHOR = "## Tư duy chức năng"
H_UPDATE = "## Bước bắt buộc: cập nhật skill"
H_START = "## Bắt đầu và cách trao đổi (BẮT BUỘC)"
H_FAST = "## Đường nhanh"

HEAD = """## Gọi skill liên quan (tự động khi bài toán chạm tới)
Mắt xích thuộc skill khác (xem `references/system-model.md`) thì không tự làm theo trí nhớ: gọi skill đó rồi quay lại.
1. **Gọi**: công cụ Skill với đúng tên bên dưới; client không có thì đọc `<thư mục skill>/../<tên skill>/SKILL.md`. Chỉ làm đúng phần của mắt xích đó.
2. **Dùng chung**, không làm lại: domain, đăng nhập, `tenant_context.json` (chỉ đọc), `manifest.py`. Việc ghi vẫn chờ user duyệt như skill đích quy định.
3. **Trả lại**: ghi id/mã vừa tạo bằng `manifest.py set` (giá trị nền: `ctx-set`), rồi tiếp tục skill đang làm. Thứ tự khi cần nhiều phần: {order}.

| Khi gặp | Gọi skill |
|---|---|
"""
HEAD_ENTRY = """## Gọi skill liên quan
Gọi bằng công cụ Skill theo bảng; thứ tự đợt và cổng: `references/orchestration.md` mục 2.

| Khi gặp | Gọi skill |
|---|---|
"""

UPDATE = ('Chạy `python "<thư mục skill>/scripts/self_update.py"` trước mọi bước khác, 1 lần/phiên (đã chạy rồi, '
          'kể cả ở skill khác, thì bỏ qua). Câu đầu tiên: '
          '`Đang dùng {name} v<phiên bản>` (dòng `SKILL_VERSION`; script lỗi thì dùng v{ver}). '
          'Script báo **SKILL.md đã thay đổi** → đọc lại từ đĩa rồi làm tiếp. Không cập nhật được → '
          'báo lý do, làm tiếp bằng bản hiện có; không sửa, xoá hay commit trong thư mục skill.')
UPDATE_ENTRY = ('Chạy `python "<thư mục skill>/scripts/self_update.py"` 1 lần/phiên, trước mọi bước khác. Câu đầu: '
                '`Đang dùng {name} v<phiên bản>` (dòng `SKILL_VERSION`; lỗi thì dùng v{ver}). Không cập nhật được '
                '→ báo lý do, làm tiếp.')
CONVERSATION = """Làm theo `references/conversation.md`, chung cho mọi skill OMI:
- Mục 1: hỏi domain → `python "<thư mục skill>/scripts/omi_login.py" ensure --domain <domain>` → `"need":"setup"` thì mở form cục bộ `omi_login.py setup --ui` trong agent (cách duy nhất; dự phòng: `references/omi-mcp.md` mục 2a). Không nhận mật khẩu qua chat, không gõ hay đọc form.
- Mục 2–6: khung 5 bước, cách hỏi lại, mẫu câu, lời thường, ít chụp ảnh."""

ORCH = Path("omicall-assistant") / "references" / "orchestration.md"
PLAN = Path("omicall-assistant") / "references" / "plan-and-approval.md"
PARALLEL = Path("shared") / "references" / "parallel.md"


def load(root=ROOT):
    return json.loads((Path(root) / "shared" / "skill-graph.json").read_text(encoding="utf-8"))


def skills(root=ROOT):
    return sorted(p.parent.name for p in Path(root).glob("*/SKILL.md"))


def gate_names(g):
    return {x["id"]: x["ten"] for x in g.get("gates", [])}


# ---------- khối trong SKILL.md ----------

def short_order(g):
    return " → ".join(w["ngan"] for w in g.get("waves", []) if w.get("ngan"))


def mode_line(g):
    who = " hoặc ".join(m["ngan"] for m in g.get("modes", []))
    return "**Chế độ subagent / hỏi đáp**: %s → bỏ qua bước này, hỏi domain, khảo sát (`parallel.md` mục 1)." % who


def links_block(g, skill):
    rows = []
    for e in g["edges"]:
        if e["from"] != skill:
            continue
        rows.append(f"| {e['when']} | `{e['to']}` |")  # cổng của cạnh (can_cong) ghi ở orchestration.md mục 2
    head = HEAD_ENTRY if skill in g.get("entry", []) else HEAD.format(order=short_order(g))
    return START + "\n" + head + "\n".join(rows) + "\n" + END + "\n\n"


def start_block(g, skill, version):
    entry = skill in g.get("entry", [])
    upd = (UPDATE_ENTRY if entry else UPDATE).format(name=skill, ver=version)
    out = H_UPDATE + "\n" + upd + "\n" + mode_line(g) + "\n\n"
    if not entry:
        out += H_START + "\n" + CONVERSATION + "\n\n"
    return out


def apply_links(text, new_block, nl):
    nb = new_block.replace("\n", nl)
    m = re.search(re.escape(START) + r".*?" + re.escape(END) + r"(\r?\n){1,2}", text, re.S)
    if m:
        return text[:m.start()] + nb + text[m.end():]
    a = text.find(ANCHOR)
    if a < 0:
        raise ValueError("thiếu mục '%s' để chèn" % ANCHOR)
    nxt = re.search(r"(?m)^## ", text[a + 3:])
    pos = a + 3 + nxt.start() if nxt else len(text)
    return text[:pos] + nb + text[pos:]


def apply_start(text, new_block, nl):
    """Thay đoạn từ '## Bước bắt buộc: cập nhật skill' tới ngay trước '## Đường nhanh'."""
    nb = new_block.replace("\n", nl)
    m = re.search(r"(?m)^" + re.escape(H_UPDATE) + r"[ \t]*\r?$", text)
    if not m:
        raise ValueError("thiếu mục '%s'" % H_UPDATE)
    f = re.search(r"(?m)^" + re.escape(H_FAST) + r"[ \t]*\r?$", text[m.end():])
    if not f:
        raise ValueError("thiếu mục '%s' sau '%s'" % (H_FAST, H_UPDATE))
    region = text[m.end():m.end() + f.start()]
    extra = [h.strip() for h in re.findall(r"(?m)^## .*$", region) if h.strip() != H_START]
    if extra:  # không xoá im lặng phần người khác thêm vào giữa hai mục
        raise ValueError("có mục lạ giữa '%s' và '%s': %s (chuyển đi trước khi sinh)" % (H_UPDATE, H_FAST, extra))
    return text[:m.start()] + nb + text[m.end() + f.start():]


# ---------- khối trong tài liệu điều phối ----------

def marker(name):
    return "<!-- gen:%s (sinh từ shared/skill-graph.json bằng tools/gen_skill_links.py, đừng sửa tay) -->" % name, \
           "<!-- /gen:%s -->" % name


def apply_marked(text, name, body, nl):
    s, e = marker(name)
    m = re.search(re.escape(s) + r".*?" + re.escape(e), text, re.S)
    if not m:
        raise ValueError("thiếu dấu khối gen:%s" % name)
    nb = (s + "\n" + body.rstrip("\n") + "\n" + e).replace("\n", nl)
    return text[:m.start()] + nb + text[m.end():]


def waves_block(g):
    names = gate_names(g)
    out = ["| Đợt | Ai làm | Việc | Song song? | Cổng user |", "|---|---|---|---|---|"]
    for w in g.get("waves", []):
        if "gate" in w:
            out.append("| ⛔ | **User** | **%s** | Không | `%s` |" % (names[w["gate"]], w["gate"]))
            continue
        gates = ", ".join("`%s`" % c for c in w.get("cong", [])) or "—"
        out.append("| %s | %s | %s | %s | %s |" % (w["dot"], w["ai"], w["viec"], w["song_song"], gates))
    out.append("")
    out.append("Thứ tự ngắn: %s." % short_order(g))
    for e in g["edges"]:
        if e.get("can_cong"):
            out.append("- `%s` → `%s`: chỉ dùng kết quả sau cổng **%s**." % (e["from"], e["to"], names[e["can_cong"]]))
    for c in g.get("can_xac_nhan", []):
        out.append("- Cần xác nhận: " + c)
    return "\n".join(out)


def gates_block(g):
    out = ["**Quy tắc duyệt** (một nguồn: `shared/skill-graph.json`):"]
    out += ["- " + a for a in g.get("approval", [])]
    out += ["", "| Cổng | Tên | Phạm vi |", "|---|---|---|"]
    out += ["| `%s` | %s | %s |" % (x["id"], x["ten"], x["pham_vi"]) for x in g.get("gates", [])]
    return "\n".join(out)


def modes_block(g):
    out = ["**Chế độ subagent / hỏi đáp** (khối \"Bước bắt buộc\" trong SKILL.md trỏ về đây):"]
    for m in g.get("modes", []):
        out.append("- **%s** (%s): bỏ qua %s; dùng %s." % (m["ten"], m["khi"], m["bo_qua"], m["dung"]))
    return "\n".join(out)


def cam_block(g):
    cam = ", ".join(g.get("cam_subagent", []))
    out = ["**CẤM cho subagent** (danh sách duy nhất; mọi chỗ khác trỏ về đây): " + cam + ".", "",
           "**Mẫu giao việc** (dán vào lời giao việc, điền phần trong `<>`; phần chung để ở `<scratch>/brief_common.md`):",
           "```"]
    out += [l.replace("{cam}", cam) for l in g.get("mau_giao_viec", [])]
    out.append("```")
    return "\n".join(out)


# ---------- chạy ----------

def plan(root=ROOT):
    """Trả (đường dẫn, nội dung cũ, nội dung mới) cho mọi file có khối sinh, và danh sách lỗi."""
    root = Path(root)
    g = load(root)
    names = set(skills(root))
    errs, out = [], []
    for e in g["edges"]:
        for k in ("from", "to"):
            if e[k] not in names:
                errs.append("cạnh trỏ skill không tồn tại: %s" % e[k])
        if e["from"] == e["to"]:
            errs.append("cạnh tự trỏ: %s" % e["from"])
        if e.get("can_cong") and e["can_cong"] not in gate_names(g):
            errs.append("cạnh %s→%s trỏ cổng không có: %s" % (e["from"], e["to"], e["can_cong"]))
    for w in g.get("waves", []):
        for c in ([w["gate"]] if "gate" in w else w.get("cong", [])):
            if c not in gate_names(g):
                errs.append("đợt trỏ cổng không có: %s" % c)
    for s in sorted(names):
        p = root / s / "SKILL.md"
        raw = p.read_text(encoding="utf-8")
        nl = "\r\n" if "\r\n" in raw else "\n"
        ver = (root / s / "VERSION").read_text(encoding="utf-8").strip() if (root / s / "VERSION").is_file() else "0.0.0"
        try:
            new = apply_start(raw, start_block(g, s, ver), nl)
            new = apply_links(new, links_block(g, s), nl)
        except ValueError as ex:
            errs.append("%s/SKILL.md: %s" % (s, ex))
            continue
        out.append((p, raw, new))
    docs = [(ORCH, [("waves", waves_block(g))]),
            (PLAN, [("gates", gates_block(g))]),
            (PARALLEL, [("modes", modes_block(g)), ("cam", cam_block(g))])]
    for rel, blocks in docs:
        p = root / rel
        if not p.is_file():
            errs.append("thiếu %s" % rel.as_posix())
            continue
        raw = p.read_text(encoding="utf-8")
        nl = "\r\n" if "\r\n" in raw else "\n"
        new = raw
        try:
            for name, body in blocks:
                new = apply_marked(new, name, body, nl)
        except ValueError as ex:
            errs.append("%s: %s" % (rel.as_posix(), ex))
            continue
        out.append((p, raw, new))
    return out, errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default=str(ROOT))
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    root = Path(a.root).resolve()
    files, errs = plan(root)
    changed = [(p, new) for p, raw, new in files if new != raw]
    for p, new in changed:
        rel = p.relative_to(root).as_posix()
        if a.check:
            errs.append("%s: khối sinh thiếu hoặc lệch skill-graph.json" % rel)
        elif a.dry_run:
            print("SẼ GHI", rel)
        else:
            p.write_text(new, encoding="utf-8", newline="")
            print("GHI", rel)
    for e in errs:
        print("FAIL", e)
    if a.check and not errs:
        print("PASS khối sinh khớp skill-graph.json ở %d file" % len(files))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
