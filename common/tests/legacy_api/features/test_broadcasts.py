import unittest
from unittest import mock
from parameterized import parameterized

from common.legacy_api.exceptions import RequestApiError, NoSessionError
import common.legacy_api.features.broadcasts as module


class TestBroadcastsAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.broadcasts_api = module.BroadcastsAPI(mock.Mock())

    def test_get_leaderboard_cb_success(self) -> None:
        resp = {'leaderboard': [{'pwsid': 'a', 'img': 'aa', 'broadcast_rank': 1, 'handle': 'aaa'},
                                {'pwsid': 'b', 'img': 'bb', 'broadcast_rank': 2, 'handle': 'bbb'}]}
        response = self.broadcasts_api._get_leaderboard_cb(resp)
        self.assertEqual(response, [{'pwsid': 'a', 'img': 'aa', 'broadcast_rank': 1},
                                    {'pwsid': 'b', 'img': 'bb', 'broadcast_rank': 2}])

    @parameterized.expand((
        ({}, RequestApiError),
        ({'error': 'no session'}, NoSessionError),
    ))
    def test_get_leaderboard_cb_error(self, result: dict, exception) -> None:
        with self.assertRaises(exception):
            self.broadcasts_api._get_leaderboard_cb(result)

    def test_get_leaderboard(self):
        result = self.broadcasts_api.get_leaderboard()
        self.assertEqual(result, self.broadcasts_api.requester.get.return_value)
        self.broadcasts_api.requester.get.assert_called_once_with(
            'coreapi/broadcasts',
            self.broadcasts_api._get_leaderboard_cb,
            query={'action': 'get_broadcast_leaderboard', 'offset': '0', 'page': '1', 'limit': '420'},
        )
