"""Tóm tắt OMIFlow thành sơ đồ văn bản gọn (tiết kiệm token thay vì đọc JSON hàng trăm KB).

    python flow_outline.py --list                 # danh sách flow của tenant
    python flow_outline.py <flow_id> [<flow_id>]  # sơ đồ từng flow: trigger -> nút -> nhánh, tên biến thay cho mã
    python flow_outline.py --save <flow_id>       # lưu JSON đầy đủ ra thư mục hiện tại, chỉ in đường dẫn

Token: dùng omi_session.py (phiên MCP OMI hoặc OMI_TOKEN_FILE).
"""
import json
import os
import re
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from omi_session import headers  # noqa: E402

B = 'https://campaign-v1-stg.omicrm.com/omi_v2/campaign'


def short(s, n=90):
    s = re.sub(r'<[^>]+>', ' ', str(s or ''))
    return re.sub(r'\s+', ' ', s).strip()[:n]


def get(fid):
    return requests.get(f'{B}/get/{fid}', headers=headers(), timeout=60).json()['payload']


def names_of(j):
    n = {v.get('field_code'): v.get('name') for v in j.get('custom_variables') or []}
    for node in j['nodes']:
        for c in node.get('conditions') or []:
            for d in c.get('data') or []:
                for mv in d.get('multi_variables') or []:
                    n[mv['field_code']] = (mv.get('field_name') or '').strip()
        for a in node.get('actions') or []:
            data = a.get('data') or {}
            for mv in (data.get('config') or {}).get('multi_variables') or []:
                n[mv['field_code']] = mv.get('field_name')
            for cv in data.get('config_variables') or []:
                for mv in (cv.get('config') or {}).get('multi_variables') or []:
                    n[mv['field_code']] = mv.get('field_name')
    return n


def outline(j):
    n = names_of(j)
    sub = lambda s: re.sub(r'\{\{(\w+)\}\}', lambda m: '{{' + str(n.get(m.group(1), m.group(1))) + '}}', str(s))
    print(f"\n# {j['name']} | id {j['_id']} | v{j['version']} | trigger {j['kick_off'].get('event')} | nút {len(j['nodes'])}")
    if j.get('description'):
        print('  mô tả:', short(j['description'], 200))
    it = {k: v for k, v in (j.get('iteration_config') or {}).items() if v}
    if it.get('is_limit'):
        print('  giới hạn:', it)
    for node in sorted(j['nodes'], key=lambda x: (not x.get('is_first_node'), float(x['position']['x']), float(x['position']['y']))):
        t = node['node_type']
        if t == 'DESCRIPTION':
            print(f"  [ghi chú] {short(node.get('description'), 120)}")
            continue
        print(f"  [{node['id']}] {t}{' (TRIGGER)' if node.get('is_first_node') else ''}{' — ' + short(node['description'], 50) if node.get('description') else ''}")
        for c in node.get('conditions') or []:
            parts = []
            for d in c.get('data') or []:
                dt = d.get('type')
                if dt == 'WEB_HOOK':
                    parts.append(f"API {d.get('method')} biến={[(m.get('field_name') or '').strip() for m in d.get('multi_variables') or []]}")
                elif dt == 'COMPARE':
                    for cc in d.get('compare_conditions') or []:
                        vals = [v.get('start_value') if isinstance(v, dict) else v for v in cc.get('values') or []]
                        parts.append(f"{cc.get('target_type')}.{cc.get('field_name') or n.get(cc.get('field_code'), cc.get('field_code'))} {cc.get('operator')} {short(sub(vals), 80)}")
                elif dt == 'CALL':
                    parts.append('CALL ' + str([(a['field_code'], a.get('values')) for a in d.get('attributes') or []]))
                elif dt == 'CUSTOM':
                    parts.append('CUSTOM ' + ','.join(cd.get('target_type', '') for cd in d.get('custom_data') or []))
                else:
                    parts.append(str(dt))
            print(f"      case {c.get('id')}: {' & '.join(parts)} -> {c.get('next_nodes')}")
        for a in node.get('actions') or []:
            d = a.get('data') or {}
            at = a.get('type')
            if at == 'ADD_TICKET':
                info = f"'{short(sub(d.get('ticket_detail', {}).get('name')), 70)}'"
            elif at == 'SEND_WEBHOOK':
                info = f"{d.get('method')} {d.get('url')}"
            elif at == 'CREATE_CUSTOM_VARIABLE':
                cfg = d.get('config') or {}
                info = f"{d.get('type')} {cfg.get('method', '')} {cfg.get('url', '')}".strip()
            elif at == 'GET_RELATED':
                info = str(d.get('options'))
            elif at == 'DELAY':
                info = f"{d.get('type')} {d.get('value_string')} {d.get('unit')}{' +điều kiện' if d.get('conditions') else ''}"
            elif at in ('PUSH_NOTIFICATION', 'INFO_DIALOG', 'FORM_DIALOG'):
                info = f"'{short(sub(d.get('title')), 60)}'"
            else:
                info = short(sub(json.dumps(d, ensure_ascii=False)), 80)
            print(f"      - {at}: {info}")
        nx = {k: node.get(k) for k in ('next_nodes', 'success_next_nodes', 'fail_next_nodes') if node.get(k)}
        if nx:
            print('      ->', nx)


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] == '--list':
        r = requests.post(f'{B}/search?page=1&size=100', headers=headers(), json={}, timeout=60).json()
        for it in r['payload']['items']:
            print(it['_id'], '|', it.get('name'), '| v', it.get('version'))
    elif args[0] == '--save':
        for fid in args[1:]:
            p = os.path.abspath(f'flow_{fid}.json')
            json.dump(get(fid), open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print(p)
    else:
        for fid in args:
            outline(get(fid))
