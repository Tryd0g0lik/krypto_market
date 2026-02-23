"""
cryptomarket/project/functions.py
"""

import asyncio
import json
import logging
import pickle
import threading
from datetime import datetime, timedelta
from idlelib.autocomplete import TRY_A
from typing import Any, Coroutine

from aiohttp import ClientWebSocketResponse, client_ws
from fastapi import (
    Request,
)
from redis import Redis

from cryptomarket.project.settings.core import DEBUG, settings
from cryptomarket.type import Person
from cryptomarket.type.db import DatabaseConnection
from cryptomarket.type.deribit_type import EncryptManagerBase

log = logging.getLogger(__name__)


# ===============================
# ---- RAM 'tracemalloc'
# ===============================
def get_memory_size(tracemalloc):
    import linecache

    log.info("=== MEMORY SNAPSHOT FROM sse_monitoring ===")
    snapshot = tracemalloc.take_snapshot()
    statistics = snapshot.statistics("lineno")[:30]
    [print(stat) for stat in statistics]
    [log.info(f"DEBUG RAM {stat}") for stat in statistics]
    statistics = [stat for stat in statistics if "None" not in str(stat)]
    log.info("-------------------")
    for index, stat in enumerate(statistics[:10], 1):
        frame = stat.traceback[0]
        filename = frame.filename
        lineno = frame.lineno
        line = linecache.getline(filename, lineno).strip()
        log.info(f"DEBUG RAM #{index}: {filename}:{lineno}: {line}")
        log.info(f"DEBUG RAM size={stat.size / 1024:.1f} KB, count={stat.count}")
    log.info("-------------------")
    other = statistics[10:]
    if other:
        size = sum(stat.size for stat in other)
        count = sum(stat.count for stat in other)
        log.info(
            f"... and {len(other)} others: size={size / 1024:.1f} KB, count={count}"
        )
    log.info("--------- END ----------")


# ===============================
# ---- ASНNCIO DEBUG
# ===============================
def run_asyncio_debug(loop, maxtimesize=0.08):
    loop.set_debug(DEBUG)
    loop.slow_callback_duration = maxtimesize
    tasks = asyncio.all_tasks(loop)
    log.info(f"Активных задач: {len(tasks)}")
    for task in tasks:
        log.info(
            f"Задача: {task.get_name()}, Статус: {task.done()}, Отменена: {task.cancelled()}"
        )
        if not task.done():
            task.print_stack()


# ===============================
# ---- CREATE THE ONE/TEMPLATE TASK
# ===============================
def run_async_worker(callback_, *args, **kwargs):
    """
    :param callback_: This is your function is handler of data.
    :param args:
    :param kwargs:
    :return:
    """
    loop = asyncio.new_event_loop()
    run_asyncio_debug(loop)
    # loop.set_debug(True)
    # loop.slow_callback_duration = 0.08
    asyncio.set_event_loop(loop)
    try:
        # if args and kwargs:
        return loop.run_until_complete(callback_(*args, **kwargs))
    except Exception as e:
        log.error(e.args[0] if e.args else str(e))
    finally:
        loop.close()


def run_sync_worker(callback_, *args, **kwargs):
    """
    :param callback_: This is your function is handler of data.
    :param args:
    :param kwargs:
    :return:
    """
    loop = asyncio.new_event_loop()
    run_asyncio_debug(loop)
    # loop.set_debug(True)
    # loop.slow_callback_duration = 0.08
    asyncio.set_event_loop(loop)
    try:
        # if args and kwargs:
        return loop.run_in_executor(None, lambda: callback_(*args, **kwargs))

    except Exception as e:
        log.error(e.args[0] if e.args else str(e))

    finally:
        loop.close()


def wrapper_delayed_task(
    callback_=None,
    asynccallback_=None,
    delay_seconds: int = 0.2,
):
    """Running handle of tasks. This is else one a worker."""
    livetime_ = 5

    async def delayed_task(*args, **kwargs):
        await asyncio.sleep(delay_seconds)
        try:
            """
            This code is opening a 'door' in the new flow/pool for an async (or a sync) function with new loop.
            The timeout (or deadline or expect) is the 5 second after start. \
            This function  (the 'asynccallback_' name or 'callback_')accept other (else one)\
             the async ( or the sync) function on the entry-point and '**kwargs'.
            """
            if asynccallback_ is not None:
                async with asyncio.Lock():
                    threading_result = threading.Thread(
                        target=lambda: run_async_worker(
                            asynccallback_, *args, **kwargs
                        ),
                        daemon=True,
                    )
                    threading_result.start()
                    threading_result.join(timeout=livetime_)

                    if not threading_result.daemon:
                        log.error(
                            """[%s]: Signal ThreadError => %s deos not found! """
                            % (
                                delayed_task.__name__,
                                threading_result.name,
                            )
                        )
                    pass
            elif callback_ is not None:
                async with asyncio.Lock():
                    threading_result = threading.Thread(
                        target=lambda: run_sync_worker(callback_, *args, **kwargs),
                        daemon=True,
                    )
                    threading_result.start()
                    threading_result.join(timeout=7)
                    if not threading_result.daemon:
                        log.error(
                            """[%s]: Signal ThreadError => %s deos not found! """
                            % (
                                delayed_task.__name__,
                                threading_result.name,
                            )
                        )
            else:
                log_t = (
                    """[%s]: Signal ValueError => Callback deos not found! """
                    % delayed_task.__name__
                )
                log.error(log_t)
                raise ValueError(log_t)
        except TypeError as e:
            log_t = """[%s]: Signal TypeError => Data is not correct! %s""" % (
                delayed_task.__name__,
                e.args[0] if e.args else str(e),
            )
            log.error(log_t)
            raise TypeError(log_t)
        except Exception as e:
            log_t = "[%s]: Signal Error => : %s" % (
                delayed_task.__name__,
                e.args[0] if e.args else str(e),
            )
            log.error(log_t)
            raise TypeError(log_t)

    return delayed_task


# ===============================
# ---- DATABASE CONNECTION (LOCAL DB) РАСКОММЕНТИРОВАТЬ
# ===============================
def connection_database(url_str):
    from cryptomarket.database.connection import DatabaseConnection

    return DatabaseConnection(url_str)


url_str = (
    settings().get_database_url_sqlite
    if DEBUG
    else settings().get_database_url_external
)
connection_db: DatabaseConnection = connection_database(url_str)


# ===============================
# ---- OBJ TO BYTE
# ===============================
def obj_to_byte(odj) -> bytes:

    return pickle.dumps(odj)


# ===============================
# ---- STR TO JSON
# ===============================
def str_to_json(data_str: str) -> dict:
    """
    :param data_str: str the type json data
    :return:
    """
    user_meta_json = {}
    if isinstance(data_str, bytes):
        user_meta_json.update(json.loads(data_str.decode("utf-8")))
    else:
        try:
            user_meta_json.update(json.loads(data_str))
        except json.decoder.JSONDecodeError as e:
            log.error(
                "%s JSONDecodeError => %s"
                % ("[str_to_json]:", e.args[0] if e.args else str(e))
            )
    return user_meta_json


# ===============================
# ---- DATETIME CALENDAR
# ===============================
def datetime_to_seconds(dt: datetime, utc: bool = False) -> float:
    if utc:
        import calendar

        return calendar.timegm(dt.utctimetuple())
    return dt.timestamp()


# ===============================
# ---- HANDLER SSE CONNECTION
# ===============================
def time_now_to_seconds() -> float:
    return datetime.now().timestamp()


async def event_generator(
    mapped_key: str, user_id: str | int, request: Request, timeout=60
):
    from cryptomarket.project.app import manager
    from cryptomarket.type.deribit_type import DeribitLimitedType

    sse_manager = manager.sse_manager
    rate_limit: DeribitLimitedType = manager.rate_limit
    # Timer
    start_time = datetime.now()
    next_timeout_at = start_time + timedelta(seconds=timeout)

    try:
        # ===============================
        # FIRST MESSAGE ABOUT CONNECTION TO THE SSE
        # ===============================
        initial_event = {
            "event": "connected",
            "detail": {
                "status": "waiting_for_exchange",
                "message": "Waiting for the exchange rate ...",
                "timestamp": str(asyncio.get_event_loop().time()),
            },
        }
        yield f"event: {initial_event['event']}\n detail: {json.dumps(initial_event['detail'])}\n\n"
        queue = await sse_manager.subscribe(mapped_key)

        while True:
            # Check the connection with a client
            if await request.is_disconnected():
                yield f'event: disconnected\ndetail: {{"index_app": "{user_id}", "message": "Client disconnected"}}\n\n'
                break

            # ===============================
            # LOCK TO THE CACHE SERVER
            # ===============================
            try:

                result = None
                now = datetime.now()
                timeout_lest = next_timeout_at.timestamp() - now.timestamp()

                async with rate_limit.context_redis_connection() as redis_client:
                    result = await luo_script_find_key(redis_client, "sse_connection:*")
                result = json.loads(result)
                result_dict = {}
                if list(result.keys())[0] is not None and timeout_lest <= 0:
                    # ===============================
                    # UPDATE USER QUEUE
                    # ===============================
                    next_timeout_at = datetime.now() + timedelta(seconds=timeout)
                    if result["keys"][0] is not None:
                        for key in result["keys"]:
                            result_str = await redis_client.get(key)
                            result_dict = json.loads(result_str)
                        await sse_manager.broadcast(result_dict)
                    else:
                        pass
                    timeout_lest += timeout
                else:
                   pass
            except Exception as e:
                log.warning(
                    f"[event_generator]: Redis luo script failed, Result: {str(result)} Error: {e.args[0] if e.args else str(e)}"
                )

            # ===============================
            # TO WAIT NEW EVENT/MESSAGE OF QUEUE
            # ===============================
            try:

                try:
                    # for mess in queue.get_nowait():
                    message_str = queue.get_nowait()
                    yield f'event: message: "index_app": "{user_id}", "message": {message_str}\n\n'
                except Exception as e:
                    message_str = await asyncio.wait_for(queue.get(), 7)
                    yield f'event: message: "index_app": "{user_id}", "message": {message_str}\n\n'
            except (asyncio.TimeoutError, asyncio.QueueEmpty):
                keep_alive_event = {}
                keep_alive_event.__setitem__("event", "keep_alive")
                keep_alive_event.__setitem__("detail", {})
                keep_alive_event["detail"].__setitem__("status", "connected")
                keep_alive_event["detail"]["status"] = "connected"
                keep_alive_event["detail"].__setitem__(
                    "timestamp", str(asyncio.get_event_loop().time())
                )
                yield f"event: {keep_alive_event['event']}\ndetail: {json.dumps(keep_alive_event['detail'])}\n\n"

                continue
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        error_event = {}
        error_event.__setitem__("event", "error")
        error_event.__setitem__("detail", {})
        error_event["detail"].__setitem__("error", e.args[0] if e.args else str(e))
        error_event["detail"].__setitem__(
            "timestamp", str(asyncio.get_event_loop().time())
        )
        yield f"event: {error_event['event']}\ndetail: {json.dumps(error_event['detail'])}\n\n"
    finally:
        # ===============================
        # ---- DELETE THE CLIENT WHEN DISCONNECTING CLIENT
        # ===============================
        yield 'event: closed\ndetail: "message": "Connection closed"\n\n'


# ===============================
# ---- FIRST A PERSON CREATING
# to the cryptomarket/tasks/queues/task_account_user.py
# ===============================
def create_person_manual(
    user_id: str | int,
    key_of_queue: str,
    headers_client_id: str,
    headers_client_secret: str,
):
    from cryptomarket.project.app import manager
    from cryptomarket.type.deribit_type import Person

    # =====================
    # ---- CREATE PERSON
    # =====================
    person_manager = manager.person_manager

    p_dict = person_manager.person_dict
    if user_id not in person_manager.person_dict:
        person_manager.add(person_id=user_id, client_id=str(headers_client_id)[:])
        p: Person = p_dict.get(user_id)
        p.key_of_queue = key_of_queue
        p.client_secret_encrypt = headers_client_secret[:]
        p.active = True
        p_dict.__setitem__(user_id, p)

    else:
        p: Person = p_dict.get(user_id)
        p.active = True
        p_dict.__setitem__(user_id, p)


async def update_person_manual(*args, **kwargs):
    """

    :param args: empty
    :param kwargs: {'ws'; ..., 'person': ...., "user_meta_json": }
    :return:
    """
    from cryptomarket.project.app import manager

    person: Person = list(args)[0]
    user_meta_json = kwargs.get("user_meta_json")

    try:
        # while person.active:
        # seconds = time_now_to_seconds()
        # time_range: float = seconds - person.last_activity
        # ----
        auth_data = {}
        client_secret_encrypt: bytes | None = person.client_secret_encrypt.encode()
        key_encrypt: bytes | None = person.key_encrypt
        access_token = person.access_token
        encrypt_manager: EncryptManagerBase = person.encrypt_manager
        # ----
        _json = user_meta_json.pop("request_data")

        # timeinterval_query = user_meta_json.pop("timeinterval_query")

        if (
            access_token is None
            and person.refresh_token is None
            and client_secret_encrypt is not None
            and key_encrypt is not None
        ):
            # ===============================
            # ---- AUTHENTICATE QUERY
            # ===============================
            user_secret = encrypt_manager.descrypt_to_str(
                {key_encrypt: client_secret_encrypt}
            )
            auth_data = person.get_autantication_data(person.client_id, user_secret)
        elif person.access_token and _json is not None and "jsonrpc" in _json:
            # ===============================
            # ---- TOTAL QUERY
            # ===============================
            _json.__setitem__("access_token", person.access_token)
            auth_data = _json.copy()
        return auth_data

    except Exception as e:
        person.active = False
        raise e
    finally:
        pass


# ===============================
# ---- REDIS CACHE SERVER
# ===============================


async def set_record(
    *args,
    **kwargs,
) -> None:
    from cryptomarket.deribit_client import DeribitLimited
    from cryptomarket.project.sse_manager import setting

    deribit_limited = DeribitLimited()
    context_redis_connection = deribit_limited.context_redis_connection

    try:

        async with context_redis_connection() as redis_client:
            result_ = await asyncio.wait_for(
                redis_client.setex(
                    args[0],
                    setting.CACHE_AUTHENTICATION_DATA_LIVE,
                    json.dumps(kwargs),
                ),
                10,
            )
            return result_
    except Exception as e:
        log.error(
            "%s ERROR => %s" % (set_record.__name__, e.args[0] if e.args else str(e))
        )


async def get_record(
    *args,
) -> None:
    from cryptomarket.deribit_client import DeribitLimited

    deribit_limited = DeribitLimited()
    context_redis_connection = deribit_limited.context_redis_connection

    try:

        async with context_redis_connection() as redis_client:
            result_ = await asyncio.wait_for(
                redis_client.get(
                    args[0],
                ),
                10,
            )
            return result_
    except Exception as e:
        log.error(
            "%s ERROR => %s" % (get_record.__name__, e.args[0] if e.args else str(e))
        )


async def delete_key(
    key_str: str,
) -> None:
    from cryptomarket.deribit_client import DeribitLimited

    deribit_limited = DeribitLimited()
    context_redis_connection = deribit_limited.context_redis_connection

    try:

        async with context_redis_connection() as redis_client:
            result_ = await asyncio.wait_for(
                redis_client.delete(key_str),
                10,
            )
            return result_
    except Exception as e:
        log.error(
            "%s ERROR => %s" % (get_record.__name__, e.args[0] if e.args else str(e))
        )


async def luo_script_find_key(redis_client: Redis, key_str: str):
    script = """
    local cursor = '0'
    local all_keys = {}
    local debug_info = {}
    local pattern = KEYS[1]
    local iteration = 1
    table.insert(debug_info, '=== SCAN RESULT ===')
    repeat
        table.insert(debug_info, 'Start luo script. iteration : ' .. iteration  .. 'whith cursor: ' .. cursor)
        local result = redis.call('SCAN', cursor, 'MATCH', pattern, 'COUNT', 500)
        cursor = result[1]
        if #result[2] > 0 then
            for _, key in ipairs(result[2]) do
                table.insert(all_keys, key)
                table.insert(debug_info, ' Found key: ' .. key)
            end
            iteration = iteration  + 1
            table.insert(debug_info, 'Redis SCAN got result. Cursor:' .. result[1] .. 'Keys:' .. #result[2])
        end
    until cursor == '0'
    table.insert(debug_info, 'Redis SCAN complete. Total keys found: ' .. #all_keys)
    return cjson.encode({keys = all_keys, debug = debug_info})
    """

    result = await asyncio.wait_for(redis_client.eval(script, 1, key_str), 7)
    return result
