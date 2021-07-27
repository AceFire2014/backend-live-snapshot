import unittest
from unittest import mock
from parameterized import parameterized

from common.legacy_api.exceptions import RequestApiError, NoSessionError
import common.legacy_api.features.honey_potted as module


class TestHoneyPottedAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.honey_potted_api = module.HoneyPottedAPI(mock.Mock())

    def test_get_honeypot_status_cb_success(self) -> None:
        result = {'payload': {'honeypot_status': False}}
        response = self.honey_potted_api._get_honeypot_status_cb(result)
        self.assertEqual(response, False)

    @parameterized.expand((
        ({'status': 403, 'payload': {}}, NoSessionError),
        ({'status': 400, 'payload': {}}, RequestApiError)
    ))
    def test_get_honeypot_status_cb_error(self, result: dict, exception) -> None:
        with self.assertRaises(exception):
            self.honey_potted_api._get_honeypot_status_cb(result)

    def test_get_honeypot_status(self):
        with mock.patch.object(module, 'config') as config_mock:
            config_mock.LEGACY_API2_USER_SECRET = '111'
            config_mock.LEGACY_API2_BASIC_PATH = '/a2/v1'
            self.honey_potted_api.get_honeypot_status()

        self.honey_potted_api.requester.post.assert_called_once_with(
            '/a2/v1/user/get',
            self.honey_potted_api._get_honeypot_status_cb,
            json={'get': ['honeypot_status'], 'sec_code': '111'}
        )
