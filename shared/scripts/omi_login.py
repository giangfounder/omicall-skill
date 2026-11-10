"""Đăng nhập OMI một lần, sau đó agent tự đăng nhập lại qua MCP OMI (file dùng chung cho mọi skill OMI).

  python omi_login.py ensure --domain <domain>          # agent: kiểm tra + tự đăng nhập lại, một lệnh
  python omi_login.py setup  --domain <domain> [--email <email>] [--tenant-id <id>] [--client auto|claude|codex|none]
  python omi_login.py setup  --ui [--no-browser]   # form trống trên trình duyệt (agent chạy được)
  python omi_login.py login  --domain <domain> [--tenant-id <id>]
  python omi_login.py status --domain <domain>
  python omi_login.py forget --domain <domain>
  python omi_login.py serve  --domain <domain>          # lệnh khởi động server MCP (client gọi, không chạy tay)

ensure : AGENT chạy đầu mỗi việc. Token dùng được → in {"ok":true}. Đã cất thông tin → tự đăng nhập lại.
         Chưa có → in {"ok":false,"need":"setup","command":"<lệnh setup>"} (exit 3) để agent mở terminal cho user.
setup  : USER chạy trong terminal của mình. Hỏi email (nếu thiếu) và mật khẩu bằng ô nhập ẩn, cất vào kho bí mật của
         hệ điều hành (Windows Credential Manager / macOS Keychain / Secret Service, hoặc thư viện keyring), đăng nhập
         thử qua MCP OMI (ghi phiên vào file của phiên Claude Code, xem omi_session.py), rồi đăng ký server MCP `OMICall-<domain>` cho client.
         Cấu hình MCP chỉ chứa lệnh `omi_login.py serve`, không chứa mật khẩu. Không có terminal (stdin không phải
         TTY) thì dừng: mật khẩu không được đi qua hội thoại hay ống dẫn của agent. Sai mật khẩu → cho nhập lại
         (tối đa 3 lần); nhiều tenant → hỏi chọn ngay trong terminal. Dòng cuối luôn là
         `OMI_LOGIN_RESULT=OK|FAIL domain=<domain>` để agent đọc terminal và tự đi tiếp, user không cần báo lại.
setup --ui: mở form (domain, email, mật khẩu) trên trình duyệt của user tại 127.0.0.1 (cổng ngẫu nhiên, đường dẫn
         một lần, chỉ nhận Host/Origin cục bộ, tự tắt sau 10 phút hoặc sau khi đăng nhập xong). Mật khẩu đi thẳng từ
         trình duyệt vào tiến trình script rồi vào kho bí mật; agent chạy lệnh này (nền) nhưng không thấy mật khẩu.
         Cùng dòng cuối `OMI_LOGIN_RESULT=...`. Không cần TTY. Thêm `--no-browser`: không mở trình duyệt hệ thống,
         dòng đầu in sẵn địa chỉ form để agent mở trong khung trình duyệt của chính nó (user điền ngay trong agent).
login  : AGENT tự chạy khi token hết hạn / sai tenant: lấy thông tin từ kho bí mật, gọi login_omicall_mcp
         (+ select_tenant), phiên mới dùng được ngay cho omi_session.py. Không hỏi user, không in mật khẩu hay token.
status : in JSON {credential_stored, email, tenant_id, token_ok, minutes_left, mcp_registered}; không gọi mạng.
forget : xoá thông tin đăng nhập đã cất (chỉ khi user yêu cầu).
serve  : đọc kho bí mật rồi chạy `npx -y omicall-mcp` với biến OMICALL_* (stdio đi thẳng tới client). Mỗi domain một
         thư mục phiên riêng (USERPROFILE/HOME = ~/.omicall-mcp/servers/<domain>) vì omicall-mcp lấy tenant từ
         session.json và ghi đè tenant khai báo: dùng chung một file thì mọi server chạy nhầm cùng một tenant.

Phiên tách riêng (11/2026): login/ensure ghi phiên vào thư mục của phiên Claude Code hiện tại
(omi_session.session_home(), theo CLAUDE_CODE_SESSION_ID); không có khoá phiên thì dùng file chung cũ.

Exit: 0 xong; 1 lỗi đăng nhập hoặc thiếu thông tin đã cất; 2 tham số sai / không có terminal; 4 tài khoản nhiều
tenant, chạy lại với --tenant-id (danh sách tenant được in ra).
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omi_session  # noqa: E402

SERVICE = 'omicall-mcp'
ACCOUNTS = os.path.join(os.path.expanduser('~'), '.omicall-mcp', 'accounts.json')  # không chứa mật khẩu
MCP_TIMEOUT = 180


# ---------- kho bí mật của hệ điều hành ----------

def _target(domain):
    return '%s/%s' % (SERVICE, domain)


def _keyring():
    try:
        import keyring  # noqa: F401
        return keyring
    except ImportError:
        return None


if os.name == 'nt':
    import ctypes
    from ctypes import wintypes

    class _CRED(ctypes.Structure):
        _fields_ = [('Flags', wintypes.DWORD), ('Type', wintypes.DWORD), ('TargetName', wintypes.LPWSTR),
                    ('Comment', wintypes.LPWSTR), ('LastWritten', wintypes.FILETIME),
                    ('CredentialBlobSize', wintypes.DWORD), ('CredentialBlob', ctypes.POINTER(ctypes.c_char)),
                    ('Persist', wintypes.DWORD), ('AttributeCount', wintypes.DWORD),
                    ('Attributes', ctypes.c_void_p), ('TargetAlias', wintypes.LPWSTR),
                    ('UserName', wintypes.LPWSTR)]

    _adv = ctypes.WinDLL('advapi32', use_last_error=True)
    _adv.CredWriteW.argtypes = [ctypes.POINTER(_CRED), wintypes.DWORD]
    _adv.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                               ctypes.POINTER(ctypes.POINTER(_CRED))]
    _adv.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    _adv.CredFree.argtypes = [ctypes.c_void_p]
    CRED_TYPE_GENERIC, CRED_PERSIST_LOCAL_MACHINE = 1, 2


def cred_save(domain, email, password):
    if os.name == 'nt':
        blob = password.encode('utf-16-le')
        c = _CRED()
        c.Type, c.Persist = CRED_TYPE_GENERIC, CRED_PERSIST_LOCAL_MACHINE
        c.TargetName, c.UserName = _target(domain), email
        c.CredentialBlobSize = len(blob)
        c.CredentialBlob = ctypes.cast(ctypes.create_string_buffer(blob, len(blob)), ctypes.POINTER(ctypes.c_char))
        if not _adv.CredWriteW(ctypes.byref(c), 0):
            raise SystemExit('Không ghi được Windows Credential Manager (mã lỗi %d).' % ctypes.get_last_error())
        return 'Windows Credential Manager'
    kr = _keyring()
    if kr:
        kr.set_password(_target(domain), email, password)
        return 'keyring'
    if sys.platform == 'darwin' and shutil.which('security'):
        subprocess.run(['security', 'delete-generic-password', '-s', _target(domain)], capture_output=True)
        # -w đặt cuối không kèm giá trị: security tự hỏi mật khẩu → không lộ qua danh sách tiến trình
        p = subprocess.run(['security', 'add-generic-password', '-s', _target(domain), '-a', email, '-w'],
                           input='%s\n%s\n' % (password, password), text=True, capture_output=True)
        if p.returncode:
            raise SystemExit('Không ghi được macOS Keychain: %s' % p.stderr.strip())
        return 'macOS Keychain'
    if shutil.which('secret-tool'):
        p = subprocess.run(['secret-tool', 'store', '--label', _target(domain), 'service', SERVICE,
                            'domain', domain, 'email', email], input=password, text=True, capture_output=True)
        if p.returncode:
            raise SystemExit('Không ghi được Secret Service: %s' % p.stderr.strip())
        return 'Secret Service'
    raise SystemExit('Máy chưa có kho bí mật dùng được: cài `pip install keyring` rồi chạy lại setup.')


def cred_load(domain):
    """Trả về (email, mật khẩu) hoặc (None, None)."""
    if os.name == 'nt':
        p = ctypes.POINTER(_CRED)()
        if not _adv.CredReadW(_target(domain), CRED_TYPE_GENERIC, 0, ctypes.byref(p)):
            return None, None
        try:
            c = p.contents
            pw = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize).decode('utf-16-le')
            return c.UserName, pw
        finally:
            _adv.CredFree(p)
    email = _accounts().get(domain, {}).get('email')
    kr = _keyring()
    if kr and email:
        pw = kr.get_password(_target(domain), email)
        return (email, pw) if pw else (None, None)
    if sys.platform == 'darwin' and shutil.which('security'):
        r = subprocess.run(['security', 'find-generic-password', '-s', _target(domain), '-w'],
                           capture_output=True, text=True)
        return (email, r.stdout.rstrip('\n')) if r.returncode == 0 and email else (None, None)
    if shutil.which('secret-tool'):
        r = subprocess.run(['secret-tool', 'lookup', 'service', SERVICE, 'domain', domain],
                           capture_output=True, text=True)
        return (email, r.stdout) if r.returncode == 0 and r.stdout and email else (None, None)
    return None, None


def cred_delete(domain):
    if os.name == 'nt':
        return bool(_adv.CredDeleteW(_target(domain), CRED_TYPE_GENERIC, 0))
    email = _accounts().get(domain, {}).get('email')
    kr = _keyring()
    if kr and email:
        try:
            kr.delete_password(_target(domain), email)
            return True
        except Exception:
            return False
    if sys.platform == 'darwin' and shutil.which('security'):
        return subprocess.run(['security', 'delete-generic-password', '-s', _target(domain)],
                              capture_output=True).returncode == 0
    if shutil.which('secret-tool'):
        return subprocess.run(['secret-tool', 'clear', 'service', SERVICE, 'domain', domain],
                              capture_output=True).returncode == 0
    return False


# ---------- thông tin không bí mật (email, tenant, môi trường) ----------

def _accounts():
    try:
        with open(ACCOUNTS, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_account(domain, **fields):
    data = _accounts()
    data.setdefault(domain, {}).update({k: v for k, v in fields.items() if v})
    os.makedirs(os.path.dirname(ACCOUNTS), exist_ok=True)
    with open(ACCOUNTS, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _mcp_env(domain, home=None):
    """Biến môi trường cho omicall-mcp. home: thư mục làm USERPROFILE/HOME để gói ghi session.json riêng."""
    email, pw = cred_load(domain)
    if not pw:
        return None
    acc = _accounts().get(domain, {})
    env = dict(os.environ, OMICALL_USERNAME=email, OMICALL_PASSWORD=pw, OMICALL_DOMAIN=domain)
    if home:
        real_npmrc = os.path.join(os.path.expanduser('~'), '.npmrc')
        os.makedirs(home, exist_ok=True)
        env.update(USERPROFILE=home, HOME=home)
        if os.path.exists(real_npmrc) and 'NPM_CONFIG_USERCONFIG' not in env:
            env['NPM_CONFIG_USERCONFIG'] = real_npmrc
    if acc.get('tenant_id'):
        env['OMICALL_TENANT_ID'] = acc['tenant_id']
    if acc.get('env'):
        env['OMICALL_ENV'] = acc['env']
    return env


def _npx():
    npx = shutil.which('npx')
    if not npx:
        raise SystemExit('Chưa có npx: cài Node.js 18+ rồi chạy lại.')
    return npx


# ---------- gọi MCP OMI qua stdio ----------

class _Mcp:
    def __init__(self, env):
        self.p = subprocess.Popen([_npx(), '-y', 'omicall-mcp'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, env=env, text=True, encoding='utf-8')
        self.n = 0

    def _send(self, msg):
        self.p.stdin.write(json.dumps(msg) + '\n')
        self.p.stdin.flush()

    def request(self, method, params=None):
        self.n += 1
        self._send({'jsonrpc': '2.0', 'id': self.n, 'method': method, 'params': params or {}})
        box = {}

        def read():
            for line in self.p.stdout:
                try:
                    m = json.loads(line)
                except ValueError:
                    continue
                if m.get('id') == self.n:
                    box['m'] = m
                    return

        t = threading.Thread(target=read, daemon=True)
        t.start()
        t.join(MCP_TIMEOUT)
        if 'm' not in box:
            raise SystemExit('MCP OMI không phản hồi %s sau %d giây.' % (method, MCP_TIMEOUT))
        if 'error' in box['m']:
            raise SystemExit('MCP OMI lỗi %s: %s' % (method, box['m']['error'].get('message')))
        return box['m']['result']

    def call(self, tool, args):
        r = self.request('tools/call', {'name': tool, 'arguments': args})
        text = '\n'.join(c.get('text', '') for c in r.get('content', []) if c.get('type') == 'text')
        return bool(r.get('isError')), text

    def start(self):
        self.request('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                                    'clientInfo': {'name': 'omi_login', 'version': '1'}})
        self._send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        return self

    def close(self):
        try:
            self.p.kill()
        except OSError:
            pass


def _drop_session_if_other_tenant(tenant_id, path=None):
    """MCP lấy tenant từ phiên cũ ở session.json; phiên của tenant khác thì xoá để đăng nhập lại từ đầu."""
    path = path or omi_session._session_path()
    try:
        with open(path, encoding='utf-8') as f:
            old = json.load(f).get('tenantId')
        if old and old != tenant_id:
            os.remove(path)
    except (OSError, ValueError):
        pass


def do_login(domain, tenant_id=None, _retry=True):
    """Đăng nhập qua MCP OMI. Trả về (exit code, thông báo) — không chứa mật khẩu hay token."""
    env = _mcp_env(domain, home=omi_session.session_home())
    if env is None:
        return 1, ('Chưa có thông tin đăng nhập đã cất cho %s: agent chạy nền `omi_login.py setup --ui --no-browser` '
                   'và mở form cho user điền một lần (dự phòng không mở được form: user tự chạy '
                   '`omi_login.py setup --domain %s` trong terminal).' % (domain, domain))
    tenant_id = tenant_id or _accounts().get(domain, {}).get('tenant_id')
    if tenant_id:
        _drop_session_if_other_tenant(tenant_id)
    mcp = _Mcp(env).start()
    try:
        err, text = mcp.call('login_omicall_mcp', {'domain': domain})
        if err:
            # tenant_id đã cất bị cũ ("Tenant X not found. Available: Y"): chỉ còn một tenant hợp lệ thì dùng luôn
            avail = set(re.findall(r'\b[0-9a-f]{24}\b', text.split('Available:', 1)[1])) if 'Available:' in text else set()
            if _retry and len(avail) == 1 and tenant_id not in avail:
                new_id = avail.pop()
                _save_account(domain, tenant_id=new_id)
                mcp.close()
                return do_login(domain, new_id, _retry=False)
            return 1, 'Đăng nhập thất bại: %s' % text.strip()[:300]
        info, _ = omi_session.inspect(expect_domain=domain)
        if not info['token_ok']:
            if not tenant_id:
                return 4, ('Tài khoản có nhiều tenant hoặc chưa chọn tenant. Chạy lại với --tenant-id <id>. '
                           'Phản hồi đăng nhập:\n%s' % text.strip()[:1500])
            err, text = mcp.call('select_tenant', {'tenant_id': tenant_id})
            if err:
                return 1, 'select_tenant thất bại: %s' % text.strip()[:300]
            info, _ = omi_session.inspect(expect_domain=domain)
        if not info['token_ok']:
            return 1, 'Đã gọi đăng nhập nhưng phiên chưa dùng được: %s' % info['error']
        if tenant_id:
            _save_account(domain, tenant_id=tenant_id)
        return 0, 'Đăng nhập %s xong (tenant %s, còn %d phút).' % (
            domain, info['tenant_id'], info['seconds_left'] // 60)
    finally:
        mcp.close()


# ---------- đăng ký server MCP cho client ----------

def _claude_cli():
    exe = shutil.which('claude')
    if exe:
        return exe
    base = os.environ.get('LOCALAPPDATA') or ''
    found = glob.glob(os.path.join(base, 'Claude-Data', '*', 'claude-code', '*', '*', 'claude.exe'))
    return max(found, key=os.path.getmtime) if found else None


def _serve_cmd(domain):
    return [sys.executable, os.path.abspath(__file__), 'serve', '--domain', domain]


def _register_claude(name, cmd):
    cli = _claude_cli()
    if cli:
        subprocess.run([cli, 'mcp', 'remove', '--scope', 'user', name], capture_output=True)
        p = subprocess.run([cli, 'mcp', 'add', '--scope', 'user', name, '--'] + cmd, capture_output=True,
                           text=True, encoding='utf-8', errors='replace')
        return p.returncode == 0, (p.stderr or p.stdout).strip()[:300]
    path = os.path.join(os.path.expanduser('~'), '.claude.json')
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    if os.path.exists(path):
        shutil.copy2(path, path + '.bak-omi')
    data.setdefault('mcpServers', {})[name] = {'type': 'stdio', 'command': cmd[0], 'args': cmd[1:], 'env': {}}
    tmp = path + '.tmp-omi'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return True, 'ghi trực tiếp ~/.claude.json (bản lưu .bak-omi)'


def _register_codex(name, cmd):
    cli = shutil.which('codex')
    subprocess.run([cli, 'mcp', 'remove', name], capture_output=True)
    p = subprocess.run([cli, 'mcp', 'add', name, '--'] + cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return p.returncode == 0, (p.stderr or p.stdout).strip()[:300]


def register(domain, client):
    name = 'OMICall-%s' % domain
    cmd = _serve_cmd(domain)
    targets = []
    if client in ('auto', 'claude') and (client == 'claude' or _claude_cli()
                                          or os.path.exists(os.path.expanduser('~/.claude.json'))):
        targets.append(('claude', _register_claude))
    if client in ('auto', 'codex') and shutil.which('codex'):
        targets.append(('codex', _register_codex))
    out = {}
    for label, fn in targets:
        ok, msg = fn(name, cmd)
        out[label] = 'OK' if ok else 'LỖI: %s' % msg
    return name, cmd, out


def _registered(domain):
    try:
        with open(os.path.join(os.path.expanduser('~'), '.claude.json'), encoding='utf-8') as f:
            srv = json.load(f).get('mcpServers', {}).get('OMICall-%s' % domain)
    except (OSError, ValueError):
        return None
    if not srv:
        return False
    return 'serve' in (srv.get('args') or []) and 'OMICALL_PASSWORD' not in (srv.get('env') or {})


# ---------- lệnh ----------

def _result(domain, ok):
    print('OMI_LOGIN_RESULT=%s domain=%s' % ('OK' if ok else 'FAIL', domain))
    return 0 if ok else 1


def _ask_tenant(text):
    print(text.strip()[:1500])
    try:
        return input('Nhập tenant_id cần dùng (Enter để huỷ): ').strip() or None
    except (EOFError, KeyboardInterrupt):
        return None


def cmd_setup(a):
    if a.ui:
        return cmd_setup_ui(a)
    if not a.domain:
        print('Thiếu --domain (hoặc dùng --ui để nhập domain trong form).', file=sys.stderr)
        return 2
    if not sys.stdin.isatty():
        print('Cần chạy trong terminal của user (ô nhập ẩn), hoặc thêm --ui để mở form đăng nhập trên trình duyệt. '
              'Agent không truyền mật khẩu qua lệnh hay ống dẫn.', file=sys.stderr)
        return 2
    import getpass
    print('== Đăng nhập OMI, domain %s ==' % a.domain)
    saved = _accounts().get(a.domain, {}).get('email')
    try:
        email = a.email or input('Email%s: ' % (' [%s]' % saved if saved else '')).strip() or saved
    except (EOFError, KeyboardInterrupt):
        print('\nĐã huỷ.', file=sys.stderr)
        _result(a.domain, False)
        return 2
    if not email:
        print('Thiếu email.', file=sys.stderr)
        _result(a.domain, False)
        return 2
    tenant_id = a.tenant_id
    for attempt in range(1, 4):
        try:
            pw = getpass.getpass('Mật khẩu (không hiện khi gõ)%s: ' % ('' if attempt == 1 else ', thử lại'))
        except (EOFError, KeyboardInterrupt):
            print('\nĐã huỷ.', file=sys.stderr)
            _result(a.domain, False)
            return 2
        if not pw:
            continue
        cred_save(a.domain, email, pw)
        del pw
        _save_account(a.domain, email=email, tenant_id=tenant_id, env=a.env)
        print('Đang đăng nhập... (lần đầu có thể mất 1-2 phút)')
        code, msg = do_login(a.domain, tenant_id)
        if code == 4:
            tenant_id = _ask_tenant(msg)
            if tenant_id:
                code, msg = do_login(a.domain, tenant_id)
        if code == 0:
            print(msg)
            break
        print(msg)
        if not msg.startswith('Đăng nhập thất bại'):
            break  # lỗi không phải sai mật khẩu: không hỏi lại
    else:
        code = 1
    if code:
        cred_delete(a.domain)
        print('Chưa đăng nhập được; đã xoá thông tin vừa nhập. Kiểm tra email/mật khẩu rồi chạy lại lệnh này.')
        return _result(a.domain, False)
    if a.client != 'none':
        name, _, res = register(a.domain, a.client)
        for k, v in res.items():
            print('Đăng ký MCP %s cho %s: %s' % (name, k, v))
    print('XONG. Quay lại cửa sổ agent, agent tự làm tiếp; có thể đóng terminal này.')
    return _result(a.domain, True)


UI_TIMEOUT = 600

_UI_HTML = """<!doctype html><html lang="vi"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Đăng nhập OMICALL</title>
<style>
:root{color-scheme:light;--pri:#00a9ff;--ink:#1d2b4f;--mut:#8a94a6;--card:#f6f8fc;--bd:#e6ebf3;--err:#d92d20;--ok:#067647}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;flex-direction:column;background:#fff;color:var(--ink);font:16px/1.5 "Be Vietnam Pro",Roboto,"Segoe UI",system-ui,sans-serif}
header{padding:40px 44px}header svg{height:44px;width:auto;display:block}
main{flex:1;display:flex;flex-direction:column;align-items:center;padding:0 16px}
.box{width:min(502px,100%);margin-top:clamp(16px,8vh,110px)}
h1{margin:0;font-size:24px;font-weight:600}
.bar{width:28px;height:4px;border-radius:2px;background:var(--pri);margin:10px 0 36px}
.field{position:relative;display:block;background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:14px 24px 12px;margin-bottom:20px}
.field:focus-within{border-color:var(--pri);box-shadow:0 0 0 3px rgba(0,169,255,.16)}
.field>span{display:block;font-size:14px;font-weight:600}
.field input{flex:1;min-width:0;width:100%;border:0;outline:0;background:transparent;color:var(--ink);font:inherit;font-size:18px;padding:2px 0 0}
.row{display:flex;align-items:baseline;gap:6px}
.eye{position:absolute;right:16px;top:50%;transform:translateY(-50%);border:0;background:transparent;color:var(--ink);cursor:pointer;padding:6px;border-radius:8px;display:grid}
.eye:focus-visible{outline:2px solid var(--pri)}
.field.pw input{padding-right:44px}
.go{width:100%;height:66px;border:0;border-radius:16px;background:var(--pri);color:#fff;font:inherit;font-size:18px;font-weight:600;cursor:pointer;margin-top:14px}
.go:hover{filter:brightness(.96)}.go:focus-visible{outline:3px solid rgba(0,169,255,.4);outline-offset:2px}.go:disabled{opacity:.6;cursor:wait}
#msg{margin-top:20px;white-space:pre-wrap;font-size:15px}.err{color:var(--err)}.ok{color:var(--ok)}
::placeholder{color:#c3cad6;opacity:1}
[hidden]{display:none!important}
@media(max-width:560px){header{padding:24px 16px}.field{padding:12px 18px 10px}.go{height:58px}}
</style>
<header><svg viewBox="0 0 300 70" role="img" aria-label="OMICALL"><path d="M54 20A24 24 0 1 0 54 50" fill="none" stroke="#00a9ff" stroke-width="12" stroke-linecap="round"/><text x="80" y="52" font-family="Montserrat,Arial,sans-serif" font-size="44" font-weight="800" letter-spacing="-2"><tspan fill="#00a9ff">OMI</tspan><tspan fill="#4cc764">CALL</tspan></text></svg></header>
<main><div class="box">
<h1>Đăng nhập</h1><div class="bar"></div>
<form id="f" autocomplete="on">
<label class="field"><span>Domain</span><div class="row"><input id="domain" name="domain" placeholder="tên doanh nghiệp" autocapitalize="none" spellcheck="false" required></div></label>
<label class="field"><span>Email</span><input id="email" name="email" type="email" placeholder="địa chỉ email" autocomplete="username" required></label>
<label class="field pw"><span>Mật khẩu</span><input id="password" name="password" type="password" autocomplete="current-password" required>
<button id="eye" class="eye" type="button" aria-label="Hiện mật khẩu" aria-pressed="false"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/><path id="slash" d="M4 4l16 16" hidden/></svg></button></label>
<label class="field" id="tr" hidden><span>Tenant ID</span><input id="tenant_id" name="tenant_id"></label>
<button id="b" class="go" type="submit">Đăng nhập</button>
</form>
<div id="msg" role="status" aria-live="polite"></div>
</div></main>
<script>
const f=document.getElementById('f'),b=document.getElementById('b'),msg=document.getElementById('msg'),eye=document.getElementById('eye'),slash=document.getElementById('slash');
f.domain.focus();
eye.onclick=()=>{const show=f.password.type==='password';f.password.type=show?'text':'password';slash.hidden=!show;
eye.setAttribute('aria-pressed',show);eye.setAttribute('aria-label',show?'Ẩn mật khẩu':'Hiện mật khẩu')};
f.onsubmit=async e=>{e.preventDefault();b.disabled=true;msg.className='';
msg.textContent='Đang đăng nhập...';
try{const r=await fetch(location.pathname+'/login',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify(Object.fromEntries([...new FormData(f)].map(([k,v])=>[k,typeof v==='string'?v.trim():v])))});const d=await r.json();
msg.className=d.ok?'ok':'err';msg.textContent=d.message;
if(d.ok){f.hidden=true;f.password.value=''}else{b.disabled=false;if(d.need_tenant)document.getElementById('tr').hidden=false}}
catch(x){msg.className='err';msg.textContent='Mất kết nối với script. Chạy lại lệnh setup.';b.disabled=false}};
</script></html>"""


def cmd_setup_ui(a):
    """Form đăng nhập trên localhost: mật khẩu đi thẳng từ trình duyệt của user vào script, không qua agent."""
    import html
    import http.server
    import secrets
    import webbrowser

    token = secrets.token_urlsafe(16)
    lock = threading.Lock()
    state = {'ok': False, 'domain': a.domain}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _local(self):
            return self.headers.get('Host') == '127.0.0.1:%d' % port

        def _send(self, code, body, ctype='text/html; charset=utf-8'):
            data = body if isinstance(body, bytes) else body.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self._local() or self.path != '/' + token:
                return self._send(404, b'', 'text/plain')
            page = _UI_HTML
            self._send(200, page)

        def do_POST(self):
            origin = self.headers.get('Origin')
            if not self._local() or self.path != '/%s/login' % token or (origin and origin != 'http://127.0.0.1:%d' % port):
                return self._send(404, b'', 'text/plain')
            try:
                n = int(self.headers.get('Content-Length') or 0)
                data = json.loads(self.rfile.read(min(n, 10000)).decode('utf-8')) if 0 < n <= 10000 else {}
            except ValueError:
                data = {}
            res = self._login(data)
            self._send(200, json.dumps(res, ensure_ascii=False), 'application/json; charset=utf-8')
            if res['ok']:
                threading.Timer(1.0, server.shutdown).start()

        def _login(self, data):
            def fail(message, **extra):
                return dict(ok=False, message=message, **extra)
            try:
                domain = omi_session._norm_domain(str(data.get('domain', '')).strip())
            except (SystemExit, ValueError):
                domain = ''
            email, pw = str(data.get('email', '')).strip(), str(data.get('password', '')).strip()
            tenant_id = str(data.get('tenant_id', '')).strip() or a.tenant_id
            if not (domain and email and pw):
                return fail('Điền đủ domain, email và mật khẩu.')
            if not lock.acquire(blocking=False):
                return fail('Đang xử lý lần đăng nhập trước, chờ một chút.')
            try:
                state['domain'] = domain
                cred_save(domain, email, pw)
                pw = None
                _save_account(domain, email=email, tenant_id=tenant_id, env=a.env)
                code, msg = do_login(domain, tenant_id)
                if code:
                    cred_delete(domain)
                    if code == 4:
                        return fail('Tài khoản có nhiều tenant: nhập Tenant ID cần dùng rồi đăng nhập lại.\n'
                                    + msg[:1500], need_tenant=True)
                    return fail(msg)
                lines = [msg]
                if a.client != 'none':
                    name, _, reg = register(domain, a.client)
                    lines += ['Đăng ký MCP %s cho %s: %s' % (name, k, v) for k, v in reg.items()]
                state['ok'] = True
                return dict(ok=True, message='\n'.join(lines))
            except SystemExit as e:
                cred_delete(domain)
                return fail(str(e.code))
            finally:
                lock.release()

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    port = server.server_address[1]
    url = 'http://127.0.0.1:%d/%s' % (port, token)
    print('Form đăng nhập OMI: %s' % url)
    if not a.no_browser:
        print('(Đang mở trình duyệt; nếu không tự mở, dán địa chỉ trên vào trình duyệt. Chờ tối đa %d phút.)'
              % (UI_TIMEOUT // 60))
    sys.stdout.flush()
    if not a.no_browser:
        webbrowser.open(url)
    timer = threading.Timer(UI_TIMEOUT, server.shutdown)
    timer.daemon = True
    timer.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        timer.cancel()
        server.server_close()
    if not state['ok']:
        print('Chưa đăng nhập xong (hết giờ hoặc đã huỷ).')
    return _result(state['domain'] or 'unknown', state['ok'])


def setup_command(domain, email=None):
    return 'python "%s" setup --ui' % os.path.abspath(__file__)


def cmd_ensure(a):
    info, _ = omi_session.inspect(expect_domain=a.domain)
    out = {'domain': a.domain, 'ok': info['token_ok']}
    if not info['token_ok']:
        email, pw = cred_load(a.domain)
        if pw:
            code, msg = do_login(a.domain)
            out.update(ok=code == 0, action='login', message=msg)
            if code == 4:
                out.update(need='tenant', command=setup_command(a.domain, email))
            elif code:
                out.update(need='setup', command=setup_command(a.domain, email))
        else:
            out.update(need='setup', command=setup_command(a.domain, _accounts().get(a.domain, {}).get('email')))
    if out['ok']:
        info, _ = omi_session.inspect(expect_domain=a.domain)
        out.update(tenant_id=info['tenant_id'], minutes_left=info['seconds_left'] // 60)
    # cùng ngưỡng và cùng nghĩa với omi_preflight.py: ok:true -> route=api, khỏi chạy preflight lần nữa
    out['route'] = 'api' if out['ok'] else ('blocked' if out.get('need') == 'setup' else 'login')
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out['ok'] else 3


def cmd_login(a):
    code, msg = do_login(a.domain, a.tenant_id)
    print(msg)
    return code


def cmd_status(a):
    email, pw = cred_load(a.domain)
    info, _ = omi_session.inspect(expect_domain=a.domain)
    left = info['seconds_left']
    print(json.dumps({'domain': a.domain, 'credential_stored': bool(pw), 'email': email,
                      'tenant_id': _accounts().get(a.domain, {}).get('tenant_id'),
                      'token_ok': info['token_ok'], 'minutes_left': None if left is None else left // 60,
                      'mcp_registered_no_password': _registered(a.domain)}, ensure_ascii=False))
    return 0


def cmd_forget(a):
    ok = cred_delete(a.domain)
    data = _accounts()
    if data.pop(a.domain, None) is not None:
        os.makedirs(os.path.dirname(ACCOUNTS), exist_ok=True)
        with open(ACCOUNTS, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    print('Đã xoá thông tin đăng nhập %s.' % a.domain if ok else 'Không có thông tin đã cất cho %s.' % a.domain)
    return 0


def cmd_serve(a):
    home = omi_session.server_home(a.domain)
    env = _mcp_env(a.domain, home=home)
    tenant_id = _accounts().get(a.domain, {}).get('tenant_id')
    if tenant_id:
        _drop_session_if_other_tenant(tenant_id, omi_session._session_path(home))
    if env is None:
        print('omi_login serve: chưa có thông tin đăng nhập cho %s; chạy omi_login.py setup.' % a.domain,
              file=sys.stderr)
        return 1
    return subprocess.call([_npx(), '-y', 'omicall-mcp'], env=env)


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('ensure', 'setup', 'login', 'status', 'forget', 'serve'):
        s = sub.add_parser(name)
        s.add_argument('--domain', required=name != 'setup', help='domain tenant (phần trước .omicrm.io)')
        if name in ('setup', 'login'):
            s.add_argument('--tenant-id', help='tenant cần chọn khi tài khoản có nhiều tenant')
        if name == 'setup':
            s.add_argument('--ui', action='store_true', help='mở form đăng nhập trên trình duyệt (localhost)')
            s.add_argument('--no-browser', action='store_true',
                           help='với --ui: chỉ in địa chỉ form (dòng đầu), agent tự mở trong khung trình duyệt của nó')
            s.add_argument('--email')
            s.add_argument('--env', help='OMICALL_ENV (mặc định của MCP: stg)')
            s.add_argument('--client', default='auto', choices=['auto', 'claude', 'codex', 'none'])
    a = ap.parse_args(argv)
    if a.domain:
        a.domain = omi_session._norm_domain(a.domain)
    return {'ensure': cmd_ensure, 'setup': cmd_setup, 'login': cmd_login, 'status': cmd_status,
            'forget': cmd_forget, 'serve': cmd_serve}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
