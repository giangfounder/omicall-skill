# -*- coding: utf-8 -*-
"""Gọi thử kịch bản Callbot ngay trên trình duyệt bằng OMICallSDK web v3 (không cần điện thoại).

  python webcall_test.py setup --domain <sipRealm> --ext <sipUser>
      User tự chạy trong terminal: nhập mật khẩu SIP của máy nhánh (ô ẩn), lưu vào kho bí mật hệ điều hành.
  python webcall_test.py open  --domain <sipRealm> --ext <sipUser> --number <số gọi> [--bot-name ...]
      Mở trang web call có phụ đề trực tiếp; user tự nói bằng micro thật.
  python webcall_test.py auto  --domain <sipRealm> --ext <sipUser> --number <số gọi> --plan <plan.json|thư mục ca>
      Tự kiểm thử: đọc các câu khách của từng ca thành giọng nói (edge-tts), mỗi ca một cuộc gọi, phát câu khách
      sau khi bot nói xong, gác máy; lưu suite.json + results/<ca>.txt|json (vòng lặp: references/webcall-test.md mục 7).
      Ca có "persona": khách AI, Claude (--model) soạn từng câu khách theo câu bot vừa nói (cần ANTHROPIC_API_KEY).

Ý nghĩa và nguồn của từng tham số: references/webcall-test.md. Mỗi lần open/auto là một cuộc gọi thật
(tính phút tổng đài): chỉ chạy khi user đồng ý. Thư mục chạy nằm ở OMI_SCRATCH (hoặc thư mục tạm),
không ghi gì vào thư mục skill. config.json (có mật khẩu SIP) bị xoá ngay khi trang đăng ký xong.
Cần: Google Chrome 135+ (phụ đề lời bot), pip install websocket-client edge-tts (anthropic cho ca khách AI).
"""
import argparse, asyncio, functools, getpass, hashlib, http.server, json, os, shutil, socket, subprocess
import sys, tempfile, threading, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE_DIR = os.path.join(HERE, 'webcall')
CDP_PORT = 9223
DEFAULT_SDK = '3.0.35'
DEFAULT_VOICE = 'vi-VN-NamMinhNeural'
DEFAULT_MODEL = 'claude-opus-5-5'
TTS_CACHE = os.path.join(os.path.expanduser('~'), '.cache', 'omicall-skill', 'tts')


# ---------- mật khẩu SIP: kho bí mật hệ điều hành (dùng chung cơ chế với omi_login.py) ----------

def _sip_key(domain, ext):
    return '%s#sip%s' % (domain, ext)


def sip_save(domain, ext, password):
    if os.name == 'nt':
        sys.path.insert(0, HERE)
        import omi_login
        return omi_login.cred_save(_sip_key(domain, ext), str(ext), password)
    import keyring
    keyring.set_password('omicall-webcall', _sip_key(domain, ext), password)
    return 'keyring'


def sip_load(domain, ext):
    if os.environ.get('OMI_SIP_PASSWORD'):
        return os.environ['OMI_SIP_PASSWORD']
    try:
        if os.name == 'nt':
            sys.path.insert(0, HERE)
            import omi_login
            return omi_login.cred_load(_sip_key(domain, ext))[1]
        import keyring
        return keyring.get_password('omicall-webcall', _sip_key(domain, ext))
    except Exception:
        return None


# ---------- phục vụ trang + điều khiển Chrome ----------

def find_chrome():
    for p in [os.environ.get('CHROME_PATH'),
              r'C:\Program Files\Google\Chrome\Application\chrome.exe',
              r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
              os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
              '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
              shutil.which('google-chrome'), shutil.which('chrome')]:
        if p and os.path.exists(p):
            return p
    sys.exit('Không tìm thấy Google Chrome (đặt biến CHROME_PATH).')


def serve(root):
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
    handler.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return 'http://localhost:%d/' % port


def _tabs():
    return json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % CDP_PORT, timeout=3).read())


class Page:
    def __init__(self, ws_url):
        import websocket
        self.ws = websocket.create_connection(ws_url, timeout=10, suppress_origin=True)
        self.n = 0

    def eval(self, expr, timeout=30, promise=False):
        self.n += 1
        self.ws.send(json.dumps({'id': self.n, 'method': 'Runtime.evaluate', 'params': {
            'expression': expr, 'returnByValue': True, 'awaitPromise': promise}}))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.ws.settimeout(max(1, deadline - time.monotonic()))
            msg = json.loads(self.ws.recv())
            if msg.get('id') == self.n:
                r = msg.get('result', {})
                if r.get('exceptionDetails'):
                    d = r['exceptionDetails']
                    raise RuntimeError(d.get('exception', {}).get('description') or d.get('text'))
                return r.get('result', {}).get('value')
        raise TimeoutError(expr[:60])


def open_page(url):
    """Mở url trong Chrome riêng (profile tạm, cổng CDP 9223), trả về Page."""
    try:
        _tabs()
        running = True
    except Exception:
        running = False
    if not running:
        profile = os.path.join(tempfile.gettempdir(), 'omicall-webcall-chrome')
        subprocess.Popen([find_chrome(), '--remote-debugging-port=%d' % CDP_PORT, '--user-data-dir=' + profile,
                          '--no-first-run', '--no-default-browser-check',
                          '--autoplay-policy=no-user-gesture-required',
                          '--use-fake-ui-for-media-stream', 'about:blank'])
    for _ in range(40):
        try:
            page = next(t for t in _tabs() if t['type'] == 'page')
            break
        except Exception:
            time.sleep(0.5)
    else:
        sys.exit('Không kết nối được Chrome qua cổng %d.' % CDP_PORT)
    p = Page(page['webSocketDebuggerUrl'])
    p.eval('location.href = %s' % json.dumps(url))
    return p


def prepare_run(args):
    base = os.environ.get('OMI_SCRATCH') or tempfile.gettempdir()
    run_dir = os.path.join(args.out or base, time.strftime('webcall-%Y%m%d-%H%M%S'))
    shutil.copytree(PAGE_DIR, run_dir)
    return run_dir


def write_config(args, password, run_dir):
    """Ghi config.json (có mật khẩu SIP) ngay trước khi mở trang; wait_registered/finally xoá nó."""
    cfg = {'sdkVersion': args.sdk_version, 'sipRealm': args.domain, 'sipUser': str(args.ext),
           'sipPassword': password, 'phoneNumber': args.number, 'botName': args.bot_name}
    with open(os.path.join(run_dir, 'config.json'), 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False)


def wait_registered(page, run_dir):
    state = None
    for _ in range(60):
        time.sleep(0.5)
        state = page.eval("document.getElementById('pill')?.dataset.s + '|' + document.getElementById('pillText')?.textContent + '|' + document.getElementById('sub')?.textContent")
        s = (state or '').split('|')[0]
        if s in ('ready', 'error'):
            break
    try:
        os.remove(os.path.join(run_dir, 'config.json'))  # trang đã đọc xong, không để mật khẩu trên đĩa
    except OSError:
        pass
    if not state or not state.startswith('ready'):
        sys.exit('Máy nhánh chưa đăng ký được: %s (xem bảng lỗi trong references/webcall-test.md)' % state)


def collect_plans(paths):
    """--plan nhận file plan.json hoặc thư mục chứa nhiều file *.json (mỗi file một ca), chạy theo thứ tự tên."""
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += sorted(os.path.join(p, f) for f in os.listdir(p) if f.endswith('.json'))
        else:
            files.append(p)
    if not files:
        sys.exit('Không có plan.json nào.')
    return files


async def tts_file(text, voice, dest):
    """Tạo mp3 cho một câu (edge-tts), có bộ nhớ đệm theo (giọng, câu) và thử lại khi dịch vụ trả rỗng."""
    import edge_tts
    key = hashlib.sha1(('%s|%s' % (voice, text)).encode('utf-8')).hexdigest()
    cached = os.path.join(TTS_CACHE, key + '.mp3')
    if os.path.exists(cached) and os.path.getsize(cached) > 0:
        shutil.copyfile(cached, dest)
        return
    # Gọi thư viện trực tiếp: truyền tiếng Việt qua dòng lệnh trên Windows bị lỗi mã hoá
    for attempt in range(4):  # dịch vụ edge-tts đôi khi trả rỗng hoặc giới hạn tần suất: thử lại
        try:
            await edge_tts.Communicate(text, voice).save(dest)
            os.makedirs(TTS_CACHE, exist_ok=True)
            shutil.copyfile(dest, cached)
            return
        except Exception as e:
            if attempt == 3:
                raise RuntimeError('Không tạo được giọng đọc cho câu "%s": %s' % (text[:40], e))
            await asyncio.sleep(2 * (attempt + 1))


def make_audio(plan_path, run_dir, voice, idx):
    """Sinh giọng đọc cho từng câu khách; trả về (đường dẫn plan tương đối với trang, plan).
    Ca khách AI (có "persona") không có câu soạn sẵn: giọng được tạo lúc gọi."""
    with open(plan_path, encoding='utf-8') as f:
        plan = json.load(f)
    plan.setdefault('id', 'ca%02d' % idx)
    plan.setdefault('name', os.path.splitext(os.path.basename(plan_path))[0])
    plan['voice'] = voice = plan.get('voice') or voice
    rel = 'autotest/%s' % plan['id']
    os.makedirs(os.path.join(run_dir, rel), exist_ok=True)

    async def gen():
        for i, t in enumerate(plan.get('turns', []), 1):
            t.setdefault('id', 't%d' % i)
            if not t.get('text'):  # lượt im lặng ({"silence": ms}): không cần giọng đọc
                continue
            t['audio'] = '%s.mp3' % t['id']
            try:
                await tts_file(t['text'], voice, os.path.join(run_dir, rel, t['audio']))
            except RuntimeError as e:
                raise SystemExit('%s/%s: %s' % (plan['id'], t['id'], e))
    if 'persona' not in plan:
        asyncio.run(gen())
    with open(os.path.join(run_dir, rel, 'plan.json'), 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    return rel + '/plan.json', plan


# ---------- khách AI (Claude) ----------

END_MARK = '[KET_THUC]'

CUSTOMER_SYSTEM = """Bạn đóng vai một khách hàng người Việt đang gọi điện tới tổng đài để kiểm thử một trợ lý tổng đài tự động.
Mỗi lượt bạn nhận câu tổng đài vừa nói (do máy nhận dạng giọng nói chép lại, có thể sai chữ) và trả lời đúng một lượt của khách.

Vai khách: {persona}
Mục tiêu cuộc gọi: {goal}
Thông tin khách được phép dùng (không bịa thêm ngoài danh sách này): {facts}

Quy tắc:
- Chỉ viết đúng câu khách nói ra miệng: tiếng Việt tự nhiên, ngắn (một đến hai câu), không ký hiệu, không emoji, không markdown, số viết bằng chữ.
- Trả lời đúng câu tổng đài vừa hỏi; tổng đài hỏi điều không có trong thông tin trên thì nói chưa rõ hoặc chưa nhớ, không bịa.
- Câu tổng đài nghe vô nghĩa hoặc bị cắt (do nhận dạng sai) thì hỏi lại như người thật ("Em nói lại giúp anh được không?").
- Tổng đài im lặng thì hỏi xem tổng đài còn nghe máy không.
- Làm theo mục tiêu, kể cả các tình huống khó nêu trong mục tiêu (đổi ý, chen ngang, hỏi giá…), nhưng không bỏ vai.
- Khi mục tiêu đã xong, hoặc tổng đài đã chào kết thúc, nói một câu chào ngắn rồi thêm {end} ở cuối. Không thêm {end} trong trường hợp khác."""


def customer_reply(client, model, plan, history, bot_text):
    """Một lượt khách: history là danh sách message (user = câu tổng đài, assistant = câu khách)."""
    import anthropic
    history.append({'role': 'user', 'content': 'Tổng đài: ' + (bot_text or '(tổng đài im lặng)')})
    system = CUSTOMER_SYSTEM.format(persona=plan.get('persona', ''), goal=plan.get('goal', ''),
                                    facts=json.dumps(plan.get('facts', {}), ensure_ascii=False), end=END_MARK)
    try:
        resp = client.beta.messages.create(
            model=model, max_tokens=1024, system=system, messages=history,
            output_config={'effort': 'low'},  # lượt thoại ngắn: ưu tiên độ trễ thấp
            betas=['server-side-fallback-2026-07-01'], fallbacks='default',
        )
    except anthropic.APIStatusError as e:
        raise RuntimeError('Claude API lỗi %s: %s' % (e.status_code, e.message))
    except anthropic.APIConnectionError:
        raise RuntimeError('Không kết nối được Claude API')
    if resp.stop_reason == 'refusal':
        raise RuntimeError('Claude từ chối soạn câu khách')
    text = ' '.join(b.text for b in resp.content if b.type == 'text').strip()
    history.append({'role': 'assistant', 'content': text})
    done = END_MARK in text
    return text.replace(END_MARK, '').strip(), done


def run_persona(page, run_dir, rel, plan, client, model):
    """Một cuộc gọi khách AI: chờ bot nói → Claude soạn câu → edge-tts → phát; lặp tới max_turns."""
    case_dir = rel.rsplit('/', 1)[0]
    if not page.eval('AutoTest.begin(%s)' % json.dumps(plan['id']), timeout=90, promise=True):
        return page.eval('AutoTest.result')
    history, last = [], {'ended': False}
    for n in range(1, int(plan.get('max_turns', 8)) + 1):
        last = page.eval('AutoTest.waitBot()', timeout=120, promise=True)
        if last['ended']:
            break
        try:
            text, done = customer_reply(client, model, plan, history, last['botText'])
            if not text:
                break
            audio = '%s/d%02d.mp3' % (case_dir, n)
            asyncio.run(tts_file(text, plan['voice'], os.path.join(run_dir, audio)))
        except RuntimeError as e:
            page.eval('(r => { r.status = "error"; r.error = %s; r.events.push({type: "error", message: r.error}); })'
                      '(AutoTest.result)' % json.dumps(str(e)))
            break
        print('  KHÁCH(AI): ' + text, flush=True)
        if not page.eval('AutoTest.say(%s, %s, %s)' % (json.dumps(audio), json.dumps(text), json.dumps('d%02d' % n)),
                         timeout=60, promise=True) or done:
            break
    if not last['ended']:
        page.eval('AutoTest.waitBot()', timeout=120, promise=True)  # câu chào cuối của bot
    return page.eval('AutoTest.end()', timeout=600, promise=True)


def run_case(page, run_dir, rel, plan, ai=None):
    """Một cuộc gọi thật cho một ca; ghi results/<id>.json và .txt, trả về dòng tóm tắt.
    ai = (client, model) cho ca khách AI."""
    print('\n=== %s: %s' % (plan['id'], plan.get('name', '')), flush=True)
    try:
        if 'persona' in plan:
            result = run_persona(page, run_dir, rel, plan, *ai)
        else:
            result = page.eval('AutoTest.run(%s)' % json.dumps(rel), timeout=900, promise=True)
    except Exception as e:  # trang treo / mất kết nối: ghi lỗi, chạy tiếp ca sau
        result = {'status': 'error', 'error': str(e), 'events': [], 'transcript': []}
    os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
    base = os.path.join(run_dir, 'results', plan['id'])
    with open(base + '.json', 'w', encoding='utf-8') as f:
        json.dump({'plan': plan, **result}, f, ensure_ascii=False, indent=2)
    lines = ['[%s] %s: %s' % (l['at'], 'BOT' if l['who'] == 'bot' else 'KHÁCH', l['text']) for l in result['transcript']]
    with open(base + '.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('Trạng thái: %s | uuid: %s' % (result['status'], result.get('callUuid')))
    if result.get('error'):
        print('Lỗi: ' + result['error'])
    print('\n'.join(lines), flush=True)
    return {'id': plan['id'], 'name': plan.get('name'), 'status': result['status'], 'error': result.get('error'),
            'callUuid': result.get('callUuid'), 'ended_early': any(e['type'] == 'ended_early' for e in result['events']),
            'transcript': os.path.relpath(base + '.txt', run_dir)}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('setup', 'open', 'auto'):
        p = sub.add_parser(name)
        p.add_argument('--domain', required=True, help='sipRealm: tên tenant, phần trước .omicrm.io')
        p.add_argument('--ext', required=True, help='sipUser: số máy nhánh dùng để gọi (ví dụ 100)')
        if name == 'setup':
            continue
        p.add_argument('--number', required=True, help='phoneNumber: số đang trỏ vào kịch bản cần thử (hotline)')
        p.add_argument('--bot-name', default='Trợ lý AI', help='chỉ để hiển thị trên trang')
        p.add_argument('--sdk-version', default=DEFAULT_SDK, help='phiên bản OMICallSDK web v3')
        p.add_argument('--out', help='thư mục chứa các lần chạy (mặc định OMI_SCRATCH hoặc thư mục tạm)')
        if name == 'auto':
            p.add_argument('--plan', required=True, nargs='+',
                           help='file plan.json hoặc thư mục nhiều ca: {"id","name","goal","expect":[],"turns":[{"text","expect"?}]}')
            p.add_argument('--gap', type=float, default=4, help='giây nghỉ giữa hai cuộc gọi')
            p.add_argument('--voice', default=DEFAULT_VOICE, help='giọng edge-tts cho câu khách')
            p.add_argument('--model', default=DEFAULT_MODEL, help='mô hình Claude cho ca khách AI (có "persona")')
    args = ap.parse_args()

    if args.cmd == 'setup':
        pw = getpass.getpass('Mật khẩu SIP của máy nhánh %s@%s (không hiện khi gõ): ' % (args.ext, args.domain))
        if not pw:
            sys.exit('Chưa nhập mật khẩu.')
        print('Đã lưu vào %s.' % sip_save(args.domain, args.ext, pw))
        return

    password = sip_load(args.domain, args.ext)
    if not password:
        sys.exit('Chưa có mật khẩu SIP cho %s@%s. User tự chạy trong terminal:\n  python "%s" setup --domain %s --ext %s'
                 % (args.ext, args.domain, os.path.abspath(__file__), args.domain, args.ext))

    run_dir = prepare_run(args)
    cases = [make_audio(p, run_dir, args.voice, i) for i, p in enumerate(collect_plans(args.plan), 1)] \
        if args.cmd == 'auto' else []
    ai = None
    if any('persona' in plan for _, plan in cases):
        try:
            import anthropic
        except ImportError:
            sys.exit('Ca khách AI cần thư viện anthropic: pip install anthropic')
        # Khóa lấy từ ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / hồ sơ `ant auth login`; user tự đặt, không nhận qua chat
        if not (os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('ANTHROPIC_AUTH_TOKEN')
                or shutil.which('ant')):
            sys.exit('Ca khách AI cần khóa Claude API: user tự đặt biến môi trường ANTHROPIC_API_KEY rồi chạy lại.')
        ai = (anthropic.Anthropic(), args.model)
    url = serve(run_dir) + ('?auto=1' if cases else '')
    write_config(args, password, run_dir)
    try:
        page = open_page(url)
        wait_registered(page, run_dir)
    finally:  # lỗi giữa chừng cũng không để mật khẩu SIP trên đĩa
        try:
            os.remove(os.path.join(run_dir, 'config.json'))
        except OSError:
            pass

    if args.cmd == 'open':
        print('Trang đã sẵn sàng, user bấm "Bắt đầu trò chuyện" trong cửa sổ Chrome. Ctrl+C để dừng.')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return

    print('Gọi %s: %d ca, thư mục %s' % (args.number, len(cases), run_dir), flush=True)
    summary = []
    for i, (rel, plan) in enumerate(cases):
        if i:
            time.sleep(args.gap)
        summary.append(run_case(page, run_dir, rel, plan, ai))
        err = summary[-1].get('error') or ''
        if 'socket' in err or 'Connection' in err:  # cửa sổ Chrome bị đóng: các ca sau chắc chắn lỗi, dừng luôn
            print('Mất kết nối với cửa sổ Chrome kiểm thử, dừng bộ ca. Chạy lại các ca còn lại sau.', flush=True)
            break
    with open(os.path.join(run_dir, 'suite.json'), 'w', encoding='utf-8') as f:
        json.dump({'number': args.number, 'domain': args.domain, 'cases': summary}, f, ensure_ascii=False, indent=2)
    print('\nTổng: %d ca, %d chạy xong, %d lỗi. Kết quả: %s' % (
        len(summary), sum(c['status'] == 'done' for c in summary),
        sum(c['status'] != 'done' for c in summary), os.path.join(run_dir, 'suite.json')))

if __name__ == '__main__':
    main()
