"""
cryptomarket/tasks/queues/task_grate_user.py

TODO Задача, где после аутентификации создаём пользователя
"""

import asyncio
import json
import logging

log = logging.getLogger(__name__)


async def task_grate_person(*args, **kwargs) -> None:
    from cryptomarket.deribit_client import Person
