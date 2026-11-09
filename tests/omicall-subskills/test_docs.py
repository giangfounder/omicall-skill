"""Kiểm tài liệu các skill con của omicall-omiflow (offline): khung SKILL.md, tài liệu tham chiếu, liên kết hai chiều với omiflow."""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SUBSKILLS = {
    'omicall-crm-config': 'crm-config.md',
    'omicall-pbx-config': 'pbx-config.md',
    'omicall-ai-insight': 'ai-insight.md',
}


def read(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


class SubskillDocsTest(unittest.TestCase):
    def test_frontmatter_and_version(self):
        for s in SUBSKILLS:
            sk = read(s, 'SKILL.md')
            self.assertTrue(sk.startswith('---\nname: %s\n' % s), s)
            ver = read(s, 'VERSION').strip()
            self.assertIn('[v%s]' % ver, sk, s)
            self.assertIn('dùng v%s)' % ver, sk, s)

    def test_skeleton(self):
        for s in SUBSKILLS:
            lines = read(s, 'SKILL.md').split('\n')
            heads = [l for l in lines if l.startswith('## ')]
            self.assertEqual(heads[0], '## Bước bắt buộc: cập nhật skill', s)
            idx = lines.index('## Đường nhanh')
            self.assertLess(idx, 30, s)
            block = '\n'.join(lines[idx:next(i for i in range(idx + 1, len(lines)) if lines[i].startswith('## '))])
            self.assertIn('omi_preflight.py', block, s)
            self.assertIn('Không bao giờ', block, s)
            for h in ('## Rules (BẮT BUỘC)', '## Quan hệ với skill khác', '## Tài liệu tham khảo'):
                self.assertIn(h, heads, s)

    def test_reference_exists(self):
        for s, ref in SUBSKILLS.items():
            self.assertIn('references/%s' % ref, read(s, 'SKILL.md'))
            self.assertTrue(os.path.isfile(os.path.join(ROOT, s, 'references', ref)), s)

    def test_omiflow_links_subskills(self):
        sk = read('omicall-omiflow', 'SKILL.md') + '\n' + read('omicall-omiflow', 'references', 'playbook.md')
        self.assertIn('## Skill con', sk)
        for s, ref in SUBSKILLS.items():
            self.assertIn('`%s`' % s, sk)
            self.assertIn('%s/references/%s' % (s, ref), sk)
        self.assertFalse(os.path.exists(os.path.join(ROOT, 'omicall-omiflow', 'references', 'crm-config.md')))
        self.assertNotRegex(sk, r'(?<![\w-]/)`references/crm-config\.md`')

    def test_pbx_numbering_and_write_status(self):
        sk = read('omicall-pbx-config', 'SKILL.md')
        rules = sk[sk.index('## Rules (BẮT BUỘC)'):sk.index('## Quan hệ với skill khác')]
        nums = [int(n) for n in re.findall(r'^(\d+)\. ', rules, re.M)]
        self.assertEqual(nums, list(range(1, len(nums) + 1)))
        ref = read('omicall-pbx-config', 'references', 'pbx-config.md')
        heads = [int(n) for n in re.findall(r'^## (\d+)\.', ref, re.M)]
        self.assertEqual(heads, list(range(1, len(heads) + 1)))
        rows = {l.split('|')[1].strip(): l for l in ref.split('\n') if l.startswith('| ') and l.count('|') == 4}
        for k in ('Tương tác phím', 'Kịch bản cuộc gọi', 'Nhóm nội bộ', 'Lời chào'):
            self.assertIn('✔', rows[k], k)
        self.assertIn('-9999', rows['Lời chào'])
        self.assertNotIn('**chưa chạy** — chỉ dùng', ref)

    def test_ai_insight_scoring_split(self):
        sk = read('omicall-ai-insight', 'SKILL.md')
        self.assertIn('references/voice-insights-scoring.md', sk)
        sc = read('omicall-ai-insight', 'references', 'voice-insights-scoring.md')
        for s in ('Quy trình 4 bước', 'Đánh giá chất lượng', 'SmartCall', 'Điểm bước'):
            self.assertIn(s, sc)
        ai = read('omicall-ai-insight', 'references', 'ai-insight.md')
        self.assertNotIn('Quy trình 4 bước', ai)
        self.assertIn('voice-insights-scoring.md', ai)
        self.assertNotIn('Windows-MCP', ai)

    def test_call_purpose_owned_by_ai_insight(self):
        sm = read('omicall-omiflow', 'references', 'solution-map.md')
        row = next(l for l in sm.split('\n') if l.startswith('| Chấm chất lượng nhân viên'))
        self.assertNotIn('crm/pbx: Mục đích', row)
        self.assertIn('omicall-ai-insight', row)
        self.assertIn('Tên mục đích', read('omicall-ai-insight', 'references', 'ai-insight.md'))
        crm = read('omicall-crm-config', 'references', 'crm-config.md')
        self.assertIn('Không đưa tài khoản admin', crm)
        self.assertNotIn('rồi xuất bản.', crm)

    def test_no_omiflow_only_paths_unprefixed(self):
        # tài liệu chỉ có ở omiflow phải ghi kèm tiền tố omicall-omiflow/ trong SKILL.md của skill con
        for s in SUBSKILLS:
            sk = read(s, 'SKILL.md')
            for m in re.finditer(r'(?<![\w/-])references/([\w.-]+\.md)', sk):
                self.assertTrue(os.path.isfile(os.path.join(ROOT, s, 'references', m.group(1))), (s, m.group(0)))


if __name__ == '__main__':
    unittest.main()
