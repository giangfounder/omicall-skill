"""build_manifest.json — sổ chung khi dựng nhiều artefact phụ thuộc nhau (flow, callbot, bot) bằng nhiều subagent.

  python <thư mục skill>/scripts/manifest.py [--path <scratch>/build_manifest.json] <lệnh> ...
  (mặc định --path lấy env OMI_MANIFEST)

Lệnh:
  init [--from plan.json] [--force]   tạo sổ rỗng (hoặc nạp danh sách artefact {key: {kind, owner, gates}})
  set <key> --json '{...}' [--owner <tên>]
        ghi/trộn trường cho artefact <key>: id, uuid, version, status (draft|published), webhook_url, verify (PASS|FAIL),
        verify_report (đường dẫn báo cáo validator), saved_at, verified_at, consumed_values {"<producer>.<trường>": giá trị},
        gates [{name, status: pending|done}]. Chỉ owner của key được set (sai owner -> exit 2).
  get <key>.<trường>                  in giá trị (JSON); không có -> exit 1
  check [--strict]                    FAIL khi: verify khác PASS; verified_at < saved_at; verify_report không tồn tại hoặc
                                      không chứa 'RESULT PASS'; consumed_values khác giá trị hiện hành của producer;
                                      producer đang stale. --strict: artefact chưa lưu cũng FAIL.
  gates                               liệt kê cổng còn chờ user (xuất bản, gắn hotline, gọi thử ...)
  stale <key> [--clear]               đánh dấu producer cần GET lại (ví dụ sau khi user xuất bản -> đổi id)

Không gọi mạng. Từ chối trường tên token/password/authorization/cookie/secret và giá trị dạng JWT (eyJ...).
Ghi an toàn khi nhiều tiến trình: khoá bằng os.open(O_CREAT|O_EXCL) có retry/timeout, ghi file tạm rồi os.replace.
Exit: 0 thành công, 1 check FAIL hoặc get không thấy, 2 sai cách gọi / sai owner / dữ liệu bị từ chối, 3 hết thời gian chờ khoá.
"""
import argparse
import datetime
import json
import os
import re
import sys
import tempfile
import time

FORBIDDEN_KEY = re.compile(r'token|password|passwd|authorization|cookie|secret|mat_?khau', re.I)
JWT = re.compile(r'eyJ[A-Za-z0-9_-]{6,}')
LOCK_TIMEOUT = float(os.environ.get('OMI_MANIFEST_LOCK_TIMEOUT') or 30)
LOCK_STALE = 120


class Refused(Exception):
    pass


def _now():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


class Lock:
    def __init__(self, path):
        self.path = path + '.lock'
        self.fd = None

    def __enter__(self):
        deadline = time.time() + LOCK_TIMEOUT
        while True:
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self.fd, str(os.getpid()).encode())
                return self
            except (FileExistsError, PermissionError):  # Windows: file khoá đang chờ xoá -> PermissionError
                try:
                    if time.time() - os.path.getmtime(self.path) > LOCK_STALE:
                        os.remove(self.path)
                        continue
                except OSError:
                    pass
                if time.time() > deadline:
                    raise TimeoutError('hết thời gian chờ khoá %s' % self.path)
                time.sleep(0.01)

    def __exit__(self, *exc):
        try:
            os.close(self.fd)
        finally:
            for _ in range(50):
                try:
                    os.remove(self.path)
                    break
                except FileNotFoundError:
                    break
                except PermissionError:
                    time.sleep(0.01)


def _load(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _save(path, data):
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix='.manifest_', suffix='.tmp', dir=d)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    for i in range(100):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # Windows: file đích đang mở ở tiến trình khác
            time.sleep(0.02)
    os.replace(tmp, path)


def _check_secrets(obj, where='json'):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if FORBIDDEN_KEY.search(str(k)):
                raise Refused('từ chối trường %r tại %s: manifest không chứa bí mật' % (k, where))
            _check_secrets(v, '%s.%s' % (where, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _check_secrets(v, '%s[%d]' % (where, i))
    elif isinstance(obj, str) and JWT.search(obj):
        raise Refused('từ chối giá trị dạng JWT tại %s' % where)


def _dig(obj, dotted):
    cur = obj
    for part in dotted.split('.'):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(dotted)
    return cur


def _ts(s):
    try:
        return datetime.datetime.fromisoformat(str(s).replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError:
        return None


def cmd_init(path, src=None, force=False):
    with Lock(path):
        if os.path.exists(path) and not force:
            print('Đã có %s (giữ nguyên; thêm --force để tạo lại)' % path)
            return 0
        data = {'version': 1, 'created_at': _now(), 'artefacts': {}}
        if src:
            with open(src, encoding='utf-8') as f:
                plan = json.load(f)
            items = plan.get('artefacts', plan) if isinstance(plan, dict) else plan
            if isinstance(items, list):
                items = {it['key']: it for it in items}
            for k, v in items.items():
                v = {kk: vv for kk, vv in v.items() if kk != 'key'}
                _check_secrets(v, k)
                v.setdefault('stale', False)
                data['artefacts'][k] = v
        _save(path, data)
    print('Đã tạo %s (%d artefact)' % (path, len(data['artefacts'])))
    return 0


def cmd_set(path, key, raw, owner=None):
    try:
        upd = json.loads(raw)
    except ValueError as e:
        raise Refused('--json không hợp lệ: %s' % e)
    if not isinstance(upd, dict):
        raise Refused('--json phải là object')
    _check_secrets(upd, key)
    owner = owner or upd.pop('owner', None) or os.environ.get('OMI_AGENT')
    upd.pop('owner', None)
    if not owner:
        raise Refused('thiếu owner (--owner hoặc env OMI_AGENT)')
    with Lock(path):
        data = _load(path) or {'version': 1, 'created_at': _now(), 'artefacts': {}}
        art = data['artefacts'].setdefault(key, {'owner': owner, 'stale': False})
        if art.get('owner') and art['owner'] != owner:
            raise Refused('artefact %r thuộc owner %r, không phải %r' % (key, art['owner'], owner))
        art['owner'] = owner
        for k, v in upd.items():
            if k == 'consumed_values' and isinstance(v, dict):
                art.setdefault('consumed_values', {}).update(v)
            else:
                art[k] = v
        if 'saved_at' in upd or 'id' in upd or 'webhook_url' in upd:
            art['stale'] = False
        art['updated_at'] = _now()
        _save(path, data)
    return 0


def cmd_get(path, dotted):
    with Lock(path):
        data = _load(path) or {}
    try:
        v = _dig(data.get('artefacts', {}), dotted)
    except KeyError:
        print('Không có %s' % dotted, file=sys.stderr)
        return 1
    print(json.dumps(v, ensure_ascii=False))
    return 0


def check(data, strict=False):
    rows = []
    arts = (data or {}).get('artefacts', {})
    for key, a in sorted(arts.items()):
        if a.get('stale'):
            rows.append(('WARN', key, 'stale: cần GET lại (id/URL có thể đã đổi sau xuất bản) rồi set'))
        if not a.get('saved_at'):
            rows.append(('FAIL' if strict else 'WARN', key, 'chưa lưu (thiếu saved_at)'))
            continue
        if a.get('verify') != 'PASS':
            rows.append(('FAIL', key, 'verify=%r (cần PASS)' % a.get('verify')))
        sa, va = _ts(a.get('saved_at')), _ts(a.get('verified_at'))
        if not va:
            rows.append(('FAIL', key, 'thiếu hoặc sai verified_at'))
        elif sa and va < sa:
            rows.append(('FAIL', key, 'verified_at %s < saved_at %s (kiểm trước lần lưu cuối)' % (a['verified_at'], a['saved_at'])))
        rep = a.get('verify_report')
        if not rep or not os.path.isfile(rep):
            rows.append(('FAIL', key, 'không thấy file verify_report %r' % rep))
        else:
            with open(rep, encoding='utf-8', errors='replace') as f:
                if 'RESULT PASS' not in f.read():
                    rows.append(('FAIL', key, 'verify_report %s không chứa RESULT PASS' % rep))
        for ref, used in sorted((a.get('consumed_values') or {}).items()):
            prod, _, field = ref.partition('.')
            if prod not in arts:
                rows.append(('FAIL', key, 'tiêu thụ %s nhưng không có producer %r' % (ref, prod)))
                continue
            if arts[prod].get('stale'):
                rows.append(('FAIL', key, 'producer %s đang stale -> %s <- %s cần cập nhật lại' % (prod, key, ref)))
                continue
            try:
                cur = _dig(arts[prod], field)
            except KeyError:
                rows.append(('FAIL', key, '%s <- %s: producer không có trường này' % (key, ref)))
                continue
            if cur != used:
                rows.append(('FAIL', key, '%s <- %s: đang dùng %r, giá trị hiện hành %r' % (key, ref, used, cur)))
        for g in a.get('gates') or []:
            if isinstance(g, dict) and g.get('status') != 'done':
                rows.append(('WARN', key, 'cổng chờ user: %s' % g.get('name')))
        if not any(r[0] == 'FAIL' and r[1] == key for r in rows):
            rows.append(('PASS', key, 'verify PASS, giá trị tiêu thụ khớp'))
    return rows


def cmd_check(path, strict=False):
    with Lock(path):
        data = _load(path)
    if data is None:
        print('FAIL - không thấy manifest %s' % path)
        print('RESULT FAIL')
        return 1
    rows = check(data, strict)
    for lvl, key, msg in rows:
        print('%s %s %s' % (lvl, key, msg))
    bad = any(r[0] == 'FAIL' for r in rows)
    print('RESULT %s' % ('FAIL' if bad else 'PASS'))
    return 1 if bad else 0


def cmd_gates(path):
    with Lock(path):
        data = _load(path) or {}
    n = 0
    for key, a in sorted(data.get('artefacts', {}).items()):
        for g in a.get('gates') or []:
            if isinstance(g, dict) and g.get('status') != 'done':
                n += 1
                print('CHỜ USER %s: %s' % (key, g.get('name')))
    if not n:
        print('Không còn cổng nào chờ user.')
    return 0


def cmd_stale(path, key, clear=False):
    with Lock(path):
        data = _load(path) or {}
        if key not in data.get('artefacts', {}):
            print('Không có artefact %r' % key, file=sys.stderr)
            return 1
        data['artefacts'][key]['stale'] = not clear
        data['artefacts'][key]['updated_at'] = _now()
        _save(path, data)
    print('%s: stale=%s' % (key, not clear))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--path', default=os.environ.get('OMI_MANIFEST'))
    sub = ap.add_subparsers(dest='cmd')
    p = sub.add_parser('init')
    p.add_argument('--from', dest='src')
    p.add_argument('--force', action='store_true')
    p = sub.add_parser('set')
    p.add_argument('key')
    p.add_argument('--json', required=True)
    p.add_argument('--owner')
    p = sub.add_parser('get')
    p.add_argument('ref')
    p = sub.add_parser('check')
    p.add_argument('--strict', action='store_true')
    sub.add_parser('gates')
    p = sub.add_parser('stale')
    p.add_argument('key')
    p.add_argument('--clear', action='store_true')
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if not a.cmd:
        ap.print_help()
        return 2
    if not a.path:
        print('Thiếu --path hoặc env OMI_MANIFEST', file=sys.stderr)
        return 2
    path = os.path.abspath(a.path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        if a.cmd == 'init':
            return cmd_init(path, a.src, a.force)
        if a.cmd == 'set':
            return cmd_set(path, a.key, a.json, a.owner)
        if a.cmd == 'get':
            return cmd_get(path, a.ref)
        if a.cmd == 'check':
            return cmd_check(path, a.strict)
        if a.cmd == 'gates':
            return cmd_gates(path)
        if a.cmd == 'stale':
            return cmd_stale(path, a.key, a.clear)
    except Refused as e:
        print('TỪ CHỐI: %s' % e, file=sys.stderr)
        return 2
    except TimeoutError as e:
        print('LỖI: %s' % e, file=sys.stderr)
        return 3
    return 2


if __name__ == '__main__':
    sys.exit(main())
