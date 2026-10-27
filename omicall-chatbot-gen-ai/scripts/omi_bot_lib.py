# -*- coding: utf-8 -*-
"""Thư viện nhỏ cho Chatbot AI (OmiBot): lấy token từ omi_session, gọi chatbot-gateway, lưu JSON đã che bí mật.

    python omi_bot_lib.py <bot_id> --domain <domain> [--out-dir DIR]

Lệnh trên GET bot rồi ghi `omi_bot_<bot_id>.json` (đã che header Authorization/token) vào --out-dir,
mặc định env OMI_SCRATCH hoặc thư mục tạm — không ghi vào thư mục skill. Không in token.
Token CHỈ lấy qua omi_session.py (env OMI_TOKEN / file OMI_TOKEN_FILE do user đặt / phiên MCP OMI).
Không đọc cookie, không dùng CDP để lấy token.
"""
import argparse
import json
import os
import sys
import tempfile

BASE = os.environ.get("OMI_CHATBOT_BASE", "https://chatbot-gateway-v1-stg.omicrm.com")
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

SECRET_KEYS = ("authorization", "token", "access_token", "accesstoken", "apikey", "api_key", "password",
               "x-access-token", "x-api-key")
MASK = "***"


def _is_secret_key(k):
    k = str(k).lower()
    return k in SECRET_KEYS or k.endswith("_token") or k.endswith("password")


def mask_secrets(obj):
    """Bản sao đã che: giá trị khoá bí mật và header {key: Authorization, value: ...}. Ưu tiên omi_api.mask_secrets."""
    try:
        from omi_api import mask_secrets as shared_mask  # file dùng chung (owner shared), có thể chưa có
        return shared_mask(obj)
    except ImportError:
        pass
    if isinstance(obj, dict):
        out = {}
        hdr_secret = _is_secret_key(obj.get("key", "")) if "key" in obj and "value" in obj else False
        for k, v in obj.items():
            if _is_secret_key(k) and isinstance(v, str) and v:
                out[k] = MASK
            elif hdr_secret and k == "value" and v:
                out[k] = MASK
            else:
                out[k] = mask_secrets(v)
        return out
    if isinstance(obj, list):
        return [mask_secrets(v) for v in obj]
    if isinstance(obj, str) and obj.startswith("Bearer ") and len(obj) > 12 and not obj.startswith("Bearer <"):
        return "Bearer " + MASK
    return obj


def forbidden_roots():
    """Thư mục không được ghi file output: thư mục skill và gốc repo chứa nó (thư mục cha gần nhất có .git
    hoặc tools/sync_shared.py). Payload có thể chứa bí mật chưa che → không để lọt vào skill hay repo."""
    skill_dir = os.path.dirname(HERE)
    roots = [skill_dir]
    d = os.path.dirname(skill_dir)
    while d and d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, ".git")) or os.path.isfile(os.path.join(d, "tools", "sync_shared.py")):
            roots.append(d)
            break
        d = os.path.dirname(d)
    return roots


def blocked_path(path):
    """Trả thư mục cấm chứa path (None nếu được phép ghi)."""
    p = os.path.normcase(os.path.abspath(path))
    for r in forbidden_roots():
        rr = os.path.normcase(os.path.abspath(r))
        if p == rr or p.startswith(rr.rstrip(os.sep) + os.sep):
            return r
    return None


def guard_out_path(path):
    """Từ chối (SystemExit 2) khi --out nằm trong thư mục skill hoặc repo; trả đường dẫn tuyệt đối."""
    r = blocked_path(path)
    if r:
        print("LỖI: không ghi output vào %s (thư mục skill/repo) — payload có thể chứa bí mật. "
              "Dùng thư mục scratch (env OMI_SCRATCH hoặc thư mục tạm)." % r, file=sys.stderr)
        raise SystemExit(2)
    return os.path.abspath(path)


def scratch_dir(out_dir=None):
    d = out_dir or os.environ.get("OMI_SCRATCH") or tempfile.gettempdir()
    guard_out_path(d)
    os.makedirs(d, exist_ok=True)
    return d


def save_json(obj, name, out_dir=None):
    """Ghi JSON đã che bí mật vào scratch qua omi_api.save_json (file dùng chung); trả đường dẫn.
    Chỉ khi omi_api chưa có mới dùng bản dự phòng bên dưới (vẫn che bằng mask_secrets)."""
    import re
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.basename(name)).strip("_") or "omi.json"
    try:
        from omi_api import save_json as shared_save
    except ImportError:
        shared_save = None
    if shared_save is not None:
        return shared_save(obj, out_dir=out_dir, name=name)
    masked = mask_secrets(obj)
    path = os.path.join(scratch_dir(out_dir), name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(masked, f, ensure_ascii=False, indent=1, default=str)
    return path


def get_token(domain=None):
    """Token từ omi_session (không cookie). domain: bắt buộc khớp claim domain của token."""
    import omi_session
    try:
        tok = omi_session.get_token(expect_domain=domain) if domain else omi_session.get_token()
    except TypeError:  # omi_session bản cũ chưa có expect_domain
        tok = omi_session.get_token()
    if tok.lower().startswith("bearer "):
        tok = tok[7:].strip()
    if domain:
        try:
            claim = (omi_session.claims(tok) or {}).get("domain")
        except Exception:
            claim = None
        if claim is not None and str(claim).strip().lower() != domain.strip().lower():
            raise SystemExit("Token thuộc domain khác --domain (claim domain lệch). Đăng nhập lại đúng tenant "
                             "(login_omicall_mcp + select_tenant) rồi chạy lại omi_preflight.py.")
    return tok


def api(method, path, body=None, tok=None, timeout=60, base=None):
    import urllib.request
    import urllib.error
    req = urllib.request.Request((base or BASE) + path, method=method)
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    data = None
    if body is not None and method in ("POST", "PUT"):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise SystemExit("401: token hết hạn hoặc sai tenant → chạy omi_preflight.py rồi đăng nhập lại.")
        raise SystemExit("HTTP %d khi gọi %s" % (e.code, path))


def get_bot(bot_id, domain=None, tok=None):
    tok = tok or get_token(domain)
    return api("POST", "/omiai_assistant/get/" + bot_id, {"_id": bot_id}, tok)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="GET bot OmiBot và lưu JSON đã che bí mật vào scratch (không in token).")
    ap.add_argument("bot_id")
    ap.add_argument("--domain", default=os.environ.get("OMI_DOMAIN") or os.environ.get("OMICALL_DOMAIN"),
                    help="domain tenant; phải khớp claim domain của token")
    ap.add_argument("--out-dir", help="thư mục ghi (mặc định OMI_SCRATCH hoặc thư mục tạm)")
    a = ap.parse_args(argv)
    out = get_bot(a.bot_id, a.domain)
    path = save_json(out, "omi_bot_%s.json" % a.bot_id, a.out_dir)
    print("status_code:", out.get("status_code"), "| payload keys:", len((out.get("payload") or {})), "| saved:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
