"""
cryptomarket/project/celery_.py
"""

from celery import Celery

from cryptomarket.project import celeryconfig
from cryptomarket.project.settings.settings_env import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
)

celery_deribit = Celery(
    __name__, broker=f"{CELERY_BROKER_URL}", backend=f"{CELERY_RESULT_BACKEND}"
)
celery_deribit.config_from_object(celeryconfig)
celery_deribit.conf.beat_schedule = {
    "add-avery-60-seconds": {
        "task": "cryptomarket.tasks.celery.add_avery_60_seconds",  # monitoring an external server of Deribit.
        "schedule": 60.0,
    }
}
