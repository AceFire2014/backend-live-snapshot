import unittest
from unittest import mock
from parameterized import parameterized

from common.legacy_api.exceptions import RequestApiError, NoSessionError
import common.legacy_api.features.gift_tips as module


class TestGiftsTipsAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.gift_tips_api = module.GiftsTipsAPI(mock.Mock())

    @parameterized.expand((
        ({'payload': {'points': 100}}, 100),
        ({'payload': {'points': 0}}, 0),
    ))
    def test_get_total_points_cb_success(self, result: dict, expected: int) -> None:
        response = self.gift_tips_api._get_total_points_cb(result)
        self.assertEqual(response, expected)

    @parameterized.expand((
        ({'status': 500, 'payload': {}}, RequestApiError),
        ({'status': 403, 'payload': {}}, NoSessionError),
    ))
    def test_get_total_points_cb_error(self, result: dict, exception) -> None:
        with self.assertRaises(exception):
            self.gift_tips_api._get_total_points_cb(result)

    def test_get_virtual_gifts_cb_success(self) -> None:
        result = {'gifts': {'a': 'b', 'c': 'd'}}
        response = self.gift_tips_api._get_virtual_gifts_cb(result)
        self.assertEqual(response, {'a': 'b', 'c': 'd'})

    @parameterized.expand((
        ({'error': 'no session'}, NoSessionError),
        ({'gifts': {}}, RequestApiError),
    ))
    def test_get_virtual_gifts_cb_error(self, result: dict, exception) -> None:
        with self.assertRaises(exception):
            self.gift_tips_api._get_virtual_gifts_cb(result)

    def test_send_gift_cb_success(self) -> None:
        result = {'111': {'send': 1}}
        self.gift_tips_api._send_gift_cb(result, '111')

    @parameterized.expand((
        ({'222': {'send': 1}},),
        ({'111': {'send': 0}},),
    ))
    def test_send_gift_cb_error(self, result: dict) -> None:
        with self.assertRaises(RequestApiError):
            self.gift_tips_api._send_gift_cb(result, '111')

    @parameterized.expand((
        (True, {'force_recalc': 1}),
        (False, {}),
    ))
    def test_get_total_points(self, force, json_query):
        with mock.patch.object(module, 'config', LEGACY_API2_BASIC_PATH='/a2/v1'):
            result = self.gift_tips_api.get_total_points(force)
            self.assertEqual(result, self.gift_tips_api.requester.post.return_value)

        self.gift_tips_api.requester.post.assert_called_once_with(
            '/a2/v1/points/get_total_points',
            self.gift_tips_api._get_total_points_cb,
            json=json_query
        )

    def test_get_virtual_gifts(self):
        result = self.gift_tips_api.get_virtual_gifts()
        self.assertEqual(result, self.gift_tips_api.requester.get.return_value)
        self.gift_tips_api.requester.get.assert_called_once_with(
            'coreapi/virtual_gifts',
            self.gift_tips_api._get_virtual_gifts_cb,
            query={'action': 'get_virtual_gifts', 'want_array': '1'}
        )

    def test_send_tips(self):
        with mock.patch.object(module, 'config') as config_mock:
            config_mock.ALLOW_TOO_NEW_TIPPING_SECRET = '1'
            config_mock.LEGACY_API2_BASIC_PATH = '/a2/v1'
            self.gift_tips_api.send_tips('111', 100)

        self.gift_tips_api.requester.post.assert_called_once_with(
            '/a2/v1/points/give_tip_points',
            self.gift_tips_api._success_check_cb,
            json={'pwsid': '111', 'amount': 100, 'type': 'tip',
                  'allow_too_new_tipping': '1'}
        )

    def test_send_gift(self):
        self.gift_tips_api.send_gift('111', 'handle111', [100, 200], 'message')
        self.gift_tips_api.requester.get.assert_called_once_with(
            'messages/send',
            self.gift_tips_api._send_gift_cb,
            query={'to_pwsids': '111', 'to_handles': 'handle111', 'body': 'message',
                   'non_restraint': 1, 'gift100': 100, 'gift200': 200},
            pwsid_to='111'
        )

    @parameterized.expand((
        ('view_broadcast',),
        ('whisper_msg',),
    ))
    def test_spend_points_success(self, prize):
        self.gift_tips_api.spend_points(prize, 'broadcast_pwsid')
        self.gift_tips_api.requester.get.assert_called_once_with(
            'coreapi/points',
            self.gift_tips_api._success_simple_cb,
            query={'action': 'spend_points_on_prize', 'prize': prize, 'streamid': 'broadcast_pwsid'}
        )

    def test_spend_points_wrong_prize(self):
        with self.assertRaises(ValueError):
            self.gift_tips_api.spend_points('some_unknown_prize', 'broadcast_pwsid')
