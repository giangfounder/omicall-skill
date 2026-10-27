"""Rút template của MỘT loại nút từ bản GET thật (đã dựng 1 nút bằng giao diện) — đã che hết dữ liệu tenant.

  python <thư mục skill>/scripts/extract_template.py --from <GET.json> --node <id nút> --type <TYPE> --out <file>
         [--edges] [--mark-verified --evidence <báo cáo validator mode post>] [--allowlist <json>]

Xuất {_meta, type, runtime, editor[], edges[]}:
- runtime: phần tử trong `nodes` có id = --node;
- editor : phần tử trong `name_mappings` / `org_nodes` có id = --node (schema editor chưa kiểm chứng ở mọi loại: chỉ khớp
           theo khoá `id`, giữ nguyên cấu trúc);
- edges  : (với --edges) cạnh trong `edges.connections` / `connections` có source hoặc target = --node.
Che dữ liệu (giữ nguyên khoá và kiểu, chỉ thay giá trị chuỗi):
- id thật -> <node_id>, <node_id_2>…, <case_id>…, <action_id>…, <id>; tenant_id -> <tenant_id>; field_code -> <code10>;
  sourceHandle của cạnh là id trường hợp (conditions[].id) của nút nguồn -> luôn <case_id…> (kể cả khi nút nguồn không
  nằm trong phần rút); chuỗi trông như id (hex 24 ký tự, UUID) ở mọi khoá, kể cả trong danh sách (tags…) -> <id>;
- chuỗi tự do (content, instruction, description, url, body_json, headers, query_prompt, prompt, system_prompt,
  personality, name, label, text, title, message, note, start_call_instruction, giá trị so sánh…) -> <text> / <url>;
- chuỗi khác không giống mã enum (có dấu cách, có dấu tiếng Việt, quá dài) -> <text>.
Sau khi che, còn sót SĐT, email, JWT, UUID, hex 24 ký tự (ngoài allowlist) hoặc domain tenant '<domain>.omicrm.io' thật -> exit 1,
không ghi file; chỉ in đường dẫn JSON + loại + giá trị đã che bớt (ví dụ 09******32), không in nguyên giá trị.
In danh sách khoá đã che. --out bắt buộc (không có đường mặc định trong thư mục skill).
_meta.verified mặc định false. Chỉ ghi {verified: true, source: 'GET', date, evidence_sha256} khi có --mark-verified kèm
--evidence là báo cáo validator mode post chứa 'RESULT PASS'. Chỉ agent chính hoặc user duyệt mới dùng cờ này;
subagent không dùng.
Không gọi mạng. Exit: 0 xong; 1 còn sót dữ liệu nhạy cảm; 2 sai cách gọi / không thấy nút / evidence không hợp lệ.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

FREE_TEXT = {
    'content', 'instruction', 'description', 'url', 'body_json', 'headers', 'query_prompt', 'prompt', 'system_prompt',
    'personality', 'name', 'label', 'text', 'title', 'message', 'note', 'start_call_instruction', 'response_config',
    'value', 'start_value', 'end_value', 'value_string', 'ml_values', 'field_name', 'shorthand_query', 'key', 'body',
    'query', 'params', 'transfer_agent_note', 'full_name', 'fullname', 'fullName', 'phone', 'phone_number', 'email',
    'subject', 'template', 'greeting', 'example', 'examples', 'answer', 'question', 'placeholder', 'link', 'image',
    'avatar', 'file_name', 'file_url', 'webhook_url', 'assistant_name', 'tags', 'tag', 'web_hook_id',
}
CODE_KEYS = {'field_code', 'code', 'variable', 'variable_name'}
KEEP_HANDLES = {'1', '2', 'success_action_step', 'fail_action_step', 'NEXT_STEP'}
ID_LIST_KEYS = {'next_nodes', 'ids', 'kick_off_ids'}
ID_STR_KEYS = {'success_next_nodes', 'fail_next_nodes', 'source', 'target', 'sourceHandle', 'targetHandle'}
ID_LIKE = re.compile(r'^(?:[0-9a-fA-F]{24}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$')
ENUM_LIKE = re.compile(r'^[A-Za-z0-9_.:#+/=<>!-]{0,40}$')

RE_PHONE = re.compile(r'(?<![\d.])(?:\+?84|0)[35789]\d{8}(?!\d)')
RE_EMAIL = re.compile(r'[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}')
RE_JWT = re.compile(r'eyJ[A-Za-z0-9_-]{6,}')
RE_UUID = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
RE_HEX24 = re.compile(r'(?<![0-9a-fA-F])[0-9a-fA-F]{24}(?![0-9a-fA-F])')
RE_TENANT = re.compile(r'(?<![\w{<%>$.-])([A-Za-z0-9][A-Za-z0-9-]*)\.omicrm\.io')
# id hệ thống công khai ghi trong tài liệu skill (tools/sensitive_allowlist.json) — được phép còn lại
DEFAULT_ALLOW = {'634d6c3042d14f7ec2df05e4', '634d6c0142d14f7ec2df0073', 'form', 'www', 'example'}


class Usage(Exception):
    pass


def load_allow(path):
    allow = set(DEFAULT_ALLOW)
    cands = [path] if path else []
    here = os.path.dirname(os.path.abspath(__file__))
    cands.append(os.path.join(here, '..', '..', 'tools', 'sensitive_allowlist.json'))  # khi chạy trong repo
    for c in cands:
        try:
            with open(c, encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        for k in ('phones', 'emails', 'tenant_domains', 'system_ids'):
            for x in data.get(k, []):
                if isinstance(x, dict) and 'value' in x:
                    allow.add(str(x['value']))
        if path:
            break
    return allow


def _payload(obj):
    if isinstance(obj, dict) and isinstance(obj.get('payload'), dict) and ('nodes' in obj['payload'] or 'org_nodes' in obj['payload']):
        return obj['payload']
    return obj


def find_node(doc, node_id):
    for n in doc.get('nodes') or []:
        if isinstance(n, dict) and str(n.get('id')) == node_id:
            return n
    return None


def find_editor(doc, node_id):
    out = []
    for key in ('name_mappings', 'org_nodes'):
        for n in doc.get(key) or []:
            if isinstance(n, dict) and str(n.get('id')) == node_id:
                out.append({'_tu': key, 'item': n})
    return out


def find_edges(doc, node_id):
    edges = doc.get('edges')
    conns = (edges.get('connections') if isinstance(edges, dict) else edges) or doc.get('connections') or []
    return [e for e in conns if isinstance(e, dict) and node_id in (str(e.get('source')), str(e.get('target')))]


class Masker:
    def __init__(self, tenant_id=None):
        self.ids = {}           # id thật -> placeholder (theo thứ tự gặp, ổn định)
        self.count = {}
        self.masked = set()     # đường dẫn khoá đã che (bỏ chỉ số mảng)
        self.tenant_id = tenant_id

    def _new(self, kind):
        self.count[kind] = self.count.get(kind, 0) + 1
        n = self.count[kind]
        return '<%s>' % kind if n == 1 else '<%s_%d>' % (kind, n)

    def collect(self, obj, ctx='id'):
        """Lượt 1: gom id theo ngữ cảnh (nút, trường hợp, hành động) để thay nhất quán ở mọi chỗ."""
        if isinstance(obj, dict):
            if 'id' in obj and isinstance(obj['id'], str) and obj['id'] and obj['id'] not in self.ids:
                self.ids[obj['id']] = self._new(ctx)
            for k, v in obj.items():
                sub = {'conditions': 'case_id', 'actions': 'action_id', 'cases': 'case_id'}.get(k, 'id')
                self.collect(v, sub)
        elif isinstance(obj, list):
            for v in obj:
                self.collect(v, ctx)

    def sub_ids(self, s):
        for real in sorted(self.ids, key=len, reverse=True):
            if real in s:
                s = s.replace(real, self.ids[real])
        if self.tenant_id and self.tenant_id in s:
            s = s.replace(self.tenant_id, '<tenant_id>')
        return s

    def mark(self, path):
        self.masked.add(re.sub(r'\[\d+\]', '[]', path))

    def str_value(self, key, s, path):
        if s in self.ids:
            if s != self.ids[s]:
                self.mark(path)
            return self.ids[s]
        k = key or ''
        if k in ('tenant_id',):
            self.mark(path)
            return '<tenant_id>'
        if k in CODE_KEYS:
            self.mark(path)
            return '<code10>'
        if k in ID_STR_KEYS:
            if k in ('sourceHandle', 'targetHandle') and s in KEEP_HANDLES:
                return s
            new = self.sub_ids(s)
            if new != s:
                self.mark(path)
                return new
            if s and s not in KEEP_HANDLES:
                self.mark(path)
                return '<id>'
            return s
        if k == 'id' or k == '_id' or k.endswith('_id') or k.endswith('Id'):
            if s:
                self.mark(path)
                return '<id>'
            return s
        if ID_LIKE.match(s):  # id trong khoá tự do / danh sách (tags: [<hex24>]…) vẫn là id
            self.mark(path)
            return '<id>'
        if re.match(r'^https?://', s) or k in ('url', 'link', 'webhook_url', 'file_url', 'image', 'avatar'):
            if s:
                self.mark(path)
                return '<url>'
            return s
        if k in FREE_TEXT:
            if s:
                self.mark(path)
                return '<text>'
            return s
        new = self.sub_ids(s)
        if new != s:
            self.mark(path)
            return new
        if not ENUM_LIKE.match(s):
            self.mark(path)
            return '<text>'
        return s

    def walk(self, obj, key=None, path='$'):
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                nk = self.ids.get(k, k) if isinstance(k, str) else k
                if nk != k:
                    self.mark(path + '.{khoá id}')
                child_key = k
                if k in ('source', 'target') and not _is_edge(obj):
                    child_key = k + '__thuong'  # 'source' của phiếu ghi ('crud'…) không phải id cạnh
                if k in ID_LIST_KEYS or k.endswith('_ids'):
                    child_key = '__idlist__'
                out[nk] = self.walk(v, child_key, '%s.%s' % (path, nk if nk == k else '<id>'))
            return out
        if isinstance(obj, list):
            return [self.walk(v, key, '%s[%d]' % (path, i)) for i, v in enumerate(obj)]
        if isinstance(obj, str):
            if key == '__idlist__':
                if obj in self.ids:
                    self.mark(path)
                    return self.ids[obj]
                if obj:
                    self.mark(path)
                    return '<id>'
                return obj
            return self.str_value(key, obj, path)
        return obj


def shorten(v):
    """Che bớt giá trị khi báo lỗi: giữ 2 ký tự đầu và 2 ký tự cuối (09******32)."""
    v = str(v)
    if len(v) <= 4:
        return '*' * len(v)
    return v[:2] + '*' * min(len(v) - 4, 8) + v[-2:]


def _scan(text, allow):
    for name, rx in (('SĐT', RE_PHONE), ('email', RE_EMAIL), ('JWT', RE_JWT), ('UUID', RE_UUID), ('hex24', RE_HEX24)):
        for m in rx.finditer(text):
            if m.group(0) not in allow:
                yield name, m.group(0)
    for m in RE_TENANT.finditer(text):
        if m.group(1).lower() not in allow:
            yield 'domain tenant', m.group(1)


def residual(obj, allow, path='$', hits=None):
    """Tìm dữ liệu nhạy cảm còn sót sau khi che. Trả về [(đường dẫn JSON, loại, giá trị đã che bớt)]."""
    hits = [] if hits is None else hits
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                for name, val in _scan(k, allow):
                    hits.append(('%s.{khoá}' % path, name, shorten(val)))
            residual(v, allow, '%s.%s' % (path, k), hits)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            residual(v, allow, '%s[%d]' % (path, i), hits)
    elif isinstance(obj, str):
        for name, val in _scan(obj, allow):
            hits.append((path, name, shorten(val)))
    return hits


def _is_edge(d):
    return isinstance(d, dict) and ('sourceHandle' in d or 'targetHandle' in d)


def referenced_nodes(obj):
    """Id các nút được nhắc trong next_nodes / success_next_nodes / fail_next_nodes / source / target (thứ tự ổn định)."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'next_nodes' and isinstance(v, list):
                out.extend(x for x in v if isinstance(x, str))
            elif k in ('success_next_nodes', 'fail_next_nodes') and isinstance(v, str):
                out.append(v)
            elif k in ('source', 'target') and isinstance(v, str) and _is_edge(obj):
                out.append(v)
            else:
                out.extend(referenced_nodes(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(referenced_nodes(v))
    return out


def build(doc, node_id, typ, with_edges, tenant_id=None):
    doc = _payload(doc)
    if not isinstance(doc, dict):
        raise Usage('file --from không phải object JSON')
    node = find_node(doc, node_id)
    editor = find_editor(doc, node_id)
    if node is None and not editor:
        raise Usage('không thấy nút id %r trong nodes / name_mappings / org_nodes' % node_id)
    edges = find_edges(doc, node_id) if with_edges else []
    m = Masker(tenant_id or doc.get('tenant_id'))
    raw = {'runtime': node, 'editor': editor, 'edges': edges}
    m.ids[node_id] = '<node_id>'
    m.count['node_id'] = 1
    for ref in referenced_nodes(raw):  # nút khác được nối tới: đánh số theo thứ tự gặp
        if ref and ref not in m.ids:
            m.ids[ref] = m._new('node_id')
    m.collect(raw)
    for e in edges:  # sourceHandle = id trường hợp của nút nguồn: cùng kiểu placeholder với conditions[].id
        sh = e.get('sourceHandle')
        if isinstance(sh, str) and sh and sh not in KEEP_HANDLES and sh not in m.ids:
            m.ids[sh] = m._new('case_id')
    masked = m.walk(raw)
    return masked, sorted(m.masked)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--from', dest='src', required=True, help='bản GET thật (JSON)')
    ap.add_argument('--node', required=True, help='id nút cần rút')
    ap.add_argument('--type', required=True, help='tên loại nút, ví dụ WEB_HOOK, CONDITION, ADD_TICKET')
    ap.add_argument('--out', required=True, help='file template đầu ra (bắt buộc)')
    ap.add_argument('--edges', action='store_true', help='kèm các cạnh dính vào nút')
    ap.add_argument('--mark-verified', action='store_true', help='CHỈ agent chính hoặc user duyệt; subagent không dùng')
    ap.add_argument('--evidence', help='báo cáo validator mode post (phải có RESULT PASS)')
    ap.add_argument('--allowlist', help='JSON allowlist (mặc định tools/sensitive_allowlist.json nếu chạy trong repo)')
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if a.mark_verified:
        print('Nhắc: --mark-verified chỉ dùng khi agent chính hoặc user đã duyệt; subagent không dùng cờ này.')
    try:
        meta = {'verified': False, 'type': a.type,
                'ghi_chu': 'Rút từ bản GET, đã che dữ liệu tenant. Chưa đánh dấu kiểm chứng: dùng làm khuôn tham khảo, '
                           'lưu thử rồi GET lại và chạy validator.'}
        if a.mark_verified:
            if not a.evidence:
                raise Usage('--mark-verified cần --evidence <báo cáo validator mode post có RESULT PASS>')
            try:
                ev = open(a.evidence, 'rb').read()
            except OSError as e:
                raise Usage('không đọc được --evidence: %s' % e)
            if b'RESULT PASS' not in ev:
                raise Usage('--evidence không chứa RESULT PASS — không đánh dấu verified')
            meta = {'verified': True, 'source': 'GET', 'type': a.type, 'date': datetime.date.today().isoformat(),
                    'evidence_sha256': hashlib.sha256(ev).hexdigest()}
        elif a.evidence:
            raise Usage('--evidence chỉ dùng kèm --mark-verified')
        try:
            with open(a.src, encoding='utf-8') as f:
                doc = json.load(f)
        except (OSError, ValueError) as e:
            raise Usage('không đọc được --from: %s' % e)
        masked, keys = build(doc, a.node, a.type, a.edges)
    except Usage as e:
        print('LỖI: %s' % e)
        return 2
    out = {'_meta': meta, 'type': a.type, 'runtime': masked['runtime'], 'editor': masked['editor'], 'edges': masked['edges']}
    hits = residual(out, load_allow(a.allowlist))
    if hits:
        print('DỪNG: còn sót dữ liệu nhạy cảm sau khi che (không ghi file):')
        for path, kind, val in hits:
            print('  %s: %s %s' % (path, kind, val))
        return 1
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write('\n')
    print('Khoá đã che (%d):' % len(keys))
    for k in keys:
        print('  ' + k)
    print('runtime: %s | editor: %d | edges: %d' % ('có' if masked['runtime'] else 'không', len(masked['editor']),
                                                    len(masked['edges'])))
    print('Đã ghi %s (_meta.verified=%s)' % (a.out, str(meta['verified']).lower()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
