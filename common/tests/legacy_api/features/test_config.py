import unittest
from unittest import mock
from parameterized import parameterized

from common.legacy_api.exceptions import RequestApiError, NoSessionError
import common.legacy_api.features.config as module


class TestConfigAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.config_api = module.ConfigAPI(mock.Mock())

    def test_get_config_cb_success(self) -> None:
        resp = {'payload': {'user': {'param': 1}, 'site': {'param': 2}}}
        response = self.config_api._get_config_cb(resp)
        self.assertEqual(response, {'user': {'param': 1}, 'site': {'param': 2}})

    @parameterized.expand((
        ({}, RequestApiError),
        ({'payload': {'data': 1}}, NoSessionError),
        ({'payload': {'user': {'param': 1}}}, NoSessionError),
        ({'payload': {'site': {'param': 1}}}, NoSessionError),
    ))
    def test_get_config_cb_error(self, result: dict, exception) -> None:
        with mock.patch.object(
            module, 'config', LEGACY_API2_BASIC_PATH='/a2/v1'
        ), self.assertRaises(exception):
            self.config_api._get_config_cb(result)

    def test_get(self) -> None:
        with mock.patch.object(module, 'config', LEGACY_API2_BASIC_PATH='/a2/v1'):
            result = self.config_api.get()

        self.assertEqual(result, self.config_api.requester.post.return_value)
        self.config_api.requester.post.assert_called_once_with(
            '/a2/v1/config',
            self.config_api._get_config_cb,
            json={},
        )

    def test_get_api_flag_success(self) -> None:
        result = self.config_api.get_api_flag('viewed_broadcaster')
        self.assertEqual(result, self.config_api.requester.get.return_value)
        self.config_api.requester.get.assert_called_once_with(
            'coreapi/pdf',
            self.config_api._api_flag_cb,
            query={'action': 'get_apiflag', 'apiflag': 'viewed_broadcaster'},
            api_flag='viewed_broadcaster'
        )

    def test_get_api_flag_wrong_flag(self) -> None:
        with self.assertRaises(ValueError):
            self.config_api.get_api_flag('wrong_flag')

    def test_set_api_flag_success(self) -> None:
        result = self.config_api.set_api_flag('viewed_broadcaster', '1')
        self.assertEqual(result, self.config_api.requester.get.return_value)
        self.config_api.requester.get.assert_called_once_with(
            'coreapi/pdf',
            self.config_api._api_flag_cb,
            query={'action': 'set_apiflag', 'apiflag': 'viewed_broadcaster', 'value': '1'},
            api_flag='viewed_broadcaster'
        )

    def test_set_api_flag_wrong_flag(self) -> None:
        with self.assertRaises(ValueError):
            self.config_api.set_api_flag('wrong_flag', '1')

    @parameterized.expand((
            ('1',),
            (None,),
    ))
    def test_api_flag_cb_success(self, value) -> None:
        resp = {'viewed_broadcaster': value}
        response = self.config_api._api_flag_cb(resp, 'viewed_broadcaster')
        self.assertEqual(response, value)

    @parameterized.expand((
            ({}, RequestApiError),
            ({'error': 'no session'}, NoSessionError),
    ))
    def test_api_flag_cb_error(self, result: dict, exception) -> None:
        with self.assertRaises(exception):
            self.config_api._api_flag_cb(result, 'viewed_broadcaster')
