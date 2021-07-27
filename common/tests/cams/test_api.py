import unittest
from unittest import mock
from urllib.parse import urlencode

import responses
from parameterized import parameterized

from common.cams.api import CamsAPI
from common.cams.objects import ShowTypeEnum, StreamSessions, StreamSession, PlaybackToken
from common.cams.requesters.syn import CamsAPISyncRequester


class TestCamsAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.cams_api = CamsAPI(requester=mock.Mock())

    @parameterized.expand((
        (None, None),
        (ShowTypeEnum.FREE, {'showType': 'FREE'}),
    ))
    def test_get_sessions(self, param, query):
        result = self.cams_api.get_sessions(param)
        self.assertEqual(result, self.cams_api.requester.get.return_value)
        self.cams_api.requester.get.assert_called_once_with(
            'api/show-sessions',
            query=query,
            cb=mock.ANY
        )

    def test_get_session(self):
        result = self.cams_api.get_session('1111')
        self.assertEqual(result, self.cams_api.requester.get.return_value)
        self.cams_api.requester.get.assert_called_once_with(
            'api/show-sessions/channel/1111',
            cb=mock.ANY,
            skip_not_found_logging=True
        )

    def test_get_broadcaster_token(self):
        result = self.cams_api.get_broadcaster_token('a_handle', 'broadcast_id', 'broadcaster_pwsid')
        self.assertEqual(result, self.cams_api.requester.get.return_value)
        self.cams_api.requester.get.assert_called_once_with(
            'api/urls/publishers/br_a_handle/broadcast_id/broadcaster_pwsid',
            cb=mock.ANY
        )

    def test_get_viewer_token(self):
        result = self.cams_api.get_viewer_token('b_handle', 'broadcast_id', 'user_pwsid')
        self.assertEqual(result, self.cams_api.requester.get.return_value)
        self.cams_api.requester.get.assert_called_once_with(
            'api/urls/viewers/vw_b_handle/broadcast_id/user_pwsid',
            cb=mock.ANY
        )

    def test_get_snapshot(self):
        result = self.cams_api.get_snapshot('broadcast_id')
        self.assertEqual(result, self.cams_api.requester.get.return_value)
        self.cams_api.requester.get.assert_called_once_with(
            'api/snapshots/broadcast_id',
            query={'format': 'jpg', 'height': '480', 'width': '640', 'fitmode': 'fit-height'},
            raw=True,
            cb=mock.ANY
        )

    def test_set_show_type(self):
        result = self.cams_api.set_show_type('b_handle', '11111', ShowTypeEnum.FREE)
        self.assertEqual(result, self.cams_api.requester.post.return_value)
        self.cams_api.requester.post.assert_called_once_with(
            'api/shows/br_b_handle',
            json={'publishToken': '11111', 'targetShowType': 'FREE'},
            cb=mock.ANY
        )

    def test_revoke_viewer_token(self):
        result = self.cams_api.revoke_viewer_token('b_handle', 'broadcast_id')
        self.assertEqual(result, self.cams_api.requester.delete.return_value)
        self.cams_api.requester.delete.assert_called_once_with(
            'api/tokens/vw_b_handle/broadcast_id',
            cb=mock.ANY
        )


class TestCallbacksCamsAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.cams_api = CamsAPI(CamsAPISyncRequester('http://broadcast.test.com'))

    @responses.activate
    def test_get_sessions(self):
        api_response = {
            'count': 1,
            'showSessions': [{
                'id': '1111',
                'broadcastSession': 'dddd',
                'channelName': 'aaa',
                'startTime': '2020-01-01T10:10:10.147Z',
                'userName': 'aaa_handle',
                'userSiteId': '123',
                'showType': 'FREE'
            }]
        }

        responses.add(responses.GET,
                      'http://broadcast.test.com/api/show-sessions?showType=FREE',
                      json=api_response,
                      status=200)

        result = self.cams_api.get_sessions(ShowTypeEnum.FREE)

        self.assertEqual(result, StreamSessions.from_dict(api_response))

    @responses.activate
    def test_get_session(self):
        api_response = {
            'id': '1111',
            'broadcastSession': 'dddd',
            'channelName': 'aaa',
            'startTime': '2020-01-01T10:10:10.147Z',
            'userName': 'aaa_handle',
            'userSiteId': '123',
            'showType': 'FREE'
        }

        responses.add(responses.GET,
                      'http://broadcast.test.com/api/show-sessions/channel/1111',
                      json=api_response,
                      status=200)

        result = self.cams_api.get_session('1111')

        self.assertEqual(result, StreamSession.from_dict(api_response))

    @responses.activate
    def test_get_broadcaster_token(self):
        api_response = {
            'token': '111-222-333',
        }

        responses.add(responses.GET,
                      'http://broadcast.test.com/api/urls/publishers/br_a_handle/broadcast_id/broadcaster_pwsid',
                      json=api_response,
                      status=200)

        result = self.cams_api.get_broadcaster_token('a_handle', 'broadcast_id', 'broadcaster_pwsid')
        self.assertEqual(result, '111-222-333')

    @responses.activate
    def test_get_viewer_token(self):
        api_response = {
            'token': '111-222-333',
            'instanceName': 'broadcast_id',
            'applicationName': 'webrct',
            'baseStreamName': 'user_pwsid',
            'origin': '11.11.11.11'
        }

        responses.add(responses.GET,
                      'http://broadcast.test.com/api/urls/viewers/vw_b_handle/broadcast_id/user_pwsid',
                      json=api_response,
                      status=200)

        result = self.cams_api.get_viewer_token('b_handle', 'broadcast_id', 'user_pwsid')
        self.assertEqual(result, PlaybackToken.from_dict(api_response))

    @responses.activate
    def test_get_snapshot(self):
        query = {
            'format': 'jpg', 'height': '480', 'width': '640', 'fitmode': 'fit-height'
        }
        responses.add(responses.GET,
                      f'http://broadcast.test.com/api/snapshots/broadcast_id?{urlencode(query)}',
                      body='aaaaaa',
                      status=200, content_type='image/jpeg')

        result = self.cams_api.get_snapshot('broadcast_id')
        self.assertEqual(result, b'aaaaaa')

    @responses.activate
    def test_set_show_type(self):
        api_response = {
            'id': '1111',
            'broadcastSession': 'dddd',
            'channelName': 'aaa',
            'startTime': '2020-01-01T10:10:10.147Z',
            'userName': 'aaa_handle',
            'userSiteId': '123',
            'showType': 'FREE'
        }
        responses.add(responses.POST,
                      'http://broadcast.test.com/api/shows/br_b_handle',
                      json={'currentShowSession': api_response},
                      status=200, content_type='plain/text')

        result = self.cams_api.set_show_type('b_handle', '11111', ShowTypeEnum.FREE)
        self.assertEqual(result, StreamSession.from_dict(api_response))

    @parameterized.expand((
        ('success', True),
        ('fail', False),
    ))
    @responses.activate
    def test_revoke_viewer_token(self, response, expected):
        responses.add(responses.DELETE,
                      'http://broadcast.test.com/api/tokens/vw_b_handle/broadcast_id',
                      json={'status': response},
                      status=200)

        result = self.cams_api.revoke_viewer_token('b_handle', 'broadcast_id')
        self.assertEqual(result, expected)
