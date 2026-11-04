"""Cập nhật TOÀN BỘ bộ skill OMI (cả repo omicall-skill) trước khi dùng — gọi một skill là cập nhật mọi skill.

  python <thư mục skill>/scripts/self_update.py [--force]

- Skill nằm trong bản git clone (cài theo README bằng junction/symlink): `git pull --ff-only` cả repo, báo mọi skill
  vừa đổi phiên bản và nhắc ĐỌC LẠI SKILL.md nếu file của skill đang gọi vừa đổi (nội dung agent đã nạp là bản cũ).
- Skill chép tay (không phải git clone): tự clone cả repo về `~/omicall-skill` (đã có thì pull), rồi thay từng thư mục
  chép tay bằng junction/symlink trỏ vào bản clone; thư mục cũ được CHUYỂN sang `~/.cache/omicall-skill/backup/`, không xoá.
  Máy không có git: chỉ so `VERSION` với GitHub và báo nếu có bản mới.
- Skill mới trong repo: tự tạo junction/symlink trong mọi thư mục skill của agent đang trỏ vào bản clone
  (`~/.claude/skills`, `~/.agents/skills`, `~/.gemini/skills`, `~/.codex/skills`, thư mục chứa skill đang gọi).
  Agent chỉ thấy skill mới khi mở phiên mới. Đường dẫn trỏ vào thư mục không còn tồn tại: chỉ cảnh báo, không xoá.
- Không cập nhật được (mất mạng, có sửa đổi chưa commit...): báo lý do, vẫn cho làm tiếp với bản hiện có.
- Bất kỳ skill OMI nào đã kiểm tra thành công trong 1 giờ gần nhất: bỏ qua, không gọi mạng (thêm `--force` để kiểm tra lại).
Không sửa nội dung, không commit trong repo skill. Dòng cuối luôn là `SKILL_VERSION=<tên skill> <phiên bản>`.
`--help` chỉ in hướng dẫn (không gọi git hay mạng); tham số lạ -> exit 2; thư mục không có VERSION (ví dụ shared/) -> exit 2.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = "https://github.com/giangfounder/omicall-skill"
RAW = "https://raw.githubusercontent.com/giangfounder/omicall-skill/main"
SKILL_DIR = Path(__file__).resolve().parent.parent
NAME = SKILL_DIR.name
CACHE = Path.home() / ".cache" / "omicall-skill"
STAMP = CACHE / "all.last"  # ngoài thư mục skill để không bẩn git; một dấu chung vì một lần pull cập nhật mọi skill
TTL = 3600
CLONE_HOME = Path.home() / "omicall-skill"  # nơi tự clone khi skill đang là bản chép tay
PREFIX = "omicall-"


def run(args, timeout=60):
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def read_version(d):
    f = Path(d) / "VERSION"
    try:
        return f.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def version():
    return read_version(SKILL_DIR) or "chưa có"


def as_tuple(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0,)


def remote_version():
    try:
        with urllib.request.urlopen(f"{RAW}/{NAME}/VERSION", timeout=8) as r:
            return r.read().decode("utf-8").strip()
    except Exception:
        return None


def recently_checked():
    try:
        return time.time() - STAMP.stat().st_mtime < TTL
    except OSError:
        return False


def mark_checked():
    try:
        STAMP.parent.mkdir(parents=True, exist_ok=True)
        STAMP.touch()
    except OSError:
        pass


def repo_skills(top):
    """{tên skill: phiên bản} của mọi thư mục omicall-* có VERSION trong repo."""
    out = {}
    try:
        for d in sorted(Path(top).iterdir()):
            if d.is_dir() and d.name.startswith(PREFIX):
                v = read_version(d)
                if v:
                    out[d.name] = v
    except OSError:
        pass
    return out


def version_changes(before, after):
    """Danh sách dòng mô tả skill đổi phiên bản, skill mới, skill bị bỏ khỏi repo."""
    lines = []
    for n in sorted(set(before) | set(after)):
        a, b = before.get(n), after.get(n)
        if a and b and a != b:
            lines.append(f"  {n}: {a} -> {b}")
        elif b and not a:
            lines.append(f"  {n}: mới ({b})")
        elif a and not b:
            lines.append(f"  {n}: đã bỏ khỏi repo")
    return lines


def _real(p):
    try:
        return Path(os.path.realpath(p))
    except OSError:
        return Path(p)


def _inside(p, top):
    try:
        _real(p).relative_to(_real(top))
        return True
    except ValueError:
        return False


def is_link(p):
    """Junction (Windows) hoặc symlink."""
    p = Path(p)
    if p.is_symlink():
        return True
    # Python < 3.12 không có os.path.isjunction: thư mục thật thì đường thật = đường thật của cha + tên
    return p.exists() and _real(p) != _real(p.parent) / p.name


def make_link(dst, src):
    dst, src = Path(dst), Path(src)
    if os.name == "nt":
        code, out, err = run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], 30)
        return code == 0, err or out
    try:
        os.symlink(src, dst, target_is_directory=True)
        return True, ""
    except OSError as e:
        return False, str(e)


def agent_dirs(top, extra=()):
    """Thư mục skill của agent đang có ít nhất một skill omicall-* trỏ vào bản clone `top` (bỏ trùng theo đường thật)."""
    cands = [Path.home() / ".claude" / "skills", Path.home() / ".agents" / "skills",
             Path.home() / ".gemini" / "skills", Path.home() / ".codex" / "skills", *map(Path, extra)]
    seen, out = set(), []
    for d in cands:
        if not d.is_dir():
            continue
        key = str(_real(d)).lower()
        if key in seen:
            continue
        try:
            entries = [e for e in d.iterdir() if e.name.startswith(PREFIX)]
        except OSError:
            continue
        if any(_inside(e, top) for e in entries if e.exists()):
            seen.add(key)
            out.append(d)
    return out


def link_skills(top, dirs):
    """Tạo junction/symlink cho skill trong repo chưa có ở thư mục agent; trả (đã thêm, cảnh báo)."""
    added, warns = [], []
    names = repo_skills(top)
    for d in dirs:
        for n in names:
            dst = Path(d) / n
            if dst.exists() or dst.is_symlink():
                continue
            ok, err = make_link(dst, Path(top) / n)
            if ok:
                added.append(f"{dst}")
            else:
                warns.append(f"không tạo được đường dẫn {dst}: {err}")
        try:
            for e in Path(d).iterdir():
                if e.name.startswith(PREFIX) and not e.exists():
                    warns.append(f"{e} trỏ vào thư mục không còn tồn tại (skill đã bỏ hoặc đổi tên) — tự xoá đường dẫn này nếu không dùng")
        except OSError:
            pass
    return added, warns


def replace_copies(top, d):
    """Thư mục chép tay omicall-* trong `d` có bản tương ứng trong repo: chuyển sang backup rồi tạo đường dẫn."""
    done, warns = [], []
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for n in repo_skills(top):
        dst = Path(d) / n
        if not dst.is_dir() or is_link(dst) or _inside(dst, top):
            continue
        bak = CACHE / "backup" / f"{n}-{stamp}"
        try:
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(bak))
        except OSError as e:
            warns.append(f"không chuyển được {dst} sang backup ({e}); giữ bản chép tay")
            continue
        ok, err = make_link(dst, Path(top) / n)
        if ok:
            done.append(f"{dst} (bản cũ: {bak})")
        else:
            try:
                shutil.move(str(bak), str(dst))
            except OSError:
                pass
            warns.append(f"không tạo được đường dẫn {dst}: {err}; đã trả lại bản chép tay")
    return done, warns


def pull(top):
    before_head = run(["git", "-C", str(top), "rev-parse", "HEAD"], 15)[1]
    before = repo_skills(top)
    code, out, err = run(["git", "-C", str(top), "pull", "--ff-only", "--quiet"], 90)
    after_head = run(["git", "-C", str(top), "rev-parse", "HEAD"], 15)[1]
    changed = []
    if code == 0 and before_head != after_head:
        changed = run(["git", "-C", str(top), "diff", "--name-only", before_head, after_head], 15)[1].splitlines()
    return code, err or out, before, repo_skills(top), changed


def report(before, after, changed, top):
    lines = version_changes(before, after)
    if lines:
        print("ĐÃ CẬP NHẬT bộ skill OMI:")
        print("\n".join(lines))
        print(f"Xem thay đổi: {Path(top) / 'CHANGELOG.md'}")
    elif changed:
        print(f"Đã kéo bản mới của repo ({len(changed)} file đổi, không skill nào đổi phiên bản).")
    else:
        print(f"Bộ skill OMI đang ở bản mới nhất ({NAME} {after.get(NAME, version())}).")
    if f"{NAME}/SKILL.md" in changed:
        print(f"SKILL.md ĐÃ THAY ĐỔI: đọc lại {SKILL_DIR / 'SKILL.md'} từ đĩa trước khi làm tiếp (bản đã nạp là bản cũ).")
    mine = [c for c in changed if c.startswith(NAME + "/") and ("/references/" in c or "/scripts/" in c)]
    if mine:
        print("File tham chiếu/script của skill này đổi: " + ", ".join(mine))


def report_links(added, warns):
    if added:
        print("ĐÃ THÊM SKILL vào thư mục của agent (mở phiên mới để dùng):")
        print("\n".join("  " + a for a in added))
    for w in warns:
        print("CẢNH BÁO: " + w)


def update_clone(top):
    code, msg, before, after, changed = pull(top)
    if code != 0:
        print(f"KHÔNG CẬP NHẬT ĐƯỢC bộ skill OMI (đang dùng {NAME} {version()}): {msg}")
        print("Báo user lý do (mất mạng, sửa đổi chưa commit trong repo skill, nhánh lệch...) rồi làm tiếp với bản hiện có."
              " Không tự sửa/xoá/commit trong thư mục skill.")
    else:
        report(before, after, changed, top)
    # vẫn nối skill còn thiếu dù pull lỗi (repo có thể đã có skill mới từ lần pull trước)
    report_links(*link_skills(top, agent_dirs(top)))
    return code == 0


def adopt_copy():
    """Skill chép tay: clone (hoặc pull) cả repo vào CLONE_HOME rồi thay bản chép tay bằng đường dẫn."""
    if run(["git", "--version"], 15)[0] != 0:
        return None  # không có git -> để nhánh báo phiên bản xử lý
    if (CLONE_HOME / ".git").exists():
        top = CLONE_HOME
        code, msg, before, after, changed = pull(top)
        if code != 0:
            print(f"KHÔNG CẬP NHẬT ĐƯỢC bản clone {top}: {msg}. Làm tiếp với bản hiện có.")
            return False
        report(before, after, changed, top)
    elif CLONE_HOME.exists():
        print(f"{CLONE_HOME} đã có nhưng không phải git clone — không đụng tới. Báo user tự cài theo README ({REPO}).")
        return False
    else:
        code, out, err = run(["git", "clone", "--quiet", REPO + ".git", str(CLONE_HOME)], 300)
        if code != 0:
            print(f"KHÔNG CLONE ĐƯỢC {REPO}: {err or out}. Làm tiếp với bản chép tay hiện có.")
            return False
        print(f"Đã tải toàn bộ bộ skill OMI về {CLONE_HOME}.")
    old = version()
    d = SKILL_DIR.parent
    done, warns = replace_copies(CLONE_HOME, d)
    added, warns2 = link_skills(CLONE_HOME, agent_dirs(CLONE_HOME, extra=[d]))
    if done:
        print("ĐÃ CHUYỂN skill chép tay sang bản git clone (tự cập nhật từ nay):")
        print("\n".join("  " + x for x in done))
    report_links(added, warns + warns2)
    new = read_version(CLONE_HOME / NAME)
    if new and new != old:
        print(f"{NAME}: {old} -> {new}. SKILL.md ĐÃ THAY ĐỔI: đọc lại {d / NAME / 'SKILL.md'} từ đĩa trước khi làm tiếp.")
    return True


def report_remote_only():
    old = version()
    remote = remote_version()
    if remote is None:
        print(f"Không kiểm tra được bản mới (không có git, không tải được VERSION từ GitHub). Đang dùng {NAME} {old}.")
    elif as_tuple(remote) > as_tuple(old):
        print(f"CÓ BẢN MỚI {NAME} {remote} (đang dùng {old}). Máy chưa có git nên không tự kéo được.")
        print(f"Báo user cài git rồi gọi lại skill (skill sẽ tự clone {REPO}), hoặc cài theo README."
              " Nếu user muốn làm tiếp ngay thì dùng bản hiện có.")
    elif as_tuple(remote) < as_tuple(old):
        print(f"{NAME} trên máy ({old}) mới hơn GitHub ({remote}) — bản gốc đang chỉnh, chưa đẩy lên.")
    else:
        print(f"{NAME} đang ở bản mới nhất: {old}")
    return remote is not None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="kiểm tra lại dù vừa kiểm trong 1 giờ")
    a = ap.parse_args(argv)  # --help -> in hướng dẫn, exit 0; tham số lạ -> exit 2 (không gọi git hay mạng)
    if not (SKILL_DIR / "VERSION").is_file():
        print(f"DỪNG: {SKILL_DIR} không có file VERSION — không phải thư mục skill (ví dụ shared/ là nguồn dùng chung). "
              "Chạy bản trong thư mục skill: <thư mục skill>/scripts/self_update.py")
        return 2
    if not a.force and recently_checked():
        print(f"Bộ skill OMI đã kiểm tra cập nhật lúc {time.strftime('%H:%M', time.localtime(STAMP.stat().st_mtime))} (dưới 1 giờ) — bỏ qua.")
        print(f"SKILL_VERSION={NAME} {version()}")
        return
    code, top, _ = run(["git", "-C", str(SKILL_DIR), "rev-parse", "--show-toplevel"], 15)
    if code == 0 and top:
        ok = update_clone(Path(top))
    else:
        ok = adopt_copy()
        if ok is None:
            ok = report_remote_only()
    if ok:
        mark_checked()
    final = read_version(SKILL_DIR) or read_version(SKILL_DIR.parent / NAME) or "chưa có"
    print(f"SKILL_VERSION={NAME} {final}")


if __name__ == "__main__":
    sys.exit(main())
