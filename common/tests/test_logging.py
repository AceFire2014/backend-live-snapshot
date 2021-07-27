# -*- coding: utf-8 -*-

import logging
from unittest import mock

import asynctest
from parameterized import parameterized

from common.logging import ForwardingFormatter
from common.logging import lower_than


class TestLowerThan(asynctest.TestCase):

    def test_lower(self):
        lt = lower_than(logging.getLevelName(logging.ERROR))
        record = mock.Mock(levelno=logging.WARNING)
        self.assertTrue(lt(record))

    def test_equal(self):
        lt = lower_than(logging.getLevelName(logging.ERROR))
        record = mock.Mock(levelno=logging.ERROR)
        self.assertFalse(lt(record))

    def test_higher(self):
        lt = lower_than(logging.getLevelName(logging.ERROR))
        record = mock.Mock(levelno=logging.CRITICAL)
        self.assertFalse(lt(record))


class TestSwitchFormatter(asynctest.TestCase):

    async def test_no_default_given(self):
        with self.assertRaisesRegex(AssertionError, 'default'):
            ForwardingFormatter(formatters={}, default='default')

    async def test_default_is_given(self):
        ForwardingFormatter(formatters={'default': logging.Formatter()}, default='default')

    async def test_build_log_extra(self):
        target_formatter = 'target_formatter'
        extra = {'extra': 'extra'}

        formatter = ForwardingFormatter(formatters={'default': logging.Formatter()})
        extra_with_switch = formatter.forward_log_record(target_formatter=target_formatter, extra=extra)

        self.assertDictEqual(
            {**extra, formatter.KEY: target_formatter},
            extra_with_switch,
        )

    @parameterized.expand((
         (mock.Mock(**{ForwardingFormatter.KEY: 'default'}),),
         (mock.Mock(**{ForwardingFormatter.KEY: 'specific'}),),
         (mock.Mock(**{ForwardingFormatter.KEY: 'non_existing'}),),
         (mock.Mock(),),
    ))
    async def test_get_formatter(self, record):
        formatters = {
            'default': mock.Mock(),
            'specific': mock.Mock(),
        }
        expected_formatter = formatters.get(
            getattr(record, ForwardingFormatter.KEY, 'default'),
            formatters['default']
        )

        switch = ForwardingFormatter(formatters=formatters, default='default')
        ret = switch.format(record)

        expected_formatter.format.assert_called_once_with(record)
        self.assertEqual(expected_formatter.format.return_value, ret)

    async def test_apply(self):
        formatters = {
            'default': mock.Mock(),
        }
        record = mock.Mock()
        apply_mock = mock.Mock()

        switch = ForwardingFormatter(formatters=formatters, default='default', apply=apply_mock)
        ret = switch.format(record)

        apply_mock.assert_called_once_with(record)
        formatters['default'].format.assert_called_once_with(record)
        self.assertEqual(formatters['default'].format.return_value, ret)

    async def test_format(self):
        expected_formatted_str = 'formatted_str'
        switch = ForwardingFormatter(formatters={'default': logging.Formatter()})
        target_formatter = mock.Mock()
        target_formatter.format.side_effect = [expected_formatted_str]

        with mock.patch.object(switch, '_get_formatter', side_effect=[target_formatter]):
            formatted_str = switch.format(record=mock.Mock())

        self.assertEqual(expected_formatted_str, formatted_str)
