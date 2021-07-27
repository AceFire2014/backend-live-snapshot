import unittest
from unittest import mock
from parameterized import parameterized

from common.legacy_api.exceptions import RequestApiError, NoSessionError, NotEnoughPointsError
import common.legacy_api.features.interactions as module


class TestInteractionsAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.interactions_api = module.InteractionsAPI(mock.Mock())

    def test_send_flirt(self):
        with mock.patch.object(module, 'config', LEGACY_API2_BASIC_PATH='/a2/v1'):
            self.interactions_api.send_flirt('111')

        self.interactions_api.requester.post.assert_called_once_with(
            '/a2/v1/interactions/flirt',
            self.interactions_api._success_check_cb,
            json={'pwsid': '111'}
        )

    def test_send_friend_invite(self):
        with mock.patch.object(module, 'config', LEGACY_API2_BASIC_PATH='/a2/v1'):
            self.interactions_api.send_friend_invite('111', 'handle111')

        self.interactions_api.requester.post.assert_called_once_with(
            '/a2/v1/friends/invite_friend',
            self.interactions_api._success_check_cb,
            json={'pwsid': '111', 'handle': 'handle111'}
        )

    def test_send_mtx_flirt(self):
        self.interactions_api.send_mtx_flirt('111')
        self.interactions_api.requester.post.assert_called_once_with(
            'qz/mtx_point/v2/flirt',
            self.interactions_api._mtx_check_cb,
            json={'recipient': '111'}
        )

    def test_success_check_cb_success(self) -> None:
        result = {'payload': {'is_success': True}, 'status': 200}
        self.interactions_api._mtx_check_cb(result)

    @parameterized.expand((
        ({'payload': {'is_success': False}}, RequestApiError),
        ({'payload': {}}, RequestApiError),
        ({'status': 400}, RequestApiError),
        ({'status': 402}, NotEnoughPointsError),
    ))
    def test_success_check_cb_error(self, result: dict, exception) -> None:
        with self.assertRaises(exception):
            self.interactions_api._mtx_check_cb(result)

    def test_get_friends(self):
        with mock.patch.object(module, 'config', LEGACY_API2_BASIC_PATH='/a2/v1'):
            self.interactions_api.get_friends('1111_2222')

        self.interactions_api.requester.post.assert_called_once_with(
            '/a2/v1/friends/get_friends',
            self.interactions_api._friends_list_cb,
            json={'pwsid': '1111_2222'}
        )

    @parameterized.expand((
        ({'status': 400}, RequestApiError),
        ({'status': 403}, NoSessionError),
    ))
    def test_friends_list_cb_error(self, result: dict, exception):
        with self.assertRaises(exception):
            self.interactions_api._friends_list_cb(result)

    def test_friends_list_cb_success(self) -> None:
        result = {'payload': {'members': [
            {
                'pwsid': 'a',
                'handle': 'a_handle',
                'online': True,
                'sex': '1',
                'age': 30,
                'last_visit_datetime': '11',
                'img': 'http://imageurl',
                'level': 300,
                'hotlisted': 0,
                'flirted': 0,
                'is_friend': 0,
                'confirm_date': 0,
                'verified': 0,
                'vip': True,
                'location': 'LA, CA',
                'country': 'US',
                'state': 'CA',
                'city': 'LA',
                'distance': 100,
            },
            {
                'pwsid': 'b',
                'handle': 'b_handle',
                'online': False,
                'sex': '2',
                'age': 21,
                'last_visit_datetime': '11',
                'img': 'http://imageurl',
                'level': 100,
                'hotlisted': 0,
                'flirted': 0,
                'is_friend': 0,
                'confirm_date': 0,
                'verified': 0,
                'vip': True,
                'location': 'NY, NY',
                'country': 'US',
                'state': 'NY',
                'city': 'NY',
                'distance': 200,
            }
        ]}}
        response = self.interactions_api._friends_list_cb(result)
        self.assertDictEqual(response, {
            'a': {
                'pwsid': 'a',
                'handle': 'a_handle',
                'online': True,
                'sex': 'M',
                'age': 30,
                'last_visit_datetime': '11',
                'img': 'http://imageurl',
                'hotlisted': False,
                'flirted': False,
                'is_friend': False,
                'is_gold': True,
                'is_confirmed': False,
                'is_verified': False,
                'is_vip': True,
                'location': 'LA, CA',
                'country': 'US',
                'state': 'CA',
                'city': 'LA',
                'distance': 100,
            },
            'b': {
                'pwsid': 'b',
                'handle': 'b_handle',
                'online': False,
                'sex': 'F',
                'age': 21,
                'last_visit_datetime': '11',
                'img': 'http://imageurl',
                'hotlisted': False,
                'flirted': False,
                'is_friend': False,
                'is_gold': False,
                'is_confirmed': False,
                'is_verified': False,
                'is_vip': True,
                'location': 'NY, NY',
                'country': 'US',
                'state': 'NY',
                'city': 'NY',
                'distance': 200,
            }
        })
