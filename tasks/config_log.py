import ujson

from common.config import config

if config.LOG_TARGET.lower() == 'logDNA'.lower():
    stream_handler_class = {'()': 'common.logging.MultipartStreamHandler'}
    formatters = {
        'logDNA': {
            '()': 'common.logging.LogDNAFormatter',
            'environment': config.MODE,
            'app_name': config.APP_NAME,
            'max_chunk_size': config.LOG_DNA_RECORD_CHUNK_MAX_LENGTH,
            'record_caption_max_length': config.LOG_DNA_RECORD_CAPTION_MAX_LENGTH,
            'record_caption_max_lines_number': 1,
            'record_chunk_max_count': config.LOG_DNA_RECORD_CHUNKS_MAX_COUNT,
            'location': '%(name)s:%(funcName)s() %(pathname)s:%(lineno)d',
        },
        'switch': {
            '()': 'common.logging.ForwardingFormatter',
            'formatters': 'cfg://formatters',
            'default': 'logDNA',
            'mask_sensitive_data': True,
        },
    }

else:
    stream_handler_class = {'class': 'logging.StreamHandler'}
    formatters = {
        'string': {
            'class': 'logging.Formatter',
            'format': '%(asctime)s [%(filename)s:%(lineno)d %(name)s:%(funcName)s() %(levelname)s] '
                      '%(message)s%(opt_data)s',
        },
        'switch': {
            '()': 'common.logging.ForwardingFormatter',
            'formatters': 'cfg://formatters',
            'default': 'string',
            'mask_sensitive_data': True,
            'apply': lambda record: (
                setattr(record, 'opt_data', f'\n{ujson.dumps(record.data, indent=2, reject_bytes=False)}'
                                            if hasattr(record, 'data') else ''),
            ),
        },
    }

LOG_CONFIG = {
    'version': 1,
    'formatters': formatters,
    'filters': {
        'lower_than_ERROR': {
            '()': 'common.logging.lower_than',
            'level': 'ERROR',
        },
    },
    'handlers': {
        'stdout': {
            **stream_handler_class,
            'formatter': 'switch',
            'filters': ['lower_than_ERROR'],
            'stream': 'ext://sys.stdout',
        },
        'stderr': {
            **stream_handler_class,
            'formatter': 'switch',
            'level': 'ERROR',
            'stream': 'ext://sys.stderr',
        },
    },
    'loggers': {
        'tasks': {
            'level': config.LOG_LEVEL_TASKS,
            'handlers': ['stdout', 'stderr'],
            'propagate': False,
        },
        'common': {
            'level': config.LOG_LEVEL_TASKS,
            'handlers': ['stdout', 'stderr'],
            'propagate': False,
        },
        'backoff': {
            'level': config.LOG_LEVEL_TASKS,
            'handlers': [],
            'propagate': False,
        },
    },
    'root': {
        'level': config.LOG_LEVEL_LIBS,
        'handlers': ['stdout', 'stderr'],
    }
}
