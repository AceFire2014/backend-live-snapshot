import logging
import sys
import traceback
from datetime import datetime
from itertools import count
from logging import Formatter, StreamHandler
from typing import Any, Callable, Dict, Optional, Collection

import ujson

from common.json_chunking import json_dumps, ChunkParams, JsonStopChunking

log = logging.getLogger(__name__)


class JsonDict:
    __slots__ = 'data',

    def __init__(self, data):
        self.data = data

    def __json__(self):
        return ujson.dumps({jsonable(k): jsonable(v) for k, v in self.data.items()}, reject_bytes=False)


class JsonCollection:
    __slots__ = 'data',

    def __init__(self, data):
        self.data = data

    def __json__(self):
        return ujson.dumps(tuple(jsonable(x) for x in self.data), reject_bytes=False)


class JsonDatetime:
    __slots__ = 'data',

    def __init__(self, data):
        self.data = data

    def __json__(self):
        return '"%s"' % self.data.isoformat()


def jsonable(data):
    if type(data) in (type(None), bool, int, float, str, bytes):
        return data
    if isinstance(data, dict):
        return JsonDict(data)
    if isinstance(data, Collection):
        return JsonCollection(data)
    if isinstance(data, datetime):
        return JsonDatetime(data)
    return str(data)


def mask_sensitive_data(data: Any):
    def is_sensitive(key):
        return isinstance(key, str) and any((word in key.upper() for word in ('PASSWORD', 'SECRET')))

    if isinstance(data, dict):
        return data.__class__({k: f'{type(v).__name__}(*****)' if is_sensitive(k) else mask_sensitive_data(v)
                               for k, v in data.items()})
    elif isinstance(data, (tuple, list)):
        return tuple((mask_sensitive_data(item) for item in data))
    else:
        return data


def lower_than(level: str) -> Callable:
    levelno = logging._checkLevel(level)

    def action(record) -> bool:
        return record.levelno < levelno

    return action


def uwsgi_filter(level: str) -> Callable:
    levelno = logging._checkLevel(level)

    def action(record) -> bool:
        record.msg = record.msg.rstrip('\r\n')
        # Examples:
        # WARNING Stream for pwsid=473788422_16843 is stopped
        # ERROR ... (HTTP/1.0 404)

        # ERROR Failed GET request to https://adultfriendfinder.com//messages/send.
        # Not enough points
        # ERROR ... (HTTP/1.0 403)

        # ERROR /bcast/api/broadcasts - Token is no longer valid.
        # ERROR ... (HTTP/1.0 401)

        # ERROR Received malformed log records from UI: {'log_records': {0: {'text': ['Not a valid string.']}}}.
        # ERROR ... (HTTP/1.0 400)

        # WARNING Cams raised error: 400 Client Error: Bad Request for url: http://.../internal/show-type/consultantffn
        # ERROR ... (HTTP/1.0 400)
        status_code = int(record.msg[-4:-1])  # (HTTP/1.1 200)
        allowed_4xx = [400, 401, 403, 404]
        record.levelno = logging.ERROR if status_code >= 400 and status_code not in allowed_4xx else logging.DEBUG
        record.levelname = logging.getLevelName(record.levelno)

        return record.levelno >= levelno

    return action


def log_stdout_stderr(logger):
    class Stream:
        def __init__(self, level, last_resort):
            self.level = level
            self.last_resort = last_resort
            self._recursive_call = False

        def write(self, msg: str):
            if self._recursive_call:
                self.last_resort.write(msg)

            elif msg not in ('', '\n'):
                try:
                    self._recursive_call = True

                    lines = msg.splitlines()
                    logger.log(self.level, lines[0], extra={'data': '\n'.join(lines[1:])})
                finally:
                    self._recursive_call = False

        def flush(self):
            self.last_resort.flush()

    logging.lastResort = logging.StreamHandler(sys.stderr)
    logging.lastResort.level = logging.WARNING

    sys.stdout = Stream(logging.INFO, sys.stdout)
    sys.stderr = Stream(logging.WARNING, sys.stderr)


class ForwardingFormatter(Formatter):
    KEY = 'target_formatter'

    def __init__(self,
                 formatters: Dict[str, Formatter],
                 default: str = 'default',
                 apply: Callable = None,
                 mask_sensitive_data: bool = True):

        super().__init__()
        assert default in formatters, f"default formatter '{default}' is missing"
        self._formatters = formatters
        self._default = default
        self._apply = apply
        self._mask_sensitive_data = mask_sensitive_data

    @classmethod
    def forward_log_record(cls, target_formatter: str, extra: Dict) -> Dict:
        return {**extra, cls.KEY: target_formatter}

    def _get_formatter(self, record: logging.LogRecord) -> Formatter:
        if self._apply:
            self._apply(record)

        formatter_name = getattr(record, self.KEY, self._default)

        try:
            return self._formatters[formatter_name]
        except KeyError:
            log.debug(f"Cannot find '{formatter_name}' formatter.")
            return self._formatters[self._default]

    def formatTime(self, record, datefmt=None) -> str:
        if self._mask_sensitive_data:
            record.__dict__.update(mask_sensitive_data(record.__dict__))

        formatter = self._get_formatter(record)
        return formatter.formatTime(record, datefmt=datefmt)

    def formatMessage(self, record) -> str:
        if self._mask_sensitive_data:
            record.__dict__.update(mask_sensitive_data(record.__dict__))

        formatter = self._get_formatter(record)
        return formatter.formatMessage(record)

    def format(self, record) -> str:
        if self._mask_sensitive_data:
            record.__dict__.update(mask_sensitive_data(record.__dict__))

        formatter = self._get_formatter(record)
        return formatter.format(record)


class LogDNAFormatter(logging.Formatter):

    exclude_fields = frozenset(dir(logging.LogRecord(
        name='name', level='INFO', pathname='pathname', lineno=0, msg='msg', args=[], exc_info=None
    )))

    def __init__(self, *args,
                 environment: str,
                 app_name: str,
                 location: str,
                 max_chunk_size: int,
                 caller: Optional[str] = None,
                 record_caption_max_length: int = 300,
                 record_caption_max_lines_number: int = 1,
                 record_chunk_max_count: int = 5,
                 **kwargs):

        super(LogDNAFormatter, self).__init__(*args, **kwargs)
        self.environment = environment
        self.app_name = app_name
        self.location = location
        self.caller = caller
        self.max_chunk_size = max_chunk_size
        self.record_caption_max_length = record_caption_max_length
        self.record_caption_max_lines_number = record_caption_max_lines_number
        self.record_chunk_max_count = record_chunk_max_count

    @classmethod
    def format_exception(cls, exc_info):
        return "".join(traceback.format_exception(*exc_info)) if exc_info else ""

    def get_caller(self, record):
        if self.caller:
            return self.caller

        return self.location % record.__dict__

    def format(self, record):
        json_log_object = {}

        if record.exc_info:
            json_log_object["stacktrace"] = self.format_exception(record.exc_info)

        for each in record.__dict__.keys():
            if each not in self.exclude_fields:
                json_log_object[each] = getattr(record, each)

        message = record.getMessage()

        record_caption_max_lines_number = json_log_object.get('record_caption_max_lines_number',
                                                              self.record_caption_max_lines_number)

        message_lines = message.splitlines()
        if len(message_lines) > record_caption_max_lines_number:
            json_log_object['message_original'] = message
            message = message_lines[0]

        if len(message) > self.record_caption_max_length:
            json_log_object.setdefault('message_original', message)
            message = message[:self.record_caption_max_length] + '...'

        def chunking():
            chunks_limit = json_log_object.get('chunks_limit', self.record_chunk_max_count)

            for idx in count(1):
                if idx > chunks_limit:
                    raise JsonStopChunking(chunks_limit)

                params = ChunkParams(
                    header={
                        'timestamp': datetime.utcnow().isoformat(),
                        'environment': self.environment,
                        'app': self.app_name,
                        'caller': self.get_caller(record),
                        'level': record.levelname,
                        'message': message if idx == 1 else f'Chunk #{idx}: {message}',
                        'chunk': idx,
                        'chunks_limit': chunks_limit,
                    },
                    limit=self.max_chunk_size,
                )

                while (yield params):
                    pass

        return '\n'.join(json_dumps(json_log_object, chunking=chunking(), reject_bytes=False))


class MultipartStreamHandler(StreamHandler):

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            for part in msg.splitlines():
                stream.write(part)
                stream.write(self.terminator * 2)
            self.flush()
        except Exception:
            self.handleError(record)
