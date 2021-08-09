from celery import Celery
from celery.signals import setup_logging

from common.config import config, load_class

AMQP_BROKER = config.AMQP_URL.format(config.AMQP_PASSWORD)
# Task result can only be retrieved once, and only by the client that initiated the task.
# Two different processes can’t wait for the same result.
# https://docs.celeryproject.org/en/stable/userguide/tasks.html#rpc-result-backend-rabbitmq-qpid
AMQP_BACKEND = 'rpc://'


@setup_logging.connect
def disable_standard_celery_logging(*args, **kwargs):
    pass


celery_app = Celery('preview_thumbnail',
                    broker=load_class(config.CELERY_BROKER_BUS),
                    backend=load_class(config.CELERY_BACKEND_BUS),
                    include=['tasks.tasks'])
celery_app.config_from_object('tasks.settings')
