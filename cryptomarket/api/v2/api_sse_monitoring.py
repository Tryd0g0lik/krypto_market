"""
cryptomarket/api/v2/api_sse_monitoring.py:
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from random import random
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    openapi,
    status,
)
from fastapi.responses import StreamingResponse

from cryptomarket.project.enums import ExternalAPIEnum, RadisKeysEnum
from cryptomarket.project.signals import signal
from cryptomarket.tasks.queues.task_user_data_to_cache import task_caching_user_data


async def sse_monitoring_child(ticker: str, request: Request) -> StreamingResponse:
    """
    ticker: ДАННЫЕ КОТОРЫЕ ПОЛУЧИТЬ
    request: Объект запроса FastAPI для проверки разрыва соединения
    parrameter: 'url/?timer=5' Пользователь устанавливает время в секундах. Время для \
        временного интервала (обновления данных). По умолчанию 60 секунд
    :param ticker:
    :param request:
    :return:
    """
    from cryptomarket.project.app import manager

    timer = request.query_params.get("timer")
    request_id = str(uuid4())
    user_id = (request_id.split("-"))[0]
    client_id = request_id.replace("-", "")

    client__auth = request.headers.get("Authorization")
    access_token = client__auth[7:] if client__auth is not None else ""

    args = [
        RadisKeysEnum.DERIBIT_GET_SUBACCOUNTS.value % user_id,
    ]
    kwargs_new = {}
    kwargs_new.__setitem__("client_id", client_id)
    kwargs_new.__setitem__("user_id", user_id)
    kwargs_new.__setitem__("access_token", access_token)

    await signal.schedule_with_delay(
        None,
        task_caching_user_data,
        0.2,
        *args,
        **kwargs_new,
    )

    key_of_queue = "sse_connection:%s:%s" % (
        user_id,
        datetime.now().strftime("%Y%m%d%H%M%S"),
    )
    # =====================
    # ---- User Meta DATA
    # =====================
    # kwargs = {
    #     "user_id": user_id,
    #     "index": 10,
    #     "method": "private/get_subaccounts",
    #     "request_id": request_id[:],
    #     "api_key": ExternalAPIEnum.WS_COMMON_URL.value,
    #     "client_id": client_id,
    #     "mapped_key": key_of_queue,
    # }
    kwargs = {
        "user_id": user_id,
        "index": request_id,
        "method": "private/get_subaccounts",
        "request_id": request_id[:],
        "api_key": ExternalAPIEnum.WS_COMMON_URL.value,
        "client_id": client_id,
        "mapped_key": key_of_queue,
    }

    # REGULAR EXPRESSION
    user_interval: int = (
        (int(timer) if re.search(r"^(\d+)$", str(timer)) else 60)
        if timer is not None
        else 60
    )
    del timer
    kwargs.__setitem__("user_interval", str(user_interval))
    ticke_r = ticker if ticker else "btc_usd"
    kwargs.setdefault("ticker", ticke_r)
    await manager.enqueue(3600, **kwargs)
    del kwargs

    async def event_generator(mapped_key: str, client_ticker_: str, timeout=60):
        import time
        from datetime import datetime, timedelta

        from cryptomarket.project.app import manager

        sse_manager = manager.sse_manager
        # Timer
        start_time = time.time()
        next_timeout_at = start_time + timeout
        # ===============================
        # ---- SUBSCRIBE
        # ===============================
        queue = await sse_manager.subscribe(mapped_key)
        try:
            # ===============================
            # FIRST MESSAGE ABOUT CONNECTION TO THE SSE
            # ===============================
            initial_event = {
                "event": "connected",
                "detail": {
                    "client_ticker": client_ticker_,
                    "status": "waiting_for_exchange",
                    "message": "Waiting for the exchange rate ...",
                    "timestamp": str(asyncio.get_event_loop().time()),
                },
            }
            yield f"event: {initial_event['event']}\n detail: {json.dumps(initial_event['detail'])}\n\n"

            while True:
                now = time.time()
                timeout_lest = next_timeout_at - now
                # Check the connection with a client
                if await request.is_disconnected():
                    yield f'event: disconnected\ndetail: {{"client_ticker": "{client_id}", "message": "Client disconnected"}}\n\n'
                    break

                # ===============================
                # TO WAIT NEW EVENT/MESSAGE OF QUEUE
                # ===============================
                try:
                    message_str = await asyncio.wait_for(
                        queue.get(), timeout=timeout_lest
                    )

                    # message_str = json.dumps(list(json.loads(message).values())[0])
                    yield f'event: message: "client_id": "{client_id}", "message": {message_str}\n\n'

                    # Then we wait for  the moment when the need is update the access-token
                    # Don't remove connection
                except asyncio.TimeoutError:
                    # Отправляем keep-alive сообщение
                    keep_alive_event = {}
                    keep_alive_event.__setitem__("event", "keep_alive")
                    keep_alive_event.__setitem__("detail", {})
                    keep_alive_event["detail"].__setitem__(
                        "client_ticker", client_ticker_
                    )
                    keep_alive_event["detail"].__setitem__("status", "connected")
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
            error_event = {}
            error_event.__setitem__("event", "error")
            error_event.__setitem__("detail", {})
            error_event["detail"].__setitem__("client_ticker", client_ticker_)
            error_event["detail"].__setitem__("error", e.args[0] if e.args else str(e))
            error_event["detail"].__setitem__(
                "timestamp", str(asyncio.get_event_loop().time())
            )
            yield f"event: {error_event['event']}\ndetail: {json.dumps(error_event['detail'])}\n\n"
        finally:
            # ===============================
            # ---- DELETE THE CLIENT WHEN DISCONNECTING CLIENT
            # ===============================
            await sse_manager.unsubscribe(client_ticker_, queue)
            yield f'event: closed\ndetail: {{"client_ticker": "{client_ticker_}", "message": "Connection closed"}}\n\n'

    return StreamingResponse(
        event_generator(key_of_queue, ticke_r, user_interval),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",  # Настройте CORS !!!!
            "Access-Control-Expose-Headers": "Content-Type",
        },
    )
