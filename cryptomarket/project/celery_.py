"""
cryptomarket/project/celery_.py
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from cryptomarket.project import celeryconfig
from cryptomarket.project.settings.settings_env import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
)

celery_deribit = Celery(
    __name__,
    broker=f"{CELERY_BROKER_URL}",
    backend=f"{CELERY_RESULT_BACKEND}",
    include=[
        "cryptomarket.tasks.celery.task_add_every_60_seconds",
        "cryptomarket.tasks.celery.task_send_every_60_seconds"
    ],
)
celery_deribit.config_from_object(celeryconfig)

celery_deribit.conf.task_queues = (
    Queue("default", Exchange("default"), routing_key="task.#"),
    Queue("high", Exchange("high"), routing_key="high.#"),
    Queue("beat", Exchange("beat"), routing_key="beat.#"),
    Queue("low", Exchange("low"), routing_key="low.#"),
    Queue("celery"),
)
celery_deribit.conf.task_default_queue = "default"
celery_deribit.conf.task_default_exchange = "high"
celery_deribit.conf.task_default_routing_key = "task.default"
#
celery_deribit.conf.beat_schedule = {
    "add-every-60-seconds": {
        "task": "cryptomarket.tasks.celery.task_add_every_60_seconds.task_celery_monitoring_currency",
        "schedule": 45,  # receiving data from the deribit server.
        "options": {
            "queue": "high",
            "routing_key": "high.priority",
            "expires": 60,
        },
    },
    "postman-every-60-seconds": {
        "task": "cryptomarket.tasks.celery.task_send_every_60_seconds.task_celery_postman_currency",
        "schedule": crontab(minute="*/1"),  # Send data (received above ) by SSE.
        "options": {
            "queue": "default",
            "routing_key": "task.default",
            "expires": 40,
        },
    },
}
