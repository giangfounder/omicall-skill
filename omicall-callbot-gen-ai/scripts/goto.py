# -*- coding: utf-8 -*-
# goto.py <script_id> — navigate the OMiCRM page tab to the callbot editor of the given script id
import json, sys, socket, base64, hashlib, struct, urllib.request

script_id = sys.argv[1]
url = 'https://giangnh2.omicrm.io/ai/callbot/script/update/%s?lng=vi' % script_id

tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=5).read().decode())
target = None
for t in tabs:
    if t['type'] == 'page' and 'omicrm.io' in t['url']:
        target = t
        break
if not target:
    print('no omicrm tab')
    sys.exit(1)
ws = target['webSocketDebuggerUrl']

# --- plain python websocket handshake ---
host, port = ws.split('://')[1].split('/')[0].split(':')
sock = socket.create_connection((host, int(port)), timeout=8)
key = base64.b64encode(b'hotchilli!').decode()
req = ("GET /devtools/page/%s HTTP/1.1\r\nHost: %s:%s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
       "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n") % (target['id'], host, port, key)
sock.sendall(req.encode())
buf = b''
while b'\r\n\r\n' not in buf:
    buf += sock.recv(4096)

def send(js):
    data = json.dumps(js).encode()
    mask = b'\x11\x22\x33\x44'
    head = b'\x81'
    ln = len(data)
    if ln < 126:
        head += bytes([0x80 | ln])
    elif ln < 65536:
        head += bytes([0x80 | 126]) + struct.pack('>H', ln)
    else:
        head += bytes([0x80 | 127]) + struct.pack('>Q', ln)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    sock.sendall(head + mask + masked)

send({"id": 1, "method": "Page.navigate", "params": {"url": url}})
try:
    print('navigated to:', url)
finally:
    sock.close()