import logging.config

from common.config import config, config_as_dict, load_logging_config
from common.logging import log_stdout_stderr
from tasks import celery_app


logging.config.dictConfig(load_logging_config())

log = logging.getLogger(__name__)
log_stdout_stderr(log)
log.info('Starting with config parameters.', extra={'data': config_as_dict(config)})


CELERYBEAT_SCHEDULE = {
    'make_all_preview_videos': {
        'task': 'tasks.tasks.make_all_preview_videos',
        'schedule': config.PREVIEW_VIDEO_UPDATE_PERIOD
    },
    'cleanup_preview_videos': {
        'task': 'tasks.tasks.cleanup_preview_videos',
        'schedule': config.PREVIEW_VIDEO_CLEAN_PERIOD
    },
}


celery_app.conf.update(
        CELERYBEAT_SCHEDULE=CELERYBEAT_SCHEDULE,
)
