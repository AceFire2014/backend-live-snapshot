import unittest
from unittest import mock

import pytest

import common.legacy_api.features.imc as module


class TestImcAPI(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    def setUp(self) -> None:
        self.imc_api = module.ImcAPI(mock.Mock())

    def test_log_short_term_chat_msg_check_cb_success(self) -> None:
        resp = {'reply': 1, 'error': ''}
        self.imc_api._log_short_term_chat_msg_check_cb(resp)

    def test_log_short_term_chat_msg_check_cb_error(self) -> None:
        resp = {'reply': 1, 'error': 'Something Wrong'}
        self.imc_api._log_short_term_chat_msg_check_cb(resp)
        assert "Failed log short term chat msg" in self._caplog.records[0].message

    def test_log_short_term_chat_msg(self) -> None:
        self.imc_api.log_short_term_chat_msg('1111')
        self.imc_api.requester.get.assert_called_once_with(
            'coreapi/imc',
            self.imc_api._log_short_term_chat_msg_check_cb,
            query={
                'action': 'log_short_term_chat_msg',
                'token': '1111'
            },
            decode_reply=True
        )
