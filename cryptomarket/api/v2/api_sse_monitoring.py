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
from cryptomarket.project.functions import create_person, event_generator
from cryptomarket.project.signals import signal
from cryptomarket.tasks.queues.task_account_user import task_account

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
    # ---- BASIS OPTIONS
    # =====================
    from cryptomarket.project.app import manager

    sse_manager = manager.sse_manager
    timer = request.query_params.get("timer")
    user_interval: int = (
        (int(timer) if re.search(r"^(\d+)$", str(timer)) else 60)
        if timer is not None
        else 60
    )
    headers_request_id = request.headers.get("X-Request-ID")
    request_id = (
        str(uuid4()) if headers_request_id is None else str(headers_request_id)[:]
    )
    headers_user_id = request.headers.get("X-User-id")
    user_id = (request_id.split("-"))[0] if headers_user_id is None else headers_user_id
    headers_client_id = request.headers.get("X-Client-Id")
    headers_client_secret = str(request.headers.get("X-Secret-key"))
    del headers_request_id

    key_of_queue = "sse_connection:%s:%s" % (
        user_id,
        datetime.now().strftime("%Y%m%d%H%M%S"),
    )
    # await sse_manager.subscribe(key_of_queue)
    task = asyncio.create_task(sse_manager.subscribe(key_of_queue))
    # =====================
    # ---- User Meta DATA
    # =====================
    user_meta_data = {
        "user_id": user_id,
        "index": 4947,  # request_id.replace("-", ""),
        "method": "private/get_subaccounts",
        "request_id": request_id[:],
        "api_key": ExternalAPIEnum.WS_COMMON_URL.value,
        "client_id": str(headers_client_id)[:],
        "mapped_key": key_of_queue,
        "timeinterval_query": "0.0",
    }
    task_0 = asyncio.to_thread(
        create_person,
        (
            str(user_id)[:],
            key_of_queue[:],
            headers_client_id,
            headers_client_secret,
        ),
    )

    # REGULAR EXPRESSION

    # del headers_client_id
    # del headers_client_secret
    # del request_id
    # =====================
    # ---- CREATE QUEUE
    # =====================
    user_meta_data.__setitem__("user_interval", str(user_interval))
    # await manager.enqueue(3600, **user_meta_data)
    task_1 = asyncio.create_task(manager.enqueue(3600, **user_meta_data))
    # del user_meta_data

    # ===============================
    # ---- RAN SIGNAL
    # ==============================
    # await signal.schedule_with_delay(callback_=None, asynccallback_=task_account)

    task_2 = asyncio.create_task(
        signal.schedule_with_delay(callback_=None, asynccallback_=task_account)
    )
    await asyncio.gather(task, task_0, task_1, task_2)
    del [task, task_0, task_1, task_2]
    del [user_meta_data, timer, headers_client_id, headers_client_secret, request_id]
    # del task_1
    # del task_2
    return StreamingResponse(
        event_generator(key_of_queue, user_id, request, user_interval),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",  # Настройте CORS !!!!
            "Access-Control-Expose-Headers": "Content-Type",
        },
    )
