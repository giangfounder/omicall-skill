"""B1 của Đường nhanh: khảo sát tenant MỘT lần, ghi tenant_context.json theo khuôn references/tenant_context.template.json.

  python <thư mục skill>/scripts/tenant_survey.py --out <scratch>/tenant_context.json [--domain <d>]
         [--replay <thư mục>] [--include-unverified] [--tenant-id <id>]

- Mặc định chỉ gọi các endpoint ĐỌC có verified=True trong bảng ENDPOINTS (mỗi dòng ghi nguồn file:dòng).
  Endpoint chưa kiểm chứng không được gọi, chỉ ghi vào can_xac_nhan (thêm --include-unverified để thử đọc,
  kết quả vẫn mang nhãn 'chưa kiểm chứng').
- Trường lấy từ MCP (agents, extensions, hotlines, channels, ticket_categories, modules_enabled, quota) để trống,
  kèm _nguon 'MCP <tên công cụ>' để agent điền bằng công cụ MCP.
- attributes: cờ is_list suy từ field_type theo bảng LIST_TYPES (Cần xác nhận mã kiểu thật) hoặc từ danh sách lựa chọn.
- agents (khi có dữ liệu API): giữ nguyên CẢ _id lẫn agent_id/contact_id thô; không tự chọn trường nào map vào
  TRANSFER_CALL (tài liệu còn mâu thuẫn: Cần xác nhận).
- --replay <thư mục>: đọc <key>.json thay vì gọi mạng (dùng cho test). Không ghi token; file ra đi qua mask_secrets.
- Đếm 'đã đọc' chỉ gồm endpoint trả về ok; endpoint lỗi in WARN riêng (phần đó KHÔNG phải trống).
Exit: 0 xong (có thể kèm WARN khi một phần lỗi); 3 chưa có token; 4 không đọc được endpoint nào (không ghi --out).
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TEMPLATE = os.path.join(os.path.dirname(HERE), 'references', 'tenant_context.template.json')

ENDPOINTS = [
    {'key': 'flows', 'service': 'campaign', 'method': 'POST', 'path': '/omi_v2/campaign/search?page=1&size=50', 'body': {},
     'verified': True, 'nguon': 'omicall-omiflow/references/api-reference.md:8 (✔ đọc); omicall-omiflow/SKILL.md:41'},
    {'key': 'callbot_scripts', 'service': 'chatbot', 'method': 'GET', 'path': '/callbot/script/list-by-tenant/{tenant_id}',
     'verified': True, 'nguon': 'omicall-callbot-flow/SKILL.md:41; omicall-callbot-flow/references/browser-snippets.md:18; '
                                'omicall-callbot-gen-ai/references/api-reference.md:163'},
    {'key': 'intents', 'service': 'chatbot', 'method': 'GET', 'path': '/callbot/intent/list-by-tenant/{tenant_id}',
     'verified': True, 'nguon': 'omicall-callbot-flow/SKILL.md:41; omicall-callbot-flow/references/browser-snippets.md:19'},
    {'key': 'entity_types', 'service': 'chatbot', 'method': 'POST', 'path': '/callbot/entity-type/search',
     'body': {'page': 1, 'size': 100, 'keyword': '', 'tenantId': '{tenant_id}', 'isSearch': True, 'with_entity_data_type': True},
     'verified': True, 'nguon': 'omicall-callbot-flow/references/browser-snippets.md:20; omicall-callbot-flow/references/api-reference.md:11'},
    {'key': 'training_history', 'service': 'chatbot', 'method': 'GET', 'path': '/callbot/training/history/search?page=1&size=3',
     'verified': True, 'nguon': 'omicall-callbot-flow/references/browser-snippets.md:22; omicall-callbot-flow/references/api-reference.md:17'},
    {'key': 'sale_allocations', 'service': 'tenant', 'method': 'POST', 'path': '/sale_allocation/search?page=1&size=50', 'body': {},
     'verified': True, 'nguon': 'omicall-omiflow/references/crm-config.md:46 (đã kiểm chứng 10/2026); omicall-omiflow/SKILL.md:43'},
    {'key': 'attributes', 'service': 'tenant', 'method': 'GET', 'path': '/attribute/get_all?has_attr=true',
     'verified': False, 'nguon': 'omicall-omiflow/SKILL.md:43; omicall-omiflow/references/crm-config.md:29 — chưa ghi method và khuôn phản hồi'},
    {'key': 'ticket_status_sets', 'service': 'ticket', 'method': 'GET', 'path': '/ticket/status-set/get-all',
     'verified': False, 'nguon': 'omicall-omiflow/SKILL.md:43 — chưa ghi method và khuôn phản hồi'},
    {'key': 'bots', 'service': 'chatbot', 'method': 'POST', 'path': '/omiai_assistant/get_list', 'body': {},
     'verified': False, 'nguon': 'omicall-chatbot-gen-ai/references/api-reference.md:12 — body chưa ghi'},
    {'key': 'agents_api', 'service': 'agent', 'method': None, 'path': None,
     'verified': False, 'nguon': 'omicall-callbot-flow/SKILL.md:41 ("agent-v1-stg …/get_all_agent/no_role" — thiếu tiền tố đường dẫn); '
                                 'dùng MCP list_agents'},
]

# Mã field_type: chỉ single_text, multi_text, date, phone có trong tài liệu (node-catalog). Mã kiểu danh sách: Cần xác nhận.
TEXT_TYPES = {'single_text', 'multi_text', 'date', 'phone', 'number', 'email'}
LIST_TYPES = {'select', 'single_select', 'multi_select', 'checkbox', 'radio', 'list', 'dropdown', 'multi_choice',
              'single_choice', 'tag', 'tags', 'option', 'options'}
MCP_FIELDS = {
    'modules_enabled': 'MCP get_service_package', 'ticket_categories': 'MCP get_ticket_categories',
    'agents': 'MCP list_agents', 'extensions': 'MCP list_extensions', 'hotlines': 'MCP list_hotlines',
    'channels': 'MCP get_all_channels',
}


def _items(resp):
    p = resp.get('payload') if isinstance(resp, dict) else resp
    if isinstance(p, dict):
        for k in ('items', 'data', 'list'):
            if isinstance(p.get(k), list):
                return p[k]
        return []
    return p if isinstance(p, list) else []


def _fill(v, tenant_id):
    if isinstance(v, str):
        return v.replace('{tenant_id}', tenant_id or '')
    if isinstance(v, dict):
        return {k: _fill(x, tenant_id) for k, x in v.items()}
    return v


def fetch(ep, tenant_id, replay):
    if replay:
        p = os.path.join(replay, ep['key'] + '.json')
        if not os.path.exists(p):
            return None, 'không có dữ liệu replay %s' % os.path.basename(p)
        with open(p, encoding='utf-8') as f:
            return json.load(f), None
    if '{tenant_id}' in json.dumps(ep) and not tenant_id:
        return None, 'thiếu tenant_id'
    import omi_api
    try:
        if ep['method'] == 'GET':
            return omi_api.get(ep['service'], _fill(ep['path'], tenant_id)), None
        return omi_api.post_json(ep['service'], _fill(ep['path'], tenant_id), _fill(ep.get('body') or {}, tenant_id)), None
    except (omi_api.ApiError, OSError) as e:
        return None, str(e)[:200]
    except Exception as e:  # requests.RequestException...
        return None, '%s: %s' % (type(e).__name__, str(e)[:160])


def is_list_type(ftype, options):
    t = (ftype or '').strip().lower()
    if t in LIST_TYPES:
        return True
    if t in TEXT_TYPES:
        return False
    if options:
        return True
    return None


def parse_attributes(items):
    out = []
    for a in items:
        if not isinstance(a, dict):
            continue
        opts = a.get('options') or a.get('values') or a.get('items') or []
        opt_names = []
        for o in opts if isinstance(opts, list) else []:
            if isinstance(o, dict):
                opt_names.append(o.get('name') or o.get('display_value') or o.get('value') or o.get('label'))
            else:
                opt_names.append(o)
        ftype = a.get('field_type') or a.get('type')
        out.append({'code': a.get('field_code') or a.get('code'), 'name': a.get('field_name') or a.get('name'),
                    'type': ftype, 'is_list': is_list_type(ftype, opt_names), 'options': [x for x in opt_names if x is not None]})
    return out


def survey(domain=None, tenant_id=None, replay=None, include_unverified=False, now=None):
    with open(TEMPLATE, encoding='utf-8') as f:
        ctx = json.load(f)
    ctx.pop('_ghi_chu', None)
    ctx.pop('_khuon', None)
    ctx['tenant'] = {'domain': domain or '<domain>', 'tenant_id': tenant_id or '<tenant_id>'}
    ctx['survey_at'] = now or datetime.datetime.now().replace(microsecond=0).isoformat()
    ctx['_nguon'] = dict(ctx.get('_nguon') or {})
    ctx['_endpoints'] = []
    cxn = ctx['can_xac_nhan']
    raw = {}
    for ep in ENDPOINTS:
        row = {'key': ep['key'], 'verified': ep['verified'], 'nguon': ep['nguon'], 'goi': False, 'ket_qua': None}
        ctx['_endpoints'].append(row)
        if not ep['verified'] and not include_unverified:
            cxn.append('%s: endpoint chưa kiểm chứng, không gọi (%s)' % (ep['key'], ep['nguon']))
            continue
        if not ep['path']:
            cxn.append('%s: chưa đủ đường dẫn để gọi (%s)' % (ep['key'], ep['nguon']))
            continue
        row['goi'] = True
        resp, err = fetch(ep, tenant_id, replay)
        if err:
            row['ket_qua'] = 'lỗi: ' + err
            cxn.append('%s: không đọc được (%s)' % (ep['key'], err))
            continue
        row['ket_qua'] = 'ok'
        raw[ep['key']] = _items(resp)
        if not ep['verified']:
            cxn.append('%s: đọc bằng endpoint chưa kiểm chứng — soát lại khuôn dữ liệu (%s)' % (ep['key'], ep['nguon']))

    for f in raw.get('flows', []):
        ctx['existing_artefacts'].append({'kind': 'flow', 'id': f.get('_id'), 'uuid': f.get('uuid'), 'name': f.get('name'),
                                          'published': f.get('is_publish'), 'hotline_attached': None,
                                          'status': f.get('status'), 'kick_off_event': (f.get('kick_off') or {}).get('event')})
    for s in raw.get('callbot_scripts', []):
        ctx['existing_artefacts'].append({'kind': 'callbot', 'id': s.get('id'), 'uuid': s.get('uuid'), 'name': s.get('name'),
                                          'type': s.get('type'), 'version': s.get('version'),
                                          'is_newest_version': s.get('is_newest_version'),
                                          'published': s.get('is_publish'), 'hotline_attached': None})
    if raw.get('callbot_scripts'):
        cxn.append('existing_artefacts[callbot].hotline_attached: kiểm bằng MCP list_hotlines (inbound_script_id)')
    for b in raw.get('bots', []):
        ctx['existing_artefacts'].append({'kind': 'bot', 'id': b.get('_id'), 'uuid': b.get('uuid'), 'name': b.get('assistant_name') or b.get('name'),
                                          'published': (not b['is_draft']) if isinstance(b.get('is_draft'), bool) else None,
                                          'hotline_attached': None})
    kb = ctx['kho_tri_thuc']
    # system_intent_id: trường có trong phản hồi intent/list-by-tenant theo omicall-callbot-flow/references/api-reference.md:9, :23
    kb['intents'] = [{'id': i.get('id'), 'code': i.get('code'), 'name': i.get('name'), 'is_system': i.get('is_system'),
                      'system_intent_id': i.get('system_intent_id')}
                     for i in raw.get('intents', [])]
    kb['entity_types'] = [{'id': e.get('id'), 'code': e.get('code'), 'name': e.get('name'),
                           'entity_data_types': e.get('entity_data_types')} for e in raw.get('entity_types', [])]
    kb['training_history'] = [{'status': h.get('status'), 'total_trainings': h.get('total_trainings'),
                               'created_date': h.get('created_date')} for h in raw.get('training_history', [])]
    ctx['sale_allocations'] = [{'_id': s.get('_id'), 'name': s.get('name'), 'type': s.get('type'),
                                'staffs': [{'contact_id': x.get('contact_id'), 'full_name': x.get('full_name'), 'percent': x.get('percent')}
                                           for x in (s.get('staffs') or []) if isinstance(x, dict)]}
                               for s in raw.get('sale_allocations', [])]
    if 'attributes' in raw:
        ctx['attributes'] = parse_attributes(raw['attributes'])
        cxn.append('attributes.is_list: suy từ field_type theo bảng LIST_TYPES — Cần xác nhận mã kiểu thật; '
                   'is_list=null nghĩa là chưa biết, kiểm trên giao diện trước khi gán biến')
    else:
        cxn.append('attributes: chưa có — kiểu thuộc tính (danh sách hay văn bản) phải biết TRƯỚC khi thiết kế; '
                   'kiểm trên giao diện Cấu hình > Thuộc tính')
    if 'ticket_status_sets' in raw:
        ctx['status_sets'] = raw['ticket_status_sets']
    if 'agents_api' in raw:
        ctx['agents'] = [{k: a.get(k) for k in ('_id', 'agent_id', 'contact_id', 'full_name', 'sip_user') if k in a}
                         for a in raw['agents_api'] if isinstance(a, dict)]
    cxn.append('agents: giữ cả _id và agent_id/contact_id; trường nào map vào TRANSFER_CALL ids/value: Cần xác nhận '
               '(omicall-callbot-gen-ai/references/api-reference.md:91 so với :95)')
    for k, src in MCP_FIELDS.items():
        if not ctx.get(k):
            ctx['_nguon'][k] = src
    ctx['_nguon']['quota'] = ctx['_nguon'].get('quota') or 'MCP get_service_package'
    return ctx


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True)
    ap.add_argument('--domain')
    ap.add_argument('--tenant-id')
    ap.add_argument('--replay')
    ap.add_argument('--include-unverified', action='store_true')
    ap.add_argument('--now', help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    tenant_id, domain = a.tenant_id, a.domain
    if not a.replay:
        import omi_session
        info, _tok = omi_session.inspect(expect_domain=domain)
        if not info['token_ok']:
            print('Chưa có token dùng được (%s) -> chạy omi_preflight.py --domain <domain>.' % info['error'], file=sys.stderr)
            return 3
        tenant_id = tenant_id or info['tenant_id']
        domain = domain or info['domain_claim']
    ctx = survey(domain, tenant_id, a.replay, a.include_unverified, a.now)
    import omi_api
    called = [r for r in ctx['_endpoints'] if r['goi']]
    ok = [r for r in called if r['ket_qua'] == 'ok']
    failed = [r for r in called if r['ket_qua'] != 'ok']
    if called and not ok:
        print('LỖI: không đọc được endpoint nào (%d/%d lỗi) — kiểm mạng/token (omi_preflight.py). Không ghi %s: '
              'tenant KHÔNG phải trống, chỉ là chưa đọc được.' % (len(failed), len(called), a.out))
        for r in failed:
            print('  %s: %s' % (r['key'], omi_api.mask_text(str(r['ket_qua']))[:200]))
        return 4
    out = os.path.abspath(a.out)
    omi_api.scratch_dir(os.path.dirname(out))  # từ chối ghi vào thư mục skill
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(omi_api.mask_secrets(ctx), f, ensure_ascii=False, indent=1)
    print('Đã ghi %s: %d endpoint đã đọc, %d lỗi, %d artefact, %d mục Cần xác nhận.'
          % (out, len(ok), len(failed), len(ctx['existing_artefacts']), len(ctx['can_xac_nhan'])))
    if failed:
        print('WARN: %d endpoint không đọc được (%s) — phần đó KHÔNG phải trống; xem can_xac_nhan, đọc lại sau.'
              % (len(failed), ', '.join(r['key'] for r in failed)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
