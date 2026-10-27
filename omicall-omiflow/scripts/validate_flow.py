"""Kiểm JSON flow OMIFlow trước khi lưu (pre) hoặc sau khi GET lại (post). Chỉ đọc, không sửa payload, không gọi mạng.

    python validate_flow.py <flow.json> [--mode pre|post] [--sent payload.json] [--quota N] [--context tenant_context.json]

<flow.json>: object flow (như GET /omi_v2/campaign/get/{id}) hoặc bọc trong {"payload": {...}}.
Mỗi dòng output: `PASS|FAIL|WARN <mã> <mô tả> [json path]`; dòng cuối `RESULT PASS|FAIL`.
Mã C1..C7 = mục checklist trong references/api-reference.md; X1..X10 = mục bổ sung.
Exit 0: không có FAIL (WARN vẫn cho qua) · 1: có FAIL · 2: sai cách gọi hoặc file không đọc được.

Validator chỉ chứng minh JSON nhất quán với các quy tắc đã ghi trong skill, KHÔNG thay cho bước test
bằng cURL hoặc sự kiện thật (C7) và không chứng minh nền tảng chấp nhận payload.
"""
import argparse
import json
import re
import sys

LINK_HANDLES = {'next_nodes': '2', 'success_next_nodes': 'success_action_step', 'fail_next_nodes': 'fail_action_step'}
VAR_RE = re.compile(r'\{\{\s*([^{}\s]+)\s*\}\}')
RANDOM_CODE_RE = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])[A-Za-z0-9]{10}$')
# Biến hệ thống đã ghi trong references (concepts.md mục 3, node-catalog.md mục 5, ui-build-and-test.md mục 1, 4).
SYSTEM_PREFIXES = ('ct_', 'ca_', 'social_', 'form_', 'utm_', 'current_', 'contact_', 'ticket_', 'interactive_',
                   'last_', 'total_', 'closest_', 'user_owner_', 'change_status_', 'transfer_agent_', 'opportunity_')
SYSTEM_NAMES = {'full_name', 'phone_number', 'mail', 'email', 'age', 'gender1', 'note', 'win_lose'}
NON_TERMINAL_LAST = ('DELAY', 'CONDITION')


class Report:
    def __init__(self):
        self.lines = []

    def add(self, level, code, msg, path=''):
        self.lines.append((level, code, msg, path))

    def has_fail(self):
        return any(l[0] == 'FAIL' for l in self.lines)

    def emit(self):
        out = []
        for level, code, msg, path in self.lines:
            out.append(f'{level} {code} {msg}' + (f' [{path}]' if path else ''))
        out.append('RESULT ' + ('FAIL' if self.has_fail() else 'PASS'))
        return '\n'.join(out)


def load(path):
    with open(path, encoding='utf-8-sig') as f:
        obj = json.load(f)
    if isinstance(obj, dict) and isinstance(obj.get('payload'), dict) and 'nodes' not in obj:
        obj = obj['payload']
    if not isinstance(obj, dict):
        raise ValueError('JSON gốc không phải object flow')
    return obj


def hk(v):
    """Khoá băm được cho id/mã: giữ nguyên kiểu vô hướng, còn list/dict (JSON hỏng) thì đổi sang chuỗi JSON."""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def as_list(v):
    if v is None or v == '':
        return []
    if isinstance(v, list):
        return v
    return [v]


def node_links(node, i):
    """Trả về [(handle, target, json_path)] của mọi liên kết khai trong node."""
    out = []
    for ci, c in enumerate(node.get('conditions') or []):
        if isinstance(c, dict):
            for t in as_list(c.get('next_nodes')):
                out.append((str(c.get('id')), hk(t), f'nodes[{i}].conditions[{ci}].next_nodes'))
    for key, handle in LINK_HANDLES.items():
        for t in as_list(node.get(key)):
            out.append((handle, hk(t), f'nodes[{i}].{key}'))
    return out


def actions_of(node):
    return [a for a in (node.get('actions') or []) if isinstance(a, dict)]


def walk_strings(obj, path=''):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f'{path}.{k}' if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f'{path}[{i}]')


def walk_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk_dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_dicts(v)


def declared_vars(flow):
    """codes: mã biến đã khai báo; names: tên hiển thị -> mã (để bắt lỗi gõ tên thay mã)."""
    codes, names = set(), {}

    def reg(code, name=None):
        if code:
            codes.add(str(code))
            if name:
                names[str(name).strip()] = str(code)

    for v in flow.get('custom_variables') or []:
        if isinstance(v, dict):
            reg(v.get('field_code'), v.get('name'))
    for v in flow.get('variables') or []:
        if isinstance(v, dict):
            reg(v.get('name'))
    for node in flow.get('nodes') or []:
        if not isinstance(node, dict):
            continue
        for v in node.get('variables') or []:
            if isinstance(v, dict):
                reg(v.get('name'))
        for d in walk_dicts([node.get('conditions'), node.get('actions')]):
            for mv in d.get('multi_variables') or []:
                if isinstance(mv, dict):
                    reg(mv.get('field_code'), mv.get('field_name'))
            if d.get('variable_code'):
                reg(d.get('variable_code'), d.get('variable_name'))
            if d.get('field_code') and d.get('field_name') and 'field_type' in d:
                # trường của FORM_DIALOG: giá trị nhân viên nhập thành biến {{<field_code>}} (node-catalog mục 4)
                reg(d.get('field_code'), d.get('field_name'))
    return codes, names


def is_system_var(code):
    return code in SYSTEM_NAMES or code.startswith(SYSTEM_PREFIXES) or '-' in code


def chat_gpt_vars(flow):
    """field_code -> prompt của các biến LLM (CREATE_CUSTOM_VARIABLE CHAT_GPT)."""
    out = {}
    for node in flow.get('nodes') or []:
        if not isinstance(node, dict):
            continue
        for a in actions_of(node):
            data = a.get('data') or {}
            if a.get('type') != 'CREATE_CUSTOM_VARIABLE' or data.get('type') != 'CHAT_GPT':
                continue
            for cv in data.get('config_variables') or []:
                for mv in ((cv or {}).get('config') or {}).get('multi_variables') or []:
                    if isinstance(mv, dict) and mv.get('field_code'):
                        out[hk(mv['field_code'])] = str(mv.get('content') or '')
    return out


def check(flow, mode='pre', sent=None, quota=None, context=None):
    r = Report()
    nodes = flow.get('nodes')
    if not isinstance(nodes, list):
        r.add('FAIL', 'C1', 'thiếu mảng nodes', 'nodes')
        return r
    nodes = [n for n in nodes if isinstance(n, dict)]
    by_id = {}
    for i, n in enumerate(nodes):
        nid = hk(n.get('id'))
        if not isinstance(n.get('id'), str) or not n.get('id'):
            r.add('FAIL', 'C2', f'id nút phải là chuỗi khác rỗng, đang là {nid!r}', f'nodes[{i}].id')
        if nid in by_id:
            r.add('FAIL', 'C2', f'id nút trùng: {nid}', f'nodes[{i}].id')
        by_id[nid] = (i, n)
    work = [(i, n) for i, n in enumerate(nodes) if n.get('node_type') != 'DESCRIPTION']

    # C1 trigger
    firsts = [(i, n) for i, n in enumerate(nodes) if n.get('is_first_node')]
    kick = flow.get('kick_off') if isinstance(flow.get('kick_off'), dict) else {}
    if len(firsts) != 1:
        r.add('FAIL', 'C1', f'cần đúng 1 nút is_first_node:true, đang có {len(firsts)}', 'nodes[*].is_first_node')
    else:
        i, n = firsts[0]
        conds = n.get('conditions') or []
        ctype = conds[0].get('type') if conds and isinstance(conds[0], dict) else None
        if n.get('node_type') != 'CONDITION':
            r.add('FAIL', 'C1', f'nút trigger phải là CONDITION, đang là {n.get("node_type")}', f'nodes[{i}].node_type')
        elif not ctype:
            r.add('FAIL', 'C1', 'trigger thiếu conditions[0].type', f'nodes[{i}].conditions[0].type')
        elif kick.get('event') and kick.get('event') != ctype:
            r.add('FAIL', 'C1', f'kick_off.event={kick.get("event")} lệch conditions[0].type={ctype}', 'kick_off.event')
        elif not kick.get('event'):
            r.add('WARN', 'C1', f'không có kick_off.event để đối chiếu với trigger {ctype}', 'kick_off')
        else:
            r.add('PASS', 'C1', f'trigger {ctype} khớp kick_off.event')

    # X2 kiểu trường liên kết
    x2 = 0
    for i, n in work:
        for key in ('success_next_nodes', 'fail_next_nodes'):
            v = n.get(key)
            if v not in (None, '') and not isinstance(v, str):
                r.add('FAIL', 'X2', f'{key} phải là chuỗi, đang là {type(v).__name__}', f'nodes[{i}].{key}')
                x2 += 1
        v = n.get('next_nodes')
        if v is not None and not isinstance(v, list):
            r.add('FAIL', 'X2', f'next_nodes phải là mảng, đang là {type(v).__name__}', f'nodes[{i}].next_nodes')
            x2 += 1
        for ci, c in enumerate(n.get('conditions') or []):
            if isinstance(c, dict) and c.get('next_nodes') is not None and not isinstance(c.get('next_nodes'), list):
                r.add('FAIL', 'X2', 'conditions[].next_nodes phải là mảng', f'nodes[{i}].conditions[{ci}].next_nodes')
                x2 += 1
    if not x2:
        r.add('PASS', 'X2', 'success/fail_next_nodes là chuỗi, next_nodes là mảng')

    # C2 id đích tồn tại
    links = []  # (src, handle, tgt, path)
    missing = 0
    for i, n in work:
        for handle, tgt, path in node_links(n, i):
            links.append((hk(n.get('id')), handle, tgt, path))
            if tgt not in by_id:
                r.add('FAIL', 'C2', f'nút {hk(n.get("id"))} trỏ tới id không tồn tại: {tgt}', path)
                missing += 1

    # X1 edge và node khớp hai chiều
    edges = flow.get('edges')
    conns = edges.get('connections') if isinstance(edges, dict) else None
    x1 = 0
    if not isinstance(conns, list):
        r.add('FAIL', 'X1', 'thiếu edges.connections (nhánh phải lưu cả trong node lẫn edge)', 'edges.connections')
        x1 += 1
        conns = []
    edge_set = {}
    for ei, e in enumerate(conns):
        if not isinstance(e, dict):
            continue
        key = (hk(e.get('source')), str(e.get('sourceHandle')), hk(e.get('target')))
        edge_set[key] = ei
        if str(e.get('targetHandle')) != '1':
            r.add('WARN', 'X1', f'targetHandle nên là "1", đang là {e.get("targetHandle")!r}', f'edges.connections[{ei}].targetHandle')
    link_set = set()
    for src, handle, tgt, path in links:
        link_set.add((src, handle, tgt))
        if (src, handle, tgt) not in edge_set:
            r.add('FAIL', 'X1', f'thiếu edge {src} --{handle}--> {tgt}', path)
            x1 += 1
    for key, ei in edge_set.items():
        if key not in link_set:
            r.add('FAIL', 'X1', f'edge {key[0]} --{key[1]}--> {key[2]} không có liên kết tương ứng trong node '
                  f'(sai sourceHandle hoặc node thiếu next)', f'edges.connections[{ei}]')
            x1 += 1
    if not x1:
        r.add('PASS', 'X1', f'{len(link_set)} liên kết khớp edges.connections, đúng sourceHandle')
    if missing or x1:
        r.add('FAIL', 'C2', 'liên kết nút/edge chưa khớp (xem X1 và các dòng C2 ở trên)')
    else:
        r.add('PASS', 'C2', 'mọi id đích tồn tại và có edge tương ứng')

    # X3 nút cuối
    x3 = 0
    for i, n in work:
        if not node_links(n, i) and n.get('node_type') in NON_TERMINAL_LAST:
            r.add('FAIL', 'X3', f'nút cuối {n.get("id")} là {n.get("node_type")}: lưu sẽ thất bại, kết thúc bằng nút Hành động',
                  f'nodes[{i}]')
            x3 += 1
    if not x3:
        r.add('PASS', 'X3', 'không có nút cuối là DELAY hoặc CONDITION')

    # X7 nút mồ côi
    if len(firsts) == 1:
        seen, stack = set(), [hk(firsts[0][1].get('id'))]
        while stack:
            nid = stack.pop()
            if nid in seen or nid not in by_id:
                continue
            seen.add(nid)
            idx, nn = by_id[nid]
            stack.extend(t for _, t, _ in node_links(nn, idx))
        orphans = [(i, n) for i, n in work if hk(n.get('id')) not in seen]
        for i, n in orphans:
            r.add('FAIL', 'X7', f'nút mồ côi {n.get("id")} ({n.get("node_type")}): không đi tới được từ trigger', f'nodes[{i}]')
        if not orphans:
            r.add('PASS', 'X7', 'mọi nút đi tới được từ trigger')
    else:
        r.add('WARN', 'X7', 'không kiểm được nút mồ côi vì trigger không hợp lệ (C1)')

    # C3 / X4 biến
    codes, names = declared_vars(flow)
    ctx_codes = set()
    if context:
        for a in context.get('attributes') or []:
            if isinstance(a, dict) and a.get('code'):
                ctx_codes.add(str(a['code']))
    x4 = 0
    x4w = 0
    for i, n in work:
        for path, s in walk_strings(n, f'nodes[{i}]'):
            for code in VAR_RE.findall(s):
                if code in codes or code in ctx_codes:
                    continue
                if code in names:
                    r.add('FAIL', 'X4', f'{{{{{code}}}}} là TÊN biến, phải dùng mã {{{{{names[code]}}}}}', path)
                    x4 += 1
                elif code.startswith('<') or RANDOM_CODE_RE.match(code):
                    r.add('FAIL', 'X4', f'{{{{{code}}}}} chưa được khai báo (trigger multi_variables, custom_variables, '
                          f'biến thu thập, biến form)', path)
                    x4 += 1
                elif not is_system_var(code):
                    r.add('WARN', 'X4', f'{{{{{code}}}}} không có trong danh sách khai báo hay biến hệ thống đã ghi: '
                          f'Cần xác nhận', path)
                    x4w += 1
    if x4:
        r.add('FAIL', 'C3', f'{x4} tham chiếu biến chưa khai báo (xem X4)')
    elif x4w:
        r.add('WARN', 'C3', f'còn {x4w} mã {{{{...}}}} chưa xác định được là biến đã khai báo (xem X4): Cần xác nhận')
    else:
        r.add('PASS', 'C3', 'mọi {{mã}} tham chiếu tới biến đã khai báo hoặc biến hệ thống')
        r.add('PASS', 'X4', 'không có mã biến lạ')

    # C4 / X5 giá trị so sánh với kết quả AI
    gpt = chat_gpt_vars(flow)
    x5 = 0
    for i, n in work:
        for ci, c in enumerate(n.get('conditions') or []):
            if not isinstance(c, dict):
                continue
            for di, d in enumerate(c.get('data') or []):
                if not isinstance(d, dict):
                    continue
                for k, cc in enumerate(d.get('compare_conditions') or []):
                    if not isinstance(cc, dict):
                        continue
                    base = f'nodes[{i}].conditions[{ci}].data[{di}].compare_conditions[{k}]'
                    vals = []
                    for vi, v in enumerate(cc.get('values') or []):
                        if isinstance(v, dict):
                            for kk in ('start_value', 'end_value'):
                                if isinstance(v.get(kk), str):
                                    vals.append((v[kk], f'{base}.values[{vi}].{kk}'))
                    for vi, v in enumerate(cc.get('ml_values') or []):
                        if isinstance(v, str):
                            vals.append((v, f'{base}.ml_values[{vi}]'))
                    prompt = gpt.get(hk(cc.get('field_code')))
                    for v, p in vals:
                        if v != v.strip():
                            r.add('FAIL', 'X5', f'giá trị so sánh {v!r} có khoảng trắng thừa: không bao giờ khớp', p)
                            x5 += 1
                        elif prompt is not None and v and v not in prompt:
                            r.add('FAIL', 'X5', f'giá trị {v!r} không có trong prompt của biến AI {cc.get("field_code")}', p)
                            x5 += 1
    if x5:
        r.add('FAIL', 'C4', f'{x5} giá trị so sánh lệch hoặc có khoảng trắng (xem X5)')
    else:
        r.add('PASS', 'C4', 'giá trị so sánh không có khoảng trắng thừa, khớp mã trong prompt AI')
        r.add('PASS', 'X5', 'mã AI khớp giá trị CONDITION')

    # C5 / X6 DELAY trước GET_RELATED CLOSEST_CALL khi đi sau ADD_TICKET
    preds = {}
    for src, _, tgt, _ in links:
        preds.setdefault(tgt, set()).add(src)

    def types(nn):
        return [a.get('type') for a in actions_of(nn)]

    def is_delay(nn):
        return nn.get('node_type') == 'DELAY' or 'DELAY' in types(nn)

    def has_closest_call(a):
        return a.get('type') == 'GET_RELATED' and 'CLOSEST_CALL' in ((a.get('data') or {}).get('options') or [])

    x6 = 0
    for i, n in work:
        acts = actions_of(n)
        for ai, a in enumerate(acts):
            if not has_closest_call(a):
                continue
            path = f'nodes[{i}].actions[{ai}]'
            before = [b.get('type') for b in acts[:ai]]
            if 'ADD_TICKET' in before and 'DELAY' not in before[before.index('ADD_TICKET'):]:
                r.add('FAIL', 'X6', 'ADD_TICKET rồi GET_RELATED CLOSEST_CALL trong cùng nút, thiếu DELAY 5–10 giây', path)
                x6 += 1
                continue
            if 'DELAY' in before:
                continue
            seen, stack, bad = set(), list(preds.get(hk(n.get('id')), ())), None
            while stack and not bad:
                pid = stack.pop()
                if pid in seen or pid not in by_id:
                    continue
                seen.add(pid)
                pn = by_id[pid][1]
                if is_delay(pn):
                    continue
                if 'ADD_TICKET' in types(pn):
                    bad = pid
                    break
                stack.extend(preds.get(pid, ()))
            if bad:
                r.add('FAIL', 'X6', f'đường từ ADD_TICKET ({bad}) tới GET_RELATED CLOSEST_CALL không qua DELAY', path)
                x6 += 1
    if x6:
        r.add('FAIL', 'C5', 'thiếu DELAY trước GET_RELATED cuộc gọi sau ADD_TICKET (xem X6)')
    else:
        r.add('PASS', 'C5', 'có DELAY trước GET_RELATED CLOSEST_CALL khi đi sau ADD_TICKET (hoặc không áp dụng)')
        r.add('PASS', 'X6', 'thứ tự ADD_TICKET → DELAY → GET_RELATED hợp lệ')

    # C6 quota + trạng thái
    q = quota
    if q is None and context:
        q = ((context.get('quota') or {}).get('nodes_per_flow'))
    try:
        q = int(q) if q not in (None, '') else None
    except (TypeError, ValueError):
        q = None
    if q is None:
        r.add('WARN', 'C6', f'{len(nodes)} nút; không biết quota nút mỗi flow (--quota hoặc --context): Cần xác nhận')
    elif len(nodes) > q:
        r.add('FAIL', 'C6', f'{len(nodes)} nút vượt quota {q}', 'nodes')
    else:
        r.add('PASS', 'C6', f'{len(nodes)}/{q} nút')
    pub = flow.get('is_publish')
    if mode == 'post':
        if pub is True and flow.get('is_draft') is not True:
            r.add('FAIL', 'C6', 'bản GET đang ở trạng thái đã xuất bản: script chỉ được lưu nháp', 'is_publish')
        elif pub is True:
            r.add('WARN', 'C6', 'is_publish=true và is_draft=true cùng lúc: Cần xác nhận ngữ nghĩa', 'is_publish')
        elif pub is False:
            r.add('PASS', 'C6', 'chưa xuất bản')
        else:
            r.add('WARN', 'C6', 'bản GET không có is_publish kiểu bool: không xác định được trạng thái xuất bản, '
                  'Cần xác nhận', 'is_publish')
    elif pub is True:
        r.add('WARN', 'C6', 'payload có is_publish=true: script chỉ được lưu nháp (omi_save không có cờ xuất bản); '
              'flow mới phải để chưa xuất bản tới khi user duyệt. Sửa flow đang chạy thì lưu nháp hoặc tạo flow mới',
              'is_publish')

    # C7 test thật
    r.add('WARN', 'C7', 'validator không thay test: gọi URL webhook bằng cURL hoặc tạo sự kiện thật (khi user đồng ý), '
          'rồi xem tab Lịch sử')

    # X8 thuộc tính danh sách không nhận biến
    if not context:
        r.add('WARN', 'X8', 'không có --context: chưa kiểm được thuộc tính khách kiểu danh sách (is_list)')
    else:
        attrs = [a for a in context.get('attributes') or [] if isinstance(a, dict)]
        list_codes = {str(a.get('code')) for a in attrs if a.get('is_list') is True}
        unknown_codes = {str(a.get('code')) for a in attrs if a.get('is_list') is None}
        x8 = 0
        for i, n in work:
            for ai, a in enumerate(actions_of(n)):
                if a.get('type') not in ('ASSIGN_ATTRIBUTE_STRUCTURE', 'UPDATE_INFO_CONTACT'):
                    continue
                for d in walk_dicts(a.get('data')):
                    fc = str(d.get('field_code'))
                    if fc not in list_codes and fc not in unknown_codes:
                        continue
                    if not any('{{' in s for _, s in walk_strings({k: v for k, v in d.items() if k != 'field_code'})):
                        continue
                    if fc in list_codes:
                        r.add('FAIL', 'X8', f'thuộc tính danh sách {fc} không nhận biến: '
                              f'rẽ nhánh theo giá trị, mỗi nhánh gán một giá trị cố định', f'nodes[{i}].actions[{ai}]')
                        x8 += 1
                    else:
                        r.add('WARN', 'X8', f'gán biến vào thuộc tính {fc} chưa rõ kiểu (is_list=null): Cần xác nhận '
                              f'trên giao diện trước khi lưu', f'nodes[{i}].actions[{ai}]')
        if not x8:
            r.add('PASS', 'X8', 'không gán biến vào thuộc tính đã biết là kiểu danh sách')

    # X9 name_mappings (bản editor) — WARN cho tới khi có template editor verified
    nm = flow.get('name_mappings')
    if not nm:
        r.add('WARN', 'X9', 'thiếu name_mappings (bản editor): editor có thể hiện "Chưa có dữ liệu"; '
              'sửa nút phải sửa cả nodes lẫn name_mappings (node-catalog.md mục 6)', 'name_mappings')
    elif isinstance(nm, list):
        ids = {hk(m.get('id')) for m in nm if isinstance(m, dict) and m.get('id')}
        lack = [hk(n.get('id')) for _, n in work if hk(n.get('id')) not in ids] if ids else []
        if not ids:
            r.add('WARN', 'X9', 'name_mappings không rỗng nhưng không phần tử nào có khoá id: không đối chiếu được với '
                  'nodes; phần tử phải chép nguyên từ bản GET của nút cùng loại (node-catalog.md mục 6): Cần xác nhận',
                  'name_mappings')
        elif lack:
            r.add('WARN', 'X9', f'name_mappings thiếu bản editor của {len(lack)} nút: {lack[:5]}', 'name_mappings')
        else:
            r.add('WARN', 'X9', 'name_mappings đủ id với nodes; nội dung phần tử chưa kiểm được (phải chép từ bản GET nút '
                  'cùng loại): Cần xác nhận', 'name_mappings')
    else:
        r.add('WARN', 'X9', 'name_mappings không phải mảng: Cần xác nhận', 'name_mappings')

    # X10 so bản gửi với bản GET
    if sent is not None:
        sent_nodes = sent.get('nodes') if isinstance(sent.get('nodes'), list) else []
        sid = {hk(n.get('id')) for n in sent_nodes if isinstance(n, dict)}
        gid = {hk(n.get('id')) for n in nodes}
        sc = len(((sent.get('edges') or {}).get('connections')) or [])
        gc = len(((flow.get('edges') or {}).get('connections')) or [])
        if sid != gid:
            r.add('FAIL', 'X10', f'id nút lệch giữa bản gửi và bản GET: thiếu {sorted(map(str, sid - gid))[:5]}, '
                  f'thừa {sorted(map(str, gid - sid))[:5]}', 'nodes')
        elif sc != gc:
            r.add('FAIL', 'X10', f'số edge lệch: gửi {sc}, GET {gc}', 'edges.connections')
        else:
            r.add('PASS', 'X10', 'bản GET khớp bản gửi về id nút và số edge')
    elif mode == 'post':
        r.add('WARN', 'X10', 'mode post mà không có --sent: chưa so được bản gửi với bản GET')
    return r


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Kiểm JSON flow OMIFlow (offline, chỉ đọc).')
    ap.add_argument('file', help='flow JSON (bản sắp gửi hoặc bản GET lại)')
    ap.add_argument('--mode', choices=('pre', 'post'), default='pre')
    ap.add_argument('--sent', help='payload đã gửi (dùng ở mode post để so với bản GET)')
    ap.add_argument('--quota', type=int, help='quota số nút mỗi flow theo gói')
    ap.add_argument('--context', help='tenant_context.json (attributes[].is_list, quota)')
    args = ap.parse_args(argv)
    try:
        flow = load(args.file)
        sent = load(args.sent) if args.sent else None
        context = None
        if args.context:
            with open(args.context, encoding='utf-8-sig') as f:
                context = json.load(f)
            if not isinstance(context, dict):
                raise ValueError('--context phải là object JSON (khuôn tenant_context.template.json)')
    except (OSError, ValueError) as e:
        print(f'Không đọc được file: {e}', file=sys.stderr)
        return 2
    rep = check(flow, args.mode, sent, args.quota, context)
    print(rep.emit())
    return 1 if rep.has_fail() else 0


if __name__ == '__main__':
    sys.exit(main())
