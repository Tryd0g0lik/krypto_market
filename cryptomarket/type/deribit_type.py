"""
cryptomarket/type/deribit_type.py
"""

import asyncio
from collections import deque
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, Protocol, TypedDict

from aiohttp.client_ws import ClientWebSocketResponse
from fastapi import Request
from pydantic import BaseModel, Field
from websockets import ClientConnection

from cryptomarket.project.enums import ExternalAPIEnum


# ----
class OAuthAutenticationParamsType:

    grant_type: str
    client_id: str
    client_secret: str


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
        pattern=r"^\d+\.\d+$", default="2.0", description="JSON-RPC version"
    )
    method: str = Field(
        pattern=r"^(public/auth)$",
        default="public/auth",
        description="Method used to the authentication",
    )
    params: dict = OAuthAutenticationParamsType

    class Config:
        from_attributes = True


# ----
class DeribitClient:

    _semaphore: asyncio.Semaphore

    client_id: str
    __client_secret: str

    def initialize(
        self,
        _url: str,
        _heartbeat: int = 30,
        _timeout: int = 10,
        _method: str = "GET",
        _autoping: bool = False,
    ):
        pass

    def client_session(self):
        pass

    @asynccontextmanager
    async def ws_send(
        self,
        _url: str,
        _heartbeat: int = 30,
        _timeout: int = 10,
        _method: str = "GET",
        _autoping: bool = True,
    ):
        pass

    @staticmethod
    def _get_autantication_data(
        index: int, client_id: int | str, client_secret_key: str
    ):
        """
        :param index:
        :param client_id:
        :param client_secret_key:
        :return: Example ```text
        {
            "jsonrpc": "2.0",
            "id": index,
            "method": "public/auth",
            "params": {
                "grant_type": "client_credentials",
                "client_id": < client_id_account_of_deribit_client >, > ,
                "client_secret": < DECRYPTIN_secret_key_of_deribit_client >,
            },
        }
        ```
        """
        pass

    @property
    def semaphore(self):
        return self._semaphore


class DeribitWebsocketPoolType:

    _clients: deque
    _current_index: int
    _auth_tokens: str

    def get_clients(self):
        pass


class DeribitMiddlewareType:
    def __init__(self):
        pass

    async def __call__(self, request: Request, call_next):
        pass


class DeribitLimitedType:

    async def context_redis_connection(self):
        pass

    @asynccontextmanager
    async def acquire(self, redis, task_id: str, user_id: str, cache_limit: int = 95):
        pass


class DeribitManageType(Protocol):
    _deque_postman: deque
    _deque_error: deque

    queue: asyncio.Queue

    processing_deribits: set
    rate_limit: DeribitLimitedType | None = None
    client_pool: DeribitWebsocketPoolType | None = None

    stripe_response_var: ContextVar | None = None
    stripe_response_var_token: str | None = None

    async def enqueue(self, cache_live: int, **kwargs):
        pass

    def __error_passed_cached(self, tasks_collections: list):
        pass

    def _start_worker(
        self,
        limitations: int = 10,
    ):
        pass


request_user_data = {
    "request_id": str,
    "api_key": str,
    "client_secret": int,
    "client_id": "< insert client_id >",
}


# ----
