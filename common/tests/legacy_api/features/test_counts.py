import unittest
from unittest import mock
from parameterized import parameterized

from common.legacy_api.exceptions import RequestApiError, NoSessionError
import common.legacy_api.features.counts as module


class TestCountsAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.counts_api = module.CountsAPI(mock.Mock())

    def test_get_counts(self):
        with mock.patch.object(module, 'config', LEGACY_API2_BASIC_PATH='/a2/v1'):
            self.counts_api.get_counts()

        self.counts_api.requester.post.assert_called_once_with(
            '/a2/v1/counts',
            self.counts_api._get_counts_cb,
            json={'request': ['inbox_new_count', 'anyone_notify_count']}
        )

    @parameterized.expand((
        ({'status': 400}, RequestApiError),
        ({'status': 400, 'payload': {}}, RequestApiError),
        ({'status': 403}, NoSessionError),
    ))
    def test_get_counts_cb_error(self, result: dict, exception):
        with self.assertRaises(exception):
            self.counts_api._get_counts_cb(result)

    def test_get_counts_cb_success(self) -> None:
        response = {'payload': {'inbox_new_count': 1, 'anyone_notify_count': 2}}
        result = self.counts_api._get_counts_cb(response)

        self.assertDictEqual({'inbox_new_count': 1, 'anyone_notify_count': 2}, result)
