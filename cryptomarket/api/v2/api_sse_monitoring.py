"""
cryptomarket/api/v2/api_sse_monitoring.py:
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from uuid import uuid4

from fastapi import (
    Request,
)
from fastapi.responses import StreamingResponse

from cryptomarket.project.enums import ExternalAPIEnum
from cryptomarket.project.signals import signal
from cryptomarket.tasks.queues.task_account_user import task_account
from cryptomarket.type.deribit_type import Person

log = logging.getLogger(__name__)


async def sse_monitoring_child(request: Request) -> StreamingResponse:
    """
    ticker: ДАННЫЕ КОТОРЫЕ ПОЛУЧИТЬ
    request: Объект запроса FastAPI для проверки разрыва соединения
    parrameter: 'url/?timer=5' Пользователь устанавливает время в секундах. Время для \
        временного интервала (обновления данных). По умолчанию 60 секунд
    :param headers["X-Client-Id"] (str) Required,
    :param headers["X-User-id"] (str).
    :param ticker:
    :param request:
    :return:
    """
    # =====================
    # ---- BASIS SETTING
    # =====================
    from cryptomarket.project.app import manager

    sse_manager = manager.sse_manager
    timer = request.query_params.get("timer")
    user_interval: int = (
        (int(timer) if re.search(r"^(\d+)$", str(timer)) else 60)
        if timer is not None
        else 60
    )
    request_id = str(uuid4())
    headers_user_id = request.headers.get("X-User-id")
    user_id = (request_id.split("-"))[0] if headers_user_id is None else headers_user_id
    headers_client_id = request.headers.get("X-Client-Id")
    headers_client_secret = str(request.headers.get("X-Secret-key"))
    # headers_client_auth = request.headers.get("Authorization")

    key_of_queue = "sse_connection:%s:%s" % (
        user_id,
        datetime.now().strftime("%Y%m%d%H%M%S"),
    )
    await sse_manager.subscribe(key_of_queue)
    # =====================
    # ---- User Meta DATA
    # =====================
    user_meta_data = {
        "user_id": user_id,
        "index": 4947,  # request_id.replace("-", ""),
        "method": "private/get_subaccounts",
        "request_id": request_id[:],
        "api_key": ExternalAPIEnum.WS_COMMON_URL.value,
        "client_id": headers_client_id,
        "mapped_key": key_of_queue,
    }

    # =====================
    # ---- PERSON
    # =====================
    person_manager = manager.person_manager
    if user_id not in person_manager.person_dict:
        person_manager.add(person_id=user_id, client_id=headers_client_id)
        p_dict = person_manager.person_dict
        p: Person = p_dict.get(user_id)
        p.key_of_queue = key_of_queue
        p.client_secret_encrypt = headers_client_secret
        p_dict.__setitem__(user_id, p)
    # REGULAR EXPRESSION

    del timer
    user_meta_data.__setitem__("user_interval", str(user_interval))
    # ticke_r = ticker if ticker else "btc_usd"
    # user_meta_data.setdefault("ticker", ticke_r)
    await manager.enqueue(3600, **user_meta_data)
    del user_meta_data

    # ===============================
    # ---- RAN SIGNAL
    # ==============================
    # Note: The 'task_account' was relocated from 'self.enqueue'.
    # await  task_account([], {})
    await signal.schedule_with_delay(callback_=None, asynccallback_=task_account)

    async def event_generator(mapped_key: str, timeout=60):
        import time
        from datetime import datetime, timedelta

        # Timer
        start_time = time.time()
        next_timeout_at = start_time + timeout
        # ===============================
        # ---- SUBSCRIBE
        # ===============================

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

                now = time.time()
                timeout_lest = next_timeout_at - now
                # Check the connection with a client
                if await request.is_disconnected():
                    yield f'event: disconnected\ndetail: {{"client_ticker": "{headers_client_id}", "message": "Client disconnected"}}\n\n'
                    break

                # ===============================
                # TO WAIT NEW EVENT/MESSAGE OF QUEUE
                # ===============================
                try:
                    # if queue.qsize() > 0:
                    message_str = None
                    try:
                        message_str = await asyncio.wait_for(
                            queue.get_nowait(), timeout=timeout_lest
                        )
                        yield f'event: message: "client_id": "{headers_client_id}", "message": {message_str}\n\n'
                    except Exception:
                        message_str = await asyncio.wait_for(
                            queue.get(), timeout=timeout_lest
                        )
                        yield f'event: message: "client_id": "{headers_client_id}", "message": {message_str}\n\n'

                        # message_str = json.dumps(list(json.loads(message).values())[0])

                    # Then we wait for  the moment when the need is update the access-token
                    # Don't remove connection
                except asyncio.TimeoutError:
                    # Отправляем keep-alive сообщение
                    # log.info("DEBUG 1 BEFORE __setitem__ ")
                    keep_alive_event = {}
                    keep_alive_event.__setitem__("event", "keep_alive")
                    keep_alive_event.__setitem__("detail", {})
                    # keep_alive_event["detail"].__setitem__(
                    #     "client_ticker", client_ticker_
                    # )
                    # keep_alive_event["detail"].__setitem__("status", "connected")
                    keep_alive_event["detail"]["status"] = "connected"
                    keep_alive_event["detail"].__setitem__(
                        "timestamp", str(asyncio.get_event_loop().time())
                    )
                    yield f"event: {keep_alive_event['event']}\ndetail: {json.dumps(keep_alive_event['detail'])}\n\n"
                    next_timeout_at = time.time() + timeout
                    continue

        except asyncio.CancelledError:
            # Клиент отключился remove of client !!!
            pass
        except Exception as e:
            log.info("DEBUG 2 BEFORE __setitem__ ")
            error_event = {}
            error_event.__setitem__("event", "error")
            error_event.__setitem__("detail", {})
            # error_event["detail"].__setitem__("client_ticker", client_ticker_)
            error_event["detail"].__setitem__("error", e.args[0] if e.args else str(e))
            error_event["detail"].__setitem__(
                "timestamp", str(asyncio.get_event_loop().time())
            )
            yield f"event: {error_event['event']}\ndetail: {json.dumps(error_event['detail'])}\n\n"
        finally:
            # ===============================
            # ---- DELETE THE CLIENT WHEN DISCONNECTING CLIENT
            # ===============================
            # await sse_manager.unsubscribe(client_ticker_, queue)
            # yield f'event: closed\ndetail: {{"client_ticker": "{client_ticker_}", "message": "Connection closed"}}\n\n'
            yield 'event: closed\ndetail: "message": "Connection closed"\n\n'

    return StreamingResponse(
        event_generator(key_of_queue, user_interval),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",  # Настройте CORS !!!!
            "Access-Control-Expose-Headers": "Content-Type",
        },
    )
