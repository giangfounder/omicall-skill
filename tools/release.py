"""Phát hành phiên bản mới cho một hoặc nhiều skill: tăng VERSION, ghi CHANGELOG.md, commit, gắn tag.

  python tools/release.py <major|minor|patch> "<ghi chú thay đổi>" <skill ...|--all> [--push]

Ví dụ:
  python tools/release.py minor "Thêm mẫu luồng nhắc lịch" omicall-omiflow
  python tools/release.py patch "Đồng bộ omi-mcp.md" --all --push
Chạy ở gốc repo, sau khi đã sửa nội dung skill (chưa commit). Commit gồm thư mục các skill được nêu + CHANGELOG.md
+ phần hạ tầng chung của repo (INFRA: shared/, tools/, tests/, README.md, .gitignore — mục nào có mới thêm), vì
file dùng chung trong skill được đồng bộ từ shared/ và phải commit cùng nguồn.
Tag dạng `<skill>/v<phiên bản>` (annotated) để `git push --follow-tags` đẩy kèm. Tác giả commit lấy từ git config.

Nhiều máy cùng phát hành (xem README, mục "Đồng bộ giữa nhiều máy"): trước khi tăng VERSION, script kéo bản mới của
GitHub về (`git fetch --tags` rồi `git pull --rebase --autostash`) và dừng nếu tag định tạo đã có trên GitHub hay
nhánh không phải main. Khi `--push` bị từ chối vì máy khác vừa đẩy, script dời commit và tag lên trên bản mới rồi
thử lại một lần; gặp xung đột thì dừng, không bao giờ đẩy ép. Chưa đặt tên và email tác giả thì không phát hành.

Trước khi tăng VERSION, preflight_checks() từ chối phát hành khi:
- file dùng chung lệch shared/ (tools/sync_shared.py --check);
- tools/check_skills.py có FAIL;
- git đang theo dõi một `*/references/credentials.md` ngoài danh sách bản mẫu TEMPLATE_CREDENTIALS,
  hoặc bản mẫu đó có thay đổi chưa commit. Chỉ xét đường dẫn qua git, không mở nội dung file.
"""
import datetime
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted(p.parent.name for p in ROOT.glob("*/SKILL.md"))
# Hạ tầng chung commit kèm mỗi lần phát hành (nguồn file dùng chung, công cụ kiểm, test offline)
INFRA = ("shared", "tools", "tests", "README.md", ".gitignore", ".gitattributes")
# bản mẫu credentials.md (chỉ placeholder) được phép nằm trong repo; mọi đường dẫn credentials.md khác bị từ chối
TEMPLATE_CREDENTIALS = {
    "omicall-callbot-gen-ai/references/credentials.md",
    "omicall-chatbot-gen-ai/references/credentials.md",
}


def preflight_checks(root=None, run=None):
    """Trả về danh sách lỗi (rỗng = được phát hành). Không sửa gì, không đọc credentials.md."""
    root = Path(root) if root else ROOT
    run = run or subprocess.run
    errors = []
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import sync_shared
    buf = []
    if sync_shared.check(root, out=buf.append):
        errors.append("file dùng chung lệch shared/ — chạy python tools/sync_shared.py rồi soát lại:\n  "
                      + "\n  ".join(l for l in buf if l.startswith("FAIL")))
        return errors  # dừng sớm: chưa chạy lệnh git nào
    r = run([sys.executable, "-B", str(Path(__file__).resolve().parent / "check_skills.py"), "--root", str(root)],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        fails = [l for l in (r.stdout or "").splitlines() if l.startswith("FAIL")]
        errors.append("tools/check_skills.py báo FAIL:\n  " + "\n  ".join(fails[:40] or [(r.stderr or "").strip()]))
    r = run(["git", "-C", str(root), "ls-files", "--", "*/references/credentials.md", "references/credentials.md"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
    tracked = [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]
    bad = [t for t in tracked if t not in TEMPLATE_CREDENTIALS]
    if bad:
        errors.append("git đang theo dõi credentials.md ngoài bản mẫu: " + ", ".join(bad))
    for t in sorted(set(tracked) & TEMPLATE_CREDENTIALS):
        d = run(["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", t], capture_output=True, text=True)
        if d.returncode:
            errors.append(f"bản mẫu {t} có thay đổi chưa commit — chỉ được giữ placeholder; soát tay rồi khôi phục")
    return errors


def git(*args):
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(f"git {' '.join(args)} lỗi: {r.stderr.strip()}")
    return r.stdout.strip()


def git_try(*args):
    """Chạy git, trả (mã thoát, đầu ra gộp) thay vì thoát chương trình."""
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout + r.stderr).strip()


def bump(v, part):
    a, b, c = (int(x) for x in v.split("."))
    return {"major": f"{a + 1}.0.0", "minor": f"{a}.{b + 1}.0", "patch": f"{a}.{b}.{c + 1}"}[part]


def author_configured():
    """Cần tên và email đặt rõ (git config hoặc biến môi trường); không nhận tên mặc định kiểu 'EC2 Default User'."""
    name = git_try("config", "--get", "user.name")[1] or os.environ.get("GIT_AUTHOR_NAME", "")
    mail = git_try("config", "--get", "user.email")[1] or os.environ.get("GIT_AUTHOR_EMAIL", "")
    return bool(name and mail)


def sync_with_remote():
    """Kéo bản mới của GitHub về trước khi tăng VERSION. Máy phát hành từ bản cũ sẽ trùng tag hoặc xung đột CHANGELOG."""
    code, branch = git_try("rev-parse", "--abbrev-ref", "HEAD")
    if code or branch != "main":
        sys.exit(f"Chỉ phát hành trên nhánh main (đang ở '{branch}'). Chạy: git switch main")
    code, out = git_try("fetch", "--tags", "--prune", "origin")
    if code:
        sys.exit(f"Không kéo được GitHub (git fetch lỗi):\n{out}\nKiểm tra mạng và token rồi chạy lại.")
    code, out = git_try("pull", "--rebase", "--autostash", "origin", "main")
    if code:
        git_try("rebase", "--abort")
        sys.exit("Không ghép được bản mới của GitHub với thay đổi trên máy này (xung đột):\n" + out
                 + "\nChưa sửa VERSION. Xử lý: git pull --rebase --autostash, sửa các file báo xung đột, "
                   "git add rồi git rebase --continue (hoặc git rebase --abort để huỷ), sau đó chạy lại release.")


def make_tags(released, note):
    for t, old, new in released:
        git("tag", "-a", f"{t}/v{new}", "-m", f"{t} {new}: {note}")
        print(f"{t}: {old} -> {new}  (tag {t}/v{new})")


def push_with_retry(released, note):
    """Đẩy kèm tag. Bị từ chối vì máy khác vừa đẩy: dời commit và tag lên trên bản mới, thử lại một lần. Không đẩy ép."""
    # --atomic: nhánh và tag cùng lên hoặc cùng không lên; bị từ chối ở nhánh thì tag cũng không lên GitHub,
    # nên dời commit rồi gắn lại tag cùng tên không gặp tag mồ côi trên GitHub
    code, out = git_try("push", "--atomic", "--follow-tags", "origin", "HEAD")
    if not code:
        return
    print("Đẩy bị từ chối (máy khác vừa đẩy). Kéo bản mới, dời commit và tag lên trên rồi thử lại một lần...")
    for t, _, new in released:
        git_try("tag", "-d", f"{t}/v{new}")
    git_try("fetch", "--tags", "origin")
    code, out = git_try("pull", "--rebase", "origin", "main")
    if not code:
        taken = [f"{t}/v{new}" for t, _, new in released
                 if git_try("rev-parse", "-q", "--verify", f"refs/tags/{t}/v{new}")[0] == 0]
        if taken:  # máy khác vừa phát hành đúng số phiên bản này: không gắn đè tag của họ
            if git_try("rev-list", "--count", "origin/main..HEAD")[1] == "0":
                sys.exit("Thay đổi của bạn trùng hoàn toàn với bản máy khác vừa phát hành (" + ", ".join(taken)
                         + "), không còn gì để phát hành thêm. Chưa tạo tag nào.")
            sys.exit("Máy khác vừa phát hành cùng số phiên bản: " + ", ".join(taken) + ". Commit của bạn đã nằm trên bản mới nhất "
                     "nhưng chưa có tag và chưa đẩy. Xử lý: git reset --soft HEAD~1; với mỗi skill trùng chạy "
                     "git checkout origin/main -- <skill>/VERSION <skill>/SKILL.md; xoá dòng của bạn trong CHANGELOG.md; "
                     "rồi chạy lại release.py (sẽ tăng lên số kế tiếp).")
    if code:
        git_try("rebase", "--abort")
        sys.exit("Xung đột khi ghép với bản mới của GitHub:\n" + out
                 + "\nCommit phát hành vẫn nằm trên máy này nhưng tag cục bộ đã xoá. Xử lý: git pull --rebase, sửa file "
                   "xung đột (thường là VERSION hoặc CHANGELOG.md), git rebase --continue, rồi gắn lại tag "
                   "`<skill>/v<phiên bản>` và git push --follow-tags origin main. Không dùng --force.")
    make_tags(released, note)
    code, out = git_try("push", "--atomic", "--follow-tags", "origin", "HEAD")
    if code:
        sys.exit("Đẩy vẫn lỗi sau khi kéo bản mới:\n" + out)


def main():
    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):  # chỉ in hướng dẫn, không chạy git
        print(__doc__)
        return 0
    push = "--push" in args
    args = [a for a in args if a != "--push"]
    if len(args) < 3 or args[0] not in ("major", "minor", "patch"):
        sys.exit(__doc__)
    part, note, targets = args[0], args[1].replace("|", "/"), args[2:]
    targets = SKILLS if targets == ["--all"] else targets
    for t in targets:
        if t not in SKILLS:
            sys.exit(f"Không có skill '{t}'. Có: {', '.join(SKILLS)}")
    if not author_configured():
        sys.exit("Chưa đặt tên và email tác giả git (không dùng tên mặc định của máy). Đặt trước: "
                 "git config user.name \"<Tên>\" && git config user.email <email>"
                 " (hoặc biến GIT_AUTHOR_NAME/GIT_AUTHOR_EMAIL/GIT_COMMITTER_NAME/GIT_COMMITTER_EMAIL), rồi chạy lại.")
    sync_with_remote()
    errs = preflight_checks()
    if errs:
        sys.exit("Dừng phát hành (chưa sửa VERSION, chưa chạy git):\n- " + "\n- ".join(errs))
    for t in targets:  # tag đã có (ví dụ máy khác vừa phát hành cùng số) thì dừng trước khi sửa file nào
        vf = ROOT / t / "VERSION"
        nxt = bump(vf.read_text(encoding="utf-8").strip() if vf.exists() else "0.0.0", part)
        if git_try("rev-parse", "-q", "--verify", f"refs/tags/{t}/v{nxt}")[0] == 0:
            sys.exit(f"Tag {t}/v{nxt} đã có. Kiểm tra git log và CHANGELOG.md xem máy khác đã phát hành chưa.")
    today = datetime.date.today().isoformat()
    cl = ROOT / "CHANGELOG.md"
    text = cl.read_text(encoding="utf-8")
    released = []
    for t in targets:
        vf = ROOT / t / "VERSION"
        old = vf.read_text(encoding="utf-8").strip() if vf.exists() else "0.0.0"
        new = bump(old, part)
        vf.write_text(new + "\n", encoding="utf-8", newline="\n")  # giữ LF trên Windows (giới hạn byte SKILL.md)
        # version hiển thị trong mô tả skill (danh sách /) và bước bắt buộc
        sk = ROOT / t / "SKILL.md"
        s = sk.read_text(encoding="utf-8")
        s, k1 = re.subn(r"\[v\d+\.\d+\.\d+\]", f"[v{new}]", s, count=1)
        s = re.sub(r"(Phiên bản skill: \*\*v)\d+\.\d+\.\d+(\*\*)", rf"\g<1>{new}\g<2>", s)
        s = re.sub(r"(dùng v)\d+\.\d+\.\d+(\))", rf"\g<1>{new}\g<2>", s)
        if not k1:
            print(f"CẢNH BÁO: {t}/SKILL.md chưa có [vX.Y.Z] trong mô tả — thêm tay đầu dòng description")
        sk.write_text(s, encoding="utf-8", newline="\n")
        row = f"| {new} | {today} | tag `{t}/v{new}` | {note} |\n"
        m = re.search(rf"## {re.escape(t)}\n\| Phiên bản .*?\n\|---.*?\n", text)
        if m:
            text = text[:m.end()] + row + text[m.end():]
        else:
            text += f"\n## {t}\n| Phiên bản | Ngày | Commit | Thay đổi |\n|---|---|---|---|\n{row}"
        released.append((t, old, new))
    cl.write_text(text, encoding="utf-8", newline="\n")
    infra = [p for p in INFRA if (ROOT / p).exists()]
    git("add", "CHANGELOG.md", *targets, *infra)
    msg = "; ".join(f"{t} v{new}" for t, _, new in released) + f": {note}"
    git("commit", "-q", "-m", msg)
    make_tags(released, note)
    if push:
        push_with_retry(released, note)
        print("Đã push kèm tag.")
    else:
        print("Chưa push. Đẩy lên: git push --follow-tags origin main")


if __name__ == "__main__":
    main()
