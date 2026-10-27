"""Cập nhật skill OMI lên bản mới nhất trước khi dùng (file dùng chung cho mọi skill trong repo omicall-skill).

  python <thư mục skill>/scripts/self_update.py [--force]

- Skill nằm trong bản git clone (cài theo README bằng junction/symlink): `git pull --ff-only`, báo phiên bản cũ → mới
  và nhắc ĐỌC LẠI SKILL.md nếu file này vừa đổi (nội dung agent đã nạp là bản cũ).
- Skill không phải git clone (chép tay): so `VERSION` với bản trên GitHub, báo nếu có bản mới và cách cập nhật.
- Không cập nhật được (mất mạng, có sửa đổi chưa commit...): báo lý do, vẫn cho làm tiếp với bản hiện có.
- Đã kiểm tra thành công trong 6 giờ gần nhất: bỏ qua, không gọi mạng (thêm `--force` để kiểm tra lại).
Không sửa, xoá hay commit gì trong thư mục skill. Dòng cuối luôn là `SKILL_VERSION=<tên skill> <phiên bản>`.
`--help` chỉ in hướng dẫn (không gọi git hay mạng); tham số lạ -> exit 2; thư mục không có VERSION (ví dụ shared/) -> exit 2.
"""
import argparse
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = "https://github.com/giangfounder/omicall-skill"
RAW = "https://raw.githubusercontent.com/giangfounder/omicall-skill/main"
SKILL_DIR = Path(__file__).resolve().parent.parent
NAME = SKILL_DIR.name
STAMP = Path.home() / ".cache" / "omicall-skill" / f"{NAME}.last"  # ngoài thư mục skill để không bẩn git
TTL = 6 * 3600


def run(args, timeout=60):
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def version():
    f = SKILL_DIR / "VERSION"
    return f.read_text(encoding="utf-8").strip() if f.exists() else "chưa có"


def as_tuple(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="kiểm tra lại dù vừa kiểm trong 6 giờ")
    a = ap.parse_args(argv)  # --help -> in hướng dẫn, exit 0; tham số lạ -> exit 2 (không gọi git hay mạng)
    if not (SKILL_DIR / "VERSION").is_file():
        print(f"DỪNG: {SKILL_DIR} không có file VERSION — không phải thư mục skill (ví dụ shared/ là nguồn dùng chung). "
              "Chạy bản trong thư mục skill: <thư mục skill>/scripts/self_update.py")
        return 2
    old = version()
    if not a.force and recently_checked():
        print(f"{NAME} đã kiểm tra cập nhật lúc {time.strftime('%H:%M', time.localtime(STAMP.stat().st_mtime))} (dưới 6 giờ) — bỏ qua.")
        print(f"SKILL_VERSION={NAME} {old}")
        return
    code, top, _ = run(["git", "-C", str(SKILL_DIR), "rev-parse", "--show-toplevel"], 15)
    if code == 0 and top:
        _, before, _ = run(["git", "-C", top, "rev-parse", "HEAD"], 15)
        code, out, err = run(["git", "-C", top, "pull", "--ff-only", "--quiet"], 90)
        _, after, _ = run(["git", "-C", top, "rev-parse", "HEAD"], 15)
        new = version()
        if code != 0:
            print(f"KHÔNG CẬP NHẬT ĐƯỢC {NAME} (đang dùng {old}): {err or out}")
            print("Báo user lý do (mất mạng, sửa đổi chưa commit trong repo skill, nhánh lệch...) rồi làm tiếp với bản hiện có."
                  " Không tự sửa/xoá/commit trong thư mục skill.")
        elif before != after:
            _, changed, _ = run(["git", "-C", top, "diff", "--name-only", before, after], 15)
            mine = [c for c in changed.splitlines() if c.startswith(NAME + "/")]
            print(f"ĐÃ CẬP NHẬT {NAME}: {old} -> {new} ({len(mine)} file của skill thay đổi)")
            if f"{NAME}/SKILL.md" in mine:
                print(f"SKILL.md ĐÃ THAY ĐỔI: đọc lại {SKILL_DIR / 'SKILL.md'} từ đĩa trước khi làm tiếp (bản đã nạp là bản cũ).")
            refs = [c for c in mine if "/references/" in c or "/scripts/" in c]
            if refs:
                print("File tham chiếu/script đổi: " + ", ".join(refs))
            print(f"Xem thay đổi: {Path(top) / 'CHANGELOG.md'}")
        else:
            print(f"{NAME} đang ở bản mới nhất: {new}")
        if code == 0:
            mark_checked()
    else:
        remote = remote_version()
        if remote is None:
            print(f"Không kiểm tra được bản mới (không phải git clone, không tải được VERSION từ GitHub). Đang dùng {NAME} {old}.")
        elif as_tuple(remote) > as_tuple(old):
            print(f"CÓ BẢN MỚI {NAME} {remote} (đang dùng {old}). Thư mục này không phải git clone nên không tự kéo được.")
            print(f"Báo user cập nhật: git clone {REPO} (hoặc git pull trong bản clone) rồi trỏ thư mục skill vào repo theo README;"
                  " sau đó gọi lại skill. Nếu user muốn làm tiếp ngay thì dùng bản hiện có.")
        elif as_tuple(remote) < as_tuple(old):
            print(f"{NAME} trên máy ({old}) mới hơn GitHub ({remote}) — bản gốc đang chỉnh, chưa đẩy lên.")
        else:
            print(f"{NAME} đang ở bản mới nhất: {old}")
        if remote is not None:
            mark_checked()
    print(f"SKILL_VERSION={NAME} {version()}")


if __name__ == "__main__":
    sys.exit(main())
