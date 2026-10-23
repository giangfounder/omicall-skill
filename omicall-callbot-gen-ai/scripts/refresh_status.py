# -*- coding: utf-8 -*-
# refresh_status.py <script_id>  — fetch script and publish to %TEMP%/omicrm-realtime/status.json (mở cùng realtime_index.html)
import json, os, sys, datetime, tempfile, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from omi_session import claims, get_token, headers

script_id = sys.argv[1]
req = urllib.request.Request(
    'https://chatbot-gateway-v1-stg.omicrm.com/callbot/script/get/' + script_id, headers=headers())
with urllib.request.urlopen(req, timeout=40) as r:
    d = json.loads(r.read().decode('utf-8'))
d['ts'] = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
d['domain'] = claims(get_token()).get('domain')
out = os.path.join(tempfile.gettempdir(), 'omicrm-realtime')
os.makedirs(out, exist_ok=True)
json.dump(d, open(os.path.join(out, 'status.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('dashboard updated:', script_id, 'v' + str(d['payload'].get('version')), '->', out)
