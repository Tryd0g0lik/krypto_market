"""
cryptomarket/tasks/queues/task_account_user.py
"""

import asyncio
import json
import logging
from contextvars import ContextVar
from datetime import datetime

from cryptomarket.project.functions import str_to_json
from cryptomarket.type import DeribitClient, Person

log = logging.getLogger(__name__)
lock = asyncio.Lock()


async def task_account(*args, **kwargs) -> bool:
    from cryptomarket.project.app import manager

    log_t = "[%s.%s]:" % (
        __name__.split(".")[-1],
        task_account.__name__,
    )
    dataVar = ContextVar("data_srt", default="")
    dataVar_token = None
    # ===============================
    # ---- RECEIVE THE REBIT CLIENT
    # ===============================
    _deque_coroutines = manager._deque_coroutines

    coroutine = _deque_coroutines.popleft()
    client: DeribitClient = await list(coroutine.values())[0]
    # ===============================
    # ---- QUEUE OF KEYS
    # ===============================
    queue_keys = manager.queue  # list of keys
    person_manager = manager.person_manager
    sse_manager = manager.sse_manager
    context_redis_connection = (
        manager.rate_limit.context_redis_connection
    )  # coroutine of the redis asynccontextmanager

    # ============= 1/2 ==================
    # ---- CACHE - RECEIVE THE USER DATA (classic a user data)
    # ===============================

    try:
        size = queue_keys.qsize()
        if size is not None and size == 0:
            return False
        async with context_redis_connection() as redis:
            key_of_queue = await queue_keys.get()

            data_str: str = await redis.get(key_of_queue)
            dataVar_token = dataVar.set(data_str)
            dataVar.set(data_str)

    except Exception as e:
        log.error("%s RedisError => %s" % (log_t, e.args[0] if e.args else str(e)))
        return False
    lock_ = asyncio.Lock()

    async with lock_:
        # ===============================
        # ---- STR TO JSON
        # ===============================
        data_str = dataVar.get()
        user_meta_json = str_to_json(data_str)
        del data_str
        # del dataVar
        dataVar.reset(dataVar_token)
        user_id = user_meta_json.get("user_id")
        person_dict = person_manager.person_dict
        if not person_dict.__has__(user_id):
            return False

        person: Person = person_dict.get(user_id)
        person.last_activity = datetime.now().timestamp()
        if not person:
            pass
        else:
            request_id = user_meta_json.get("index")
            data_json = person.get_subaccount_data(request_id)
            dataVar.set(json.dumps(data_json))

        data_json = json.loads(dataVar.get())
        del dataVar
        person.client = client
        try:
            # ===============================
            # RESPONSE / MASSAGE
            # ===============================
            await person.ws_json(data_json)
            if person.msg is None:
                return False
            msg = person.msg
            result_kwargs_new: dict = {**msg}
            result_kwargs_new.__setitem__("user_meta", user_meta_json)

            await sse_manager.broadcast(result_kwargs_new)
            return True
        except Exception as e:
            log.error("%s Error => %s" % (log_t, e.args[0] if e.args else str(e)))
            person.active = False
            return False
