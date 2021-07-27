import copy
from contextlib import closing, suppress
from typing import Any, Optional, Generator, Tuple, Union, Iterable

import ujson

STR_CHUNK_MIN_LEN = 100


class JsonStopChunking(Exception):
    pass


class JsonValueError(ValueError):

    def __init__(self, msg: str, *, keys: Tuple, value: Any, bytes_needed: int):
        super().__init__(msg, keys, value, bytes_needed)

    @property
    def keys(self):
        return self.args[1]

    @keys.setter
    def keys(self, value):
        self.args = self.args[0], value, *self.args[2:]

    @property
    def value(self):
        return self.args[2]

    @value.setter
    def value(self, value):
        self.args = *self.args[0:1], value, *self.args[3:]

    @property
    def bytes_needed(self):
        return self.args[3]

    @bytes_needed.setter
    def bytes_needed(self, value):
        self.args = *self.args[0:2], value, *self.args[4:]

    def __str__(self):
        return f"{self.args[0]}: keys=({', '.join(map(repr, self.keys))})"


class ChunkParams:
    def __init__(self, header: dict, limit: int, breakable: bool = False, try_dump_whole: bool = True,
                 str_chunk_min_len: Optional[int] = None):
        assert isinstance(header, dict)

        self.header = header
        self.limit = limit
        self.breakable = breakable
        self.try_dump_whole = try_dump_whole
        self.str_chunk_min_len = STR_CHUNK_MIN_LEN if str_chunk_min_len is None else str_chunk_min_len


def json_dumps(body: Any, *, chunking: Generator, **kwargs):
    """
    Splits the monolith `body` into several json-serialized chunks
    , each of length not bigger than `chunking.limit`.

    :param body: any json serializable
    :param chunking: must yield `ChunkParams`. Each iteration queries new chunk
                   , unless `yield` returns True, what means the same chunk repetition is requested.
    :param kwargs: passed to ujson.dumps()
    :raise JsonValueError` if `limit` provided is not enough for the longest chunk allocation
    :return:

    Examples:
        1. {'0': {'1': 1, '2': 2, '3': 3, '4': 4}}
           limit=29, header={"chunk": idx}

           '{"chunk":1,"0":{"1":1,"2":2}}'
           '{"chunk":2,"0":{"3":3,"4":4}}'

        2. {'0': {'1': {'2': {'3': 3,
                                  '33': {'4': {'5': {'6': 6,
                                                     '66': 66}}}}}}}
           limit=56, header={"chunk": idx}

           '{"chunk":1,"0":{"1":{"2":{"3":3}}}}'
           '{"chunk":2,"0":{"1":{"2":{"33":{"4":{"5":{"6":6}}}}}}}'
           '{"chunk":3,"0":{"1":{"2":{"33":{"4":{"5":{"66":66}}}}}}}'

        3. {'0': 'aaaaaaa'}
           limit=21, header={"chunk": idx}, str_chunk_min_len=3

           '{"chunk":1,"0":"aaa"}'
           '{"chunk":2,"0":"aaa"}'
           '{"chunk":3,"0":"a"}'

        4. {'0': [1, 1, 1, 1, 1, 1, 1]}
           limit=23, header={"chunk": idx}

           '{"chunk":1,"0":[1,1,1]}',
           '{"chunk":2,"0":[1,1,1]}',
           '{"chunk":3,"0":[1]}'

        5. {'0': {'1': 1, '22': 22}
           limit=23, header={"chunk": idx}

           raise JsonValueError("Value(2 bytes) cannot be allocated, increase chunk limit by 2: keys=('0', '22')")
           ex.keys - keys path to the entity, that could not be allocated. List of keys.
           ex.value - the value, that could not be allocated, referenced by the keys path.
    """

    if isinstance(body, dict):
        return json_dumps_dict(body, chunking=chunking, **kwargs)
    elif isinstance(body, (str, bytes)):
        return json_dumps_str(body, chunking=chunking, **kwargs)
    elif isinstance(body, Iterable):
        return json_dumps_array(body, chunking=chunking, **kwargs)
    else:
        return json_dumps_unbreakable(body, chunking=chunking, **kwargs)


def json_dumps_unbreakable(body: Any, *, chunking: Generator, **kwargs):
    arg = None
    rv = ujson.dumps(body, **kwargs)

    with closing(chunking), suppress(JsonStopChunking):
        while True:
            chunk_params = chunking.send(arg)
            arg = True

            if len(rv) > chunk_params.limit:
                if chunk_params.breakable:
                    yield None
                else:
                    raise JsonValueError(
                        f'Value({len(rv)} bytes) cannot be allocated'
                        f', increase chunk limit by {len(rv) - chunk_params.limit}',
                        keys=tuple(), value=body, bytes_needed=len(rv) - chunk_params.limit,
                    )
            else:
                return (yield rv)


def json_dumps_str(body: Union[str, bytes], *, chunking: Generator, **kwargs):
    rv = ujson.dumps(body, **kwargs)  # conversions may be performed

    def new_chunk(repeat: Optional[bool]):
        nonlocal chunk_params
        chunk_params = chunking.send(repeat)

    def request_space(amount):
        if chunk_params.breakable:
            yield None
            new_chunk(True)
        else:
            raise JsonValueError(
                f'Value({len(rv)} bytes) cannot be allocated'
                f', increase chunk limit by {amount}',
                keys=tuple(), value=body, bytes_needed=amount,
            )

    def dump_empty_body():
        while chunk_params.limit < 2:
            if chunk_params.breakable:
                yield None
                new_chunk(True)
            else:
                raise JsonValueError(
                    f'Value(2 bytes) cannot be allocated'
                    f', increase chunk limit by {2 - chunk_params.limit}',
                    keys=tuple(), value=body, bytes_needed=2 - chunk_params.limit,
                )

        yield '""'

    def breaks_escape_sequence(start, end):
        count = 0

        for idx in range(end - 1, start - 1, -1):
            if rv[idx] == '\\':
                count += 1
            else:
                break

        return bool(count % 2)

    with closing(chunking), suppress(JsonStopChunking):

        chunk_params = None
        new_chunk(None)

        if not body:
            return (yield from dump_empty_body())

        if len(rv) <= chunk_params.limit:
            return (yield rv)

        pos, rv_max = 1, len(rv) - 1
        while pos < rv_max:

            min_amount = min(rv_max - pos, chunk_params.str_chunk_min_len) + 2
            if chunk_params.limit < min_amount:
                yield from request_space(min_amount - chunk_params.limit)
            else:
                end = pos + min(rv_max - pos, chunk_params.limit - 2)
                if breaks_escape_sequence(pos, end):
                    end -= 1
                    if end == pos:
                        yield from request_space(1)
                        continue
                yield f'"{rv[pos:end]}"'
                new_chunk(False)
                pos = end


def json_dumps_array(body: Iterable, *, chunking: Generator, **kwargs):

    def new_chunk(repeat: Optional[bool]):
        nonlocal chunk, chunk_params, comma, chunk_just_started
        chunk_params = chunking.send(repeat)

        chunk = '['
        comma = ''
        chunk_just_started = True

    def add_to_chunk(value: Any):
        nonlocal chunk, comma, chunk_just_started

        if value is None:
            if chunk_just_started:
                if chunk_params.breakable:
                    yield None
                    new_chunk(True)
                else:
                    raise Exception('Chunk-break request received despite chunk is unbreakable')
            else:
                yield chunk + ']'
                new_chunk(False)

        else:
            chunk += comma + value
            comma = ','
            chunk_just_started = False

    def dump_empty_body():
        while chunk_params.limit < 2:
            if chunk_params.breakable:
                yield None
                new_chunk(True)
            else:
                raise JsonValueError(
                    f'Value(2 bytes) cannot be allocated'
                    f', increase chunk limit by {2 - chunk_params.limit}',
                    keys=tuple(), value=body, bytes_needed=2 - chunk_params.limit,
                )

        yield '[]'

    def subchunking():
        while True:
            params = copy.copy(chunk_params)
            params.header = {}
            params.limit = chunk_params.limit - len(chunk) - len(comma) - 1
            params.breakable = chunk_params.breakable or not chunk_just_started
            params.try_dump_whole = False
            yield params

    with closing(chunking), suppress(JsonStopChunking):

        chunk, chunk_params, comma, chunk_just_started = [None] * 4
        new_chunk(None)

        if not body:
            return (yield from dump_empty_body())

        if chunk_params.try_dump_whole:
            # performance optimization
            rv = ujson.dumps(body, **kwargs)
            if len(rv) <= chunk_params.limit:
                return (yield rv)

        for idx, value in enumerate(body):
            try:

                for v in json_dumps(value, chunking=subchunking(), **kwargs):
                    yield from add_to_chunk(v)

            except JsonValueError as e:
                e.keys = ([idx], *e.keys)
                raise e

        yield chunk + ']'


def json_dumps_dict(body: dict, *, chunking: Generator, **kwargs):

    def new_chunk(repeat: Optional[bool]):
        nonlocal chunk, chunk_params, comma, chunk_just_started
        chunk_params = chunking.send(repeat)

        chunk = ujson.dumps(chunk_params.header, **kwargs)[:-1]  # cut off trailing '}'
        comma = ',' if chunk_params.header else ''
        chunk_just_started = True

        while len(chunk) + 1 > chunk_params.limit:
            if chunk_params.breakable:
                yield None
                chunk_params = chunking.send(True)
            else:
                raise JsonValueError(
                    f'Chunk Header({len(chunk) + 1} bytes) cannot be allocated'
                    f', increase chunk limit by {len(chunk) + 1 - chunk_params.limit}',
                    keys=tuple(), value=chunk_params.header, bytes_needed=len(chunk) + 1 - chunk_params.limit,
                )

    def add_to_chunk(key: Any, value: Any):
        nonlocal chunk, comma, chunk_just_started

        if value is None:
            if chunk_just_started:
                if chunk_params.breakable:
                    yield None
                    yield from new_chunk(True)
                else:
                    raise Exception('Chunk-break request received despite chunk is unbreakable')
            else:
                yield chunk + '}'
                yield from new_chunk(False)

        else:
            chunk += comma + key + value
            comma = ','
            chunk_just_started = False

    def dump_empty_body():
        while chunk_params.limit < len(chunk) + 1:
            if chunk_params.breakable:
                yield None
                yield from new_chunk(True)
            else:
                raise JsonValueError(
                    f'Value({len(chunk) + 1} bytes) cannot be allocated'
                    f', increase chunk limit by {2 - chunk_params.limit}',
                    keys=tuple(), value=body, bytes_needed=2 - chunk_params.limit,
                )

        yield chunk + '}'

    def subchunking():
        while True:
            params = copy.copy(chunk_params)
            params.header = {}
            params.limit = chunk_params.limit - len(chunk) - len(comma) - len(k) - 1
            params.breakable = chunk_params.breakable or not chunk_just_started
            params.try_dump_whole = False
            yield params

    with closing(chunking), suppress(JsonStopChunking):

        chunk, chunk_params, comma, chunk_just_started = [None] * 4
        yield from new_chunk(None)

        if not body:
            return (yield from dump_empty_body())

        if chunk_params.try_dump_whole:
            # performance optimization
            rv = ujson.dumps({**chunk_params.header, **body}, **kwargs)
            if len(rv) <= chunk_params.limit or not body:
                return (yield rv)

        for key, value in body.items():
            k = ujson.dumps({key: 0}, **kwargs)  # Special Case: {1: 1} -> {"1": 1}
            k = k[1:-2]  # {"key": 0} -> "key":

            try:

                for v in json_dumps(value, chunking=subchunking(), **kwargs):
                    yield from add_to_chunk(k, v)

            except JsonValueError as e:
                e.keys = (key, *e.keys)
                raise e

        yield chunk + '}'
