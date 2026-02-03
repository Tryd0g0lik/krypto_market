"""
cryptomarket/api/v2/api_sse.py
"""

import asyncio
import json
import logging

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
from cryptomarket.project.settings.settings_env import (
    DERIBIT_CLIENT_ID,
    DERIBIT_SECRET_KEY,
)
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


@router_v2.get(
    "/auth-stream/",
    summary="SSE stream for authentication results",
    description="""Server-Sent Events эндпоинт для получения результатов аутентификации.

    Клиент должен передать уникальный client_id в query параметрах.
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
    """,
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
    request: Request = None,
):
    """


    Args:
        client_id: Уникальный идентификатор клиента (обязательный параметр)
        request: Объект запроса FastAPI для проверки разрыва соединения

    Returns:
        StreamingResponse: SSE поток с событиями аутентификации
    """
    request_id = request.state.request_id
    client_id = None
    from cryptomarket.project.app import manager

    if client_id is None or not client_id:
        # raise HTTPException(status_code=400, detail="client_id parameter is required")
        request_id = request_id[:]
    # ===============================
    # START THE DERIBIT MANAGE
    # ===============================
    encrypt_manager = EncryptManager()
    # Note!! Now the "deribit_secret_encrypt" will get a dictionary type value.
    #
    kwargs = {
        "index": request_id[:],
        "request_id": request_id[:],
        "api_key": ExternalAPIEnum.WS_COMMON_URL.value,
        "client_id": (lambda: client_id)(),
    }
    del request_id

    kwargs_new = {}
    kwargs_new.__setitem__("client_id", "client_id")
    result: dict = await encrypt_manager.str_to_encrypt(DERIBIT_SECRET_KEY)
    # Get the encrypt key
    kwargs_new.__setitem__("encrypt_key", list(result.keys()).pop())
    kwargs.__setitem__("deribit_secret_encrypt", list(result.values()).pop())
    args = [RadisKeysEnum.AES_REDIS_KEY.value % kwargs.get("client_id")]
    del result
    # ===============================
    # ---- RAN SIGNAL The encrypt key we savinf
    # ===============================
    await signal.schedule_with_delay(
        user_id=kwargs.get("client_id"),
        callback_=None,
        asynccallback_=task_caching_user_data,
        *args,
        **kwargs_new,
    )
    del kwargs_new
    del args

    await manager.enqueue(43200, **kwargs)
    del kwargs

    async def event_generator():
        """Генератор событий для SSE потока"""
        from cryptomarket.project.app import manager

        sse_manager = manager.sse_manager
        # ===============================
        # ---- SUBSCRIBE
        # ===============================
        queue = await sse_manager.subscribe("connection")

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
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield message

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
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",  # Настройте CORS !!!!
            "Access-Control-Expose-Headers": "Content-Type",
        },
    )
