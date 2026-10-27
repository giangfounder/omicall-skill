# -*- coding: utf-8 -*-
"""Tiện ích chung cho test của omicall-callbot-gen-ai (chạy offline)."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SKILL = os.path.join(REPO, "omicall-callbot-gen-ai")
SCRIPTS = os.path.join(SKILL, "scripts")
FIX = os.path.join(HERE, "fixtures")

_BLOCK = (
    "import socket\n"
    "_orig = socket.socket.connect\n"
    "def _guard(self, addr):\n"
    "    host = addr[0] if isinstance(addr, tuple) else addr\n"
    "    if host not in ('127.0.0.1', 'localhost', '::1'):\n"
    "        raise OSError('NO_NETWORK: chan ket noi toi %r trong test' % (host,))\n"
    "    return _orig(self, addr)\n"
    "socket.socket.connect = _guard\n"
)


def run(script, *args, home=None, cwd=None):
    """Chạy script của skill bằng python -B, chặn mạng ngoài 127.0.0.1, HOME tạm."""
    guard_dir = tempfile.mkdtemp(prefix="cg_guard_")
    with open(os.path.join(guard_dir, "sitecustomize.py"), "w", encoding="utf-8") as f:
        f.write(_BLOCK)
    env = dict(os.environ)
    home = home or tempfile.mkdtemp(prefix="cg_home_")
    env.update({"PYTHONPATH": guard_dir, "PYTHONDONTWRITEBYTECODE": "1", "NO_NETWORK": "1",
                "HOME": home, "USERPROFILE": home, "PYTHONIOENCODING": "utf-8"})
    for k in ("OMI_TOKEN", "OMI_TOKEN_FILE"):
        env.pop(k, None)
    p = subprocess.run([sys.executable, "-B", os.path.join(SCRIPTS, script)] + [str(a) for a in args],
                       capture_output=True, env=env, timeout=120, cwd=cwd)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
