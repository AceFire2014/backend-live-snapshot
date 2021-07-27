import logging
import unittest
from datetime import datetime
from unittest import mock

import pytest
from parameterized import parameterized

import common.legacy_api.features.passport as module
import common.legacy_api.requesters.syn as requester_module
from common.legacy_api.exceptions import ReRunException


DEFAULT_PASSPORT_RESULT = {
    'age': 18,
    'age2': None,
    'city': '',
    'confirm_date': 0,
    'country': 'US',
    'date_registered': '2000-01-01 00:00:00',
    'flirted': False,
    'has_buzzmode': False,
    'hotlisted': False,
    'img': 'https://adultfriendfinder.com/bcast/assets/images/thumb-background.png',
    'is_confirmed': False,
    'is_friend': False,
    'is_gold': False,
    'is_verified': False,
    'is_vip': False,
    'last_visit_datetime': '2000-01-01 00:00:00',
    'lat': 0,
    'level': 100,
    'location': '',
    'lon': 0,
    'looking_for_person': [],
    'online': False,
    'race': 0,
    'race2': None,
    'sex': 'M',
    'standard_contact': False,
    'state': 'CA',
    'verified': 0,
    'vip': False,
    'blocked_me': 0,
    'confirmid': 0,
    'fake': True
}


class TestPassportAPI(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    def setUp(self) -> None:
        self.passport_api = module.PassportAPI(mock.Mock())

    def test_get_passport_cb_success(self) -> None:
        result = {
            'status': 200,
            'payload': {
                'total': 2,
                'results': {
                    '111': {
                        'handle': '111_handle',
                        'sex': '7',
                        'date_registered': '4/7/13:1:11:18',
                        'looking_for_person': '2,5',
                        'level': '300',
                        'hotlisted': 0,
                        'flirted': 0,
                        'is_friend': 0,
                        'confirm_date': 0,
                        'verified': 0,
                        'vip': True,
                        'online': 1,
                        'standard_contact': 1,
                        'race': 'abds',
                        'img': 'url',
                    },
                    '222': {
                        'age': 18,
                        'handle': '222_handle',
                        'sex': '1',
                        'date_registered': '4/7/13:1:11:18',
                        'looking_for_person': '1,2',
                        'level': '300',
                        'hotlisted': 0,
                        'flirted': 0,
                        'is_friend': 0,
                        'confirm_date': 0,
                        'verified': 0,
                        'vip': True,
                        'online': 0,
                        'standard_contact': 0,
                        'race': None,
                        'race2': None,
                        'img': 'url',
                    },
                    '333': {
                        'handle': '333_handle',
                        'sex': '1',
                        'date_registered': '4/7/13:1:11:18',
                        'looking_for_person': '1,2',
                        'level': '300',
                        'hotlisted': 0,
                        'flirted': 0,
                        'is_friend': 0,
                        'confirm_date': 0,
                        'verified': 0,
                        'vip': True,
                        'online': 0,
                        'standard_contact': 0,
                        'race': '',
                        'img': 'url',
                    }}}}
        expected = {
            '111': {
                'age': 18,
                'handle': '111_handle',
                'sex': 'T',
                'pwsid': '111',
                'date_registered': '2013-04-07 01:11:18',
                'looking_for_person': ['F', 'C_2F'],
                'level': 300,
                'is_gold': True,
                'hotlisted': False,
                'flirted': False,
                'is_friend': False,
                'is_confirmed': False,
                'is_verified': False,
                'is_vip': True,
                'vip': True,
                'confirm_date': 0,
                'verified': 0,
                'online': True,
                'standard_contact': True,
                'race': 0,
                'img': 'url',
            },
            '222': {
                'age': 18,
                'age2': None,
                'handle': '222_handle',
                'sex': 'M',
                'pwsid': '222',
                'date_registered': '2013-04-07 01:11:18',
                'looking_for_person': ['M', 'F'],
                'level': 300,
                'is_gold': True,
                'hotlisted': False,
                'flirted': False,
                'is_friend': False,
                'is_confirmed': False,
                'is_verified': False,
                'is_vip': True,
                'vip': True,
                'confirm_date': 0,
                'verified': 0,
                'online': False,
                'standard_contact': False,
                'race': 0,
                'race2': None,
                'img': 'url',
            },
            '333': {
                'age': 18,
                'handle': '333_handle',
                'sex': 'M',
                'pwsid': '333',
                'date_registered': '2013-04-07 01:11:18',
                'looking_for_person': ['M', 'F'],
                'level': 300,
                'is_gold': True,
                'hotlisted': False,
                'flirted': False,
                'is_friend': False,
                'is_confirmed': False,
                'is_verified': False,
                'is_vip': True,
                'vip': True,
                'confirm_date': 0,
                'verified': 0,
                'online': False,
                'standard_contact': False,
                'race': 0,
                'img': 'url',
            },
        }
        response = self.passport_api._get_passport_cb(result, ['111', '222', '333'])
        self.assertEqual(response, expected)

    @parameterized.expand((
        ({'status': 200, 'payload': {}},),
        ({'status': 200, 'payload': {'results': {}}},),
        ({'status': 200, 'payload': {'total': 2}},),
        ({'status': 200, 'payload': {'total': 2, 'results': {
            '111': {'age': 30, 'sex': '7', 'date_registered': '4/7/13:1:11:18',
                    'looking_for_person': '2,5', 'level': '300', 'online': 1},
            '333': {'age': 36, 'sex': '1', 'date_registered': '4/7/13:1:11:18',
                    'looking_for_person': '1,2', 'level': '300', 'online': 0}}}},)
    ))
    def test_get_total_points_cb_error(self, result: dict) -> None:
        with self.assertRaises(ReRunException):
            self.passport_api._get_passport_cb(result, ['111', '222'])

    def test_get(self) -> None:
        json_body = {
            'pwsids': ['111', '222'],
            'show_hidden_accounts': 1,
            'passport_fields': [
                'handle',
                'sex',
                'age',
                'age2',
                'flirted',
                'hotlisted',
                'level',
                'location',
                'country',
                'state',
                'city',
                'vip',
                'confirm_date',
                'has_buzzmode',
                'img',
                'is_friend',
                'verified',
                'last_visit_datetime',
                'date_registered',
                'looking_for_person',
                'race',
                'race2',
                'lon',
                'lat',
                'online',
                'standard_contact',
                'confirmid'
            ]
        }

        with mock.patch.object(module, 'config', LEGACY_API2_BASIC_PATH='/a2/v1'):
            result = self.passport_api.get(['111', '222'])

        self.assertEqual(result, self.passport_api.requester.retry.return_value)
        self.passport_api.requester.retry.assert_called_once_with(
            retry_func=mock.ANY,
            tries_time=[3, 1],
            json=json_body,
            pwsids=['111', '222']
        )

    def test_get_with_retries(self) -> None:
        requester = requester_module.LegacyAPISyncRequester('http://test.com')
        passport_api = module.PassportAPI(requester)
        response_1_mock = mock.Mock(status_code=200, headers={})
        response_1_mock.json.return_value = {'status': 200, 'payload': {'total': 2, 'results': {
            '111': {
                'handle': '111_handle',
                'sex': '7',
                'date_registered': '4/7/13:1:11:18',
                'looking_for_person': '2,5',
                'level': '300',
                'hotlisted': 0,
                'flirted': 0,
                'is_friend': 0,
                'confirm_date': 0,
                'verified': 0,
                'vip': True,
                'online': 1,
                'standard_contact': 1,
                'race': 0,
                'img': 'url',
            },
            '222': {
                'handle': 0,
            },
            '333': {
                'handle': 0,
            }
        }}}
        response_2_mock = mock.Mock(status_code=200, headers={})
        response_2_mock.json.return_value = {'status': 200, 'payload': {'total': 2, 'results': {
            '222': {
                'handle': '222_handle',
                'sex': '1',
                'date_registered': '4/7/13:1:11:18',
                'looking_for_person': '1,2',
                'level': '300',
                'hotlisted': 0,
                'flirted': 0,
                'is_friend': 0,
                'confirm_date': 0,
                'verified': 0,
                'vip': True,
                'online': 0,
                'standard_contact': 0,
                'race': None,
                'img': 'url',
            },
            '333': {
                'handle': 0,
            }
        }}}
        response_3_mock = mock.Mock(status_code=200, headers={})
        response_3_mock.json.return_value = {'status': 200, 'payload': {'total': 2, 'results': {
            '333': {
                'handle': '333_handle',
                'sex': '1',
                'date_registered': '4/7/13:1:11:18',
                'looking_for_person': '1,2',
                'level': '300',
                'hotlisted': 0,
                'flirted': 0,
                'is_friend': 0,
                'confirm_date': 0,
                'verified': 0,
                'vip': True,
                'online': 0,
                'standard_contact': 0,
                'race': '',
                'img': 'url',
            }
        }}}

        with mock.patch.object(
            module, 'config', LEGACY_API2_BASIC_PATH='a2/v1'
        ), mock.patch.object(
            requester_module.time, 'sleep'
        ), mock.patch.object(
            requester_module, 'requests'
        ) as requests_mock:
            requests_mock.post.side_effect = [response_1_mock, response_2_mock, response_3_mock]
            result = passport_api.get(['111', '222', '333'])

        self.assertDictEqual({
            '111': {
                'age': 18,
                'handle': '111_handle',
                'sex': 'T',
                'pwsid': '111',
                'date_registered': '2013-04-07 01:11:18',
                'looking_for_person': ['F', 'C_2F'],
                'level': 300,
                'is_gold': True,
                'hotlisted': False,
                'flirted': False,
                'is_friend': False,
                'is_confirmed': False,
                'is_verified': False,
                'is_vip': True,
                'vip': True,
                'confirm_date': 0,
                'verified': 0,
                'online': True,
                'standard_contact': True,
                'race': 0,
                'race2': None,
                'img': 'url',
            },
            '222': {
                'age': 18,
                'handle': '222_handle',
                'sex': 'M',
                'pwsid': '222',
                'date_registered': '2013-04-07 01:11:18',
                'looking_for_person': ['M', 'F'],
                'level': 300,
                'is_gold': True,
                'hotlisted': False,
                'flirted': False,
                'is_friend': False,
                'is_confirmed': False,
                'is_verified': False,
                'is_vip': True,
                'vip': True,
                'confirm_date': 0,
                'verified': 0,
                'online': False,
                'standard_contact': False,
                'race': 0,
                'img': 'url',
            },
            '333': {
                'age': 18,
                'handle': '333_handle',
                'sex': 'M',
                'pwsid': '333',
                'date_registered': '2013-04-07 01:11:18',
                'looking_for_person': ['M', 'F'],
                'level': 300,
                'is_gold': True,
                'hotlisted': False,
                'flirted': False,
                'is_friend': False,
                'is_confirmed': False,
                'is_verified': False,
                'is_vip': True,
                'vip': True,
                'confirm_date': 0,
                'verified': 0,
                'online': False,
                'standard_contact': False,
                'race': 0,
                'img': 'url',
            },
        }, result)

    def test_get_with_retries_part_only(self) -> None:
        requester = requester_module.LegacyAPISyncRequester('http://test.com')
        passport_api = module.PassportAPI(requester)
        response_1_mock = mock.Mock(status_code=200, headers={})
        response_1_mock.json.return_value = {'status': 200, 'payload': {'total': 2, 'results': {
            '111': {
                'handle': '111_handle',
                'sex': '7',
                'date_registered': '4/7/13:1:11:18',
                'looking_for_person': '2,5',
                'level': '300',
                'hotlisted': 0,
                'flirted': 0,
                'is_friend': 0,
                'confirm_date': 0,
                'verified': 0,
                'vip': True,
                'online': 1,
                'standard_contact': 1,
                'race': 0,
                'img': 'url',
            },
            '222': {
                'handle': 0,
            },
            '333': {
                'handle': 0,
            }
        }}}
        response_2_mock = mock.Mock(status_code=200, headers={})
        response_2_mock.json.return_value = {'status': 200, 'payload': {'total': 2, 'results': {
            '222': {
                'handle': '222_handle',
                'sex': '1',
                'date_registered': '4/7/13:1:11:18',
                'looking_for_person': '1,2',
                'level': '300',
                'hotlisted': 0,
                'flirted': 0,
                'is_friend': 0,
                'confirm_date': 0,
                'verified': 0,
                'vip': True,
                'online': 0,
                'standard_contact': 0,
                'race': None,
                'img': 'url',
            },
            '333': {
                'handle': 0,
            }
        }}}
        response_3_mock = mock.Mock(status_code=200, headers={})
        response_3_mock.json.return_value = {'status': 200, 'payload': {'total': 2, 'results': {
            '333': {
                'handle': 0,
            }
        }}}
        datetime_mock = mock.Mock()
        datetime_mock.datetime.now.return_value = datetime(year=2000, month=1, day=1)
        datetime_mock.datetime.strftime = datetime.strftime
        datetime_mock.datetime.strptime = datetime.strptime

        with mock.patch.object(module, 'config', LEGACY_API2_BASIC_PATH='/a2/v1'), \
                mock.patch.object(module, 'datetime', datetime_mock), \
                mock.patch.object(requester_module, 'requests') as requests_mock, \
                mock.patch.object(requester_module.time, 'sleep'):
            requests_mock.post.side_effect = [response_1_mock, response_2_mock, response_3_mock]
            result = passport_api.get(['111', '222', '333'])

        self.assertDictEqual({
            '111': {
                'age': 18,
                'handle': '111_handle',
                'sex': 'T',
                'pwsid': '111',
                'date_registered': '2013-04-07 01:11:18',
                'looking_for_person': ['F', 'C_2F'],
                'level': 300,
                'is_gold': True,
                'hotlisted': False,
                'flirted': False,
                'is_friend': False,
                'is_confirmed': False,
                'is_verified': False,
                'is_vip': True,
                'vip': True,
                'confirm_date': 0,
                'verified': 0,
                'online': True,
                'standard_contact': True,
                'race': 0,
                'race2': None,
                'img': 'url',
            },
            '222': {
                'age': 18,
                'handle': '222_handle',
                'sex': 'M',
                'pwsid': '222',
                'date_registered': '2013-04-07 01:11:18',
                'looking_for_person': ['M', 'F'],
                'level': 300,
                'is_gold': True,
                'hotlisted': False,
                'flirted': False,
                'is_friend': False,
                'is_confirmed': False,
                'is_verified': False,
                'is_vip': True,
                'vip': True,
                'confirm_date': 0,
                'verified': 0,
                'online': False,
                'standard_contact': False,
                'race': 0,
                'img': 'url',
            },
            '333': {
                'pwsid': '333',
                'handle': '333',
                **DEFAULT_PASSPORT_RESULT
            },
        }, result)

    def test_get_with_non_200_status(self) -> None:
        self._caplog.set_level(logging.INFO)

        requester = requester_module.LegacyAPISyncRequester('http://test.com')
        passport_api = module.PassportAPI(requester)
        response_1_mock = mock.Mock(status_code=200, headers={})
        response_1_mock.json.return_value = {'status': 500, 'payload': {}}
        response_2_mock = mock.Mock(status_code=200, headers={})
        response_2_mock.json.return_value = {'status': 400, 'payload': {}}
        response_3_mock = mock.Mock(status_code=200, headers={})
        response_3_mock.json.return_value = {'status': 403, 'payload': {}}

        datetime_mock = mock.Mock()
        datetime_mock.datetime.now.return_value = datetime(year=2000, month=1, day=1)
        datetime_mock.datetime.strftime = datetime.strftime
        datetime_mock.datetime.strptime = datetime.strptime

        with mock.patch.object(
            module, 'config', LEGACY_API2_BASIC_PATH='a2/v1'
        ), mock.patch.object(
            module, 'datetime', datetime_mock
        ), mock.patch.object(
            requester_module.time, 'sleep'
        ), mock.patch.object(
            requester_module, 'requests'
        ) as requests_mock:
            requests_mock.post.side_effect = [response_1_mock, response_2_mock, response_3_mock]
            result = passport_api.get(['111', '222', '333'])

        self.assertDictEqual({
            '111': {
                'pwsid': '111',
                'handle': '111',
                **DEFAULT_PASSPORT_RESULT
            },
            '222': {
                'pwsid': '222',
                'handle': '222',
                **DEFAULT_PASSPORT_RESULT
            },
            '333': {
                'pwsid': '333',
                'handle': '333',
                **DEFAULT_PASSPORT_RESULT
            }
        }, result)

        info_msg = (
            "Call to a2/v1/passport for ['111', '222', '333'] "
            "returned a non-200 status code. Will retry again."
        )
        error_msg = "There is not full response with re-requests"

        assert info_msg == self._caplog.records[0].message
        assert info_msg == self._caplog.records[1].message
        assert info_msg == self._caplog.records[2].message
        assert error_msg == self._caplog.records[3].message
