"""
cryptomarket/tasks/queues/task_account_user.py
"""

import asyncio
import json
import logging
from contextvars import ContextVar
from datetime import datetime

from cryptomarket.project.enums import RadisKeysEnum
from cryptomarket.project.functions import (
    str_to_json,
    update_person_manual,
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
    # ---- RECEIVE THE REBIT CLIENT FOR CONNECTION
    # ===============================
    _deque_coroutines = manager.deque_coroutines
    coroutine = _deque_coroutines.popleft()
    client: DeribitClient = await list(coroutine.values())[0]
    # ===============================
    # ---- COMMON QUEUE OF KEYS (THEY FROM THE USER META DATA (str/json)
    # ===============================
    queue_keys = manager.queue  # list of keys
    person_manager = manager.person_manager

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

    async with lock:
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
        try:
            # ===============================
            # RESPONSE / MASSAGE / LOOP / THREADING.THREAD
            # ===============================
            person_manager.client = client if person.client is None else person.client
            async with person_manager.ws_json() as ws:
                try:
                    while person.active:
                        request_id = user_meta_json.get("index")
                        method = user_meta_json.get("method")
                        # ===============================
                        # ---- PERSON CREATE DATA FOR PERSON's QUERY
                        # ===============================
                        # data_json = person_manager.get_subaccount_data(request_id, person.access_token)
                        data_json = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                        }
                        data_json["method"] = method
                        data_json["params"] = {}
                        tickers = user_meta_json.get("tickers")
                        data_json["params"].__setitem__("index_name", tickers)
                        data_json.__setitem__("method", method)
                        user_meta_json.__setitem__("request_data", data_json)
                        # ----
                        auth_data = await update_person_manual(
                            person, **{"user_meta_json": user_meta_json}
                        )
                        await asyncio.wait_for(ws.send_json(auth_data), 7)
                        msg_data = await person_manager.safe_receive_json(ws)
                        if (
                            "error" not in msg_data.keys()
                            and person.access_token is None
                        ):
                            person.access_token = msg_data["result"]["access_token"]
                            person.refresh_token = msg_data["result"]["refresh_token"]
                            person.expires_in = msg_data["result"]["expires_in"]
                            person.scope = msg_data["result"]["scope"]
                            person.token_type = msg_data["result"]["token_type"]
                            continue
                        else:

                            person.access_token = None
                            person.refresh_token = None

                        # ===============================
                        # ---- SEND DATA IN THE USE QUEUE
                        # ===============================
                        if (
                            msg_data is not None
                            and "error" not in msg_data
                            and len(msg_data) > 0
                        ):
                            result_kwargs_new: dict = {**msg_data}
                            result_kwargs_new.__setitem__("user_meta", user_meta_json)
                            # ----
                            person.email = msg_data["result"][0]["email"]
                            person.username = msg_data["result"][0]["email"]
                            person.is_password = msg_data["result"][0]["is_password"]
                            person.system_name = msg_data["result"][0]["system_name"]

                            # ============= 2/2 ==================
                            # ---- CACHE - RECEIVE THE USER DATA (classic a user data)
                            # ===============================
                            try:
                                key = (
                                    RadisKeysEnum.DERIBIT_PERSON_RESULT.value
                                    % person.person_id
                                )
                                serialize_ = {
                                    k: v
                                    for k, v in person.__dict__.items()
                                    if not k.startswith("_") and "token" not in k
                                }
                                async with context_redis_connection() as redis:
                                    result_cache = await redis.get("deribit:person")
                                    data_for_cache = {}
                                    if result_cache is None:
                                        # This we don't found the key "deribit:person"
                                        data_for_cache = {key: serialize_}
                                    else:
                                        # This we found the key "deribit:person"
                                        data_for_cache: dict = json.loads(result_cache)
                                        data_for_cache.update(serialize_)

                                    await redis.setex(
                                        "deribit:person",
                                        27 * 60 * 60,
                                        json.dumps(data_for_cache),
                                    )
                            except Exception as e:
                                log.error(
                                    "%s RedisError => %s"
                                    % (log_t, e.args[0] if e.args else str(e))
                                )
                                return False
                            return True

                except Exception as e:
                    log.error(
                        "%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e))
                    )
                    return False
                finally:
                    person.refresh_token = None
                    person.access_token = None
                    # manager.person_manager.person_dict.__setitem__(person.person_id, person)

        except Exception as e:
            log.error("%s Error => %s" % (log_t, e.args[0] if e.args else str(e)))
            person.active = False
