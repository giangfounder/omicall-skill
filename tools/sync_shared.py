"""Đồng bộ các file dùng chung từ shared/ sang thư mục từng skill.

  python tools/sync_shared.py              # chép shared/ -> các skill theo bảng MAP
  python tools/sync_shared.py --check      # chỉ so sha256, exit 1 khi lệch hoặc thiếu (nêu đúng file)
  python tools/sync_shared.py --dry-run    # in việc sẽ làm, không ghi
  python tools/sync_shared.py --root <thư mục repo>   # mặc định: thư mục cha của tools/

Nguồn duy nhất là shared/. Muốn sửa file dùng chung thì sửa bản trong shared/ rồi chạy lệnh này;
không sửa trực tiếp bản trong skill (lần đồng bộ sau sẽ ghi đè). Không đụng tới credentials.md.
"""
import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BUILDERS = ["omicall-callbot-gen-ai", "omicall-callbot-flow", "omicall-chatbot-gen-ai", "omicall-omiflow"]
# skill con của omicall-omiflow (cấu hình nền): chỉ nhận phần đăng nhập, gọi API, khảo sát, đọc tài liệu
SUBSKILLS = ["omicall-crm-config", "omicall-pbx-config", "omicall-ai-insight"]
ALL = BUILDERS + SUBSKILLS

# file trong shared/ -> danh sách skill nhận bản chép (cùng đường dẫn tương đối)
MAP = {
    "references/omi-mcp.md": ALL,
    "references/tenant_context.template.json": ALL,
    "scripts/self_update.py": ALL,
    "scripts/omi_session.py": ALL,
    "scripts/omi_preflight.py": ALL,
    "scripts/omi_login.py": ALL,
    "scripts/omi_api.py": ALL,
    "scripts/omi_save.py": BUILDERS,
    "scripts/tenant_survey.py": ALL,
    "scripts/manifest.py": BUILDERS,
    "scripts/extract_text.py": ALL,
    "scripts/extract_template.py": BUILDERS,
    "scripts/config_survey.py": ["omicall-omiflow", "omicall-callbot-gen-ai", "omicall-callbot-flow"] + SUBSKILLS,
    "scripts/cdp.py": ["omicall-callbot-gen-ai", "omicall-chatbot-gen-ai"],
}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check(root=ROOT, out=print):
    """Trả về số lỗi (0 = khớp hết). In một dòng cho mỗi bản chép."""
    root = Path(root)
    errors = 0
    for rel, skills in MAP.items():
        src = root / "shared" / rel
        if not src.is_file():
            out(f"FAIL thiếu nguồn shared/{rel}")
            errors += 1
            continue
        h = sha256(src)
        out(f"SRC  {h[:16]} shared/{rel}")
        for s in skills:
            if not (root / s).is_dir():
                continue
            dst = root / s / rel
            if not dst.is_file():
                out(f"FAIL thiếu {s}/{rel}")
                errors += 1
                continue
            d = sha256(dst)
            if d != h:
                out(f"FAIL lệch {s}/{rel} ({d[:16]} != {h[:16]})")
                errors += 1
            else:
                out(f"OK   {d[:16]} {s}/{rel}")
    return errors


def sync(root=ROOT, dry_run=False, out=print):
    root = Path(root)
    missing = 0
    for rel, skills in MAP.items():
        src = root / "shared" / rel
        if not src.is_file():
            out(f"BỎ QUA shared/{rel} chưa có")
            missing += 1
            continue
        h = sha256(src)
        for s in skills:
            if not (root / s).is_dir():
                continue
            dst = root / s / rel
            if dst.is_file() and sha256(dst) == h:
                continue
            out(f"{'SẼ CHÉP' if dry_run else 'CHÉP'} shared/{rel} -> {s}/{rel}")
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
    return missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default=str(ROOT))
    a = ap.parse_args(argv)
    if a.check:
        n = check(a.root)
        print(f"RESULT {'PASS' if n == 0 else 'FAIL'} ({n} lỗi)")
        return 1 if n else 0
    sync(a.root, dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
