# -*- coding: utf-8 -*-

from itertools import count
from typing import Callable, Optional
from unittest import mock

import asynctest
from parameterized import parameterized

from common.json_chunking import json_dumps, JsonValueError, JsonStopChunking, ChunkParams


class TestChunkJson(asynctest.TestCase):

    @staticmethod
    def chunking(limit: int, str_chunk_min_len: Optional[int] = None, header: Optional[Callable] = None) -> Callable:
        def fun():
            for idx in count(1):
                repeat = True
                while repeat:
                    fun.iterations_num = idx
                    repeat = yield ChunkParams(
                        header={'chunk': idx} if (header is None) else header(idx),
                        limit=limit,
                        try_dump_whole=False,
                        str_chunk_min_len=str_chunk_min_len,
                    )
        return fun


class TestChunkJsonDict(TestChunkJson):

    def test_chunking_generator_is_closed(self):
        gen = mock.Mock()
        gen.send.return_value = ChunkParams(header={}, limit=100)
        list(json_dumps({'1': 1}, chunking=gen))
        gen.close.assert_called_once()

    def test_chunking_generator_is_closed_on_exception(self):
        gen = mock.Mock()
        ex = Exception()
        gen.send.side_effect = ex
        with self.assertRaises(Exception) as e:
            list(json_dumps({'1': 1}, chunking=gen))
        self.assertIs(e.exception, ex)
        gen.close.assert_called_once()

    def test_chunk_repetition_is_requested(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=0, breakable=True),
                                ChunkParams(header={}, limit=0, breakable=True),
                                ChunkParams(header={}, limit=7)]
        res = list(json_dumps({'1': 1}, chunking=gen))
        self.assertSequenceEqual(res, [None, None, '{"1":1}'])
        self.assertSequenceEqual(gen.send.call_args_list, [mock.call(None), mock.call(True), mock.call(True)])

    def test_workflow_1(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=0, breakable=True),
                                ChunkParams(header={}, limit=7, breakable=True),
                                ChunkParams(header={}, limit=0, breakable=True),
                                ChunkParams(header={}, limit=7)]
        res = list(json_dumps({'1': 1, '2': 2}, chunking=gen))
        self.assertSequenceEqual(res, [None, '{"1":1}', None, '{"2":2}'])
        self.assertSequenceEqual(gen.send.call_args_list,
                                 [mock.call(None), mock.call(True), mock.call(False), mock.call(True)])

    def test_workflow_2(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=2, breakable=False)]
        with self.assertRaises(JsonValueError) as ex:
            list(json_dumps({'1': 1, '2': 2}, chunking=gen))
        self.assertSequenceEqual(ex.exception.keys, ['1'])
        self.assertEqual(ex.exception.value, 1)

    def test_chunk_header_oversize(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={'header': None}, limit=0, breakable=False)]
        with self.assertRaises(JsonValueError) as ex:
            list(json_dumps({'value': None}, chunking=gen))
        self.assertSequenceEqual(ex.exception.keys, [])
        self.assertEqual(ex.exception.value, {'header': None})

    def test_empty_header(self):
        chunking = self.chunking(limit=7, header=lambda idx: {})
        res = list(json_dumps({'1': 1}, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"1":1}'])
        self.assertEqual(len(res[0]), 7)
        self.assertEqual(chunking.iterations_num, 1)

    def test_empty_body(self):
        chunking = self.chunking(limit=11)
        res = list(json_dumps({}, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1}'])
        self.assertEqual(len(res[0]), 11)
        self.assertEqual(chunking.iterations_num, 1)

    def test_empty_body_and_header(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=0, breakable=True),
                                ChunkParams(header={}, limit=1, breakable=True),
                                ChunkParams(header={}, limit=2)]
        res = list(json_dumps({}, chunking=gen))
        self.assertSequenceEqual(res, [None, None, '{}'])
        self.assertSequenceEqual(gen.send.call_args_list,
                                 [mock.call(None), mock.call(True), mock.call(True)])

    def test_data_transformation_correctness(self):
        chunking = self.chunking(limit=17)
        res = list(json_dumps({1: 1}, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1,"1":1}'])
        self.assertEqual(len(res[0]), 17)
        self.assertEqual(chunking.iterations_num, 1)

    def test_splitting(self):
        chunking = self.chunking(limit=17)
        res = list(json_dumps({'1': 1, '2': 2}, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1,"1":1}',
                                       '{"chunk":2,"2":2}'])
        self.assertEqual(chunking.iterations_num, 2)

    def test_conjunction(self):
        chunking = self.chunking(limit=23)
        res = list(json_dumps({'1': 1, '2': 2}, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1,"1":1,"2":2}'])
        self.assertEqual(chunking.iterations_num, 1)

    def test_distribution(self):
        chunking = self.chunking(limit=23)
        res = list(json_dumps({'1': 1, '2': 2, '3': 3, '4': 4}, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1,"1":1,"2":2}',
                                       '{"chunk":2,"3":3,"4":4}'])
        self.assertEqual(chunking.iterations_num, 2)

    def test_oversize(self):
        chunking = self.chunking(limit=17)
        with self.assertRaises(JsonValueError) as ex:
            list(json_dumps({'1': 1, '22': 22}, chunking=chunking()))
        self.assertSequenceEqual(ex.exception.keys, ['22'])
        self.assertEqual(ex.exception.value, 22)
        self.assertEqual(chunking.iterations_num, 2)

    def test_chunks_limit(self):
        gen = mock.Mock()
        gen.send.side_effect = [JsonStopChunking]

        data = {'0': None, '1': None}
        res = list(json_dumps(data, chunking=gen))
        self.assertSequenceEqual(res, [])

    def test_chunks_limit2(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=1, breakable=True),
                                JsonStopChunking]

        data = {}
        res = list(json_dumps(data, chunking=gen))
        self.assertSequenceEqual(res, [None])

    def test_chunks_limit3(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=10, breakable=True, str_chunk_min_len=1),
                                JsonStopChunking]

        data = {'0': None, '1': None}
        res = list(json_dumps(data, chunking=gen))
        self.assertSequenceEqual(res, ['{"0":null}'])

    def test_inner_splitting(self):
        chunking = self.chunking(limit=24)
        res = list(json_dumps({'0': {'1': 1, '2': 2}}, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1,"0":{"1":1}}',
                                       '{"chunk":2,"0":{"2":2}}'])
        self.assertEqual(chunking.iterations_num, 2)

    def test_inner_conjunction_1(self):
        chunking = self.chunking(limit=29)
        res = list(json_dumps({'0': {'1': 1, '2': 2}}, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1,"0":{"1":1,"2":2}}'])
        self.assertEqual(chunking.iterations_num, 1)

    def test_inner_distribution_2(self):
        chunking = self.chunking(limit=29)
        res = list(json_dumps({'0': {'1': 1, '2': 2, '3': 3, '4': 4}}, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1,"0":{"1":1,"2":2}}',
                                       '{"chunk":2,"0":{"3":3,"4":4}}'])
        self.assertEqual(chunking.iterations_num, 2)

    def test_inner_distribution_3(self):
        chunking = self.chunking(limit=31)
        res = list(json_dumps({'-1': -1, '0': {'1': 1, '2': 2, '3': 3}}, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1,"-1":-1,"0":{"1":1}}',
                                       '{"chunk":2,"0":{"2":2,"3":3}}'])
        self.assertEqual(chunking.iterations_num, 2)

    def test_inner_distribution_4(self):
        chunking = self.chunking(limit=37)
        res = list(json_dumps({'-1': -1, '0': {'1': 1, '2': 2, '3': 3, '4': 4}}, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1,"-1":-1,"0":{"1":1,"2":2}}',
                                       '{"chunk":2,"0":{"3":3,"4":4}}'])
        self.assertEqual(chunking.iterations_num, 2)

    def test_inner_oversize(self):
        chunking = self.chunking(limit=23)
        with self.assertRaises(JsonValueError) as ex:
            list(json_dumps({'0': {'1': 1, '22': 22}}, chunking=chunking()))
        self.assertSequenceEqual(ex.exception.keys, ['0', '22'])
        self.assertEqual(ex.exception.value, 22)
        self.assertEqual(chunking.iterations_num, 2)

    def test_traceback(self):
        chunking = self.chunking(limit=56)
        data = {'0': {'1': {'2': {'3': 3,
                                  '33': {'4': {'5': {'6': 6,
                                                     '66': 66}}}}}}}
        res = list(json_dumps(data, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1,"0":{"1":{"2":{"3":3}}}}',
                                       '{"chunk":2,"0":{"1":{"2":{"33":{"4":{"5":{"6":6}}}}}}}',
                                       '{"chunk":3,"0":{"1":{"2":{"33":{"4":{"5":{"66":66}}}}}}}'])
        self.assertEqual(chunking.iterations_num, 3)

    @parameterized.expand((
         *[[i] for i in range(-10, 17)],
    ))
    def test_brute_force_1(self, size):
        chunking = self.chunking(limit=size)
        with self.assertRaises(JsonValueError):
            list(json_dumps({'1': 1, '2': 2}, chunking=chunking()))
        self.assertEqual(chunking.iterations_num, 1)

    @parameterized.expand((
         *[[i] for i in range(17, 23)],
    ))
    def test_brute_force_2(self, size):
        chunking = self.chunking(limit=size)
        res = list(json_dumps({'1': 1, '2': 2}, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1,"1":1}',
                                       '{"chunk":2,"2":2}'])
        self.assertEqual(chunking.iterations_num, 2)

    @parameterized.expand((
         *[[i] for i in range(23, 33)],
    ))
    def test_brute_force_3(self, size):
        chunking = self.chunking(limit=size)
        res = list(json_dumps({'1': 1, '2': 2}, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1,"1":1,"2":2}'])
        self.assertEqual(chunking.iterations_num, 1)


class TestChunkJsonString(TestChunkJson):

    @parameterized.expand((
            (True,),
            (False,),
    ))
    def test_splitting(self, as_bytes):
        chunking = self.chunking(limit=21, str_chunk_min_len=3)
        data = {'0': (b'a' if as_bytes else 'a')*(3*3+1)}
        res = list(json_dumps(data, chunking=chunking(), reject_bytes=not as_bytes))
        self.assertSequenceEqual(res, ['{"chunk":1,"0":"aaa"}',
                                       '{"chunk":2,"0":"aaa"}',
                                       '{"chunk":3,"0":"aaa"}',
                                       '{"chunk":4,"0":"a"}'])
        self.assertEqual(chunking.iterations_num, 4)

    def test_oversize(self):
        chunking = self.chunking(limit=20, str_chunk_min_len=3)
        data = {'0': 'a'*(3*3+1)}
        with self.assertRaises(JsonValueError) as ex:
            list(json_dumps(data, chunking=chunking()))
        self.assertSequenceEqual(ex.exception.keys, ['0'])
        self.assertEqual(ex.exception.value, 'a'*(3*3+1))
        self.assertEqual(chunking.iterations_num, 1)

    def test_chunks_limit(self):
        gen = mock.Mock()
        gen.send.side_effect = [JsonStopChunking]

        data = 'ab'
        res = list(json_dumps(data, chunking=gen))
        self.assertSequenceEqual(res, [])

    def test_chunks_limit2(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=1, breakable=True),
                                JsonStopChunking]

        data = ''
        res = list(json_dumps(data, chunking=gen))
        self.assertSequenceEqual(res, [None])

    def test_chunks_limit3(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=3, breakable=True, str_chunk_min_len=1),
                                JsonStopChunking]

        data = 'ab'
        res = list(json_dumps(data, chunking=gen))
        self.assertSequenceEqual(res, ['"a"'])

    def test_chunking_generator_is_closed(self):
        gen = mock.Mock()
        gen.send.return_value = ChunkParams(header={}, limit=100)
        list(json_dumps({'0': 'aaa'}, chunking=gen))
        gen.close.assert_called_once()

    def test_chunking_generator_is_closed_on_exception(self):
        gen = mock.Mock()
        ex = Exception()
        gen.send.side_effect = ex
        with self.assertRaises(Exception) as e:
            list(json_dumps({'0': 'aaa'}, chunking=gen))
        self.assertIs(e.exception, ex)
        gen.close.assert_called_once()

    def test_chunk_repetition_is_requested(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=0, breakable=True),
                                ChunkParams(header={}, limit=0, breakable=True),
                                ChunkParams(header={}, limit=11)]
        res = list(json_dumps({'0': 'aaa'}, chunking=gen))
        self.assertSequenceEqual(res, [None, None, '{"0":"aaa"}'])
        self.assertSequenceEqual(gen.send.call_args_list, [mock.call(None), mock.call(True), mock.call(True)])

    def test_empty(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=0, breakable=True),
                                ChunkParams(header={}, limit=1, breakable=True),
                                ChunkParams(header={}, limit=2)]
        res = list(json_dumps('', chunking=gen))
        self.assertSequenceEqual(res, [None, None, '""'])
        self.assertSequenceEqual(gen.send.call_args_list, [mock.call(None), mock.call(True), mock.call(True)])

    @parameterized.expand((
            ('"', ['"\\""'], 4),
            ('\\', ['"\\\\"'], 4),
            ('\\"', ['"\\\\"', '"\\""'], 4),

            ('_"_', ['"_\\""', '"_"'], 5),
            ('_\\_', ['"_\\\\"', '"_"'], 5),
            ('_\\"_', ['"_\\\\"', '"\\"_"'], 5),

            ('_"_', ['"_\\"_"'], 6),
            ('_\\_', ['"_\\\\_"'], 6),
            ('_\\"_', ['"_\\\\\\"_"'], 8),

            ('_"', ['"_"', '"\\""'], 4),  # odd number of '\' on boundary
            ('_\\', ['"_"', '"\\\\"'], 4),  # odd number of '\' on boundary
            ('\\\\', ['"\\\\"', '"\\\\"'], 4),  # even number of '\' on boundary
            ('\\\\', ['"\\\\"', '"\\\\"'], 5),  # odd number of '\' on boundary
    ))
    def test_escape_symbols(self, data, expected, limit):
        chunking = self.chunking(limit=limit, str_chunk_min_len=1)
        res = list(json_dumps(data, chunking=chunking()))
        self.assertSequenceEqual(res, expected)

    @parameterized.expand((
            ('"',),
            ('\\',),
    ))
    def test_escape_symbols_oversize(self, data):
        chunking = self.chunking(limit=3, str_chunk_min_len=1)
        with self.assertRaises(JsonValueError) as ex:
            list(json_dumps(data, chunking=chunking()))
        self.assertEqual(ex.exception.bytes_needed, 1)


class TestChunkJsonArray(TestChunkJson):

    def test_splitting(self):
        chunking = self.chunking(limit=23)
        data = {'0': [1]*(3*3+1)}
        res = list(json_dumps(data, chunking=chunking()))
        self.assertSequenceEqual(res, ['{"chunk":1,"0":[1,1,1]}',
                                       '{"chunk":2,"0":[1,1,1]}',
                                       '{"chunk":3,"0":[1,1,1]}',
                                       '{"chunk":4,"0":[1]}'])
        self.assertEqual(chunking.iterations_num, 4)

    def test_oversize(self):
        chunking = self.chunking(limit=22)
        data = {'0': [0, 1, 12345678]}
        with self.assertRaises(JsonValueError) as ex:
            list(json_dumps(data, chunking=chunking()))
        self.assertSequenceEqual(ex.exception.keys, ('0', [2]))
        self.assertEqual(ex.exception.value, 12345678)
        self.assertEqual(chunking.iterations_num, 2)

    def test_chunks_limit(self):
        gen = mock.Mock()
        gen.send.side_effect = [JsonStopChunking]

        data = [1, 2]
        res = list(json_dumps(data, chunking=gen))
        self.assertSequenceEqual(res, [])

    def test_chunks_limit2(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=1, breakable=True),
                                JsonStopChunking]

        data = []
        res = list(json_dumps(data, chunking=gen))
        self.assertSequenceEqual(res, [None])

    def test_chunks_limit3(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=3),
                                JsonStopChunking]

        data = [1, 2]
        res = list(json_dumps(data, chunking=gen))
        self.assertSequenceEqual(res, ['[1]'])

    def test_chunking_generator_is_closed(self):
        gen = mock.Mock()
        gen.send.return_value = ChunkParams(header={}, limit=100)
        list(json_dumps({'0': [1, 1, 1]}, chunking=gen))
        gen.close.assert_called_once()

    def test_chunking_generator_is_closed_on_exception(self):
        gen = mock.Mock()
        ex = Exception()
        gen.send.side_effect = ex
        with self.assertRaises(Exception) as e:
            list(json_dumps({'0': [1]}, chunking=gen))
        self.assertIs(e.exception, ex)
        gen.close.assert_called_once()

    def test_chunk_repetition_is_requested(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=0, breakable=True),
                                ChunkParams(header={}, limit=0, breakable=True),
                                ChunkParams(header={}, limit=9)]
        res = list(json_dumps({'0': [1]}, chunking=gen))
        self.assertSequenceEqual(res, [None, None, '{"0":[1]}'])
        self.assertSequenceEqual(gen.send.call_args_list, [mock.call(None), mock.call(True), mock.call(True)])

    def test_chunk_empty(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=0, breakable=True),
                                ChunkParams(header={}, limit=0, breakable=True),
                                ChunkParams(header={}, limit=2)]
        res = list(json_dumps([], chunking=gen))
        self.assertSequenceEqual(res, [None, None, '[]'])
        self.assertSequenceEqual(gen.send.call_args_list, [mock.call(None), mock.call(True), mock.call(True)])


class TestChunkJsonScalar(TestChunkJson):

    def test_dump(self):
        chunking = self.chunking(limit=2)
        data = 11
        res = list(json_dumps(data, chunking=chunking()))
        self.assertSequenceEqual(res, ['11'])
        self.assertEqual(chunking.iterations_num, 1)

    def test_oversize(self):
        chunking = self.chunking(limit=1)
        data = 11
        with self.assertRaises(JsonValueError) as ex:
            list(json_dumps(data, chunking=chunking()))
        self.assertSequenceEqual(ex.exception.keys, [])
        self.assertEqual(ex.exception.value, 11)
        self.assertEqual(chunking.iterations_num, 1)

    def test_chunks_limit(self):
        gen = mock.Mock()
        gen.send.side_effect = [JsonStopChunking]

        data = 11
        res = list(json_dumps(data, chunking=gen))
        self.assertSequenceEqual(res, [])

    def test_chunks_limit2(self):
        gen = mock.Mock()
        gen.send.side_effect = [ChunkParams(header={}, limit=1, breakable=True),
                                JsonStopChunking]

        data = 11
        res = list(json_dumps(data, chunking=gen))
        self.assertSequenceEqual(res, [None])

    def test_chunking_generator_is_closed(self):
        gen = mock.Mock()
        gen.send.return_value = ChunkParams(header={}, limit=100)
        list(json_dumps(11, chunking=gen))
        gen.close.assert_called_once()

    def test_chunking_generator_is_closed_on_exception(self):
        gen = mock.Mock()
        ex = Exception()
        gen.send.side_effect = ex
        with self.assertRaises(Exception) as e:
            list(json_dumps(11, chunking=gen))
        self.assertIs(e.exception, ex)
        gen.close.assert_called_once()


class TestChunkJsonAll(TestChunkJson):

    def test_all(self):
        chunking = self.chunking(limit=74, str_chunk_min_len=5)
        data = {'0': {'1': {'2': {'3': {3.5: ['aaaaaAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',  None, []]},
                                  '33': {'4': {'5': {'6': ["",
                                                           {},
                                                           {6.666: tuple()},
                                                           {6.666: [1, 2, b'zzzz\\']}],
                                                     '66': 66}}}}}}}
        res = list(json_dumps(data, chunking=chunking(), reject_bytes=False))
        self.assertSequenceEqual(res, ['{"chunk":1,"0":{"1":{"2":{"3":{"3.5":["aaaaaAAAAAAAAAAAAAAAAAAAAAAA"]}}}}}',
                                       '{"chunk":2,"0":{"1":{"2":{"3":{"3.5":["AAAAAAAAAA",null,[]]}}}}}',
                                       '{"chunk":3,"0":{"1":{"2":{"33":{"4":{"5":{"6":["",{},{"6.666":[]}]}}}}}}}',
                                       '{"chunk":4,"0":{"1":{"2":{"33":{"4":{"5":{"6":[{"6.666":[1,2]}]}}}}}}}',
                                       '{"chunk":5,"0":{"1":{"2":{"33":{"4":{"5":{"6":[{"6.666":["zzzz"]}]}}}}}}}',
                                       '{"chunk":6,"0":{"1":{"2":{"33":{"4":{"5":{"6":[{"6.666":["\\\\"]}]}}}}}}}',
                                       '{"chunk":7,"0":{"1":{"2":{"33":{"4":{"5":{"66":66}}}}}}}'])
        self.assertEqual(chunking.iterations_num, 7)
