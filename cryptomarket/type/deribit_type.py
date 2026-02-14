"""
cryptomarket/type/deribit_type.py
"""

import asyncio
from collections import deque
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Protocol, TypedDict

from aiohttp import client_ws
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
class Person:
    """
    TODO: В данный момент  'person_is' отсутствует.
        Получить его через MIDDLEWARE и JWT токен
    """

    SUPPORTED_CURRENCIES = {}
    encrypt_manager: "EncryptManagerBase"

    def __init__(
        self,
        client_id,
        person_id,
        last_activity=datetime.now().timestamp(),
    ):
        self.person_id = person_id
        self.__deribit_client_id = client_id
        self.__access_token: str | None = None
        self.expires_in: int | None = None
        self.__refresh_token: str | None = None
        self.last_activity: float = last_activity  # last time when
        # self.timeinterval_query: int | float = 0.0
        self.last_data_query: dict = {}
        self.ws: ClientWebSocketResponse | None = None
        self.active: bool = True
        self.__deribit_client_secret_encrypt: bytes | None = None
        self.__key_encrypt: bytes | None = None
        self.key_of_queue: str | None = None
        self.scope: str | None = None
        self.token_type: str | None = None
        # self.msg: dict | None = None
        self.client: DeribitClient | None = None
        self.log_t = f"{self.__class__.__name__}.%s"

    @asynccontextmanager
    async def ws_send(self, client: DeribitClient):
        pass

    @property
    def access_token(self) -> str | None:
        pass

    @access_token.setter
    def access_token(self, access_token: str) -> None:
        pass

    @property
    def client_id(self) -> str | None:
        pass

    @client_id.setter
    def client_id(self, client_id: str) -> int | str | None:
        pass

    @property
    def client_secret_encrypt(self) -> str | None:
        return self.__deribit_client_secret_encrypt

    @property
    def key_encrypt(self) -> bytes:
        return self.__key_encrypt

    @client_secret_encrypt.setter
    def client_secret_encrypt(self, client_secret: str) -> None:
        """
        Async
        :param client_secret:
        :return:
        """
        pass

    @property
    def refresh_token(self) -> str | None:
        pass

    @refresh_token.setter
    def refresh_token(self, refresh_token: str) -> str:
        pass

    async def ws_json(
        self, _json: dict | None = None, timinterval: float = 15.0
    ) -> None:
        """
        :param _json: (dict) {"method": < deribit private or public >
            "params":{....}, "id": < request index >
        }
        """
        pass

    @staticmethod
    def get_autantication_data(
        client_id: int | str, client_secret_key: str, index: int | None = None
    ) -> dict:
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

    @staticmethod
    def get_subaccount_data(request_id: str | int | None, with_portfolio=False) -> dict:
        pass

    async def _safe_receive_json(self, ws) -> None | dict:
        """
        Безопасное получение JSON с защитой от конкурентного доступа.

        ВАЖНО: В системе должен быть только ОДИН получатель сообщений на WebSocket!
        """
        pass


class EncryptManagerBase:
    """
    Used to the 'cryptomarket.project.encrypt_manager.EncryptManager' and more
    """

    def __init__(
        self,
    ) -> None:
        pass

    async def str_to_encrypt(self, plaintext: str, *args) -> dict[str, str]:
        """
        :param plaintext: (str) Clean text for encryption.
        :return: asynccontext: Example '{key: encrypted}' or \
            by type '{< key_generated_Fernet >: <decrypt_text >}'
        :return args: This data for recording the 'encrypt_key' to the cache server
        """
        pass

    def descrypt_to_str(self, encrypted_dict: dict[bytes, bytes]) -> str:
        """
        :param encrypted_dict: (dict[bytes, bytes]) Encrypted dict. Example '{key: encrypted}' or\
            by type '{< bytes_key_generated_Fernet >: <bytes_decrypt_text >}'.
        :return: str
        """
        pass
