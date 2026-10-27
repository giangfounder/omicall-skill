# -*- coding: utf-8 -*-
"""In dàn ý dạng cây của kịch bản Callbot SmartAgent (AI_AGENT), thay cho việc in cả payload.

Lệnh:
  python script_outline.py --file <script.json>          # offline, đọc GET hoặc payload đã lưu
  python script_outline.py --id <script_id> [--save]     # GET /callbot/script/get/{id}
  python script_outline.py --list                        # GET /callbot/script/list-by-tenant/{tenant_id}

In: BEGIN, intents → next_node, nodes, connections, classifies, biến, knowledge (chỉ in số header, không in giá trị).
--save ghi bản GET qua omi_api.save_json vào OMI_SCRATCH hoặc thư mục tạm, không ghi vào thư mục skill. Không in token.
Bản lưu chỉ che giá trị BÍ MẬT (khoá Authorization/token/password/cookie/secret/api_key và header có tên như vậy);
header thường như Content-Type giữ nguyên để dùng được làm --base cho build_smartagent.py. Script có header bí mật
thì bản lưu còn '***' → build_smartagent.py dừng exit 2 (không ghi '***' đè giá trị thật); phần đó sửa trên giao diện.
"""
import argparse
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DEFAULT_BASE = "https://chatbot-gateway-v1-stg.omicrm.com"


def api_base():
    """Host chatbot-gateway lấy qua omi_api.base('chatbot') (env OMI_API_BASE chỉ nhận 127.0.0.1/localhost cho stub
    test, kèm WARN). Thiếu omi_api thì dùng host mặc định, không đọc env."""
    try:
        import omi_api
        return omi_api.base("chatbot")
    except ImportError:
        return DEFAULT_BASE
SECRET_RE = re.compile(r"^(authorization|x-access-token|access_?token|refresh_?token|token|id_token|password|passwd|"
                       r"mat_khau|cookie|set-cookie|secret|client_secret|api_?key|x-api-key)$", re.I)


def utf8_stdout():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def mask(obj):
    """Che giá trị bí mật: dùng omi_api.mask_secrets nếu có; dự phòng: khoá bí mật (khớp đúng tên) và value của header
    có key bí mật. Header thường (Content-Type...) giữ nguyên."""
    try:
        import omi_api
        return omi_api.mask_secrets(obj)
    except ImportError:
        pass
    if isinstance(obj, dict):
        hk = obj.get("key") if isinstance(obj.get("key"), str) else None
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and SECRET_RE.match(k) and v not in (None, "", [], {}):
                out[k] = "***"
            elif k == "value" and hk and SECRET_RE.match(hk) and v not in (None, ""):
                out[k] = "***"
            else:
                out[k] = mask(v)
        return out
    if isinstance(obj, list):
        return [mask(v) for v in obj]
    return obj


def short(s, n=90):
    s = (s or "") if isinstance(s, str) else json.dumps(s, ensure_ascii=False)
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n - 1] + "…"


def unwrap(obj):
    if isinstance(obj, dict) and "nodes" not in obj and isinstance(obj.get("payload"), dict):
        return obj["payload"]
    return obj


def outline(s):
    s = unwrap(s)
    L = []
    L.append("SCRIPT %s | id=%s | version=%s | type=%s | model=%s | voice=%s | is_publish=%s | is_newest_version=%s" % (
        s.get("name"), s.get("id"), s.get("version"), s.get("type"), s.get("model"), s.get("voice"),
        s.get("is_publish"), s.get("is_newest_version")))
    nodes = [n for n in (s.get("nodes") or []) if isinstance(n, dict)]
    by_id = {n.get("id"): n for n in nodes}
    org_by_id = {o.get("id"): o for o in (s.get("org_nodes") or []) if isinstance(o, dict)}

    def label(nid):
        n = by_id.get(nid)
        if not n:
            return "%s (KHÔNG CÓ NODE)" % nid
        kinds = ",".join(a.get("type", "?") for a in (n.get("actions") or []) if isinstance(a, dict))
        name = ((org_by_id.get(nid) or {}).get("data") or {}).get("name") or ""
        return "%s [%s%s]%s" % (nid, n.get("node_type"), (":" + kinds) if kinds else "", (" " + name) if name else "")

    begin = next((n for n in nodes if n.get("node_type") == "BEGIN"), None)
    if begin:
        cfg = begin.get("ai_agent_config") or {}
        an = cfg.get("ai_analyze") or {}
        L.append("BEGIN %s" % begin.get("id"))
        L.append("  start_call_instruction: %s" % short(cfg.get("start_call_instruction")))
        L.append("  instruction: %d ký tự | %s" % (len(cfg.get("instruction") or ""), short(cfg.get("instruction"), 70)))
        L.append("  intents:")
        for c in an.get("conditions") or []:
            if not isinstance(c, dict):
                continue
            nn = c.get("next_node")
            steps = []
            for st in c.get("action_steps") or []:
                if isinstance(st, dict):
                    steps.append("%s%s" % (st.get("action"), (":" + ",".join(st.get("variables_code") or [])) if st.get("variables_code") else ""))
            if c.get("type") == "CUSTOM_INTENT":
                content = "; ".join(short(d.get("content"), 60) for d in (c.get("data") or []) if isinstance(d, dict))
                L.append("    - %s (%s) → %s%s | %s" % (c.get("name"), c.get("id"), label(nn) if nn else "xử lý trong BEGIN",
                                                  (" | " + " ".join(steps)) if steps else "", content))
            else:
                L.append("    - [hệ thống] %s → %s" % (c.get("id"), label(nn) if nn else "null"))
        bca = an.get("bot_can_not_answer") if isinstance(an.get("bot_can_not_answer"), dict) else {}
        L.append("  ai_analyze.bot_can_not_answer.next_node: %s" % bca.get("next_node"))
        cv = [v.get("variable_code") for v in (cfg.get("collect_variables") or []) if isinstance(v, dict)]
        L.append("  collect_variables: %s" % (", ".join(cv) or "-"))
        kn = cfg.get("knowledge") or {}
        files = kn.get("files") or []
        apis = kn.get("apis") or []
        L.append("  knowledge.files: %d%s" % (len(files), "".join("\n    - %s" % short((f or {}).get("name")) for f in files if isinstance(f, dict))))
        L.append("  knowledge.apis: %d" % len(apis))
        for a in apis:
            if isinstance(a, dict):
                nh = len([h for h in (a.get("headers") or []) if isinstance(h, dict)])
                L.append("    - %s (ref_id=%s) %s %s | headers: %d (không in giá trị)" % (a.get("name"), a.get("ref_id"), a.get("method"), short(a.get("url"), 60), nh))
    else:
        L.append("BEGIN: KHÔNG CÓ")
    L.append("NODES:")
    for n in nodes:
        if n is begin:
            continue
        extra = ""
        for a in n.get("actions") or []:
            if not isinstance(a, dict):
                continue
            d = a.get("data") if isinstance(a.get("data"), dict) else {}
            if a.get("type") == "TRANSFER_CALL":
                extra += " ids=%s sip=%s collected=%s" % (d.get("ids"), d.get("sip_number"), d.get("transfer_collected_info"))
            elif a.get("type") == "ADD_CLASSIFY":
                extra += " nhãn=%s" % [x.get("name") for x in (d.get("classifies") or []) if isinstance(x, dict)]
        if n.get("node_type") == "END_CALL":
            extra += " | %s" % short(n.get("description"), 70)
        vs = [v.get("field_code") for v in (n.get("variables") or []) if isinstance(v, dict)]
        L.append("  - %s%s%s" % (label(n.get("id")), extra, (" | biến: " + ",".join(vs)) if vs else ""))
    L.append("CONNECTIONS:")
    for c in s.get("connections") or []:
        if isinstance(c, dict):
            L.append("  - %s.%s → %s" % (c.get("source"), c.get("sourceHandle"), c.get("target")))
    L.append("CLASSIFIES: %s" % [x.get("name") for x in (s.get("classifies") or []) if isinstance(x, dict)])
    tv = ["%s(%s)" % (v.get("field_code"), v.get("type")) for v in (s.get("variables") or []) if isinstance(v, dict)]
    L.append("VARIABLES: %s" % (", ".join(tv) or "-"))
    return "\n".join(L)


def _http_get(url):
    try:
        import omi_api  # file dùng chung (owner shared), có thể chưa có
        return omi_api.get(url)
    except ImportError:
        pass
    import requests
    from omi_session import headers
    r = requests.get(url, headers=headers(), timeout=60)
    if r.status_code == 401:
        raise SystemExit("401: token hết hạn hoặc sai tenant → chạy omi_preflight.py / login_omicall_mcp")
    r.raise_for_status()
    return r.json()


def save(obj, name):
    obj = mask(obj)
    try:
        import omi_api
        return omi_api.save_json(obj, None, name)  # tự che lần nữa bằng omi_api.mask_secrets
    except ImportError:
        pass
    out_dir = os.environ.get("OMI_SCRATCH") or tempfile.gettempdir()
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return path


def main(argv=None):
    utf8_stdout()
    ap = argparse.ArgumentParser(description="Dàn ý kịch bản Callbot SmartAgent (không in token, che header).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", help="đọc offline từ file JSON")
    g.add_argument("--id", help="GET /callbot/script/get/{id}")
    g.add_argument("--list", action="store_true", help="liệt kê script của tenant")
    ap.add_argument("--save", action="store_true", help="lưu bản GET (chỉ che giá trị bí mật) vào OMI_SCRATCH/thư mục tạm")
    a = ap.parse_args(argv)
    if a.file:
        try:
            with open(a.file, encoding="utf-8") as f:
                s = json.load(f)
        except (OSError, ValueError) as e:
            print("Không đọc được %s: %s" % (a.file, e), file=sys.stderr)
            return 2
        print(outline(s))
        return 0
    if a.list:
        from omi_session import claims, get_token
        tid = claims(get_token()).get("tenant_id")
        res = _http_get("%s/callbot/script/list-by-tenant/%s" % (api_base(), tid))
        items = res.get("payload") if isinstance(res, dict) else res
        for it in items or []:
            if isinstance(it, dict):
                print("%s | uuid=%s | v%s | %s | type=%s | is_publish=%s" % (it.get("id"), it.get("uuid"), it.get("version"),
                                                                             it.get("name"), it.get("type"), it.get("is_publish")))
        return 0
    res = _http_get("%s/callbot/script/get/%s" % (api_base(), a.id))
    s = unwrap(res)
    print(outline(s))
    if a.save:
        print("Đã lưu: %s" % save(s, "callbot_script_%s.json" % a.id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
