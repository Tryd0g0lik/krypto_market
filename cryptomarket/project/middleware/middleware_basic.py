"""
cryptomarket/project/middleware/middleware_basic.py
This the middleware mock is model of start for work by DERIBIT API.
"""

from typing import Any, Dict

from fastapi import Request, Response, status

from cryptomarket.type import DeribitManageProp


class DeribitMiddleware:

    def __init__(self, manage: DeribitManageProp):
        self.manager: DeribitManageProp = manage

    async def __call__(self, request: Request, call_next):
        """

        TODO:  Here add additional user identification.
        """
        # ===============================
        # START THE DERIBIT MANAGE
        # ===============================
        kwargs = {"deribit_id": 1, "client_id": "< insert client_id >"}
        await self.manager.enqueue(**kwargs)
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
        return response

    async def _capture_body_and_form(self, request: Request):
        """
        TODO: Here add additional logic by getting the request context data
        """
        return {"data": "All successfully!"}
