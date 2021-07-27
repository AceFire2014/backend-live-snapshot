import unittest
from unittest import mock

from parameterized import parameterized

import common.config as module


class TestEnvironmentVariablesProcessor(unittest.TestCase):

    def test_successful_types_conversion(self) -> None:
        config_module = mock.Mock(
            STR_VAR='str',
            INT_VAR=2,
            BOOL_VAR=True,
        )

        with mock.patch.object(module.os.environ, 'items', return_value=[
            ('TEST_STR_VAR', 'another_str'),
            ('TEST_INT_VAR', '3'),
            ('TEST_BOOL_VAR', 'False'),
        ]):
            result = module.environment_variables_processor(config_module, 'TEST_')

            self.assertEqual(result.STR_VAR, 'another_str')
            self.assertEqual(result.INT_VAR, 3)
            self.assertEqual(result.BOOL_VAR, False)

    @parameterized.expand((
        (2, 'not int'),
        (True, 'not bool'),
    ))
    def test_failed_types_conversion(self, original, modified) -> None:
        config_module = mock.Mock(
            VAR=original,
        )

        with mock.patch.object(module.os.environ, 'items', return_value=[
            ('VAR', modified),
        ]):
            with self.assertRaises(ValueError):
                module.environment_variables_processor(config_module, '')
