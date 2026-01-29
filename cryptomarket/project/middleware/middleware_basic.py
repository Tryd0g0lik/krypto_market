"""
cryptomarket/project/middleware/middleware_basic.py
This the middleware mock is model of start for work by DERIBIT API.
"""

import logging
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

from fastapi import Request, status

from cryptomarket.project.enum import ExternalAPIEnum
from cryptomarket.type import DeribitManageType
from cryptomarket.type.deribit_type import DeribitMiddlewareType

log = logging.getLogger(__name__)


class DeribitMiddleware(DeribitMiddlewareType):
    def __init__(self, manager: DeribitManageType):
        super().__init__()
        self.manager: DeribitManageType = manager

    async def __call__(self, request: Request, call_next):
        """

        TODO:  Here add additional user identification.
        """

        # ===============================
        # CREATE REQUEST ID
        # Get a request index and token for ContexVar
        # This request id will be with us until user gets response.
        # ===============================
        request_id_var = ContextVar("request_id", default="")
        request_id_var_token = request_id_var.set(str(uuid4()))
        log.info("Start request id: %s", request_id_var.get())
        # ===============================
        # START THE DERIBIT MANAGE
        # ===============================
        kwargs = {
            "request_id": request_id_var.get(),
            "api_key": ExternalAPIEnum.WS_COMMON_URL.value,
            "deribit_id": 1,
            "client_id": "< insert client_id >",
        }
        await self.manager.enqueue(43200, **kwargs)
        # ===============================
        # GET RESPONSE DATA
        # ===============================
        captured_data: dict[str, Any] = {
            "headers": {},
            "query_params": {},
            "cookies": {},
            "body": None,
            "form_data": {},
            "files": {},
            "client": {},
            "method": "",
            "url": {},
        }

        captured_data["headers"] = dict(request.headers)
        captured_data["cookies"] = request.cookies
        captured_data["query_params"] = dict(request.query_params)
        captured_data["client"] = {
            "host": request.client.host if request.client else None,
            "port": request.client.port if request.client else None,
        }
        body_data = await self._capture_body_and_form(request)
        captured_data.update(body_data)

        # Store in request state for use in endpoints
        request.state.captured_data = captured_data

        # Continue with the request
        response = await call_next(request)

        # Add captured data to response headers
        response.headers["X-Request-Captured"] = "true"
        response.status_code = status.HTTP_201_CREATED
        request_id_var.reset(request_id_var_token)
        return response

    async def _capture_body_and_form(self, request: Request):
        """
        TODO: Here add additional logic by getting the request context data
        """
        return {"data": "All successfully!"}
