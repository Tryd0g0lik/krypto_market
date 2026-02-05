"""
cryptomarket/api/v2/api_sse.py
"""

import asyncio
import json
import logging
from datetime import datetime
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

from cryptomarket.project.encrypt_manager import EncryptManager
from cryptomarket.project.enums import ExternalAPIEnum, RadisKeysEnum
from cryptomarket.project.signals import signal
from cryptomarket.tasks.queues.task_user_data_to_cache import task_caching_user_data

log = logging.getLogger(__name__)

router_v2 = APIRouter(
    prefix="/sse",
    tags=["sse"],
    # responses={}
    responses={
        404: {"description": "Not found"},
        200: {"description": "Success"},
        500: {"description": "Internal server error"},
    },
)


# ======================
# ---- USER AUTHENTICATE
# ======================
@router_v2.get(
    "/auth-stream/{ticker}",
    summary="SSE stream for the user authentication ",
    description="""Server-Sent Events эндпоинт для получения результатов аутентификации.

    **Required parameters of Headers**
    |HEADER|TYPE|REQUIRED|DESCRIPTION|
    |------|----|--------|-----------|
    |X-Secret-key|string|True|'pc4e....-PKQY'|
    |X-Client-Id|string|False|'_XcQ7xuV'|

    Клиент должен передать уникальный 'client_id' в query параметрах.
    После успешной аутентификации через другой эндпоинт, результат будет отправлен через этот SSE поток.

    Формат событий:
    - connected: начальное событие при подключении
    - auth_result: событие с результатом аутентификации
    - error: событие с ошибкой

    Пример успешного ответа:
    ```json
    {
        'state': 'auth_result',
        "client_id": "uuid-client-id",
        "access_token": "eyJhbGciOi...",
        "expires_in": 3600,
        "refresh_token": "dGhpcyBpcy...",
        "scope": "read write",
        "token_type": "Bearer"
    }
    ```
    После успешной аутентификации, канал остается открытым для обновления токена.
    """,
    status_code=status.HTTP_201_CREATED,
    dependencies=[],
    responses={
        200: {
            "description": "SSE stream established successfully",
            "content": {
                "text/event-stream": {
                    "state": "auth_result",
                    "client_id": "_XcQ7xuV",
                    "access_token": "eyJhbGciOi...",
                    "expires_in": 31536000,
                    "refresh_token": "dGhpcyBpcy...",
                    "scope": "read write",
                    "token_type": "Bearer",
                }
            },
        },
        400: {"description": "Missing or invalid client_id parameter"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def sse_auth_endpoint(
    ticker: str,
    request: Request = None,
):
    """


    Args:
        client_id: Уникальный идентификатор клиента (обязательный параметр)
        request: Объект запроса FastAPI для проверки разрыва соединения

    Returns:
        StreamingResponse: SSE поток с событиями аутентификации
    """
    encrypt_manager = EncryptManager()
    # request_id = str(request.state.request_id)
    request_id = str(uuid4())
    user_id = (request_id.split("-"))[0]
    client_id = request.headers.get("X-Client-Id")
    client_secret_key = str(request.headers.get("X-Secret-key"))
    # user_id = str(request.state.user_id)
    from cryptomarket.project.app import manager

    args = [
        RadisKeysEnum.AES_REDIS_KEY.value % user_id,
    ]
    kwargs_new = {}
    kwargs_new.__setitem__("client_id", client_id)
    kwargs_new.__setitem__("user_id", user_id)
    result: dict = await encrypt_manager.str_to_encrypt(client_secret_key)

    kwargs_new.__setitem__("encrypt_key", list(result.keys()).pop())
    kwargs_new.__setitem__("deribit_secret_encrypt", list(result.values()).pop())
    await signal.schedule_with_delay(
        None,
        task_caching_user_data,
        0.2,
        *args,
        **kwargs_new,
    )

    ticker = ticker[:]
    # ===============================
    # START THE DERIBIT MANAGE
    # ===============================
    # encrypt_manager = EncryptManager()
    # Note!! Now the "deribit_secret_encrypt" will get a dictionary type value.

    # This is (the 'key_of_queue') the reference between SSE and data of the cache server
    key_of_queue = "sse_connection:%s:%s" % (
        user_id,
        datetime.now().strftime("%Y%m%d%H%M%S"),
    )
    kwargs = {
        "user_id": user_id,
        "index": request_id[:],
        "method": "public/auth",
        "request_id": request_id[:],
        "api_key": ExternalAPIEnum.WS_COMMON_URL.value,
        "client_id": client_id,
        "mapped_key": key_of_queue,
    }
    del request_id

    await manager.enqueue(43200, **kwargs)
    del kwargs

    async def event_generator(mapped_key):
        """Генератор событий для SSE потока"""
        from cryptomarket.project.app import manager

        sse_manager = manager.sse_manager
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
                    "client_id": client_id,
                    "status": "waiting_for_auth",
                    "message": "Connected to authentication stream. Waiting for authentication...",
                    "timestamp": str(asyncio.get_event_loop().time()),
                },
            }
            yield f"event: {initial_event['event']}\n detail: {json.dumps(initial_event['detail'])}\n\n"

            while True:
                # Check the connection with a client
                if await request.is_disconnected():
                    yield f'event: disconnected\ndetail: {{"client_id": "{client_id}", "message": "Client disconnected"}}\n\n'
                    break

                # ===============================
                # TO WAIT NEW EVENT/MESSAGE OF QUEUE
                # ===============================
                try:
                    """
                            {"text/event-stream": {
                        'state': 'auth_result',
                        "client_id": "_XcQ7xuV",
                        "access_token": "eyJhbGciOi...",
                        "expires_in": 31536000,
                        "refresh_token": "dGhpcyBpcy...",
                        "scope": "read write",
                        "token_type": "Bearer"
                    }} CH-E-CK
                    """
                    message_str = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # message_str = json.dumps(list(json.loads(message).values())[0])
                    # message_str = json.dumps(list(json.loads(message)[0])
                    yield f'event: message: "client_id": "{client_id}", "message": {message_str}\n\n'

                    # Then we wait for  the moment when the need is update the access-token
                    # Don't remove connection
                except asyncio.TimeoutError:
                    # Отправляем keep-alive сообщение
                    keep_alive_event = {}
                    keep_alive_event.__setitem__("event", "keep_alive")
                    keep_alive_event.__setitem__("detail", {})
                    keep_alive_event["detail"].__setitem__("client_id", client_id)
                    keep_alive_event["detail"].__setitem__("status", "connected")
                    keep_alive_event["detail"].__setitem__(
                        "timestamp", str(asyncio.get_event_loop().time())
                    )
                    yield f"event: {keep_alive_event['event']}\ndetail: {json.dumps(keep_alive_event['detail'])}\n\n"
                    continue

        except asyncio.CancelledError:
            # Клиент отключился remove of client !!!
            pass
        except Exception as e:
            error_event = {}
            error_event.__setitem__("event", "error")
            error_event.__setitem__("detail", {})
            error_event["detail"].__setitem__("client_id", client_id)
            error_event["detail"].__setitem__("error", e.args[0] if e.args else str(e))
            error_event["detail"].__setitem__(
                "timestamp", str(asyncio.get_event_loop().time())
            )
            yield f"event: {error_event['event']}\ndetail: {json.dumps(error_event['detail'])}\n\n"
        finally:
            # ===============================
            # ---- DELETE THE CLIENT WHEN DISCONNECTING CLIENT
            # ===============================
            await sse_manager.unsubscribe(client_id, queue)
            yield f'event: closed\ndetail: {{"client_id": "{client_id}", "message": "Connection closed"}}\n\n'

    return StreamingResponse(
        event_generator(key_of_queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",  # Настройте CORS !!!!
            "Access-Control-Expose-Headers": "Content-Type",
        },
    )
