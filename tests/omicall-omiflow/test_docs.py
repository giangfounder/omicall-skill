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
        sk = read('SKILL.md')
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
        for code in ['C%d' % i for i in range(1, 8)] + ['X%d' % i for i in range(1, 11)]:
            self.assertIn('[%s]' % code, checklist, code)
            self.assertIn("'%s'" % code, val, code)
        self.assertNotIn('add_v2', api[api.index('## Lưu flow'):api.index('## Checklist')].split('chưa chạy')[0]
                         .replace('`add_v2` / `update_v2` chỉ thấy', ''))

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
        for ref in set(re.findall(r'references/([\w.-]+\.(?:md|json))', sk)):
            self.assertTrue(os.path.exists(os.path.join(REF, ref)), ref)
        own = {'flow_outline.py', 'validate_flow.py', 'omi_session.py', 'self_update.py'}
        for sc in set(re.findall(r'scripts/([\w.-]+\.py)', sk)) & own:
            self.assertTrue(os.path.exists(os.path.join(SKILL, 'scripts', sc)), sc)


if __name__ == '__main__':
    unittest.main()
