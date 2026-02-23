"""
cryptomarket/api/v2/api_sse.py
"""

import linecache
import logging
import tracemalloc

from fastapi import (
    APIRouter,
    Request,
    status,
)
from fastapi.responses import StreamingResponse

from cryptomarket.api.v2.api_sse_monitoring import sse_monitoring_child

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
    tracemalloc.start()
    response = await sse_monitoring_child(request)
    log.info("=== MEMORY SNAPSHOT FROM sse_monitoring ===")
    snapshot = tracemalloc.take_snapshot()
    statistics = snapshot.statistics("lineno")[:10]
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
    return response
