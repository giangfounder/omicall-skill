"""Chạy toàn bộ test offline của repo (unittest, thư viện chuẩn).

  python tools/selftest.py                 # mọi thư mục con trong tests/
  python tools/selftest.py tests/shared    # chỉ một (hoặc vài) thư mục

Môi trường test:
- HOME/USERPROFILE trỏ thư mục tạm (không đụng ~/.omicall-mcp, ~/.cache thật);
- PYTHONDONTWRITEBYTECODE=1, NO_NETWORK=1;
- sitecustomize trong thư mục tạm chặn mọi socket.connect ngoài 127.0.0.1/localhost/::1;
- mỗi thư mục test chạy trong một tiến trình riêng (tránh trùng tên module).
In bảng PASS/FAIL/SKIP, exit 1 khi có FAIL hoặc ERROR. Thiếu thư viện ngoài (requests, openpyxl, python-docx,
pymupdf, websocket-client) thì test liên quan tự SKIP và được liệt kê ở đầu báo cáo.
Sau khi chạy, xoá các thư mục __pycache__ mới sinh trong repo.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
OPTIONAL = {"requests": "requests", "openpyxl": "openpyxl", "python-docx": "docx",
            "pymupdf": "fitz", "websocket-client": "websocket"}

SITECUSTOMIZE = r'''
import os, socket
_ALLOWED = {"127.0.0.1", "localhost", "::1"}
_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex
def _host(addr):
    if isinstance(addr, tuple) and addr:
        return str(addr[0])
    return None
def _guard(addr):
    h = _host(addr)
    if h is not None and h not in _ALLOWED:
        raise OSError("NO_NETWORK: selftest chặn kết nối tới %s" % h)
def connect(self, addr):
    _guard(addr)
    return _orig_connect(self, addr)
def connect_ex(self, addr):
    _guard(addr)
    return _orig_connect_ex(self, addr)
socket.socket.connect = connect
socket.socket.connect_ex = connect_ex
'''


def pycache_dirs():
    return {p for p in ROOT.rglob("__pycache__") if ".git" not in p.parts}


def inner(start):
    """Chạy trong tiến trình con: discover một thư mục, in một dòng JSON cho mỗi test."""
    start = str(Path(start).resolve())
    sys.path.insert(0, start)

    class R(unittest.TextTestResult):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.rows = []

        def addSuccess(self, t):
            super().addSuccess(t)
            self.rows.append((t.id(), "PASS", ""))

        def addFailure(self, t, err):
            super().addFailure(t, err)
            self.rows.append((t.id(), "FAIL", self._exc_info_to_string(err, t)))

        def addError(self, t, err):
            super().addError(t, err)
            self.rows.append((t.id(), "ERROR", self._exc_info_to_string(err, t)))

        def addSkip(self, t, reason):
            super().addSkip(t, reason)
            self.rows.append((t.id(), "SKIP", reason))

        def addExpectedFailure(self, t, err):
            super().addExpectedFailure(t, err)
            self.rows.append((t.id(), "PASS", "expected failure"))

        def addUnexpectedSuccess(self, t):
            super().addUnexpectedSuccess(t)
            self.rows.append((t.id(), "FAIL", "unexpected success"))

    suite = unittest.defaultTestLoader.discover(start, pattern="test_*.py", top_level_dir=start)
    with open(os.devnull, "w") as devnull:
        runner = unittest.TextTestRunner(stream=devnull, resultclass=R, verbosity=0)
        res = runner.run(suite)
    for tid, st, detail in res.rows:
        print("@@ROW " + json.dumps({"id": tid, "status": st, "detail": detail}, ensure_ascii=False))
    return 0


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="*", help="thư mục test (mặc định: mọi thư mục con trong tests/)")
    ap.add_argument("--inner", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)  # -h/--help -> exit 0; cờ lạ -> exit 2
    if a.inner:
        return inner(a.inner)
    targets = [Path(x).resolve() for x in a.dirs] if a.dirs else sorted(p for p in TESTS.iterdir() if p.is_dir() and p.name != "__pycache__") if TESTS.is_dir() else []
    missing = [name for name, mod in OPTIONAL.items() if importlib.util.find_spec(mod) is None]
    print("Thiếu thư viện (test liên quan sẽ SKIP): " + (", ".join(missing) if missing else "không"))
    before = pycache_dirs()
    tmp = Path(tempfile.mkdtemp(prefix="omi_selftest_"))
    home = tmp / "home"
    home.mkdir()
    site = tmp / "site"
    site.mkdir()
    (site / "sitecustomize.py").write_text(SITECUSTOMIZE, encoding="utf-8")
    env = dict(os.environ)
    env.update({"HOME": str(home), "USERPROFILE": str(home), "PYTHONDONTWRITEBYTECODE": "1", "NO_NETWORK": "1",
                "PYTHONIOENCODING": "utf-8", "OMI_SCRATCH": str(tmp / "scratch"),
                "PYTHONPATH": str(site) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")})
    for k in [k for k in env if k.startswith("OMI_API_BASE")] + [
            "OMI_TOKEN", "OMI_TOKEN_FILE", "OMI_DOMAIN", "OMI_MANIFEST", "OMI_VALIDATOR_OVERRIDE", "OMI_TEST_MODE"]:
        env.pop(k, None)
    rows = []
    try:
        for t in targets:
            if not t.is_dir():
                rows.append({"id": str(t), "status": "ERROR", "detail": "không phải thư mục"})
                continue
            p = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--inner", str(t)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=str(ROOT))
            got = [json.loads(l[6:]) for l in p.stdout.splitlines() if l.startswith("@@ROW ")]
            rows.extend(got)
            if p.returncode != 0 or (not got and p.stderr.strip()):
                rows.append({"id": f"{t.name} (tiến trình)", "status": "ERROR", "detail": p.stderr[-2000:]})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for d in pycache_dirs() - before:
            shutil.rmtree(d, ignore_errors=True)
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        line = f"{r['status']:<5} {r['id']}"
        if r["status"] == "SKIP":
            line += f"  ({r['detail']})"
        print(line)
    for r in rows:
        if r["status"] in ("FAIL", "ERROR"):
            print(f"\n--- {r['status']} {r['id']}\n{r['detail']}")
    bad = counts.get("FAIL", 0) + counts.get("ERROR", 0)
    print("\nTổng: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + f" | RESULT {'FAIL' if bad or not rows else 'PASS'}")
    return 1 if bad or not rows else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
