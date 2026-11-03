#!/usr/bin/env python3
"""Tối ưu 1 kịch bản Callbot Gen AI (bản GET) -> payload mới + file FAQ cho RAG (xem references/optimize-existing.md).
Chuẩn hoá biến lõi, tách mục KHO CÂU HỎI THƯỜNG GẶP ra RAG, vá cấu trúc theo schema skill."""
import copy, json, os, re, sys

CORE_NAMES = {
    'var_ho_ten': 'Họ và tên',
    'var_sdt': 'Số điện thoại liên hệ',
    'var_nhu_cau': 'Nhu cầu chính',
    'var_thoi_gian': 'Thời gian mong muốn',
    'var_khu_vuc': 'Khu vực hoặc chi nhánh',
    'var_dong_y': 'Đồng ý được liên hệ lại',
}
# ứng viên đổi mã -> mã chuẩn (chỉ đổi khi mã đích chưa có trong kịch bản)
RENAME = [
    ('var_so_dien_thoai', 'var_sdt'), ('var_dong_y_lien_he', 'var_dong_y'),
    ('var_ngay_gio', 'var_thoi_gian'), ('var_khung_gio', 'var_thoi_gian'),
    ('var_gio_goi_lai', 'var_thoi_gian'), ('var_gio_nghe_may', 'var_thoi_gian'),
    ('var_ngay', 'var_thoi_gian'),
    ('var_chi_nhanh', 'var_khu_vuc'), ('var_co_so', 'var_khu_vuc'),
    ('var_dich_vu', 'var_nhu_cau'),
]


def walk(o, fn):
    if isinstance(o, dict):
        fn(o)
        for v in list(o.values()):
            walk(v, fn)
    elif isinstance(o, list):
        for v in o:
            walk(v, fn)


def begin_node(d):
    return [n for n in d['nodes'] if n.get('node_type') == 'BEGIN'][0]


def codes_of(d):
    return [v['variable_code'] for v in begin_node(d)['ai_agent_config']['collect_variables']]


def rename_vars(d, log):
    for old, new in RENAME:
        cur = codes_of(d)
        if old in cur and new not in cur:
            s = json.dumps(d, ensure_ascii=False)
            s = re.sub(r'(?<![A-Za-z0-9_])' + re.escape(old) + r'(?![A-Za-z0-9_])', new, s)
            d.clear(); d.update(json.loads(s))
            log.append(f'đổi mã {old} -> {new}')
        elif old in cur:
            log.append(f'giữ {old} (đã có {new})')


def standardize_names(d):
    def fn(o):
        c = o.get('variable_code')
        if c in CORE_NAMES and 'variable_name' in o: o['variable_name'] = CORE_NAMES[c]
        c = o.get('field_code')
        if c in CORE_NAMES and 'field_name' in o: o['field_name'] = CORE_NAMES[c]
        c = o.get('id')
        if c in CORE_NAMES:
            if 'label' in o: o['label'] = CORE_NAMES[c]
            if 'oldName' in o: o['oldName'] = CORE_NAMES[c]; o['name'] = CORE_NAMES[c]
    walk(d, fn)


def extract_faq(d, doc_dir, title):
    b = begin_node(d)['ai_agent_config']
    ins = b['instruction']
    m = re.search(r'^# (?:KHO|CÂU HỎI THƯỜNG GẶP)[^\n]*\n(.*?)(?=^# |\Z)', ins, re.S | re.M)
    if not m:
        return None
    body = m.group(1).strip()
    pointer = ('# TRA CỨU KIẾN THỨC\nCâu hỏi thường gặp về giá tham khảo, giờ làm việc và chính sách: tra cứu trong '
               'kho tri thức đào tạo, luôn nói đó là mức tham khảo. Ngoài kho tri thức em không tự nêu thêm con số '
               'hay chính sách nào. Chưa có thông tin thì nói em xin chuyển nhân viên hỗ trợ.\n')
    new_ins = ins[:m.start()] + pointer + ins[m.end():]

    def fn(o):
        for k, v in o.items():
            if v == ins: o[k] = new_ins
    walk(d, fn)
    from docx import Document
    doc = Document()
    doc.add_heading(title, 1)
    doc.add_paragraph('Dữ liệu mẫu để trình diễn, không phải thông tin của doanh nghiệp thật. '
                      'Giá và chính sách chỉ là mức tham khảo.')
    for line in body.splitlines():
        line = line.strip().lstrip('-').strip()
        if not line or line.startswith('Ngoài kho'): continue
        if ':' in line:
            t, a = line.split(':', 1)
            doc.add_heading(t.strip(), 2); doc.add_paragraph(a.strip())
        else:
            doc.add_paragraph(line)
    path = os.path.join(doc_dir, title.replace(' ', '_') + '.docx')
    doc.save(path)
    return path


def patch_structure(d, log):
    b = begin_node(d)
    ai = b['ai_agent_config']['ai_analyze']
    conds = ai['conditions']
    xfer = (ai.get('bot_can_not_answer') or {}).get('next_node')
    keys = ['intent_code', 'intent_name', 'name', 'keywords', 'operator', 'compare_operator', 'percent',
            'next_node', 'repeat_contents', 'repeat_time', 'apply_targets', 'attachment', 'limit', 'limit_ai_config']
    types = [c.get('type') for c in conds]
    if 'bot_can_not_answer' not in types:
        c = {k: None for k in keys}; c.update({'data': [], 'id': 'bot_can_not_answer', 'type': 'bot_can_not_answer',
                                               'operator_type': None, 'action_steps': None, 'next_node': xfer})
        conds.append(c); log.append('thêm điều kiện hệ thống bot_can_not_answer')
    if 'customer_not_response' not in types:
        c = {k: None for k in keys}; c.update({'data': [], 'id': 'customer_not_response',
                                               'type': 'customer_not_response', 'operator_type': None, 'action_steps': None})
        conds.append(c); log.append('thêm điều kiện hệ thống customer_not_response')
    for c in conds:
        if c.get('type') == 'bot_can_not_answer' and not c.get('next_node'): c['next_node'] = xfer
    # C8: biến cho node ACTION nối từ intent thu biến
    names = {v['variable_code']: v['variable_name'] for v in b['ai_agent_config']['collect_variables']}
    byid = {n['id']: n for n in d['nodes']}
    for cn in d['connections']:
        if cn['source'] != b['id']: continue
        cond = next((c for c in conds if c.get('id') == cn.get('sourceHandle')), None)
        tgt = byid.get(cn['target'])
        if not cond or not tgt or tgt.get('node_type') != 'ACTION': continue
        steps = cond.get('action_steps') or []
        vcodes = [vc for s in steps if s.get('action') == 'collect_variables' for vc in (s.get('variables_code') or [])]
        if vcodes and tgt['actions'][0]['type'] == 'ADD_CLASSIFY':
            tgt['variables'] = [{'field_name': names.get(v, v), 'field_code': v, 'field_value': '', 'field_type': '',
                                 'type': 'COLLECT_INFO', 'is_dynamic_attribute': False} for v in vcodes]
            log.append(f'C8 biến cho {tgt["id"]}')
    # C9: classifies
    for n in d['nodes']:
        if n.get('node_type') == 'ACTION':
            for a in n.get('actions', []):
                if a['type'] == 'ADD_CLASSIFY':
                    ids = a['data'].get('ids', [])
                    a['data']['classifies'] = [{'name': i} for i in ids]
    for n in d['org_nodes']:
        for key in ('actions',):
            for a in n['data'].get(key, []) or []:
                if a.get('type') == 'ADD_CLASSIFY':
                    ids = a['datas'].get('ids', [])
                    a['datas']['classifies'] = [{'name': i} for i in ids]
        for od in n.get('orgDatas', []) or []:
            if od.get('type') == 'ADD_CLASSIFY':
                ids = od['datas'].get('ids', [])
                od['datas']['classifies'] = [{'name': i} for i in ids]
    # C10: END_CALL
    for n in d['nodes']:
        if n.get('node_type') == 'END_CALL' and not n.get('description'):
            org = next((o for o in d['org_nodes'] if o['id'] == n['id']), None)
            n['description'] = (org['data'].get('description') if org else None) or (
                'Kết thúc cuộc gọi: chỉ cúp sau khi khách xác nhận không còn nhu cầu. Bot cảm ơn khách, chúc sức khỏe, '
                'xin phép kết thúc, lịch sự tạm biệt rồi kết thúc cuộc gọi.')
            log.append('C10 mô tả END_CALL')


def main(src, outdir):
    os.makedirs(outdir, exist_ok=True)
    d = json.load(open(src, encoding='utf-8'))
    d = d.get('data', d) if 'nodes' not in d else d
    log = []
    base_name = d['name']
    rename_vars(d, log)
    standardize_names(d)
    faq = extract_faq(d, outdir, base_name.replace('Demo - ', 'FAQ ').replace(' OMI', ''))
    log.append('FAQ -> RAG: ' + (faq or 'KHÔNG tìm thấy mục KHO'))
    patch_structure(d, log)
    d['name'] = base_name + ' - Tối ưu'
    d['is_publish'] = False
    out = os.path.join(outdir, os.path.basename(src).replace('callbot_script_', 'opt_'))
    json.dump(d, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print(json.dumps({'out': out, 'faq': faq, 'log': log}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
