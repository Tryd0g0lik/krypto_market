"""
cryptomarket/api/v2/api_sse.py
"""

import logging
import tracemalloc

from fastapi import (
    APIRouter,
    Request,
    status,
)
from fastapi.responses import StreamingResponse

from cryptomarket.api.v2.api_sse_monitoring import sse_monitoring_child
from cryptomarket.project.functions import get_memory_size

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
# ---- CRYPTO EXCHANGE RATE MONITORING
# ======================
@router_v2.get(
    path="/connection",
    summary="SSE Crypto exchange rate monitoring",
    tags=["sse"],
    description="""

    **Required parameters of Headers**

    |HEADER|TYPE|REQUIRED|DESCRIPTION|
    |------|----|--------|-----------|
    |X-Requested-ID|string|False|<uuid> - X-Requested-ID is not required|
    |X-Client-Id|string|True|Получаем при регистрации в deribit|
    |X-Secret-key|string|True|Получаем при регистрации в deribit|
    |X-User-id|string|True|ID пользователя из базы данных приложения|

    **Params**
    |PARAMS|TYPE|REQUIRED|DESCRIPTION|
    |------|----|--------|-----------|
    |timer|integer|False|Пример: 60 |
    """,
)
async def sse_monitoring(request: Request) -> StreamingResponse:

    response = await sse_monitoring_child(request)

    return response
