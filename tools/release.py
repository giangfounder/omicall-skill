"""Phát hành phiên bản mới cho một hoặc nhiều skill: tăng VERSION, ghi CHANGELOG.md, commit, gắn tag.

  python tools/release.py <major|minor|patch> "<ghi chú thay đổi>" <skill ...|--all> [--push]

Ví dụ:
  python tools/release.py minor "Thêm mẫu luồng nhắc lịch" omicall-omiflow
  python tools/release.py patch "Đồng bộ omi-mcp.md" --all --push
Chạy ở gốc repo, sau khi đã sửa nội dung skill (chưa commit). Commit gồm thư mục các skill được nêu + CHANGELOG.md.
Tag dạng `<skill>/v<phiên bản>` (annotated) để `git push --follow-tags` đẩy kèm. Tác giả commit lấy từ git config.
"""
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted(p.parent.name for p in ROOT.glob("*/SKILL.md"))


def git(*args):
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(f"git {' '.join(args)} lỗi: {r.stderr.strip()}")
    return r.stdout.strip()


def bump(v, part):
    a, b, c = (int(x) for x in v.split("."))
    return {"major": f"{a + 1}.0.0", "minor": f"{a}.{b + 1}.0", "patch": f"{a}.{b}.{c + 1}"}[part]


def main():
    args = sys.argv[1:]
    push = "--push" in args
    args = [a for a in args if a != "--push"]
    if len(args) < 3 or args[0] not in ("major", "minor", "patch"):
        sys.exit(__doc__)
    part, note, targets = args[0], args[1].replace("|", "/"), args[2:]
    targets = SKILLS if targets == ["--all"] else targets
    for t in targets:
        if t not in SKILLS:
            sys.exit(f"Không có skill '{t}'. Có: {', '.join(SKILLS)}")
    ident = subprocess.run(["git", "-C", str(ROOT), "var", "GIT_AUTHOR_IDENT"], capture_output=True, text=True)
    if ident.returncode:
        sys.exit("Chưa có tên tác giả git. Đặt trước: git config user.name \"<Tên>\" && git config user.email <email>"
                 " (hoặc biến GIT_AUTHOR_NAME/GIT_AUTHOR_EMAIL/GIT_COMMITTER_NAME/GIT_COMMITTER_EMAIL), rồi chạy lại.")
    today = datetime.date.today().isoformat()
    cl = ROOT / "CHANGELOG.md"
    text = cl.read_text(encoding="utf-8")
    released = []
    for t in targets:
        vf = ROOT / t / "VERSION"
        old = vf.read_text(encoding="utf-8").strip() if vf.exists() else "0.0.0"
        new = bump(old, part)
        vf.write_text(new + "\n", encoding="utf-8")
        # version hiển thị trong mô tả skill (danh sách /) và bước bắt buộc
        sk = ROOT / t / "SKILL.md"
        s = sk.read_text(encoding="utf-8")
        s, k1 = re.subn(r"\[v\d+\.\d+\.\d+\]", f"[v{new}]", s, count=1)
        s = re.sub(r"(Phiên bản skill: \*\*v)\d+\.\d+\.\d+(\*\*)", rf"\g<1>{new}\g<2>", s)
        s = re.sub(r"(dùng v)\d+\.\d+\.\d+(\))", rf"\g<1>{new}\g<2>", s)
        if not k1:
            print(f"CẢNH BÁO: {t}/SKILL.md chưa có [vX.Y.Z] trong mô tả — thêm tay đầu dòng description")
        sk.write_text(s, encoding="utf-8")
        row = f"| {new} | {today} | tag `{t}/v{new}` | {note} |\n"
        m = re.search(rf"## {re.escape(t)}\n\| Phiên bản .*?\n\|---.*?\n", text)
        if m:
            text = text[:m.end()] + row + text[m.end():]
        else:
            text += f"\n## {t}\n| Phiên bản | Ngày | Commit | Thay đổi |\n|---|---|---|---|\n{row}"
        released.append((t, old, new))
    cl.write_text(text, encoding="utf-8")
    git("add", "CHANGELOG.md", *targets)
    msg = "; ".join(f"{t} v{new}" for t, _, new in released) + f": {note}"
    git("commit", "-q", "-m", msg)
    for t, old, new in released:
        git("tag", "-a", f"{t}/v{new}", "-m", f"{t} {new}: {note}")
        print(f"{t}: {old} -> {new}  (tag {t}/v{new})")
    if push:
        git("push", "--follow-tags", "origin", "HEAD")
        print("Đã push kèm tag.")
    else:
        print("Chưa push. Đẩy lên: git push --follow-tags origin main")


if __name__ == "__main__":
    main()
