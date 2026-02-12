"""
cryptomarket/project/functions.py
"""

import asyncio
import json
import logging
import pickle
import threading
from datetime import datetime

from fastapi import (
    Request,
)

from cryptomarket.project.settings.core import DEBUG, settings

log = logging.getLogger(__name__)


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


url_str = (
    settings().get_database_url_sqlite
    if DEBUG
    else settings().get_database_url_external
)


def connection_database():
    from cryptomarket.database.connection import DatabaseConnection

    return DatabaseConnection(url_str)


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


def string_to_seconds(
    date_string: str, format_string: str = "%d.%m.%Y", utc: bool = False
) -> float:
    """Преобразовать строку с датой напрямую в секунды"""
    dt = datetime.strptime(date_string, format_string)
    return datetime_to_seconds(dt, utc)


# ===============================
# ---- HANDLER SSE CONNECTION
# ===============================


def time_now_to_seconds() -> float:
    return datetime.now().timestamp()


async def event_generator(
    mapped_key: str, user_id: str | int, request: Request, timeout=60
):
    import time

    from cryptomarket.project.app import manager
    from cryptomarket.type.deribit_type import Person

    sse_manager = manager.sse_manager
    person_manager = manager.person_manager
    p_dict = person_manager.person_dict
    p: Person = p_dict.get(user_id)

    # Timer
    start_time = time.time()
    next_timeout_at = start_time + timeout

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
        # _connections = sse_manager._connections
        while True:

            now = time.time()
            timeout_lest = next_timeout_at - now
            # Check the connection with a client
            if await request.is_disconnected():
                yield f'event: disconnected\ndetail: {{"client_ticker": "{p.client_id}", "message": "Client disconnected"}}\n\n'
                break

            # ===============================
            # TO WAIT NEW EVENT/MESSAGE OF QUEUE
            # ===============================
            try:

                try:

                    message_str = await asyncio.wait_for(
                        queue.get_nowait(), timeout=timeout_lest
                    )
                    yield f'event: message: "client_id": "{p.client_id}", "message": {message_str}\n\n'
                except Exception:
                    message_str = await asyncio.wait_for(
                        queue.get(), timeout=timeout_lest
                    )
                    yield f'event: message: "client_id": "{p.client_id}", "message": {message_str}\n\n'

            # Then we wait for  the moment when the need is update the access-token
            # Don't remove connection
            except asyncio.TimeoutError:
                # Отправляем keep-alive сообщение
                # log.info("DEBUG 1 BEFORE __setitem__ ")
                keep_alive_event = {}
                keep_alive_event.__setitem__("event", "keep_alive")
                keep_alive_event.__setitem__("detail", {})
                keep_alive_event["detail"].__setitem__("status", "connected")
                keep_alive_event["detail"]["status"] = "connected"
                keep_alive_event["detail"].__setitem__(
                    "timestamp", str(asyncio.get_event_loop().time())
                )
                yield f"event: {keep_alive_event['event']}\ndetail: {json.dumps(keep_alive_event['detail'])}\n\n"
                next_timeout_at = time.time() + timeout
                continue
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        # Клиент отключился remove of client !!!
        pass
    except Exception as e:
        log.info("DEBUG 2 BEFORE __setitem__ ")
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
