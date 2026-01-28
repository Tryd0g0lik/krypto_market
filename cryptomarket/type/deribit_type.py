"""
cryptomarket/type/deribit_type.py
"""

import asyncio
from collections import deque
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import Request
from pydantic import BaseModel, Field

from cryptomarket.deribit_client import DeribitLimited, DeribitWebsocketPool


class OAuthAutenticationParamsType(BaseModel):

    grant_type: str = Field(default="client_credentials")
    client_id: str = Field(default="YOUR_CLIENT_ID")
    client_secret: str = Field(default="YOUR_CLIENT_SECRET")


class OAuthAutenticationType(BaseModel):
    """
    Method used to authenticate
    https://docs.deribit.com/articles/deribit-quickstart#websocket-authentication
    Template for a user authentication:
        '''
        {
            "jsonrpc": "2.0",
            "method": "public/auth",
            "params": {
              "grant_type": "client_credentials",
              "client_id": "YOUR_CLIENT_ID",
              "client_secret": "YOUR_CLIENT_SECRET"
            },
            "id": 1
          }

        '''
    return
    """

    id: int = Field(gt=0, description="Must be a positive integer")
    api_key: str = Field(description="""Must be a string contain the api key (url)""")
    jsonrpc: str = Field(
        pattern="^\d+\.\d+$", default="2.0", description="JSON-RPC version"
    )
    method: str = Field(
        pattern="^(public\/auth)$",
        default="public/auth",
        description="Method used to the authentication",
    )
    params: dict = OAuthAutenticationParamsType

    class Config:
        from_attributes = True


class DeribitMiddlewareType(BaseModel):
    def __init__(self):
        super().__init__()
        pass

    async def __call__(self, request: Request, call_next):
        pass


class DeribitLimitedType(BaseModel):

    def context_redis_connection(self):
        pass

    @asynccontextmanager
    async def acquire(self, redis, task_id: str, user_id: str, cache_limit: int = 95):
        pass


class DeribitManageType(BaseModel):
    _deque_postman: deque
    _deque_error: deque

    def __init__(
        self,
    ) -> None:
        """
        :param max_concurrent: int.  This is our calculater/limiter for the one user's requests to the Stripe server. \
            Rate/ limitation quantities of requests per 1 second from one user (it is request to the Stripe server) .
            Default value is number from  the variable of 'app_settings.STRIPE_MAX_CONCURRENT'.

        """
        super().__init__()
        self.queue: asyncio.Queue

        self.processing_tasks: set
        self.rate_limit: DeribitLimited | None
        self.connection_pool: DeribitWebsocketPool

        self.stripe_response_var: ContextVar
        self.stripe_response_var_token: str | None

    async def enqueue(self, cache_live: int, **kwargs):
        pass

    def __error_passed_cached(self, tasks_collections: list):
        pass

    def _start_worker(
        self,
        limitations: int = 10,
    ):
        pass
