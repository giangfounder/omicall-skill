"""Kiểm tài liệu omicall-omiflow (offline): Đường nhanh, node-status.json, checklist khớp validator, dữ liệu khách đã làm sạch.
Không mở bất kỳ file credentials.md nào (bỏ qua theo đường dẫn).
"""
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SKILL = os.path.join(ROOT, 'omicall-omiflow')
REF = os.path.join(SKILL, 'references')
ENUM_MIN = 33  # số nhãn [enum] trong node-catalog.md ở bản trước đợt sửa (baseline)


def read(*p):
    with open(os.path.join(SKILL, *p), encoding='utf-8') as f:
        return f.read()


def read_path(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def skill_text_files():
    for d, _, files in os.walk(SKILL):
        if '__pycache__' in d:
            continue
        for fn in files:
            if fn == 'credentials.md' or not fn.endswith(('.md', '.py', '.json')):
                continue
            yield os.path.join(d, fn)


class DocsTest(unittest.TestCase):
    def test_fast_path_block(self):
        lines = read('SKILL.md').split('\n')
        idx = [i for i, l in enumerate(lines) if l.strip() == '## Đường nhanh']
        self.assertEqual(len(idx), 1)
        self.assertLess(idx[0], 30)
        end = next(i for i in range(idx[0] + 1, len(lines)) if lines[i].startswith('## '))
        self.assertLessEqual(end - idx[0], 20, 'khối Đường nhanh dài quá 20 dòng')
        block = '\n'.join(lines[idx[0]:end])
        for s in ('omi_preflight.py', 'tenant_survey.py', 'node-status.json', 'validate_flow.py', 'omi_save.py', 'is_list'):
            self.assertIn(s, block)
        before = '\n'.join(lines[:idx[0]])
        self.assertIn('## Bước bắt buộc: cập nhật skill', before)

    def test_safety_phrases_kept(self):
        allt = '\n'.join(read_path(p) for p in skill_text_files())
        for s in ('name_mappings', 'Hoạt động', 'Xuất bản', 'Cần xác nhận', 'mật khẩu'):
            self.assertIn(s, allt)

    def test_no_pointer_event_main_and_no_cookie_bypass(self):
        sk = read('SKILL.md') + '\n' + read('references', 'playbook.md')  # thao tác UI nằm ở playbook
        self.assertNotIn('dùng PointerEvent qua JS', sk)
        self.assertIn('left_click_drag', sk)
        self.assertNotIn('rồi lấy token từ cookie', sk)
        ui = read('references', 'ui-build-and-test.md')
        self.assertNotIn('Cách dùng được: gọi API bằng `fetch` **ngay trong trang**', ui)
        self.assertNotIn('cookie `{domain}_omicrm_io` → key', read('references', 'api-reference.md'))

    def test_api_reference_dual_and_checklist(self):
        api = read('references', 'api-reference.md')
        dual = api[api.index('## Node và nhánh — DUAL'):api.index('## Lưu flow')]
        self.assertIn('name_mappings', dual)
        checklist = api[api.index('## Checklist'):]
        self.assertIn('name_mappings', checklist)
        self.assertRegex(checklist, r'DELAY.*CONDITION')
        val = read('scripts', 'validate_flow.py')
        for code in ['C%d' % i for i in range(1, 8)] + ['X%d' % i for i in range(1, 12)]:
            self.assertIn('[%s]' % code, checklist, code)
            self.assertIn("'%s'" % code, val, code)
        # add_v2 ✔ 11/2026 nhưng tạo luôn bản ĐÃ xuất bản: mọi chỗ nhắc trong mục Lưu flow và bảng Endpoint phải kèm cảnh báo
        save = api[api.index('## Lưu flow'):api.index('## Checklist')]
        if 'add_v2' in save:
            self.assertIn('ĐÃ xuất bản', save)
        row = next(l for l in api.split('\n') if l.startswith('| POST | `/omi_v2/campaign/add_v2`'))
        self.assertIn('ĐÃ xuất bản', row)
        self.assertIn('user duyệt', row)
        self.assertNotIn('chưa chạy', row)
        upd = next(l for l in api.split('\n') if l.startswith('| POST | `/omi_v2/campaign/update_v2'))
        self.assertIn('chưa kiểm chứng', upd)
        self.assertEqual(len(re.findall(r'^## Tạo flow mới bằng `add_v2`', api, re.M)), 1)
        self.assertNotIn('chưa chạy thật', read('references', 'playbook.md'))

    def test_id_and_webhook_url_single_section(self):
        api = read('references', 'api-reference.md')
        self.assertEqual(api.count('## Ba loại id và URL webhook'), 1)
        sec = api[api.index('## Ba loại id và URL webhook'):]
        sec = sec[:sec.index('\n## ', 1)] if '\n## ' in sec[1:] else sec
        for s in ('flow_outline.py --list', 'kick_off.id', 'Cần xác nhận'):
            self.assertIn(s, sec)
        stale = ['không xem lại được sau khi xuất bản', 'URL webhook có thể sinh mới', 'Xuất bản đổi id flow →']
        for f in ('playbook.md', 'ui-build-and-test.md', 'node-catalog.md'):
            t = read('references', f)
            for s in stale:
                self.assertNotIn(s, t, (f, s))

    def test_agent_does_not_publish(self):
        ui = read('references', 'ui-build-and-test.md')
        for s in ('dựng, xuất bản và kiểm thử', 'đặt lại giá trị thật và xuất bản', '→ **Xuất bản** → Xác nhận'):
            self.assertNotIn(s, ui)

    def test_limit_patterns_flag_x11(self):
        # mẫu đặt giới hạn lượt phải ghi rõ lệch quy ước mặc định (X11)
        tail = 'lệch quy ước mặc định, chỉ giữ nếu user yêu cầu'
        dp = read('references', 'design-patterns.md')
        nc = read('references', 'node-catalog.md')
        for text, key in ((dp, 'Flow B — GENERAL'), (dp, 'tối đa N lần'), (dp, 'giao bot một lần'),
                          (nc, '1 lần/đối tượng')):
            line = next(l for l in text.split('\n') if key in l)
            self.assertIn(tail, line, key)
        for f, s in (('SKILL.md', read('SKILL.md')), ('playbook.md', read('references', 'playbook.md'))):
            self.assertNotIn('Giới hạn số lần đi qua (mặc định 2)', s, f)

    def test_write_before_send_in_gotchas(self):
        sk = read('SKILL.md')
        got = sk[sk.index('## Gotchas'):sk.index('## Chi tiết theo bước')]
        self.assertIn('Ghi dữ liệu trước, gửi tin sau', got)
        self.assertIn('chưa kiểm chứng', got)

    def test_single_canvas_section(self):
        ui = read('references', 'ui-build-and-test.md')
        heads = re.findall(r'^## (\d+)\. (.+)$', ui, re.M)
        self.assertEqual([int(n) for n, _ in heads], list(range(1, len(heads) + 1)))
        canvas = [n for n, t in heads if t.startswith('Canvas')]
        self.assertEqual(len(canvas), 1)
        start = ui.index('## %s. Canvas' % canvas[0])
        end = ui.index('\n## ', start + 1)
        before_after = ui[:start] + ui[end:]
        self.assertNotIn('left_click_drag', before_after)
        self.assertNotIn('chỉ làm trôi canvas; bấm cổng cũng không mở bảng chọn. Đường chắc chắn', ui)
        for f in ('playbook.md', 'react-flow-selectors.md'):
            self.assertIn('Canvas: nối, xoá, sửa cạnh', read('references', f), f)
        self.assertIn('Cần xác nhận', ui[start:end])

    def test_first_save_single_statement(self):
        api = read('references', 'api-reference.md')
        self.assertEqual(api.count('**Vỏ flow tối thiểu và lần "Lưu lại" đầu**'), 1)
        for f in ('node-catalog.md', 'playbook.md', 'ui-build-and-test.md'):
            t = read('references', f)
            self.assertNotIn('editor không còn nút lưu nháp', t, f)
            self.assertNotIn('lưu ngay sau khi chọn trigger', t, f)
        self.assertIn('vỏ tối thiểu', read('SKILL.md'))

    def test_b5_split_wait_and_reminder_fail_branch(self):
        dp = read('references', 'design-patterns.md')
        b5 = dp[dp.index('### B5.'):dp.index('### B6.')]
        self.assertNotIn('`DELAY 5 giây` →', b5)
        self.assertIn('phút', b5)
        self.assertIn('Cần xác nhận', b5)
        row = next(l for l in dp.split('\n') if l.startswith('| **Nhắc lịch hẹn'))
        self.assertIn('Thất bại', row)
        self.assertIn('Cần xác nhận', row)

    def test_webhook_examples_clean(self):
        w = read('references', 'webhook-examples.md')
        for s in ('{tenant_id}-{token}', 'TODO'):
            self.assertNotIn(s, w)
        self.assertIn('{kick_off.id}', w)
        self.assertIn('Ba loại id và URL webhook', w)

    def test_bot_end_branch_documented(self):
        self.assertNotIn('FAIL X1 giả', read('references', 'node-catalog.md'))
        api = read('references', 'api-reference.md')
        self.assertIn('customer_not_response.id', api[api.index('## Node và nhánh'):api.index('## Lưu flow')])

    def test_no_machine_or_host_guess_or_industry(self):
        own = ['SKILL.md'] + ['references/%s' % f for f in (
            'api-reference.md', 'concepts.md', 'design-patterns.md', 'node-catalog.md', 'playbook.md',
            'react-flow-selectors.md', 'solution-map.md', 'ui-build-and-test.md', 'webhook-examples.md')]
        for f in own:
            t = read(*f.split('/'))
            for s in ('1142', 'Windows-MCP', 'production đổi domain', 'bệnh nhân', 'tái khám', 'phân bón'):
                self.assertNotIn(s, t, (f, s))
            self.assertNotRegex(t, r'\bHIS\b', f)

    def test_ui_section_refs_resolve(self):
        ui = read('references', 'ui-build-and-test.md')
        heads = dict(re.findall(r'^## (\d+)\. (.+)$', ui, re.M))
        files = [os.path.join(SKILL, 'SKILL.md'), os.path.join(SKILL, 'scripts', 'validate_flow.py')]
        files += [os.path.join(REF, f) for f in os.listdir(REF) if f.endswith(('.md', '.json'))]
        for s in ('omicall-ai-insight', 'omicall-crm-config', 'omicall-pbx-config'):
            files.append(os.path.join(ROOT, s, 'SKILL.md'))
            files += [os.path.join(ROOT, s, 'references', f) for f in os.listdir(os.path.join(ROOT, s, 'references'))]
        n = 0
        for p in files:
            for m in re.finditer(r'ui-build-and-test\.md`?\)? \(?mục ([\d, –]+)(?: \*([^*]+)\*)?', read_path(p)):
                for num in re.findall(r'\d+', m.group(1)):
                    self.assertIn(num, heads, (p, m.group(0)))
                    n += 1
                if m.group(2):
                    self.assertIn(m.group(2), heads[re.findall(r'\d+', m.group(1))[-1]], (p, m.group(0)))
            for m in re.finditer(r'ui-build-and-test\.md`? mục \*([^*]+)\*', read_path(p)):
                self.assertTrue(any(m.group(1) in t for t in heads.values()), (p, m.group(0)))
                n += 1
        self.assertGreater(n, 5)

    def test_cleaned_customer_data(self):
        banned = ['/api/BenhNhan', 'mabenhnhan', 'CẤP CỨU KHẨN CẤP', '0912345678', '3 skill',
                  'LichKham', 'tenBenhNhan', 'Xe tải']
        phone = re.compile(r'(?<!\d)0[35789]\d{8}(?!\d)')
        for p in skill_text_files():
            s = read_path(p)
            for b in banned:
                self.assertNotIn(b, s, f'{b} còn trong {p}')
            self.assertIsNone(phone.search(s), f'SĐT trong {p}')
            self.assertNotRegex(s, r'eyJ[A-Za-z0-9_-]{10,}')

    def test_enum_count_not_decreased(self):
        self.assertGreaterEqual(read('references', 'node-catalog.md').count('[enum]'), ENUM_MIN)
        base = os.environ.get('OMI_BASELINE_DIR')
        if base:
            p = os.path.join(base, 'omicall-omiflow', 'references', 'node-catalog.md')
            if os.path.exists(p):
                self.assertGreaterEqual(read('references', 'node-catalog.md').count('[enum]'),
                                        read_path(p).count('[enum]'))

    def test_node_catalog_numbering(self):
        nc = read('references', 'node-catalog.md')
        nums = [int(m) for m in re.findall(r'^## (\d+)\.', nc, re.M)]
        self.assertEqual(nums, list(range(1, len(nums) + 1)))
        for t in ('ADD_NEW_CONTACT', 'UPDATE_INFO_CONTACT'):
            row = next(l for l in nc.split('\n') if l.startswith(f'| `{t}` |'))
            self.assertIn('runtime verify (mục 6', row)
            self.assertIn('editor một phần', row)

    def test_node_status(self):
        with open(os.path.join(REF, 'node-status.json'), encoding='utf-8') as f:
            rows = json.load(f)
        self.assertIsInstance(rows, list)
        self.assertGreater(len(rows), 10)
        keys = {'type', 'side', 'status', 'template', 'source', 'verified_on', 'ui_hint'}
        cache = {}
        for r in rows:
            self.assertEqual(set(r), keys, r)
            self.assertIn(r['side'], ('runtime', 'editor', 'edge', 'action'))
            self.assertIn(r['status'], ('verified', 'enum', 'ui_only', 'unverified'))
            self.assertIsNone(r['template'])  # chưa có template nào được duyệt verified
            m = re.match(r'^references/([\w.-]+):(\d+)$', r['source'])
            self.assertTrue(m, r['source'])
            fn, ln = m.group(1), int(m.group(2))
            if fn not in cache:
                cache[fn] = read('references', fn).split('\n')
            lines = cache[fn]
            self.assertLessEqual(ln, len(lines), r['source'])
            if r['status'] == 'verified':
                win = lines[max(0, ln - 6):ln + 5]
                self.assertTrue(any('[verify JSON' in l or l.strip() == '```json' for l in win),
                                f"{r['type']} verified nhưng {r['source']} không gần nhãn [verify JSON] hay khối ```json")
        by = {r['type']: r['status'] for r in rows}
        for t in ('SEND_RESPONSE_WEBHOOK_API', 'OMI_BOT_AI', 'START_OTHER_CAMPAIGN', 'CREATE_CUSTOM_VARIABLE/CHAT_GPT (tab LLM)',
                  'UPDATE_INFO_CONTACT/thuộc tính kiểu danh sách'):
            self.assertEqual(by.get(t), 'enum', t)
        for t in ('WEB_HOOK', 'CONDITION', 'DELAY', 'ADD_TICKET', 'GET_RELATED', 'edges.connections'):
            self.assertEqual(by.get(t), 'verified', t)

    def test_skill_md_paths_exist(self):
        sk = read('SKILL.md')
        # `omicall-<skill con>/references/x` trỏ sang skill con, còn lại là references của omiflow
        for other, ref in set(re.findall(r'(?:(omicall-[a-z-]+)/)?references/([\w.-]+\.(?:md|json))', sk)):
            base = os.path.join(ROOT, other, 'references') if other else REF
            self.assertTrue(os.path.exists(os.path.join(base, ref)), (other, ref))
        own = {'flow_outline.py', 'validate_flow.py', 'omi_session.py', 'self_update.py'}
        for sc in set(re.findall(r'scripts/([\w.-]+\.py)', sk)) & own:
            self.assertTrue(os.path.exists(os.path.join(SKILL, 'scripts', sc)), sc)


if __name__ == '__main__':
    unittest.main()
