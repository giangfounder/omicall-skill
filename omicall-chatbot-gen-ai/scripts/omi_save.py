"""B6 của Đường nhanh: lưu một artefact qua API đã kiểm chứng rồi GET lại và kiểm tự động.

  python <thư mục skill>/scripts/omi_save.py <callbot|callflow|bot|flow> payload.json --domain <domain>
         [--new | --update] [--base base.json] [--confirm-update] [--dry-run] [--out-dir DIR]

Trình tự: (1) token (kiểm hạn + domain) -> (2) --new/--update -> (3) guard version so với --base (lệch -> exit 3)
-> (4) validator của skill, mode pre (FAIL -> exit 1) -> (5) POST multipart field 'file' -> (6) GET lại, validator mode post
kèm --sent, diff trường đã gửi với bản GET -> (7) in id, version, URL editor.

Bảng endpoint CHỈ gồm đường đã kiểm chứng:
  callbot, callflow : chatbot-gateway /callbot/script/add_v2 (multipart 'file'); GET /callbot/script/get/{id}
  bot               : chatbot-gateway /omiai_assistant/save_draft_v2 (multipart 'file', giữ _id); GET POST /omiai_assistant/get/{id}
  flow              : campaign-v1 /omi_v2/campaign/save_draft_v2 (multipart 'file') — CHỈ cho flow nháp có _id
                      (add_v2/update_v2 của OMIFlow chưa kiểm chứng nên không có ở đây).
Không có cờ xuất bản; is_publish giữ nguyên như payload. --new KHÔNG tự đổi is_publish: payload --new có is_publish:true
-> exit 2 (kịch bản mới chỉ lưu nháp; đặt is_publish:false trong payload, hoặc dựng bằng build_smartagent.py --new /
build_callflow.py — hai builder tự đặt false).
Không bật flow, không gắn hotline hay kênh.
Payload còn giá trị đã che ('***', 'Bearer ***', "***" trong chuỗi JSON — ví dụ bản *_outline.py --save hay file
*_sent.json) -> exit 2: lưu sẽ ghi đè bí mật thật bằng '***'. Dùng bản GET chưa che làm gốc, hoặc sửa phần đó trên giao diện.
Callbot/callflow: --new xoá id/uuid/public_key (tạo kịch bản mới); --update bắt buộc payload có CẢ id lẫn uuid và cờ
--confirm-update (script đang gắn hotline có thể chạy bản mới ngay — Cần xác nhận; kiểm list_hotlines bằng MCP).
--context <tenant_context.json>: chuyền cho validator ở cả mode pre và post (mọi validator nhận --context).
Riêng callflow --update: chuyền thêm cho verify_callflow.py mode post --base <file --base> hoặc --base-version <version
bản mới nhất lấy ở bước guard> (để kiểm C7 version tăng).
--dry-run: chạy validator pre rồi chỉ in request (Authorization đã che), không gửi gì.
File ghi ra (payload đã gửi, bản GET, báo cáo validator) đều qua mask_secrets, vào --out-dir (mặc định OMI_SCRATCH/tạm).
Validator chạy trên bản CHƯA che (file tạm chỉ tồn tại trong lúc validator chạy, xoá ngay sau đó) để kiểm đúng cái được gửi.
Exit: 0 xong; 1 validator FAIL; 2 sai cách gọi / bị từ chối / thiếu validator; 3 version lệch; 4 lỗi API.
"""
import argparse
import contextlib
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import omi_api  # noqa: E402

KINDS = {
    'callbot': {'service': 'chatbot', 'save': '/callbot/script/add_v2', 'get': ('GET', '/callbot/script/get/{id}'),
                'list': '/callbot/script/list-by-tenant/{tenant_id}', 'id_key': 'id',
                'validator': 'validate_smartagent.py',
                'editor': 'https://<domain>.omicrm.io/ai/callbot/script/update/{id}?lng=vi',
                'nguon': 'omicall-callbot-gen-ai/references/api-reference.md (Endpoints, Save add_v2)'},
    'callflow': {'service': 'chatbot', 'save': '/callbot/script/add_v2', 'get': ('GET', '/callbot/script/get/{id}'),
                 'list': '/callbot/script/list-by-tenant/{tenant_id}', 'id_key': 'id',
                 'validator': 'verify_callflow.py',
                 'editor': 'https://<domain>.omicrm.io/ai/callbot/script/update/{id}?lng=vi',
                 'nguon': 'omicall-callbot-flow/references/api-reference.md (§3 Kịch bản — endpoint)'},
    'bot': {'service': 'chatbot', 'save': '/omiai_assistant/save_draft_v2', 'get': ('POST', '/omiai_assistant/get/{id}'),
            'list': None, 'id_key': '_id', 'validator': 'validate_bot.py',
            'editor': 'https://<domain>.omicrm.io/ai/bot/edit/{id}?lng=vi',
            'nguon': 'omicall-chatbot-gen-ai/references/api-reference.md (Endpoints, Save save_draft_v2)'},
    'flow': {'service': 'campaign', 'save': '/omi_v2/campaign/save_draft_v2', 'get': ('GET', '/omi_v2/campaign/get/{id}'),
             'list': None, 'id_key': '_id', 'validator': 'validate_flow.py',
             'editor': 'https://<domain>.omicrm.io/flow/edit/{id}?lng=vi',
             'nguon': 'omicall-omiflow/references/api-reference.md (Endpoint: save_draft_v2 ✔ flow chưa xuất bản)'},
}
VERSION_KEYS = ('version', 'last_updated_date', 'last_updated_time', 'updated_at', 'last_publish_time')
IGNORE_DIFF = {'id', '_id', 'uuid', 'version', 'public_key', 'is_newest_version', 'created_by', 'last_updated_by',
               'created_date', 'last_updated_date', 'last_updated_time', 'updated_at', 'created_at', 'last_publish_time'}
SUMMARY_KEYS = ('instruction', 'system_prompt', 'intents', 'nodes', 'org_nodes', 'connections', 'edges', 'campaign',
                'name_mappings', 'variables', 'custom_variables')


# Giá trị đã bị mask_secrets che (cùng mẫu với validate_bot.py X6). Không bắt markdown ***chữ***.
# '***' đứng riêng (đầu/cuối chuỗi, giữa khoảng trắng, sau '/', '?', '=', trước ',', ';'...) cũng bị bắt:
# mask_text che JWT nằm trong câu hay trong đường dẫn URL thành '***' trần.
MASK_RE = re.compile(r'^\s*(?:bearer\s+)?\*\*\*\s*$|bearer\s+\*\*\*|"\*\*\*"|\\"\*\*\*\\"|[=:]\s*\*\*\*(?![*\w])'
                     r'|(?<![*\w])\*\*\*(?![*\w])', re.I)


def masked_paths(obj, path='$', out=None):
    """Đường dẫn JSON của mọi chuỗi đang là giá trị đã che. Không trả giá trị."""
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            masked_paths(v, '%s.%s' % (path, k), out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            masked_paths(v, '%s[%d]' % (path, i), out)
    elif isinstance(obj, str) and MASK_RE.search(obj):
        out.append(path)
    return out


class Stop(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def say(msg=''):
    print(omi_api.mask_text(msg))


def _payload(resp):
    return resp.get('payload') if isinstance(resp, dict) and 'payload' in resp else resp


def _size(v):
    if isinstance(v, (list, dict)):
        return len(v)
    if isinstance(v, str):
        return '%d ký tự' % len(v)
    return v


def summary_diff(a, b, keys=SUMMARY_KEYS):
    out = []
    for k in keys:
        if k in a or k in b:
            va, vb = a.get(k), b.get(k)
            if json.dumps(va, sort_keys=True, ensure_ascii=False) != json.dumps(vb, sort_keys=True, ensure_ascii=False):
                out.append('  %s: base %s | hiện tại %s (KHÁC)' % (k, _size(va), _size(vb)))
    return out


def field_diff(sent, got, prefix='', out=None, limit=40):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(sent, dict) and isinstance(got, dict):
        for k, v in sent.items():
            if not prefix and k in IGNORE_DIFF:
                continue
            if k not in got:
                out.append('%s%s: có trong bản gửi, thiếu trong bản GET' % (prefix, k))
            else:
                field_diff(v, got[k], '%s%s.' % (prefix, k), out, limit)
    elif isinstance(sent, list) and isinstance(got, list):
        if len(sent) != len(got):
            out.append('%s: gửi %d phần tử, GET %d' % (prefix.rstrip('.'), len(sent), len(got)))
        for i, (x, y) in enumerate(zip(sent, got)):
            field_diff(x, y, '%s%d.' % (prefix, i), out, limit)
    elif sent != got:
        out.append('%s: gửi %s, GET %s' % (prefix.rstrip('.'), json.dumps(sent, ensure_ascii=False)[:60],
                                          json.dumps(got, ensure_ascii=False)[:60]))
    return out


def find_validator(kind):
    override = os.environ.get('OMI_VALIDATOR_OVERRIDE')  # chỉ dùng trong test, cần thêm OMI_TEST_MODE=1
    if override:
        if os.environ.get('OMI_TEST_MODE') != '1':
            raise Stop(2, 'env OMI_VALIDATOR_OVERRIDE chỉ dùng trong test (cần OMI_TEST_MODE=1). Bỏ biến này để dùng '
                          'validator của skill — không lưu khi chưa kiểm được.')
        sys.stderr.write('WARN: OMI_VALIDATOR_OVERRIDE đang bật -> dùng validator thay thế %s (chỉ dùng trong test)\n'
                         % override)
    path = override or os.path.join(HERE, KINDS[kind]['validator'])
    if not os.path.isfile(path):
        raise Stop(2, 'Thiếu validator %s cho kind %s — không lưu khi chưa kiểm được.' % (os.path.basename(path), kind))
    return path


def run_validator(kind, file, mode, sent=None, report=None, extra=None):
    cmd = [sys.executable, '-B', find_validator(kind), file, '--mode', mode]
    if sent:
        cmd += ['--sent', sent]
    cmd += list(extra or [])
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    text = (p.stdout or '') + (('\n' + p.stderr) if p.stderr.strip() else '')
    if report:
        with open(report, 'w', encoding='utf-8') as f:
            f.write(omi_api.mask_text(text))
    for line in text.splitlines():
        if line.startswith(('FAIL', 'WARN', 'RESULT')):
            say('  [%s] %s' % (mode, line))
    if p.returncode == 2:
        raise Stop(2, 'validator báo sai cách gọi (exit 2) ở mode %s' % mode)
    return p.returncode == 0


def write(out_dir, name, obj):
    return omi_api.save_json(obj, out_dir, name)


@contextlib.contextmanager
def raw_file(obj):
    """File tạm CHƯA che cho validator (kiểm đúng cái được gửi/nhận). Tạo trong thư mục tạm riêng (quyền 0700 trên
    POSIX), xoá ngay khi validator chạy xong. Không phải file kết quả — file lưu lại luôn là bản đã che."""
    d = tempfile.mkdtemp(prefix='omi_save_raw_')
    path = os.path.join(d, 'payload.json')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False)
        yield path
    finally:
        with contextlib.suppress(OSError):
            os.remove(path)
        with contextlib.suppress(OSError):
            os.rmdir(d)


def load_json(path, what):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise Stop(2, 'không đọc được %s %s: %s' % (what, path, type(e).__name__ + ': ' + str(e)[:150]))


def stamp():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')


def fetch_current(kind, cfg, payload, tenant_id, domain):
    """Bản hiện tại trên server để so version. Callbot: bản mới nhất cùng uuid trong list-by-tenant."""
    if kind in ('callbot', 'callflow'):
        items = _payload(omi_api.get(cfg['service'], cfg['list'].format(tenant_id=tenant_id), expect_domain=domain)) or []
        same = [s for s in items if isinstance(s, dict) and s.get('uuid') == payload.get('uuid')]
        if not same:
            raise Stop(2, 'Không thấy kịch bản uuid này trong list-by-tenant — kiểm lại id/uuid (Cần xác nhận).')
        newest = [s for s in same if s.get('is_newest_version')]
        return max(newest or same, key=lambda s: (s.get('version') or 0))
    return get_saved(kind, cfg, payload[cfg['id_key']], domain)


def get_saved(kind, cfg, obj_id, domain):
    method, path = cfg['get']
    path = path.format(id=obj_id)
    if method == 'GET':
        return _payload(omi_api.get(cfg['service'], path, expect_domain=domain))
    return _payload(omi_api.post_json(cfg['service'], path, {cfg['id_key']: obj_id}, expect_domain=domain))


def guard(kind, cfg, payload, base, current):
    """So version/ngày sửa của base với bản hiện tại. Trả về danh sách khác biệt (rỗng = khớp)."""
    diffs = []
    for k in VERSION_KEYS:
        if k in base and k in current and base[k] != current[k]:
            diffs.append('%s: base %r, hiện tại %r' % (k, base[k], current[k]))
    if kind in ('callbot', 'callflow') and base.get('id') and current.get('id') and base['id'] != current['id']:
        diffs.append('id: base %r, bản mới nhất %r' % (base['id'], current['id']))
    return diffs


def editor_url(template, raw_domain, domain, obj_id):
    """URL editor theo đúng đuôi miền user truyền (.omicrm.com hay mặc định .omicrm.io)."""
    suffix = '.omicrm.com' if '.omicrm.com' in (raw_domain or '').lower() else '.omicrm.io'
    return template.replace('<domain>.omicrm.io', domain + suffix).format(id=obj_id)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('kind', choices=sorted(KINDS))
    ap.add_argument('payload')
    ap.add_argument('--domain', required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--new', action='store_true', help='callbot/callflow: tạo kịch bản mới (xoá id/uuid/public_key)')
    g.add_argument('--update', action='store_true', help='callbot/callflow: cập nhật (cần id + uuid + --confirm-update)')
    ap.add_argument('--base', help='bản GET đã dùng làm gốc khi sửa (guard version)')
    ap.add_argument('--confirm-update', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--out-dir')
    ap.add_argument('--context', help='tenant_context.json (chuyền cho validator mode pre/post)')
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    try:
        return run(a)
    except Stop as e:
        say('DỪNG: %s' % e)
        return e.code
    except omi_api.ApiError as e:
        say('LỖI API: %s' % e)
        return 4
    except SystemExit as e:  # omi_session.get_token
        if isinstance(e.code, str):
            say('DỪNG: %s' % e.code)
            return 2
        raise
    except Exception as e:  # lỗi mạng của requests...
        say('LỖI: %s: %s' % (type(e).__name__, str(e)[:200]))
        return 4


def run(a):
    import omi_session
    cfg = KINDS[a.kind]
    domain = omi_session._norm_domain(a.domain)
    payload = load_json(a.payload, 'payload')
    if not isinstance(payload, dict):
        raise Stop(2, 'payload phải là object JSON')
    if 'payload' in payload and isinstance(payload['payload'], dict) and len(payload) <= 3:
        payload = payload['payload']  # chấp nhận nguyên phản hồi GET
    base = None
    if a.base:
        base = _payload(load_json(a.base, '--base'))
        if not isinstance(base, dict):
            raise Stop(2, '--base phải là object JSON')
    if a.context and not os.path.isfile(a.context):
        raise Stop(2, 'không thấy file --context %s' % a.context)
    vextra = ['--context', a.context] if a.context else []
    masked = masked_paths(payload)
    if masked:
        raise Stop(2, 'payload còn %d giá trị đã che (***): %s%s — lưu sẽ ghi đè bí mật thật bằng "***". Dùng bản GET '
                      'chưa che làm gốc (không dùng file *_sent.json hay bản *_outline.py --save), hoặc sửa phần đó trên '
                      'giao diện (Cần xác nhận).' % (len(masked), ', '.join(masked[:5]), ' ...' if len(masked) > 5 else ''))

    # (1) token
    if a.dry_run:
        info, _ = omi_session.inspect(expect_domain=domain)
        tenant_id = info['tenant_id']
        if not info['token_ok']:
            say('Lưu ý (dry-run): token chưa dùng được (%s) — lần chạy thật sẽ dừng.' % info['error'])
    else:
        omi_session.get_token(expect_domain=domain)
        tenant_id = omi_session.inspect(expect_domain=domain)[0]['tenant_id']

    # (2) new / update
    if a.kind in ('callbot', 'callflow'):
        if not (a.new or a.update):
            raise Stop(2, 'callbot/callflow cần chọn --new (tạo kịch bản mới) hoặc --update (cập nhật kịch bản có sẵn).')
        if a.new:
            for k in ('id', 'uuid', 'public_key'):
                payload.pop(k, None)
            if payload.get('is_publish') is True:
                raise Stop(2, 'payload --new có is_publish:true — kịch bản mới chỉ lưu nháp. --new KHÔNG tự đổi is_publish: '
                              'đặt is_publish:false trong payload (hoặc dựng bằng build_smartagent.py --new / build_callflow.py) '
                              'rồi chạy lại.')
        else:
            if not payload.get('id') or not payload.get('uuid'):
                raise Stop(2, '--update cần payload có CẢ id lẫn uuid của bản mới nhất (chỉ id -> sinh kịch bản trùng).')
            if not a.confirm_update:
                raise Stop(2, '--update cần thêm --confirm-update. Trước đó kiểm list_hotlines bằng MCP: script đang gắn '
                              'hotline có thể chạy bản mới ngay (Cần xác nhận).')
            say('Nhắc: kiểm list_hotlines bằng MCP: script đang gắn hotline có thể chạy bản mới ngay (Cần xác nhận).')
    else:
        if a.new:
            raise Stop(2, '--new chỉ dùng cho callbot/callflow. Tạo %s mới qua API chưa kiểm chứng: tạo vỏ trên giao diện '
                          '(lưu nháp), GET lấy _id rồi dựng tiếp.' % a.kind)
        if not payload.get('_id'):
            raise Stop(2, 'payload %s thiếu _id. Chỉ lưu được %s đã có: tạo vỏ trên giao diện (%s nháp), GET lấy _id, '
                          'rồi chạy lại. (add_v2/update_v2 chưa kiểm chứng nên không dùng.)'
                       % (a.kind, a.kind, 'flow' if a.kind == 'flow' else 'bot'))

    out_dir = omi_api.scratch_dir(a.out_dir)
    tag = '%s_%s' % (a.kind, stamp())
    sent_path = write(out_dir, tag + '_sent.json', payload)

    # (3) guard version
    updating = a.update or a.kind in ('bot', 'flow')
    base_version = None
    if updating and not a.dry_run:
        if base is None:
            base = payload
        current = fetch_current(a.kind, cfg, payload, tenant_id, domain)
        if a.kind == 'flow' and current.get('is_publish') is True:
            raise Stop(2, 'flow này đang ở bản đã xuất bản: save_draft_v2 mới kiểm chứng trên flow chưa xuất bản (Cần xác nhận). '
                          'Lưu nháp/sửa qua giao diện hoặc tạo flow mới tắt sẵn.')
        base_version = current.get('version') if isinstance(current, dict) else None
        diffs = guard(a.kind, cfg, payload, base, current)
        if diffs:
            say('VERSION LỆCH — bản trên server đã đổi sau khi lấy base:')
            for d in diffs:
                say('  ' + d)
            for d in summary_diff(base, current):
                say(d)
            say('Lấy lại bản mới nhất (GET), áp lại thay đổi rồi chạy lại. Không ghi đè.')
            return 3
    elif updating:
        say('dry-run: bỏ qua guard version (không gọi mạng).')

    # (4) validator pre
    pre_report = os.path.join(out_dir, tag + '_pre_report.txt')
    with raw_file(payload) as raw:
        ok = run_validator(a.kind, raw, 'pre', report=pre_report, extra=vextra)
    if not ok:
        say('Validator (pre) FAIL — không lưu. Báo cáo: %s' % pre_report)
        return 1

    # (5) POST
    url = omi_api.url(cfg['service'], cfg['save'])
    if a.dry_run:
        say('DRY-RUN: POST %s' % url)
        say('  headers: {"Authorization": "Bearer ***"}')
        say('  multipart field "file" = %s (%d byte)' % (sent_path, os.path.getsize(sent_path)))
        say('Không gửi request nào.')
        return 0
    resp = omi_api.post_multipart(cfg['service'], cfg['save'], payload, expect_domain=domain)
    saved = _payload(resp) or {}
    new_id = saved.get(cfg['id_key']) if isinstance(saved, dict) else None
    if not new_id:
        write(out_dir, tag + '_response.json', resp)
        raise omi_api.ApiError('phản hồi lưu không có %s (status_code %r)' % (cfg['id_key'], resp.get('status_code') if isinstance(resp, dict) else None))
    say('Đã lưu %s: %s=%s version=%s' % (a.kind, cfg['id_key'], new_id, saved.get('version')))

    # (6) GET lại + validator post + diff
    got = get_saved(a.kind, cfg, new_id, domain)
    got_path = write(out_dir, tag + '_get_%s.json' % new_id, got)
    post_report = os.path.join(out_dir, tag + '_post_report.txt')
    post_extra = list(vextra)
    if a.kind == 'callflow' and a.update:
        if a.base:
            post_extra += ['--base', a.base]
        elif isinstance(base_version, int):
            post_extra += ['--base-version', str(base_version)]
    with raw_file(got) as raw_got, raw_file(payload) as raw_sent:
        ok = run_validator(a.kind, raw_got, 'post', sent=raw_sent, report=post_report, extra=post_extra)
    diffs = field_diff(payload, got if isinstance(got, dict) else {})
    if diffs:
        say('Khác nhau giữa bản gửi và bản GET (%d, bỏ qua id/version/ngày giờ):' % len(diffs))
        for d in diffs[:20]:
            say('  ' + d)
    else:
        say('Bản GET khớp các trường đã gửi.')

    # (7) giao
    say('id: %s | version: %s' % (new_id, (got or {}).get('version') if isinstance(got, dict) else None))
    say('Editor: %s' % editor_url(cfg['editor'], a.domain, domain, new_id))
    say('Nhắc: tải lại hoặc đóng tab editor cũ (editor đang mở có thể lưu đè bản cũ).')
    say('Báo cáo validator post: %s (dùng làm verify_report cho manifest.py)' % post_report)
    if not ok:
        say('Validator (post) FAIL trên bản GET — xem báo cáo, sửa rồi lưu lại.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
