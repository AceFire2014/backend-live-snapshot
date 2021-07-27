from kombu import Exchange, Queue

from common.celery.enums import Priority

task_default_queue = 'priority_celery'
task_default_priority = Priority.MID.value
task_queues = (
    Queue('priority_celery', Exchange('priority_celery'), routing_key='priority_celery',
          queue_arguments={'x-max-priority': 10}),
)
