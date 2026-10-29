"""config_survey.py (offline): rút gọn đúng khuôn API, lỗi endpoint không làm dừng, không gọi mạng."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'shared', 'scripts'))
import config_survey  # noqa: E402

FAKE = {
    'public_number_of_tenant/list_active': {'payload': {'items': [
        {'_id': 'h1', 'number': '840000000000', 'configs': {'default_script': 's1', 'working_days': [
            {'weekday': 2, 'type': 'full_day', 'script': 's1', 'time_frames': []}]}}]}},
    'key_interactive_script/get/list': {'payload': [
        {'_id': 'k1', 'script_name': 'IVR', 'webhook': {'url': 'https://x', 'enable': True},
         'scripts': [{'key': None, 'ivr': '2', 'action_type': 'Ring_group', 'action': 'g1'}]}]},
    'internal_group/get/list': {'payload': [{'_id': 'g1', 'group_name': 'Nhóm', 'strategy': 'rollover',
                                             'members': [{}, {}], 'create_by': {'name': 'ai đó'}}]},
    'call_transaction/assistant/list': {'payload': [{'_id': 'a1', 'name': 'Trợ lý', 'features': [
        {'type': 'SUMMARY', 'items': [{'prompt': 'p'}]}], 'contact_ids': ['c1']}]},
}


def fake_call(service, method, path):
    if path in FAKE:
        return FAKE[path]
    if path == 'outer_group/get/list':
        raise RuntimeError('404')
    return {'payload': []}


class ConfigSurveyTest(unittest.TestCase):
    def test_slim_and_errors(self):
        pbx, ai, errors = config_survey.survey(call=fake_call)
        self.assertEqual(pbx['hotlines'][0]['working_days'][0]['type'], 'full_day')
        self.assertEqual(pbx['key_interactions'][0]['keys'], [{'digit': '2', 'action_type': 'Ring_group', 'action': 'g1'}])
        self.assertTrue(pbx['key_interactions'][0]['webhook_enabled'])
        g = pbx['internal_groups'][0]
        self.assertEqual((g['strategy'], g['members']), ('rollover', 2))
        self.assertNotIn('create_by', g)
        self.assertEqual(ai['assistants'][0]['features'], [{'type': 'SUMMARY', 'items': 1}])
        self.assertIsNone(pbx['outer_groups'])
        self.assertTrue(any(e.startswith('outer_groups:') for e in errors))

    def test_only_read_methods(self):
        for service, method, path, _ in config_survey.ENDPOINTS.values():
            self.assertIn(method, ('GET', 'POST'))
            self.assertNotRegex(path, r'(add|update|delete)')


if __name__ == '__main__':
    unittest.main()
