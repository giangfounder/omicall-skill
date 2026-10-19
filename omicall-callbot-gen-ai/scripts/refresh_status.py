# -*- coding: utf-8 -*-
# refresh_status.py <script_id>  — fetch script and publish to realtime/status.json
import json, sys, datetime, urllib.request

script_id = sys.argv[1]
session = json.load(open(r'C:\Users\User\.omicall-mcp\session.json', encoding='utf-8'))
h = {'Authorization': 'Bearer ' + session['accessToken']}
req = urllib.request.Request(
    'https://chatbot-gateway-v1-stg.omicrm.com/callbot/script/get/' + script_id, headers=h)
with urllib.request.urlopen(req, timeout=40) as r:
    d = json.loads(r.read().decode('utf-8'))
d['ts'] = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
json.dump(d, open(r'C:\Users\User\AppData\Local\Temp\opencode\realtime\status.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('dashboard updated:', script_id, 'v' + str(d['payload'].get('version')))