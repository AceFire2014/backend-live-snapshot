import unittest
from unittest import mock
from parameterized import parameterized

from common.legacy_api.exceptions import RequestApiError
import common.legacy_api.features.broadcast_logger as module


class TestBroadcastLoggerAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.broadcast_logger_api = module.BroadcastLoggerAPI(mock.Mock())

    @parameterized.expand(
        (
            (
                [
                    'viewer_pwsid',
                    'viewer_handle',
                    'chrome',
                    'viewer',
                    'inactive',
                    'broadcaster_pwsid',
                    'broadcaster_handle',
                    'a_stream_id',
                ],
                {
                    'pwsid': 'viewer_pwsid',
                    'handle': 'viewer_handle',
                    'site': 'ffnbroadcast.com',
                    'ua': 'chrome',
                    'type': 'viewer',
                    'action': 'inactive',
                    'streamId': 'a_stream_id',
                    'with_pwsid': 'broadcaster_pwsid',
                    'with_handle': 'broadcaster_handle',
                },
            ),
            (
                ['viewer_pwsid', 'viewer_handle', 'chrome', 'viewer', 'inactive'],
                {
                    'pwsid': 'viewer_pwsid',
                    'handle': 'viewer_handle',
                    'site': 'ffnbroadcast.com',
                    'ua': 'chrome',
                    'type': 'viewer',
                    'action': 'inactive',
                    'streamId': None,
                    'with_pwsid': None,
                    'with_handle': None,
                },
            ),
        )
    )
    def test_post(self, params: list, expected: dict):
        self.broadcast_logger_api.requester.url = 'https://ffnbroadcast.com/'
        self.broadcast_logger_api.post(*params)
        self.broadcast_logger_api.requester.post.assert_called_once_with(
            'qz/broadcast_logger',
            self.broadcast_logger_api._post_broadcast_logger_cb,
            json=expected,
        )

    @parameterized.expand(
        (({'status': 400}, RequestApiError), ({'status': 403}, RequestApiError))
    )
    def test_post_broadcast_logger_cb_exception(self, result: dict, exception):
        with self.assertRaises(exception):
            self.broadcast_logger_api._post_broadcast_logger_cb(result)

    def test_post_broadcast_logger_cb_success(self) -> None:
        response = {'status': '200 OK'}
        result = self.broadcast_logger_api._post_broadcast_logger_cb(response)
        self.assertDictEqual(result, response)
