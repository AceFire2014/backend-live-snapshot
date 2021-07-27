import unittest
from unittest import mock
import asynctest

from common.cams.objects import StreamSession, StreamSessions, ShowTypeEnum
import tasks.tasks as module


class TestGetStreams(unittest.TestCase):
    def test_success(self) -> None:
        stream_sessions = StreamSessions(
            count=5,
            streams=[
                StreamSession(
                    id=None,
                    channel_name='aaa_aaaa',
                    start_time=None,
                    end_time=None,
                    broadcast_session=None,
                    handle='aaaa_handle',
                    pwsid='aaaa_pwsid',
                    show_type=None
                ),
                StreamSession(
                    id=None,
                    channel_name='bbb_bbbb',
                    start_time=None,
                    end_time=None,
                    broadcast_session=None,
                    handle='bbbb_handle',
                    pwsid='bbbb_pwsid',
                    show_type=None
                ),
                StreamSession(
                    id=None,
                    channel_name='aaa_cccc',
                    start_time=None,
                    end_time=None,
                    broadcast_session=None,
                    handle='cccc_handle',
                    pwsid='cccc_pwsid',
                    show_type=None
                ),
                StreamSession(
                    id=None,
                    channel_name='aaa_dddd',
                    start_time=None,
                    end_time='2020-01-01',
                    broadcast_session=None,
                    handle='dddd_handle',
                    pwsid='dddd_pwsid',
                    show_type=None
                ),
                StreamSession(
                    id=None,
                    channel_name='aaa_eeee',
                    start_time=None,
                    end_time=None,
                    broadcast_session=None,
                    handle='eeee_handle',
                    pwsid='eeee_pwsid',
                    show_type=None
                ),
            ]
        )

        streaming_service = mock.Mock()
        streaming_service.get_sessions.return_value = stream_sessions
        redis = mock.Mock()
        redis.nonatomic_mget.return_value = [True, None, True]
        cache_renew_mock = mock.Mock()

        with mock.patch.object(module, 'streaming_service', streaming_service), \
                mock.patch.object(module, 'config', STREAM_INSTALLATION_PREFIX='aaa_', REDIS_BUS='redis.Redis'):
            online, lost = module.get_streams(redis, streaming_service, cache_renew=cache_renew_mock)

        streaming_service.get_sessions.assert_called_once_with(mode=ShowTypeEnum.FREE, cache_renew=cache_renew_mock)
        self.assertDictEqual({
            'aaaa_pwsid': StreamSession(
                id=None,
                channel_name='aaa_aaaa',
                start_time=None,
                end_time=None,
                broadcast_session=None,
                handle='aaaa_handle',
                pwsid='aaaa_pwsid',
                show_type=None
            ),
            'eeee_pwsid': StreamSession(
                id=None,
                channel_name='aaa_eeee',
                start_time=None,
                end_time=None,
                broadcast_session=None,
                handle='eeee_handle',
                pwsid='eeee_pwsid',
                show_type=None
            ),
        }, online)
        self.assertDictEqual({
            'cccc_pwsid': StreamSession(
                id=None,
                channel_name='aaa_cccc',
                start_time=None,
                end_time=None,
                broadcast_session=None,
                handle='cccc_handle',
                pwsid='cccc_pwsid',
                show_type=None
            ),
        }, lost)


class TestPreviewUpdateTask(unittest.TestCase):
    def test_success(self) -> None:
        online = {
            'aaaa_pwsid': StreamSession(
                id=None,
                channel_name='aaa_aaaa',
                start_time=None,
                end_time=None,
                broadcast_session=None,
                handle='aaaa_handle',
                pwsid='aaaa_pwsid',
                show_type=None
            ),
            'cccc_pwsid': StreamSession(
                id=None,
                channel_name='aaa_cccc',
                start_time=None,
                end_time=None,
                broadcast_session=None,
                handle='cccc_handle',
                pwsid='cccc_pwsid',
                show_type=None
            ),
            'eeee_pwsid': StreamSession(
                id=None,
                channel_name='aaa_eeee',
                start_time=None,
                end_time=None,
                broadcast_session=None,
                handle='eeee_handle',
                pwsid='eeee_pwsid',
                show_type=None
            ),
        }

        with mock.patch.object(module, 'get_streams', return_value=(online, {})) as get_streams_mock, \
                mock.patch.object(module, 'os') as os_mock, \
                mock.patch.object(module, 'config', STREAM_SNAPSHOT_STORAGE_PATH='/tmp',
                                  STREAM_INSTALLATION_PREFIX='aaa_', SNAPSHOT_TASK_CHUNK_SIZE=2,
                                  REDIS_BUS='redis.Redis', SNAPSHOT_TASK_COUNTDOWN_MULTIPLIER=3), \
                mock.patch.object(module, 'make_snapshots') as make_snapshots_mock:
            self.assertIsNone(module.make_all_snapshots())

        get_streams_mock.assert_called_once_with(mock.ANY, module.streaming_service)
        os_mock.makedirs.assert_called_once_with('/tmp')
        self.assertListEqual(
            make_snapshots_mock.apply_async.call_args_list,
            [mock.call(kwargs={'streams': [('aaa_aaaa', 'aaaa_pwsid', 'aaaa_handle'),
                                           ('aaa_cccc', 'cccc_pwsid', 'cccc_handle')],
                               'fake': False},
                       ignore_result=True,
                       countdown=0),
             mock.call(kwargs={'streams': [('aaa_eeee', 'eeee_pwsid', 'eeee_handle')],
                               'fake': False},
                       ignore_result=True,
                       countdown=3)]
        )


class TestMakePreviewTask(unittest.TestCase):
    def test_success(self) -> None:
        streaming_service = mock.Mock()
        streaming_service.get_sessions = asynctest.CoroutineMock(return_value=mock.Mock(streams=[]))

        # file_mock.assert_called
        file_mock = mock.Mock()
        file_mock.__aenter__ = asynctest.CoroutineMock()
        file_mock.__aexit__ = asynctest.CoroutineMock()
        file_mock.__aenter__.return_value.write = asynctest.CoroutineMock()
        get_snapshot_mock = asynctest.CoroutineMock(side_effect=(b'aaa', b'bbb'))

        redis_mock = asynctest.CoroutineMock(return_value=mock.Mock(set=asynctest.CoroutineMock()))()

        save_persist_snapshot_mock = mock.Mock()

        with mock.patch.object(module, 'config', PREVIEW_URL_TTL=120, SNAPSHOT_CAPTURING_MAX_DURATION=2,
                               SNAPSHOT_UPDATE_PERIOD=30, STREAM_SNAPSHOT_STORAGE_PATH='/tmp111'), \
                mock.patch.object(module, 'AIOFile', return_value=file_mock), \
                mock.patch.object(module, 'os') as os_mock, \
                mock.patch.object(module, 'astreaming_service', streaming_service), \
                mock.patch.object(module, 'get_snapshot', get_snapshot_mock), \
                mock.patch.object(module, '_save_persist_snapshot', save_persist_snapshot_mock), \
                mock.patch.object(module, 'aredis_factory', return_value=redis_mock):
            module.make_snapshots([['aaa', 'aaa_pwsid', 'aaa_handle'], ['bbb', 'bbb_pwsid', 'bbb_handle']])

        os_mock.makedirs.assert_called_once_with('/tmp111')
        self.assertSequenceEqual(sorted(get_snapshot_mock.call_args_list),
                                 [mock.call('aaa', mock.ANY), mock.call('bbb', mock.ANY)])
        self.assertSequenceEqual(sorted(file_mock.__aenter__.return_value.write.call_args_list),
                                 [mock.call(b'aaa'), mock.call(b'bbb')])
        self.assertSequenceEqual(sorted(save_persist_snapshot_mock.call_args_list),
                                 [mock.call(b'aaa', mock.ANY), mock.call(b'bbb', mock.ANY)])
