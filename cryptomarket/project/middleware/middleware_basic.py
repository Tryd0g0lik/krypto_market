"""
cryptomarket/project/middleware/middleware_basic.py
This the middleware mock is model of start for work by DERIBIT API.
"""

import logging
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

from fastapi import Request, status

from cryptomarket.project.encrypt_manager import EncryptManager
from cryptomarket.project.enums import ExternalAPIEnum
from cryptomarket.project.settings.settings_env import (
    DERIBIT_CLIENT_ID,
    DERIBIT_SECRET_KEY,
)
from cryptomarket.project.signals import signal
from cryptomarket.tasks.queues.task_user_encrypt_key import task_record_user_encrypt_key
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
        encrypt_manager = EncryptManager()
        # Note!! Now the "deribit_secret_encrypt" will get a dictionary type value.
        #
        kwargs = {
            "index": request_id_var.get(),
            "request_id": request_id_var.get(),
            "api_key": ExternalAPIEnum.WS_COMMON_URL.value,
            "client_id": (lambda: DERIBIT_CLIENT_ID)(),
        }
        kwargs_new = {}
        kwargs_new["client_id"] = kwargs.get("client_id")
        result: dict = await encrypt_manager.str_to_encrypt(DERIBIT_SECRET_KEY)
        # Get the encrypt key
        kwargs_new["encrypt_key"] = list(result.keys()).pop()
        kwargs["deribit_secret_encrypt"] = list(result.values()).pop()
        del result
        # ===============================
        # ---- RAN SIGNAL encrypt key saving
        # ===============================
        await signal.schedule_with_delay(
            user_id=kwargs.get("client_id"),
            callback_=None,
            asynccallback_=task_record_user_encrypt_key,
            **kwargs_new
        )
        del kwargs_new

        await self.manager.enqueue(43200, **kwargs)
        del kwargs
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
        return {"detail": "All successfully!"}
