"""
cryptomarket/tasks/queues/task_account_user.py
"""

import asyncio
import json
import logging
from contextvars import ContextVar
from datetime import datetime

from cryptomarket.project.functions import (
    str_to_json,
    string_to_seconds,
    wrapper_delayed_task,
)
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
    # sse_manager = manager.sse_manager
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
    # lock_ = asyncio.Lock()

    # async with lock_:
    # ===============================
    # ---- STR TO JSON
    # ===============================
    data_str = dataVar.get()
    user_meta_json = str_to_json(data_str)
    del data_str
    dataVar.reset(dataVar_token)
    user_id = user_meta_json.get("user_id")
    person_dict = person_manager.person_dict
    if not person_dict.__has__(user_id):
        return False
    # ===============================
    # ---- PERSON RECEIVE
    # ===============================
    person: Person = person_dict.get(user_id)
    person.last_activity = datetime.now().timestamp()

    request_id = user_meta_json.get("index")
    method = user_meta_json.get("method")
    # ===============================
    # ---- PERSON CREATE DATA FOR QUERY
    # ===============================
    data_json = person.get_subaccount_data(request_id)
    data_json["params"] = {}
    tickers = user_meta_json.get("tickers")
    data_json["params"].__setitem__("index_name", tickers)
    data_json.__setitem__("method", method)
    if method == "public/get_tradingview_chart_data":
        ticker: str | None = tickers.split("_")[0]
        currency_atr: list | None = (
            person.SUPPORTED_CURRENCIES.get(ticker.upper())
            if ticker is not None
            else "SOL"
        )
        data_json["params"].__setitem__("currency", str(ticker.upper()))
        data_json["params"].__setitem__("instrument_name", currency_atr[0])
        data_json["params"].__setitem__("start_timestamp", currency_atr[0])
        # Dates to seconds
        dates = json.loads(user_meta_json.get("dates"))
        date_k = (dates.keys())[0]
        date_v = (dates.values())[0]
        data_json["params"].__setitem__(
            "end_timestamp", float(date_k) if date_k is not None else 0.0
        )
        data_json["params"].__setitem__(
            "resolution", float(date_v) if date_v is not None else 0.0
        )
    del dataVar
    person.client = client if person.client is None else person.client
    try:
        # ===============================
        # RESPONSE / MASSAGE / LOOP / THREADING.THREAD
        # ===============================
        ws_json = person.ws_json
        user_meta_json.__setitem__("request_data", data_json)

        wrapper_delayed = wrapper_delayed_task(callback_=None, asynccallback_=ws_json)
        await wrapper_delayed([], **user_meta_json)
        return True
    except Exception as e:
        log.error("%s Error => %s" % (log_t, e.args[0] if e.args else str(e)))
        person.active = False
        return False
