#!/usr/bin/env python3
"""Kiểm luồng gọi vào sau mỗi lần sửa/xuất bản bot, bằng MỘT lệnh (chỉ đọc, không ghi gì lên tenant).

  python <thư mục skill>/scripts/check_callin.py --domain <d> [--scratch <thư mục có tenant_context.json>]

Kiểm:
  1. Mỗi phím Tương tác phím có hành động Callbot: id kịch bản có phải bản MỚI NHẤT cùng uuid không (xuất bản đổi id,
     để id cũ thì phím chạy bản cũ). Lệch -> STALE kèm id mới cần map.
  2. Phím Ring_group/Ivr_menu: id còn tồn tại không (nhóm có trong internal_groups, menu có trong key_interactions).
  3. Đầu số: default_script có trống không (trống = gọi vào chưa nghe menu) -> WARN.
Exit 0: không STALE/MISSING (WARN vẫn 0). Exit 1: có STALE hoặc MISSING. Exit 2: lỗi chạy.
Không in token. Thay cho việc subagent hay LLM tự so từng id (tốn token và dễ sót).
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
PBX = os.path.join(SKILLS, 'omicall-pbx-config', 'scripts')
BOT = os.path.join(SKILLS, 'omicall-callbot-gen-ai', 'scripts')


def run_survey(domain, out):
    r = subprocess.run([sys.executable, os.path.join(PBX, 'config_survey.py'), '--out', out, '--domain', domain],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print('Không khảo sát được cấu hình tổng đài:', r.stdout[-300:], r.stderr[-300:])
        sys.exit(2)
    return json.load(open(out, encoding='utf-8'))


def list_callbot_scripts(domain, tenant_id):
    sys.path.insert(0, BOT)
    import omi_api
    import omi_save
    resp = omi_api.get('chatbot', '/callbot/script/list-by-tenant/%s' % tenant_id, expect_domain=domain)
    return [s for s in (omi_save._payload(resp) or []) if isinstance(s, dict)]


def newest_of(scripts, script):
    same = [s for s in scripts if s.get('uuid') == script.get('uuid')]
    newest = [s for s in same if s.get('is_newest_version')]
    return max(newest or same, key=lambda s: (s.get('version') or 0))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--domain', required=True)
    ap.add_argument('--scratch', default=tempfile.gettempdir())
    a = ap.parse_args()
    out = os.path.join(a.scratch, 'tenant_context.json')
    ctx = run_survey(a.domain, out)
    pbx = ctx.get('pbx', {})
    tenant_id = (ctx.get('tenant') or {}).get('tenant_id')
    if not tenant_id:
        print('Thiếu tenant_id trong tenant_context.json (chạy tenant_survey.py trước).')
        sys.exit(2)
    scripts = list_callbot_scripts(a.domain, tenant_id)
    by_id = {s.get('id'): s for s in scripts}
    groups = {g.get('_id') for g in pbx.get('internal_groups', [])}
    menus = {m.get('_id') for m in pbx.get('key_interactions', [])}
    bad = 0
    for menu in pbx.get('key_interactions', []):
        print('Menu "%s" (%s)' % (menu.get('name'), menu.get('_id')))
        for k in menu.get('keys', []):
            d, t, act = k.get('digit'), k.get('action_type'), k.get('action')
            if t == 'Callbot':
                cur = by_id.get(act)
                if not cur:
                    print('  phím %s: MISSING  Callbot %s không có trong danh sách kịch bản' % (d, act))
                    bad += 1
                    continue
                new = newest_of(scripts, cur)
                if new.get('id') != act:
                    print('  phím %s: STALE    %s v%s -> map sang %s v%s (%s)' % (
                        d, act, cur.get('version'), new.get('id'), new.get('version'), new.get('name')))
                    bad += 1
                else:
                    print('  phím %s: OK       %s v%s (%s)' % (d, act, cur.get('version'), cur.get('name')))
            elif t == 'Ring_group':
                ok = act in groups
                print('  phím %s: %s  nhóm %s' % (d, 'OK     ' if ok else 'MISSING', act))
                bad += 0 if ok else 1
            elif t == 'Ivr_menu':
                ok = act in menus
                print('  phím %s: %s  menu %s' % (d, 'OK     ' if ok else 'MISSING', act))
                bad += 0 if ok else 1
            else:
                print('  phím %s: ?        %s %s (chưa kiểm loại này)' % (d, t, act))
    for h in pbx.get('hotlines', []):
        ds = h.get('default_script')
        print('Đầu số %s: %s' % (h.get('number'), ('kịch bản ' + str(ds)) if ds else
                                'WARN chưa gắn kịch bản gọi vào (gọi vào chưa nghe menu)'))
    print('RESULT %s' % ('FAIL' if bad else 'PASS'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
