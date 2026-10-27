# -*- coding: utf-8 -*-
"""Tiện ích chung cho test omicall-chatbot-gen-ai (offline, không gọi mạng ngoài 127.0.0.1).

Fixture trong fixtures/ được ghép từ các khối JSON có sẵn trong references/api-reference.md (đã làm sạch):
chúng chỉ chứng minh script nhất quán với tài liệu, KHÔNG chứng minh hợp lệ với nền tảng.
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SKILL = os.path.join(REPO, "omicall-chatbot-gen-ai")
SCRIPTS = os.path.join(SKILL, "scripts")
FIX = os.path.join(HERE, "fixtures")
BASE_FIXTURE = os.path.join(FIX, "bot_base.json")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return path


def env(extra=None):
    e = dict(os.environ)
    home = tempfile.mkdtemp(prefix="omi_cb_home_")
    e.update({"HOME": home, "USERPROFILE": home, "PYTHONDONTWRITEBYTECODE": "1", "NO_NETWORK": "1",
              "PYTHONIOENCODING": "utf-8", "OMI_SCRATCH": tempfile.mkdtemp(prefix="omi_cb_scratch_")})
    for k in ("OMI_TOKEN", "OMI_TOKEN_FILE", "OMI_DOMAIN"):
        e.pop(k, None)
    if extra:
        e.update(extra)
    return e


def run(script, *args, extra_env=None, timeout=60):
    cmd = [sys.executable, "-B", os.path.join(SCRIPTS, script)] + [str(a) for a in args]
    p = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env(extra_env))
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def fake_jwt(domain="<domain>", exp_offset=3600):
    def b64(o):
        return base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip("=")
    return "%s.%s.%s" % (b64({"alg": "HS256", "typ": "JWT"}),
                         b64({"tenant_id": "<tenant_id>", "domain": domain, "exp": int(time.time()) + exp_offset}),
                         "Y2hva2hvbmd0aGF0")
