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
)
async def sse_monitoring(request: Request) -> StreamingResponse:

    response = await sse_monitoring_child(request)

    return response
