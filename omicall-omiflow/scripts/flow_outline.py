"""Tóm tắt OMIFlow thành sơ đồ văn bản gọn (tiết kiệm token thay vì đọc JSON hàng trăm KB).

    python flow_outline.py --list                 # danh sách flow của tenant (tự phân trang)
    python flow_outline.py <flow_id> [<flow_id>]  # sơ đồ từng flow: trigger -> nút -> nhánh, tên biến thay cho mã
    python flow_outline.py --file flow.json       # tóm tắt file JSON có sẵn, không gọi mạng
    python flow_outline.py --save <flow_id>       # lưu JSON đầy đủ vào thư mục scratch (OMI_SCRATCH hoặc thư mục tạm), chỉ in đường dẫn
                                                  # file đã che bí mật (***): flow có header Authorization/token
                                                  # không dùng làm base cho omi_save (exit 2) -> sửa phần đó trên UI

Token: dùng omi_session.py (phiên MCP OMI hoặc OMI_TOKEN_FILE). --help và --file không cần token, không gọi mạng.
"""
import argparse
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.environ.get('OMI_FLOW_API_BASE') or 'https://campaign-v1-stg.omicrm.com/omi_v2/campaign'  # biến env chỉ dùng trong test
# Chỉ bỏ thẻ HTML thật; giữ nguyên placeholder dạng <id>, <code10>, <tên>.
HTML_TAG = re.compile(r'</?(?:p|br|div|span|strong|b|i|em|u|s|ul|ol|li|a|h[1-6]|img|table|tr|td|th|tbody|thead|'
                      r'blockquote|pre|code|hr|font|sup|sub)(?:\s[^<>]*)?/?>', re.I)


def short(s, n=90):
    s = HTML_TAG.sub(' ', str(s if s is not None else ''))
    return re.sub(r'\s+', ' ', s).strip()[:n]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _pos(node):
    p = node.get('position') if isinstance(node.get('position'), dict) else {}
    return _num(p.get('x')), _num(p.get('y'))


# ---------- mạng (import lười: --help/--file không chạm requests hay token) ----------

def _headers():
    sys.path.insert(0, HERE)
    from omi_session import headers  # noqa: E402
    return headers()


def _request(method, url, **kw):
    import requests
    try:
        r = requests.request(method, url, headers=_headers(), timeout=60, **kw)
    except requests.RequestException as e:
        raise SystemExit(f'Lỗi mạng khi gọi {url.split("?")[0]}: {type(e).__name__}')
    if r.status_code == 401:
        raise SystemExit('401: token hết hạn hoặc sai tenant → chạy omi_preflight.py / đăng nhập lại MCP OMI rồi chạy lại.')
    if r.status_code != 200:
        raise SystemExit(f'HTTP {r.status_code} từ {url.split("?")[0]}: {short(r.text, 200)}')
    try:
        body = r.json()
    except ValueError:
        raise SystemExit(f'Phản hồi không phải JSON từ {url.split("?")[0]} (có thể trang đăng nhập): {short(r.text, 120)}')
    if not isinstance(body, dict) or 'payload' not in body:
        raise SystemExit(f'Phản hồi thiếu payload: {short(json.dumps(body, ensure_ascii=False), 200)}')
    return body['payload']


def get(fid):
    return _request('GET', f'{B}/get/{fid}')


def list_flows(size=100, max_pages=50):
    out = []
    for page in range(1, max_pages + 1):
        p = _request('POST', f'{B}/search?page={page}&size={size}', json={}) or {}
        items = p.get('items') or []
        out.extend(items)
        total = p.get('total') or p.get('total_items')
        if len(items) < size or (isinstance(total, int) and len(out) >= total):
            break
    return out


def save(obj, fid):
    fid = re.sub(r'[^A-Za-z0-9_.-]', '_', str(fid)).strip('.') or 'flow'  # tên file an toàn, không thoát khỏi scratch
    try:
        sys.path.insert(0, HERE)
        from omi_api import save_json  # file dùng chung: che bí mật rồi ghi vào scratch
        try:
            p = save_json(obj, os.environ.get('OMI_SCRATCH') or None, name=f'flow_{fid}.json')
        except TypeError:  # bản omi_api cũ không có tham số name
            p = save_json(obj, os.environ.get('OMI_SCRATCH') or None)
        if p:
            return p
    except ImportError:
        pass
    d = os.environ.get('OMI_SCRATCH') or tempfile.gettempdir()
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f'flow_{fid}.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return p


# ---------- tóm tắt ----------

def names_of(j):
    n = {}
    for v in j.get('custom_variables') or []:
        if isinstance(v, dict) and v.get('field_code'):
            n[v['field_code']] = v.get('name')

    def walk(o):
        if isinstance(o, dict):
            for mv in o.get('multi_variables') or []:
                if isinstance(mv, dict) and mv.get('field_code'):
                    n[mv['field_code']] = (mv.get('field_name') or '').strip() or mv['field_code']
            if o.get('variable_code'):  # COLLECT_INFO
                n[o['variable_code']] = o.get('variable_name') or o['variable_code']
            if o.get('field_code') and o.get('field_name') and o['field_code'] not in n:  # trường FORM / FORM_DIALOG
                n[o['field_code']] = o.get('field_name')
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    for node in j.get('nodes') or []:
        walk([node.get('conditions'), node.get('actions')])
    return n


def _key(v):
    """id băm được: JSON hỏng (id là list/dict) thì đổi sang chuỗi thay vì crash."""
    return v if v is None or isinstance(v, (str, int, float, bool)) else json.dumps(v, ensure_ascii=False)


def _as_list(v):
    return v if isinstance(v, list) else [v]


def links_of(node):
    out = []
    for c in node.get('conditions') or []:
        if isinstance(c, dict):
            out += [_key(t) for t in _as_list(c.get('next_nodes')) if t]
    out += [_key(t) for t in _as_list(node.get('next_nodes')) if t]
    for k in ('success_next_nodes', 'fail_next_nodes'):
        out += [_key(t) for t in _as_list(node.get(k)) if t]
    return out


def orphan_warnings(j):
    nodes = [x for x in j.get('nodes') or [] if isinstance(x, dict)]
    ids = {_key(x.get('id')) for x in nodes}
    warn = []
    for x in nodes:
        for t in links_of(x):
            if t not in ids:
                warn.append(f'nút {x.get("id")} trỏ tới id không tồn tại: {t}')
    first = [x for x in nodes if x.get('is_first_node')]
    if first:
        by = {_key(x.get('id')): x for x in nodes}
        seen, stack = set(), [_key(first[0].get('id'))]
        while stack:
            k = stack.pop()
            if k in seen or k not in by:
                continue
            seen.add(k)
            stack += links_of(by[k])
        for x in nodes:
            if x.get('node_type') != 'DESCRIPTION' and _key(x.get('id')) not in seen:
                warn.append(f'nút mồ côi (không đi tới từ trigger): {x.get("id")} {x.get("node_type")}')
    return warn


def outline(j, out=print):
    n = names_of(j)

    def sub(s):
        return re.sub(r'\{\{([^{}\s]+)\}\}', lambda m: '{{' + str(n.get(m.group(1)) or m.group(1)) + '}}', str(s))

    kick = j.get('kick_off') if isinstance(j.get('kick_off'), dict) else {}
    nodes = [x for x in j.get('nodes') or [] if isinstance(x, dict)]
    out(f"\n# {j.get('name')} | id {j.get('_id')} | v{j.get('version')} | trigger {kick.get('event')} | nút {len(nodes)}")
    if j.get('description'):
        out('  mô tả: ' + short(j.get('description'), 200))
    it = {k: v for k, v in (j.get('iteration_config') or {}).items() if v}
    if it.get('is_limit'):
        out(f'  giới hạn: {it}')
    for node in sorted(nodes, key=lambda x: (not x.get('is_first_node'),) + _pos(x)):
        t = node.get('node_type')
        if t == 'DESCRIPTION':
            out(f"  [ghi chú] {short(node.get('description'), 120)}")
            continue
        desc = ' — ' + short(node.get('description'), 50) if node.get('description') else ''
        out(f"  [{node.get('id')}] {t}{' (TRIGGER)' if node.get('is_first_node') else ''}{desc}")
        for c in node.get('conditions') or []:
            if not isinstance(c, dict):
                continue
            parts = []
            for d in c.get('data') or []:
                if not isinstance(d, dict):
                    continue
                dt = d.get('type')
                if dt == 'WEB_HOOK':
                    vs = [(m.get('field_name') or m.get('field_code') or '?').strip() for m in d.get('multi_variables') or []
                          if isinstance(m, dict)]
                    parts.append(f"API {d.get('method')} biến={vs}")
                elif dt == 'COMPARE':
                    for cc in d.get('compare_conditions') or []:
                        if not isinstance(cc, dict):
                            continue
                        vals = [v.get('start_value') if isinstance(v, dict) else v for v in cc.get('values') or []]
                        vals += cc.get('ml_values') or []
                        fname = cc.get('field_name') or n.get(cc.get('field_code')) or cc.get('field_code')
                        parts.append(f"{cc.get('target_type')}.{fname} {cc.get('operator')} {short(sub(vals), 80)}")
                elif dt == 'CALL':
                    parts.append('CALL ' + str([(a.get('field_code'), a.get('values')) for a in d.get('attributes') or []
                                                if isinstance(a, dict)]))
                elif dt == 'CUSTOM':
                    parts.append('CUSTOM ' + ','.join(str(cd.get('target_type', '')) for cd in d.get('custom_data') or []
                                                      if isinstance(cd, dict)))
                else:
                    parts.append(str(dt))
            out(f"      case {c.get('id')}: {' & '.join(parts)} -> {c.get('next_nodes')}")
        for a in node.get('actions') or []:
            if not isinstance(a, dict):
                continue
            d = a.get('data') if isinstance(a.get('data'), dict) else {}
            at = a.get('type')
            if at == 'ADD_TICKET':
                info = f"'{short(sub((d.get('ticket_detail') or {}).get('name')), 70)}'"
            elif at == 'SEND_WEBHOOK':
                info = f"{d.get('method')} {d.get('url')}"
            elif at == 'CREATE_CUSTOM_VARIABLE' and d.get('type') == 'CHAT_GPT':
                vs = []
                for cv in d.get('config_variables') or []:
                    for mv in ((cv or {}).get('config') or {}).get('multi_variables') or []:
                        if isinstance(mv, dict):
                            vs.append(f"{mv.get('field_name') or mv.get('field_code')} ({mv.get('chat_gpt_model')}): "
                                      f"{short(sub(mv.get('content')), 100)}")
                info = 'CHAT_GPT ' + ' | '.join(vs)
            elif at == 'CREATE_CUSTOM_VARIABLE':
                cfg = d.get('config') or {}
                vs = [mv.get('field_name') or mv.get('field_code') for mv in cfg.get('multi_variables') or [] if isinstance(mv, dict)]
                info = f"{d.get('type')} {cfg.get('method', '')} {cfg.get('url', '')} -> {vs}".strip()
            elif at == 'COLLECT_INFO':
                vs = [f"{v.get('variable_name') or v.get('variable_code')}={short(v.get('variable_value'), 30)}"
                      for v in d.get('variables') or [] if isinstance(v, dict)]
                info = str(vs)
            elif at == 'GET_RELATED':
                info = str(d.get('options'))
            elif at == 'DELAY':
                info = f"{d.get('type')} {d.get('value_string')} {d.get('unit')}{' +điều kiện' if d.get('conditions') else ''}"
            elif at in ('PUSH_NOTIFICATION', 'INFO_DIALOG', 'FORM_DIALOG'):
                info = f"'{short(sub(d.get('title')), 60)}'"
            else:
                info = short(sub(json.dumps(d, ensure_ascii=False)), 80)
            out(f"      - {at}: {info}")
        nx = {k: node.get(k) for k in ('next_nodes', 'success_next_nodes', 'fail_next_nodes') if node.get(k)}
        if nx:
            out(f'      -> {nx}')
    for w in orphan_warnings(j):
        out('  CẢNH BÁO ' + w)


def load_file(path):
    with open(path, encoding='utf-8-sig') as f:
        j = json.load(f)
    if isinstance(j, dict) and isinstance(j.get('payload'), dict) and 'nodes' not in j:
        j = j['payload']
    if not isinstance(j, dict):
        raise ValueError('JSON gốc không phải object flow')
    return j


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Tóm tắt OMIFlow (trigger -> nút -> nhánh).')
    ap.add_argument('ids', nargs='*', help='id flow cần tóm tắt (gọi API)')
    ap.add_argument('--list', action='store_true', help='liệt kê flow của tenant (phân trang)')
    ap.add_argument('--file', action='append', default=[], help='tóm tắt file JSON có sẵn (offline), dùng được nhiều lần')
    ap.add_argument('--save', nargs='+', metavar='FLOW_ID', help='lưu JSON đầy đủ vào scratch, chỉ in đường dẫn')
    args = ap.parse_args(argv)
    if args.file:
        for p in args.file:
            try:
                outline(load_file(p))
            except (OSError, ValueError) as e:
                print(f'Không đọc được {p}: {e}', file=sys.stderr)
                return 2
        return 0
    if args.save:
        for fid in args.save:
            print(save(get(fid), fid))
        return 0
    if args.list or not args.ids:
        for it in list_flows():
            print(it.get('_id'), '|', it.get('name'), '| v', it.get('version'))
        return 0
    for fid in args.ids:
        outline(get(fid))
    return 0


if __name__ == '__main__':
    sys.exit(main())
