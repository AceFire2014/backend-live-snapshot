import unittest
from unittest import mock
from parameterized import parameterized

from common.legacy_api.exceptions import RequestApiError
import common.legacy_api.features.following as module


class TestFollowingAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.following_api = module.FollowingAPI(mock.Mock())

    @parameterized.expand((
        ({'found': '0'}, False),
        ({'found': '1'}, True),
    ))
    def test_check_following_cb_success(self, response, expected):
        self.assertIs(self.following_api._check_following_cb(response), expected)

    def test_check_following_cb_error(self):
        response = {'error': '1'}
        with self.assertRaises(RequestApiError):
            self.following_api._check_following_cb(response)

    def test_list_followers_cb_success(self):
        response = {'results': [
            {'distance': '100.23', 'passport': {
                'pwsid': '111',
                'age': 30,
                'online': 1,
                'sex': '1',
                'handle': '111_handle',
                'last_visit_datetime': '111',
                'img': 'http://image',
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
            }},
            {'distance': 200, 'passport': {
                'pwsid': '222',
                'age': 25,
                'online': 0,
                'sex': '3',
                'handle': '222_handle',
                'last_visit_datetime': '222',
                'img': 'http://image2',
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
            }}
        ]}

        result = self.following_api._list_followers_cb(response)
        self.assertDictEqual({
            '111': {
                'pwsid': '111',
                'age': 30,
                'online': 1,
                'sex': 'M',
                'handle': '111_handle',
                'last_visit_datetime': '111',
                'img': 'http://image',
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
            '222': {
                'pwsid': '222',
                'age': 25,
                'online': 0,
                'sex': 'C',
                'handle': '222_handle',
                'last_visit_datetime': '222',
                'img': 'http://image2',
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
        }, result)

    def test_list_followers_cb_error(self):
        response = {'error': '1'}
        with self.assertRaises(RequestApiError):
            self.following_api._list_followers_cb(response)

    def test_list_following_cb_success(self):
        response = {'m': [{'pwsid': '111'}, {'pwsid': '222'}]}
        self.assertListEqual(self.following_api._list_following_cb(response), ['111', '222'])

    def test_list_following_cb_error(self):
        response = {'error': '1'}
        with self.assertRaises(RequestApiError):
            self.following_api._list_following_cb(response)

    def test_check(self):
        self.following_api.check('111')
        self.following_api.requester.get.assert_called_once_with(
            'p/imc/view_video.cgi',
            self.following_api._check_following_cb,
            query={
                'do_json': '1',
                'bcast': '111',
                'action': 'lookup_favorite',
            }
        )

    def test_add(self):
        self.following_api.add('111')
        self.following_api.requester.get.assert_called_once_with(
            'p/imc/view_video.cgi',
            self.following_api._success_simple_cb,
            query={
                'do_json': '1',
                'bcast': '111',
                'action': 'add_favorite',
            }
        )

    def test_remove(self):
        self.following_api.remove('111')
        self.following_api.requester.get.assert_called_once_with(
            'p/imc/view_video.cgi',
            self.following_api._success_simple_cb,
            query={
                'do_json': '1',
                'bcast': '111',
                'action': 'del_favorite',
            }
        )

    def test_get_followers(self):
        self.following_api.get_followers()
        self.following_api.requester.get.assert_called_once_with(
            'coreapi/interactions',
            self.following_api._list_followers_cb,
            query={'type': 'followed_me'}
        )

    def test_get_followed(self):
        self.following_api.get_followed()
        self.following_api.requester.get.assert_called_once_with(
            'p/imc/view_video.cgi',
            self.following_api._list_following_cb,
            query={
                'do_json': '1',
                'followed': '1',
                'perpage': '500'
            }
        )
