"""Test offline cho omicall-omiflow/scripts/validate_flow.py.

Fixture fixtures/flow_basic.json ghép từ các khối [verify JSON] của node-catalog.md và api-reference.md.
Chỉ chứng minh validator nhất quán với quy tắc đã ghi trong tài liệu, KHÔNG chứng minh nền tảng chấp nhận payload.
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRIPT = os.path.join(ROOT, 'omicall-omiflow', 'scripts', 'validate_flow.py')
FIXTURE = os.path.join(HERE, 'fixtures', 'flow_basic.json')


def load_base():
    with open(FIXTURE, encoding='utf-8') as f:
        return json.load(f)


def node(flow, nid):
    return next(n for n in flow['nodes'] if n['id'] == nid)


class ValidateFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def run_validator(self, flow, *extra):
        p = os.path.join(self.tmp.name, 'flow.json')
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(flow, f, ensure_ascii=False)
        env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
        r = subprocess.run([sys.executable, '-B', SCRIPT, p, *extra], capture_output=True, text=True,
                           encoding='utf-8', env=env, timeout=60)
        return r.returncode, r.stdout

    @staticmethod
    def fails(out):
        return {line.split()[1] for line in out.splitlines() if line.startswith('FAIL ')}

    def assert_fail(self, flow, *codes, extra=()):
        rc, out = self.run_validator(flow, *extra)
        self.assertEqual(rc, 1, out)
        for c in codes:
            self.assertIn(c, self.fails(out), out)
        self.assertTrue(out.strip().endswith('RESULT FAIL'), out)
        return out

    def test_base_passes(self):
        rc, out = self.run_validator(load_base())
        self.assertEqual(rc, 0, out)
        self.assertTrue(out.strip().endswith('RESULT PASS'))
        for line in out.splitlines()[:-1]:
            self.assertRegex(line, r'^(PASS|FAIL|WARN) [CX]\d+ ')

    def test_missing_name_mappings_only_warns(self):
        flow = load_base()
        flow.pop('name_mappings', None)
        rc, out = self.run_validator(flow)
        self.assertEqual(rc, 0, out)
        self.assertIn('WARN X9', out)

    def test_missing_edge(self):
        flow = load_base()
        flow['edges']['connections'].pop()
        self.assert_fail(flow, 'X1', 'C2')

    def test_wrong_source_handle(self):
        flow = load_base()
        flow['edges']['connections'][3]['sourceHandle'] = 'success_action_step'
        self.assert_fail(flow, 'X1')

    def test_success_next_nodes_array(self):
        flow = load_base()
        node(flow, '<node_ticket>')['success_next_nodes'] = ['<node_cond>']
        self.assert_fail(flow, 'X2')

    def test_last_node_delay(self):
        flow = load_base()
        node(flow, '<node_delay>')['next_nodes'] = []
        flow['edges']['connections'] = [e for e in flow['edges']['connections'] if e['source'] != '<node_delay>']
        self.assert_fail(flow, 'X3')

    def test_unknown_variable(self):
        flow = load_base()
        node(flow, '<node_ticket>')['actions'][0]['data']['ticket_detail']['name'] = 'YÊU CẦU - {{<code_ghost>}}'
        self.assert_fail(flow, 'X4', 'C3')

    def test_random_code_undeclared(self):
        flow = load_base()
        node(flow, '<node_ticket>')['actions'][0]['data']['ticket_detail']['name'] = 'YÊU CẦU - {{AbCdEfGh12}}'
        self.assert_fail(flow, 'X4')

    def test_variable_name_instead_of_code(self):
        flow = load_base()
        node(flow, '<node_ticket>')['actions'][0]['data']['ticket_detail']['name'] = 'YÊU CẦU - {{phone_number}}'
        out = self.assert_fail(flow, 'X4')
        self.assertIn('TÊN biến', out)

    def test_value_with_trailing_space(self):
        flow = load_base()
        node(flow, '<node_cond>')['conditions'][0]['data'][0]['compare_conditions'][0]['values'][0]['start_value'] = 'A '
        self.assert_fail(flow, 'X5', 'C4')

    def test_ghost_target(self):
        flow = load_base()
        node(flow, '<node_ticket>')['next_nodes'] = ['GHOST']
        self.assert_fail(flow, 'C2')

    def test_orphan_node(self):
        flow = load_base()
        extra = copy.deepcopy(node(flow, '<node_ticket>'))
        extra['id'] = '<node_orphan>'
        flow['nodes'].append(extra)
        self.assert_fail(flow, 'X7')

    def test_trigger_mismatch(self):
        flow = load_base()
        flow['kick_off']['event'] = 'GENERAL'
        self.assert_fail(flow, 'C1')

    def test_get_related_call_after_ticket_without_delay(self):
        flow = load_base()
        ticket = node(flow, '<node_ticket>')
        ticket['actions'].append({'id': '<a_rel>', 'type': 'GET_RELATED',
                                  'data': {'options': ['CLOSEST_CALL'], 'sort_by_created_date': True}})
        self.assert_fail(flow, 'X6', 'C5')

    def test_get_related_after_delay_ok(self):
        flow = load_base()
        # ADD_TICKET -> DELAY -> GET_RELATED (mẫu B1): thêm nút DELAY và nút GET_RELATED sau phiếu
        ticket = node(flow, '<node_ticket>')
        delay = copy.deepcopy(node(flow, '<node_delay>'))
        delay['id'] = '<node_delay2>'
        delay['next_nodes'] = ['<node_rel>']
        rel = {'id': '<node_rel>', 'is_first_node': False, 'node_type': 'ACTION', 'position': {'x': 1600, 'y': 0},
               'actions': [{'id': '<a_rel>', 'type': 'GET_RELATED', 'data': {'options': ['CLOSEST_CALL']}}],
               'next_nodes': []}
        ticket['next_nodes'] = ['<node_delay2>']
        flow['nodes'] += [delay, rel]
        tpl = flow['edges']['connections'][3]
        for src, tgt in (('<node_ticket>', '<node_delay2>'), ('<node_delay2>', '<node_rel>')):
            e = copy.deepcopy(tpl)
            e.update(source=src, target=tgt, sourceHandle='2', id=f'reactflow__edge-{src}2-{tgt}1')
            flow['edges']['connections'].append(e)
        rc, out = self.run_validator(flow)
        self.assertEqual(rc, 0, out)

    def test_quota_exceeded(self):
        self.assert_fail(load_base(), 'C6', extra=('--quota', '3'))

    def test_post_published(self):
        flow = load_base()
        flow['is_publish'] = True
        flow['is_draft'] = False
        self.assert_fail(flow, 'C6', extra=('--mode', 'post'))

    def test_post_missing_is_publish_warns(self):
        flow = load_base()
        flow.pop('is_publish', None)
        flow.pop('is_draft', None)
        rc, out = self.run_validator(flow, '--mode', 'post')
        self.assertIn('WARN C6 bản GET không có is_publish', out)
        self.assertNotIn('PASS C6 chưa xuất bản', out)

    def test_post_unpublished_passes_c6(self):
        rc, out = self.run_validator(load_base(), '--mode', 'post')
        self.assertIn('PASS C6 chưa xuất bản', out)

    def test_pre_published_warns(self):
        flow = load_base()
        flow['is_publish'] = True
        rc, out = self.run_validator(flow)
        self.assertIn('WARN C6 payload có is_publish=true', out)

    def test_unknown_plain_variable_warns_c3(self):
        flow = load_base()
        node(flow, '<node_ticket>')['actions'][0]['data']['ticket_detail']['name'] = 'X {{zzz}}'
        rc, out = self.run_validator(flow)
        self.assertEqual(rc, 0, out)
        self.assertIn('WARN X4 {{zzz}}', out)
        self.assertIn('WARN C3', out)
        self.assertNotIn('PASS C3', out)
        self.assertNotIn('PASS X4', out)

    def test_name_mappings_without_ids_warns(self):
        flow = load_base()
        flow['name_mappings'] = [{'type': 'BEGIN'}, {'foo': 'bar'}]
        rc, out = self.run_validator(flow)
        self.assertIn('WARN X9 name_mappings không rỗng nhưng không phần tử nào có khoá id', out)
        self.assertNotIn('PASS X9', out)

    def test_name_mappings_full_ids_still_warn(self):
        # đủ id nhưng nội dung tự bịa: không được PASS cho tới khi name_mappings có template verified
        flow = load_base()
        flow['name_mappings'] = [{'id': n['id'], 'made_up': True} for n in flow['nodes']]
        rc, out = self.run_validator(flow)
        self.assertEqual(rc, 0, out)
        self.assertIn('WARN X9 name_mappings đủ id với nodes', out)
        self.assertNotIn('PASS X9', out)

    def test_list_attribute_with_variable(self):
        flow = load_base()
        node(flow, '<node_ticket>')['actions'].append({'id': '<a_attr>', 'type': 'ASSIGN_ATTRIBUTE_STRUCTURE', 'data': {
            'attribute_structures': [{'field_code': '<attr_list>', 'field_type': 'single_text',
                                      'value': [{'display_value': '{{<code_status>}}'}]}]}})
        ctx = os.path.join(self.tmp.name, 'ctx.json')
        with open(ctx, 'w', encoding='utf-8') as f:
            json.dump({'attributes': [{'code': '<attr_list>', 'name': 'Loại', 'type': '<type>', 'is_list': True}]}, f)
        self.assert_fail(flow, 'X8', extra=('--context', ctx))

    def test_list_attribute_unknown_type_warns(self):
        flow = load_base()
        node(flow, '<node_ticket>')['actions'].append({'id': '<a_attr>', 'type': 'ASSIGN_ATTRIBUTE_STRUCTURE', 'data': {
            'attribute_structures': [{'field_code': '<attr_x>', 'field_type': 'single_text',
                                      'value': [{'display_value': '{{<code_status>}}'}]}]}})
        ctx = os.path.join(self.tmp.name, 'ctx.json')
        with open(ctx, 'w', encoding='utf-8') as f:
            json.dump({'attributes': [{'code': '<attr_x>', 'name': 'Loại', 'type': '<type>', 'is_list': None}]}, f)
        rc, out = self.run_validator(flow, '--context', ctx)
        self.assertEqual(rc, 0, out)
        self.assertIn('WARN X8', out)

    def test_context_not_object_is_usage_error(self):
        ctx = os.path.join(self.tmp.name, 'ctx.json')
        with open(ctx, 'w', encoding='utf-8') as f:
            json.dump([], f)
        rc, out = self.run_validator(load_base(), '--context', ctx)
        self.assertEqual(rc, 2, out)

    def test_malformed_ids_no_traceback(self):
        flow = load_base()
        flow['nodes'][1]['id'] = ['x']
        rc, out = self.run_validator(flow)
        self.assertEqual(rc, 1, out)
        self.assertIn('C2', self.fails(out))
        flow = load_base()
        node(flow, '<node_cond>')['conditions'][0]['data'][0]['compare_conditions'][0]['field_code'] = ['x']
        rc, out = self.run_validator(flow)
        self.assertIn(rc, (0, 1), out)
        self.assertTrue(out.strip().startswith(('PASS', 'FAIL', 'WARN')), out)

    def test_ai_code_not_in_prompt(self):
        flow = load_base()
        flow['custom_variables'] = [{'name': 'intent', 'field_code': '<code_intent>'}]
        node(flow, '<node_ticket>')['actions'].insert(0, {'id': '<a_gpt>', 'type': 'CREATE_CUSTOM_VARIABLE', 'data': {
            'type': 'CHAT_GPT', 'config_variables': [{'type': 'CHAT_GPT', 'config': {'multi_variables': [
                {'field_code': '<code_intent>', 'field_name': 'intent', 'chat_gpt_model': 'gpt-4o-mini', 'llm_config': {},
                 'content': 'Trả về DUY NHẤT một mã: khieu_nai, tu_van'}]}}]}})
        cc = node(flow, '<node_cond>')['conditions'][0]['data'][0]['compare_conditions'][0]
        cc['field_code'] = '<code_intent>'
        cc['values'] = [{'start_value': 'cap_cuu'}]
        self.assert_fail(flow, 'X5')

    def test_sent_mismatch(self):
        flow = load_base()
        sent = load_base()
        sent['nodes'].append({'id': '<node_extra>', 'node_type': 'DESCRIPTION'})
        sp = os.path.join(self.tmp.name, 'sent.json')
        with open(sp, 'w', encoding='utf-8') as f:
            json.dump(sent, f, ensure_ascii=False)
        self.assert_fail(flow, 'X10', extra=('--mode', 'post', '--sent', sp))

    def test_payload_wrapper_and_usage_error(self):
        rc, out = self.run_validator({'payload': load_base(), 'status_code': 9999})
        self.assertEqual(rc, 0, out)
        r = subprocess.run([sys.executable, '-B', SCRIPT, os.path.join(self.tmp.name, 'khong_co.json')],
                           capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 2)
        r = subprocess.run([sys.executable, '-B', SCRIPT], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 2)


if __name__ == '__main__':
    unittest.main()
