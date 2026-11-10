"""omi_api (offline): dùng chung một requests.Session; hai lệnh khảo sát truyền timeout (connect, read) riêng.

Không gọi mạng: Session được thay bằng đối tượng giả ghi lại tham số.
"""
import importlib.util
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'shared', 'scripts'))
import omi_api  # noqa: E402
import tenant_survey  # noqa: E402
import config_survey  # noqa: E402

HAS_REQUESTS = importlib.util.find_spec('requests') is not None


class FakeResp:
    status_code = 200
    text = '{}'

    def json(self):
        return {'payload': {'items': []}}


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kw):
        self.calls.append(('GET', url, kw))
        return FakeResp()

    def post(self, url, **kw):
        self.calls.append(('POST', url, kw))
        return FakeResp()


@unittest.skipUnless(HAS_REQUESTS, 'thiếu thư viện requests (pip install requests)')
class OmiApiSessionTest(unittest.TestCase):
    def setUp(self):
        self.fake = FakeSession()
        p1 = mock.patch.object(omi_api, '_session', return_value=self.fake)
        p2 = mock.patch.object(omi_api, '_headers', return_value={'Authorization': 'Bearer x'})
        p1.start()
        p2.start()
        self.addCleanup(p1.stop)
        self.addCleanup(p2.stop)

    def test_get_post_multipart_use_session_default_timeout(self):
        omi_api.get('chatbot', '/a')
        omi_api.post_json('campaign', '/b', {})
        omi_api.post_multipart('chatbot', '/c', {'x': 1})
        self.assertEqual([c[0] for c in self.fake.calls], ['GET', 'POST', 'POST'])
        self.assertEqual({c[2]['timeout'] for c in self.fake.calls}, {omi_api.TIMEOUT})
        self.assertEqual(omi_api.TIMEOUT, 120)  # lệnh lưu/tải lớn giữ timeout cũ

    def test_tenant_survey_uses_survey_timeout(self):
        for ep in tenant_survey.ENDPOINTS:
            if ep['verified']:
                tenant_survey.fetch(ep, '<tenant_id>', None)
        self.assertEqual(len(self.fake.calls), sum(1 for e in tenant_survey.ENDPOINTS if e['verified']))
        self.assertEqual({c[2]['timeout'] for c in self.fake.calls}, {omi_api.SURVEY_TIMEOUT})
        self.assertEqual(omi_api.SURVEY_TIMEOUT, (5, 30))

    def test_config_survey_uses_survey_timeout(self):
        config_survey.survey()
        self.assertEqual(len(self.fake.calls), len(config_survey.ENDPOINTS))
        self.assertEqual({c[2]['timeout'] for c in self.fake.calls}, {omi_api.SURVEY_TIMEOUT})


@unittest.skipUnless(HAS_REQUESTS, 'thiếu thư viện requests (pip install requests)')
class OmiApiSessionReuseTest(unittest.TestCase):
    def test_session_is_shared(self):
        import requests
        omi_api._SESSION = None
        s1 = omi_api._session()
        self.addCleanup(s1.close)
        self.assertIsInstance(s1, requests.Session)
        self.assertIs(omi_api._session(), s1)
        omi_api._SESSION = None


if __name__ == '__main__':
    unittest.main()
