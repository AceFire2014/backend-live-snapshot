import unittest
from unittest import mock
from parameterized import parameterized

from common.legacy_api.exceptions import (RequestApiError, NoSessionError, NotEnoughPointsError, TooNewTargetAccError,
                                          TooNewAccError, FloodSpamError)
import common.legacy_api.features.base as module


class TestBaseAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.base_api = module.BaseAPI(mock.Mock())

    def test_success_check_cb_success(self) -> None:
        result = {'payload': {'success': 1}}
        self.base_api._success_check_cb(result)

    @parameterized.expand((
        ({'payload': {'success': 0}}, RequestApiError),
        ({'payload': {}}, RequestApiError),
        ({}, RequestApiError),
        ({'payload': {'error': 'insufficient points'}}, NotEnoughPointsError),
        ({'payload': {'error': 'recipient is too new'}}, TooNewTargetAccError),
        ({'payload': {'error': 'sender is too new'}}, TooNewAccError),
        ({'payload': {'error': 'user is spamming'}}, FloodSpamError),
        ({'payload': {'error': 'please do not double click'}}, FloodSpamError),
    ))
    def test_success_check_cb_error(self, result: dict, exception) -> None:
        with self.assertRaises(exception):
            self.base_api._success_check_cb(result)

    def test_success_simple_cb_success(self):
        response = {'success': '1'}
        self.base_api._success_simple_cb(response)

    @parameterized.expand((
        ({'success': '0'}, RequestApiError),
        ({'error': '1'}, RequestApiError),
        ({'error': 'no session'}, NoSessionError),
        ({'error': 'user does not have enough points for this prize'}, NotEnoughPointsError),
        ({'error_code': 5}, NotEnoughPointsError),
        ({'error_code': 2}, TooNewTargetAccError),
        ({'error_code': 3}, TooNewAccError),
    ))
    def test_success_simple_cb_error(self, response, exception):
        with self.assertRaises(exception):
            self.base_api._success_simple_cb(response)
