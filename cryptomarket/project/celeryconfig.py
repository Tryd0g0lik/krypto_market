"""
cryptomarket/project/celeryconfig.py:4

broker_url = < Look to the 'cryptomarket/project/settings/settings_env.py' >
result_backend = < Look to the 'cryptomarket/project/settings/settings_env.py' >
"""

from celery.worker.control import pool_grow

from cryptomarket.database.connection import log
from cryptomarket.project.settings.settings_env import REDIS_MASTER_NAME, REDIS_PASSWORD

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "Asia/Krasnoyarsk"
enable_utc = True

# Перезапуск пула при ошибках
poolrestart = True
time_limit = 600


# celery speed for handle of tasks
# task_annotations = {
#     'one_tasks.celery_task_money': {'rate_limit': '10/m'}
# }

# THe True when need the sync
# task_always_eager = False
worker_redirect_stdouts = False
worker_redirect_stdouts_level = "INFO"
# quantity of workers
worker_concurrency = 2
worker_prefetch_multiplier = 1

# Redis
broker_transport_options = {
    "master_name": str(REDIS_MASTER_NAME),
    "sentinel_kwargs": {"password": str(REDIS_PASSWORD)},
}
