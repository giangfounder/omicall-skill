"""Sinh mục 'Gọi skill liên quan' vào mọi SKILL.md từ shared/skill-graph.json (nguồn duy nhất).

  python tools/gen_skill_links.py            # ghi/cập nhật mục trong mọi SKILL.md
  python tools/gen_skill_links.py --check    # chỉ kiểm: exit 1 khi mục thiếu/lệch hoặc cạnh trỏ skill không tồn tại

Mục nằm giữa hai dòng đánh dấu START/END; chưa có thì chèn ngay sau mục '## Tư duy chức năng'.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START = "<!-- skill-links:start (sinh từ shared/skill-graph.json bằng tools/gen_skill_links.py, đừng sửa tay) -->"
END = "<!-- skill-links:end -->"
ANCHOR = "## Tư duy chức năng"

HEAD = """## Gọi skill liên quan (tự động khi bài toán chạm tới)
Mắt xích thuộc skill khác (xem `references/system-model.md`) thì không tự làm theo trí nhớ: gọi skill đó rồi quay lại.
1. **Gọi**: công cụ Skill với đúng tên bên dưới; client không có thì đọc `<thư mục skill>/../<tên skill>/SKILL.md`. Chỉ làm đúng phần của mắt xích đó.
2. **Dùng chung**, không làm lại: domain, đăng nhập, `tenant_context.json`, `manifest.py`. Việc ghi vẫn chờ user duyệt như skill đích quy định.
3. **Trả lại**: ghi id/mã trường/tên vừa tạo vào `tenant_context.json` hoặc manifest, rồi tiếp tục skill đang làm. Thứ tự khi cần nhiều phần: crm-config → ai-insight → pbx-config (nhóm, lời chào) → bot/callbot → omiflow (nháp) → user Xuất bản → pbx-config (gắn hotline/webhook).

| Khi gặp | Gọi skill |
|---|---|
"""


def load():
    return json.loads((ROOT / "shared" / "skill-graph.json").read_text(encoding="utf-8"))["edges"]


def skills():
    return sorted(p.parent.name for p in ROOT.glob("*/SKILL.md"))


def block(skill, edges):
    rows = [f"| {e['when']} | `{e['to']}` |" for e in edges if e["from"] == skill]
    return START + "\n" + HEAD + "\n".join(rows) + "\n" + END + "\n\n"


def apply(text, new_block, nl):
    nb = new_block.replace("\n", nl)
    m = re.search(re.escape(START) + r".*?" + re.escape(END) + r"(\r?\n){1,2}", text, re.S)
    if m:
        return text[:m.start()] + nb + text[m.end():]
    a = text.find(ANCHOR)
    if a < 0:
        raise SystemExit("thiếu mục '%s' để chèn" % ANCHOR)
    nxt = re.search(r"(?m)^## ", text[a + 3:])
    pos = a + 3 + nxt.start() if nxt else len(text)
    return text[:pos] + nb + text[pos:]


def main(check):
    edges = load()
    names = set(skills())
    errs = []
    for e in edges:
        for k in ("from", "to"):
            if e[k] not in names:
                errs.append("cạnh trỏ skill không tồn tại: %s" % e[k])
        if e["from"] == e["to"]:
            errs.append("cạnh tự trỏ: %s" % e["from"])
    for s in sorted(names):
        p = ROOT / s / "SKILL.md"
        raw = p.read_text(encoding="utf-8")
        nl = "\r\n" if "\r\n" in raw else "\n"
        try:
            new = apply(raw, block(s, edges), nl)
        except SystemExit as ex:
            errs.append("%s: %s" % (s, ex))
            continue
        if new != raw:
            if check:
                errs.append("%s/SKILL.md: mục 'Gọi skill liên quan' thiếu hoặc lệch skill-graph.json" % s)
            else:
                p.write_text(new, encoding="utf-8", newline="")
                print("GHI", s)
    for e in errs:
        print("FAIL", e)
    if check and not errs:
        print("PASS skill-links khớp skill-graph.json ở %d skill" % len(names))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv[1:]))
