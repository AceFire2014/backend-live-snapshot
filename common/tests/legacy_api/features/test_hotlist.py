import unittest
from unittest import mock

import common.legacy_api.features.hotlist as module


class TestHotlistAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.hotlist_api = module.HotlistAPI(mock.Mock())

    def test_add(self):
        with mock.patch.object(module, 'config', LEGACY_API2_BASIC_PATH='/a2/v1'):
            self.hotlist_api.add('111')

        self.hotlist_api.requester.post.assert_called_once_with(
            '/a2/v1/interactions/hotlist/add',
            self.hotlist_api._success_check_cb,
            json={'pwsid': '111'}
        )

    def test_remove(self):
        with mock.patch.object(module, 'config', LEGACY_API2_BASIC_PATH='/a2/v1'):
            self.hotlist_api.remove('111')

        self.hotlist_api.requester.post.assert_called_once_with(
            '/a2/v1/interactions/hotlist/remove',
            self.hotlist_api._success_check_cb,
            json={'pwsid': '111'}
        )

    def test_get_leaderboard_cb_success(self) -> None:
        resp = {'leaderboard': [
            {'spender_pwsid': 'a', 'points': 100, 'rank': 1,
             'spender_passport': {'handle': 'aaa', 'img': 'aaa_img', 'sex': '1'}},
            {'spender_pwsid': 'b', 'points': 50, 'rank': 2,
             'spender_passport': {'handle': 'bbb', 'img': 'bbb_img', 'sex': '2'}}
        ]}
        response = self.hotlist_api._get_leaderboard_cb(resp)
        self.assertEqual(response, [{'pwsid': 'a', 'points': 100, 'rank': 1, 'handle': 'aaa',
                                     'img': 'aaa_img', 'sex': 'M'},
                                    {'pwsid': 'b', 'points': 50, 'rank': 2, 'handle': 'bbb',
                                     'img': 'bbb_img', 'sex': 'F'}])

    def test_get_leaderboard(self):
        result = self.hotlist_api.get_leaderboard('aaa')
        self.assertEqual(result, self.hotlist_api.requester.get.return_value)
        self.hotlist_api.requester.get.assert_called_once_with(
            'coreapi/points',
            self.hotlist_api._get_leaderboard_cb,
            query={'action': 'get_personal_leaderboard_by_spendee', 'of_pwsid': 'aaa',
                   'offset': 0, 'page': 1, 'limit': 5}
        )

    def test_make_bid(self):
        result = self.hotlist_api.make_bid('aaa', 100)
        self.assertEqual(result, self.hotlist_api.requester.get.return_value)
        self.hotlist_api.requester.get.assert_called_once_with(
            'coreapi/points',
            self.hotlist_api._success_simple_cb,
            query={'action': 'spend_points', 'do_hotlist': 1, 'to_pwsid': 'aaa', 'points': 100}
        )
