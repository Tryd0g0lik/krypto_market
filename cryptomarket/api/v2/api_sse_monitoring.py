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
from cryptomarket.project.functions import (
    create_person_manual,
    event_generator,
    update_person_manual,
)
from cryptomarket.project.signals import signal
from cryptomarket.tasks.queues.task_account_user import task_account

log = logging.getLogger(__name__)


async def sse_monitoring_child(request: Request) -> StreamingResponse:
    """
    This is a connection for a sending data and regulation the time for sending.
    parameter: 'url/?timer=5' You can regulate the (in seconds) time interval for a signal to the front.
        Default value is 60 seconds.
    :param headers["X-Client-Id"] (str) Required, This is the deribit param.
    :param headers["X-Secret-key"] (str) Required, This is the deribit param.
        When we receive a string, we make encrypt of that string. Decryption before use.
    :param headers["X-User-id"] (str). Required/ After this parameter (under the hood) we will save how the 'person_id'
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
        (int(timer) if timer is None or re.search(r"^(\d+)$", str(timer)) else 60)
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
    headers_client_secret = request.headers.get("X-Secret-key")
    del headers_request_id

    key_of_queue = "sse_connection:%s:%s" % (
        user_id,
        datetime.now().strftime("%Y%m%d%H%M%S"),
    )
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
        create_person_manual,
        *(
            str(user_id)[:],
            key_of_queue[:],
            headers_client_id,
            headers_client_secret,
        ),
    )
    # =====================
    # ---- CREATE QUEUE
    # =====================
    user_meta_data.__setitem__("user_interval", str(user_interval))
    task_1 = asyncio.create_task(manager.enqueue(3600, **user_meta_data))

    # ===============================
    # ---- RAN SIGNAL
    # ==============================
    task_2 = asyncio.create_task(
        signal.schedule_with_delay(
            callback_=None,
            asynccallback_=task_account,
        )
    )
    await asyncio.gather(task, task_0, task_1, task_2)
    del [user_meta_data, timer, headers_client_id, headers_client_secret, request_id]
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
