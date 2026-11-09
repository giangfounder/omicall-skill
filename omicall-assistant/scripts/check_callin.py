#!/usr/bin/env python3
"""Kiểm luồng gọi vào sau mỗi lần sửa/xuất bản bot, bằng MỘT lệnh (chỉ đọc, không ghi gì lên tenant).

  python <thư mục skill>/scripts/check_callin.py --domain <d> [--scratch <thư mục có tenant_context.json>]

Kiểm:
  1. Mỗi phím Tương tác phím có hành động Callbot: id kịch bản có phải bản MỚI NHẤT cùng uuid không (xuất bản đổi id,
     để id cũ thì phím chạy bản cũ). Lệch -> STALE kèm id mới cần map.
  2. Phím Ring_group/Ivr_menu: id còn tồn tại không (nhóm có trong internal_groups, menu có trong key_interactions).
  3. Kịch bản cuộc gọi (call_scripts, vd "Call in"): từng bước scripts[].action_id kiểm như phím (Callbot bản mới
     nhất, nhóm/menu còn tồn tại). Tenant gắn Callbot thẳng vào kịch bản cuộc gọi, không qua Tương tác phím, cũng bị
     STALE sau mỗi lần xuất bản.
  4. Đầu số: default_script có trống không (trống = gọi vào chưa nghe menu) -> WARN.
Script CHỈ BÁO. Map lại phím/kịch bản cuộc gọi/đầu số là cổng `gan_so` của user (orchestration.md mục 2), không tự làm.
tenant_context.json chỉ đọc (lấy tenant_id); khảo sát tổng đài ghi ra file riêng <scratch>/callin_survey.json.
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


def run_survey(domain, out):
    r = subprocess.run([sys.executable, os.path.join(HERE, 'config_survey.py'), '--out', out, '--domain', domain],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        print('Không khảo sát được cấu hình tổng đài:', r.stdout[-300:], r.stderr[-300:])
        sys.exit(2)
    with open(out, encoding='utf-8') as f:
        return json.load(f)


def read_tenant_id(ctx_path):
    try:
        with open(ctx_path, encoding='utf-8') as f:
            return ((json.load(f).get('tenant') or {}).get('tenant_id'))
    except (OSError, ValueError):
        return None


def list_callbot_scripts(domain, tenant_id):
    sys.path.insert(0, HERE)
    import omi_api
    resp = omi_api.get('chatbot', '/callbot/script/list-by-tenant/%s' % tenant_id, expect_domain=domain)
    data = resp.get('payload') if isinstance(resp, dict) and 'payload' in resp else resp
    return [s for s in (data or []) if isinstance(s, dict)]


def newest_of(scripts, script):
    same = [s for s in scripts if s.get('uuid') == script.get('uuid')]
    newest = [s for s in same if s.get('is_newest_version')]
    return max(newest or same, key=lambda s: (s.get('version') or 0))


def evaluate(pbx, scripts):
    """Trả (các dòng báo cáo, số lỗi STALE/MISSING). Không gọi mạng."""
    by_id = {s.get('id'): s for s in scripts}
    groups = {g.get('_id') for g in pbx.get('internal_groups', [])}
    menus = {m.get('_id') for m in pbx.get('key_interactions', [])}
    call_scripts = {c.get('_id'): c for c in pbx.get('call_scripts', [])}
    lines, bad = [], 0

    def check(label, t, act):
        """Một đích (phím TTP hoặc bước của kịch bản cuộc gọi) -> (dòng báo cáo, 1 nếu STALE/MISSING)."""
        if t == 'Callbot':
            cur = by_id.get(act)
            if not cur:
                return '  %s: MISSING  Callbot %s không có trong danh sách kịch bản' % (label, act), 1
            new = newest_of(scripts, cur)
            if new.get('id') != act:
                return '  %s: STALE    %s v%s -> map sang %s v%s (%s)' % (
                    label, act, cur.get('version'), new.get('id'), new.get('version'), new.get('name')), 1
            return '  %s: OK       %s v%s (%s)' % (label, act, cur.get('version'), cur.get('name')), 0
        if t == 'Ring_group':
            ok = act in groups
            return '  %s: %s  nhóm %s' % (label, 'OK     ' if ok else 'MISSING', act), 0 if ok else 1
        if t == 'Ivr_menu':
            ok = act in menus
            return '  %s: %s  menu %s' % (label, 'OK     ' if ok else 'MISSING', act), 0 if ok else 1
        return '  %s: ?        %s %s (chưa kiểm loại này)' % (label, t, act), 0

    for menu in pbx.get('key_interactions', []):
        lines.append('Menu "%s" (%s)' % (menu.get('name'), menu.get('_id')))
        for k in menu.get('keys', []):
            line, b = check('phím %s' % k.get('digit'), k.get('action_type'), k.get('action'))
            lines.append(line)
            bad += b
    # Kịch bản cuộc gọi (vd "Call in") trỏ thẳng Callbot bằng action_id = id bản đã xuất bản: xuất bản lại đổi id
    # nên phải chọn lại kịch bản AI Callbot trong kịch bản cuộc gọi, kể cả khi tenant không dùng Tương tác phím.
    for cs in call_scripts.values():
        lines.append('Kịch bản cuộc gọi "%s" (%s)' % (cs.get('name'), cs.get('_id')))
        for s in cs.get('scripts') or []:
            line, b = check('bước %s' % s.get('order'), s.get('action_type'), s.get('action_id'))
            lines.append(line)
            bad += b
    for h in pbx.get('hotlines', []):
        ds = h.get('default_script')
        if not ds:
            note = 'WARN chưa gắn kịch bản gọi vào (gọi vào chưa nghe menu)'
        elif ds in call_scripts:
            note = 'kịch bản %s ("%s")' % (ds, call_scripts[ds].get('name'))
        else:
            note = 'kịch bản ' + str(ds)
        lines.append('Đầu số %s: %s' % (h.get('number'), note))
    if bad:
        lines.append('STALE/MISSING: liệt kê phím/đầu số sẽ đổi và chờ user duyệt cổng gắn số trước khi map lại.')
    lines.append('RESULT %s' % ('FAIL' if bad else 'PASS'))
    return lines, bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--domain', required=True)
    ap.add_argument('--scratch', default=tempfile.gettempdir())
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    tenant_id = read_tenant_id(os.path.join(a.scratch, 'tenant_context.json'))
    if not tenant_id:
        print('Thiếu tenant_id trong tenant_context.json (khảo sát đợt 0 bằng tenant_survey.py trước).')
        return 2
    ctx = run_survey(a.domain, os.path.join(a.scratch, 'callin_survey.json'))
    lines, bad = evaluate(ctx.get('pbx', {}), list_callbot_scripts(a.domain, tenant_id))
    print('\n'.join(lines))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
