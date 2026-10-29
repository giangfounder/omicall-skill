"""Khảo sát cấu hình tổng đài và AI của tenant bằng API (chỉ đọc) — thay cho việc mở từng màn hình và chụp ảnh.

  python <thư mục skill>/scripts/config_survey.py --out <scratch>/tenant_context.json [--domain <domain>]

- Gọi các endpoint đọc mà giao diện OMICRM dùng (✔ GET 10/2026, bảng ENDPOINTS), token lấy từ omi_session (không in).
- Ghi/gộp vào file --out (thường là tenant_context.json ở scratch) hai khoá: `pbx` và `ai_config`; giữ nguyên các khoá khác.
- In ra màn hình chỉ số lượng và tên; không in token, không in số điện thoại.
- Endpoint lỗi (404, 401, mạng) → ghi vào `can_xac_nhan`, chạy tiếp phần còn lại.
Không tạo, sửa hay xoá gì trên tenant.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omi_api  # noqa: E402

# khoá -> (service, method, path, nơi lấy danh sách trong payload)
ENDPOINTS = {
    'hotlines': ('pbx', 'GET', 'public_number_of_tenant/list_active', 'items'),
    'call_scripts': ('pbx', 'GET', 'call_script/get?page=0&size=0', 'items'),
    'key_interactions': ('pbx', 'POST', 'key_interactive_script/get/list', None),
    'internal_groups': ('pbx', 'POST', 'internal_group/get/list', None),
    'outer_groups': ('pbx', 'POST', 'outer_group/get/list', None),
    'greetings': ('pbx', 'POST', 'greeting/get/list', None),
    'call_purposes': ('cdr', 'POST', 'call_transaction/purpose/get_list', None),
    'assistants': ('cdr', 'POST', 'call_transaction/assistant/list', None),
    'chat_criteria': ('ai', 'POST', 'natural_language/criteria/get_list', None),
    'evaluation_criteria': ('contact', 'GET', 'evaluation_criteria/get_all', None),
}


def _items(payload, key):
    if isinstance(payload, dict):
        payload = payload.get(key or 'items', payload)
    return payload if isinstance(payload, list) else []


def _ref(x):
    return {'_id': x.get('_id'), 'name': x.get('name')}


# rút gọn từng loại: chỉ giữ trường cần để thiết kế (id, tên, cấu trúc), bỏ dấu vết người tạo
def slim(kind, x):
    if kind == 'hotlines':
        c = x.get('configs') or {}
        return {'_id': x.get('_id'), 'number': x.get('number'), 'provider': x.get('provider'), 'status': x.get('status'),
                'expire_date': x.get('expire_date'), 'allow_call_in': c.get('allow_call_in'),
                'allow_call_out': c.get('allow_call_out'), 'default_script': c.get('default_script'),
                'working_days': c.get('working_days'), 'special_days': c.get('special_days')}
    if kind == 'call_scripts':
        return {'_id': x.get('_id'), 'name': x.get('script_name'), 'extension': x.get('extension'),
                'enable_criteria': x.get('enable_criteria'), 'criterias': x.get('criterias'),
                'scripts': [{k: s.get(k) for k in ('order', 'action_type', 'action_id', 'callbot_script_uuid')}
                            for s in x.get('scripts') or []]}
    if kind == 'key_interactions':
        return {'_id': x.get('_id'), 'name': x.get('script_name'), 'number': x.get('script_number'),
                'greeting_id': x.get('greeting_id'), 'time_out': x.get('time_out'), 'max_failure': x.get('max_failure'),
                'end_action_type': x.get('action_type'), 'ivr_direct_menu_dial': x.get('ivr_direct_menu_dial'),
                'webhook_enabled': bool((x.get('webhook') or {}).get('enable')),
                # phím nằm ở trường `ivr` ("1", "2"…); `key` để trống
                'keys': [{'digit': s.get('ivr'), 'action_type': s.get('action_type'), 'action': s.get('action')}
                         for s in x.get('scripts') or []]}
    if kind in ('internal_groups', 'outer_groups'):
        return {'_id': x.get('_id'), 'name': x.get('group_name'), 'number': x.get('group_number'),
                'strategy': x.get('strategy'), 'members': len(x.get('members') or []),
                'call_queue_config': x.get('call_queue_config'), 'timeout': x.get('timeout')}
    if kind == 'greetings':
        return {'_id': x.get('_id'), 'name': x.get('greeting_name'), 'source': x.get('formality_code'),
                'duration': x.get('duration')}
    if kind == 'assistants':
        return {'_id': x.get('_id'), 'name': x.get('name'), 'type': x.get('type'), 'enable': x.get('enable'),
                'call_types': x.get('call_types'), 'call_purpose_id': x.get('call_purpose_id'),
                'agents': len(x.get('contact_ids') or []), 'agent_groups': len(x.get('agent_cate_ids') or []),
                'numbers': len(x.get('numbers') or []),
                'features': [{'type': f.get('type'), 'items': len(f.get('items') or [])} for f in x.get('features') or []]}
    if kind == 'evaluation_criteria':
        return {'_id': x.get('_id'), 'name': x.get('name'), 'scopes': x.get('scopes')}
    return _ref(x)


def survey(call=None):
    """Trả về (pbx, ai_config, lỗi). `call(service, method, path)` để test thay mạng."""
    def default_call(service, method, path):
        return omi_api.get(service, path) if method == 'GET' else omi_api.post_json(service, path, {})
    call = call or default_call
    out, errors = {}, []
    for kind, (service, method, path, key) in ENDPOINTS.items():
        try:
            res = call(service, method, path)
            payload = res.get('payload') if isinstance(res, dict) else res
            out[kind] = [slim(kind, x) for x in _items(payload, key) if isinstance(x, dict)]
        except Exception as e:  # noqa: BLE001 — ghi lại rồi chạy tiếp
            out[kind] = None
            errors.append(f'{kind}: {method} {service} {path} lỗi ({type(e).__name__}) — đọc giao diện thay thế')
    pbx = {k: out[k] for k in ('hotlines', 'call_scripts', 'key_interactions', 'internal_groups', 'outer_groups',
                               'greetings')}
    ai = {k: out[k] for k in ('call_purposes', 'assistants', 'chat_criteria', 'evaluation_criteria')}
    return pbx, ai, errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, help='file JSON ở scratch (gộp vào nếu đã có)')
    ap.add_argument('--domain', help='kiểm token đúng domain')
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if a.domain:
        omi_api._headers(expect_domain=a.domain)  # dừng sớm nếu token sai tenant
    pbx, ai, errors = survey()
    ctx = {}
    if os.path.exists(a.out):
        with open(a.out, encoding='utf-8') as f:
            ctx = json.load(f)
    ctx['pbx'], ctx['ai_config'] = pbx, ai
    ctx['can_xac_nhan'] = [c for c in ctx.get('can_xac_nhan', []) if not c.startswith(tuple(ENDPOINTS))] + errors
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(omi_api.mask_secrets(ctx), f, ensure_ascii=False, indent=1)
    for k, v in list(pbx.items()) + list(ai.items()):
        names = [x.get('name') for x in v or [] if x.get('name')][:8]
        print(f"{k}: {'LỖI' if v is None else len(v)} {names if names else ''}")
    for e in errors:
        print('CẦN XÁC NHẬN', e)
    print(f'Đã ghi {a.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
