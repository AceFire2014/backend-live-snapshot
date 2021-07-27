# -*- coding: utf-8 -*-
import unittest
import responses
import aioresponses
import asynctest
from unittest import mock
from parameterized import parameterized

from common.legacy_api.exceptions import RequestApiError
import common.legacy_api.requesters.syn as sync_module
import common.legacy_api.requesters.asyn as async_module


class TestSyncRequester(unittest.TestCase):
    def setUp(self) -> None:
        self.requester = sync_module.LegacyAPISyncRequester('http://test.com', 'Browser agent', 'cookies data')

    @responses.activate
    def test_get_success(self) -> None:
        responses.add(responses.GET, 'http://test.com/api/test',
                      json={'test': 1}, status=200)
        cb_mock = mock.Mock()

        self.requester.get('api/test', cb_mock, some_param='some_param')
        cb_mock.assert_called_once_with({'test': 1}, some_param='some_param')

    def test_get_success_requests_parameters(self):
        headers = {'User-Agent': 'Browser agent', 'Cookie': 'cookies data'}
        params = {'a': 'b'}
        cb_mock = mock.Mock()

        with mock.patch.object(sync_module.requests, 'get') as get_mock:
            self.requester.get('api/test', cb_mock, params)

        get_mock.assert_called_once_with('http://test.com/api/test', headers=headers, params=params)

    @responses.activate
    def test_get_non_json(self) -> None:
        responses.add(responses.GET, 'http://test.com/api/test',
                      body='sssss', status=200)
        cb_mock = mock.Mock()

        with self.assertRaises(RequestApiError):
            self.requester.get('api/test', cb_mock, some_param='some_param')
        self.assertIs(cb_mock.called, False)

    @responses.activate
    def test_get_decode_reply_success(self) -> None:
        cb_mock = mock.Mock()
        responses.add(responses.GET, 'http://test.com/api/test',
                      body='ddddd', status=200)

        with mock.patch.object(sync_module, 'config', FRAUD_LOG_SECRET='secret'), \
                mock.patch.object(sync_module, 'jwt') as jwt_mock:

            jwt_mock.decode.return_value = {'test': 1}
            self.requester.get('api/test', cb_mock, decode_reply=True)

        jwt_mock.decode.assert_called_once_with('ddddd', 'secret', algorithms=['HS256'])
        cb_mock.assert_called_once_with({'test': 1})

    @responses.activate
    def test_get_decode_reply_non_json(self) -> None:
        responses.add(responses.GET, 'http://test.com/api/test', body='error', status=200)
        cb_mock = mock.Mock()

        with mock.patch.object(sync_module, 'jwt') as jwt_mock, \
                self.assertRaises(RequestApiError):
            jwt_mock.decode.side_effect = Exception

            self.requester.get('api/test', cb_mock, decode_reply=True)
            jwt_mock.decode.assert_called_once_with('error', 'secret', algorithms=['HS256'])

        self.assertIs(cb_mock.called, False)

    @responses.activate
    def test_post_success(self) -> None:
        responses.add(responses.POST, 'http://test.com/api/test',
                      json={'test': 1}, status=200)
        cb_mock = mock.Mock()

        self.requester.post('api/test', cb_mock, some_param='some_param')
        cb_mock.assert_called_once_with({'test': 1}, some_param='some_param')

    @parameterized.expand((
        (
            {'data': {'aaa': 'bbb'}, 'json': None},
            {'User-Agent': 'Browser agent', 'Cookie': 'cookies data'},
        ),
        (
            {'json': {'param': 'value'}, 'data': None},
            {'User-Agent': 'Browser agent', 'Cookie': 'cookies data',
             'Content-Type': 'application/json; charset=utf-8'},
        ),
    ))
    def test_post_success_requests_parameters(self, params, headers):
        cb_mock = mock.Mock()

        with mock.patch.object(sync_module.requests, 'post') as post_mock:
            self.requester.post('api/test', cb_mock, **params)

        post_mock.assert_called_once_with('http://test.com/api/test', headers=headers, **params)

    @responses.activate
    def test_post_non_json(self) -> None:
        responses.add(responses.POST, 'http://test.com/api/test',
                      body='sssss', status=200)
        cb_mock = mock.Mock()

        with self.assertRaises(RequestApiError):
            self.requester.post('api/test', cb_mock, json={'param': 'value'})
        self.assertIs(cb_mock.called, False)


class TestAsyncRequester(asynctest.TestCase):
    def setUp(self) -> None:
        self.requester = async_module.LegacyAPIAsyncRequester('http://test.com', 'Browser agent', 'cookies data')

    @property
    def session_cb_mock_fixture(self):
        return asynctest.CoroutineMock(
            post=asynctest.CoroutineMock(
                return_value=asynctest.Mock(json=asynctest.CoroutineMock(), text=asynctest.CoroutineMock(), headers={})
            ),
            get=asynctest.CoroutineMock(
                return_value=asynctest.Mock(json=asynctest.CoroutineMock(), text=asynctest.CoroutineMock(), headers={})
            )
        )

    async def test_get_success(self) -> None:
        cb_mock = mock.Mock()
        with aioresponses.aioresponses() as mocker:
            mocker.get('http://test.com/api/test', status=200, body='{"test":1}')
            await self.requester.get('api/test', cb_mock, some_param='some_param')

        cb_mock.assert_called_once_with({'test': 1}, some_param='some_param')

    async def test_request_request_params_are_used(self) -> None:
        session_cb_mock = self.session_cb_mock_fixture
        headers = {'User-Agent': 'Browser agent', 'Cookie': 'cookies data'}
        params = {'a': 'b'}

        with asynctest.patch.object(async_module.aiohttp, 'ClientSession') as session_mock:
            session_mock.return_value.__aenter__.return_value = session_cb_mock
            await self.requester.get('api/test', mock.Mock(), params)

        session_cb_mock.get.assert_awaited_once_with('http://test.com/api/test', headers=headers, params=params)

    async def test_get_non_json(self) -> None:
        cb_mock = mock.Mock()
        with aioresponses.aioresponses() as mocker:
            mocker.get('http://test.com/api/test', status=200, body='ssss')

            with self.assertRaises(RequestApiError):
                await self.requester.get('api/test', cb_mock, some_param='some_param')

        self.assertIs(cb_mock.called, False)

    async def test_get_decode_reply_success(self) -> None:
        cb_mock = mock.Mock()

        with asynctest.patch.object(async_module, 'config', FRAUD_LOG_SECRET='secret'), \
                asynctest.patch.object(async_module, 'jwt') as jwt_mock, \
                aioresponses.aioresponses() as mocker:

            mocker.get('http://test.com/api/test', status=200, body='dddd')
            jwt_mock.decode.return_value = {'test': 1}

            await self.requester.get('api/test', cb_mock, decode_reply=True)

        jwt_mock.decode.assert_called_once_with('dddd', 'secret', algorithms=['HS256'])
        cb_mock.assert_called_once_with({'test': 1})

    async def test_get_decode_reply_non_json(self) -> None:
        cb_mock = mock.Mock()

        with aioresponses.aioresponses() as mocker:
            mocker.get('http://test.com/api/test', status=200, body='error')

            with mock.patch.object(sync_module, 'config', FRAUD_LOG_SECRET='secret'), \
                    mock.patch.object(sync_module, 'jwt') as jwt_mock, \
                    self.assertRaises(RequestApiError):
                jwt_mock.decode.side_effect = Exception

                await self.requester.get('api/test', cb_mock, decode_reply=True)
                jwt_mock.decode.assert_called_once_with('error', 'secret', algorithms=['HS256'])

        self.assertIs(cb_mock.called, False)

    async def test_post_success(self) -> None:
        cb_mock = mock.Mock()
        with aioresponses.aioresponses() as mocker:
            mocker.post('http://test.com/api/test', status=200, body='{"test":1}')
            await self.requester.post('api/test', cb_mock, some_param='some_param')

        cb_mock.assert_called_once_with({'test': 1}, some_param='some_param')

    @parameterized.expand((
        (
            {'data': {'aaa': 'bbb'}, 'json': None},
            {'User-Agent': 'Browser agent', 'Cookie': 'cookies data'},
        ),
        (
            {'json': {'param': 'value'}, 'data': None},
            {'User-Agent': 'Browser agent', 'Cookie': 'cookies data',
             'Content-Type': 'application/json; charset=utf-8'},
        ),
    ))
    async def test_post_success_requests_parameters(self, params, headers):
        session_cb_mock = self.session_cb_mock_fixture

        with asynctest.patch.object(async_module.aiohttp, 'ClientSession') as session_mock:
            session_mock.return_value.__aenter__.return_value = session_cb_mock
            await self.requester.post('api/test', mock.Mock(), **params)

        session_cb_mock.post.assert_awaited_once_with('http://test.com/api/test', headers=headers, **params)

    async def test_post_non_json(self) -> None:
        cb_mock = mock.Mock()
        with aioresponses.aioresponses() as mocker:
            mocker.post('http://test.com/api/test', status=200, body='ssss')

            with self.assertRaises(RequestApiError):
                await self.requester.post('api/test', cb_mock, some_param='some_param')

        self.assertIs(cb_mock.called, False)
