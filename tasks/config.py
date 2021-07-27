from common.common_config import *

CONFIG_MODULE = 'Env'
ENV_CONFIG_VAR_PREFIX = ''

COMMIT_ID = ''

APP_NAME = "CD.Thumbnail.BE.tasks"
MODE = 'prod'  # 'dev'

LOG_LEVEL_TASKS = 'INFO'
LOG_LEVEL_LIBS = 'WARNING'
LOG_TARGET = 'logDNA'  # stdout
LOG_CONFIG = '..config_log'
LOG_DNA_RECORD_CHUNK_MAX_LENGTH = 8 * 1024
LOG_DNA_RECORD_CHUNKS_MAX_COUNT = 5
LOG_DNA_RECORD_CAPTION_MAX_LENGTH = 500

REDIS_BUS = 'rediscluster.RedisCluster'  # 'redis.Redis'
AREDIS_BUS = 'aredis.StrictRedisCluster'  # 'aredis.StrictRedis'

AMQP_URL = 'amqp://guest:{}@127.0.0.1:5672'
AMQP_PASSWORD = 'guest'

CELERY_BROKER_BUS = 'AMQP_BROKER'  # 'REDIS_BROKER'
CELERY_BACKEND_BUS = 'AMQP_BACKEND'  # 'REDIS_BACKEND'

CAMS_URL = 'https://beta-api.cams.com'
PREVIEW_VIDEO_UPDATE_PERIOD = 15  # 60 * 10  # todo: change to correct period
PREVIEW_VIDEO_STORAGE_PATH = '/var/storage/videos/preview/mp4'
PREVIEW_VIDEO_TASK_CHUNK_SIZE = 10
PREVIEW_VIDEO_TASK_COUNTDOWN_MULTIPLIER = 3
PREVIEW_VIDEO_FILE_SIZE_THRESHOLD = 100 * 1024  # bytes
PREVIEW_VIDEO_EXPIRE_PERIOD = 60 * 60 * 24
PREVIEW_VIDEO_CLEAN_PERIOD = 30  # 60 * 60 * 24

try:
    from tasks.local_config import *
except ImportError:
    pass
