"""
cryptomarket/deribit_client/deribit_person.py
TODO создать объект пользователя который получает данные при аутентификации
    Note:: app требует регистрацию пользователя в Deribit, для получения получения сеуретных ключей.
    Ключи вероятнго должны УЖЕ поступать с первым запросом и перехватываю в MIDDLEWARE
    После MIDDLEWARE отправляются на аутентификацию и в отсете получает access_token, refresh_token и время жижни
    - -
    В данный момент Person:
     - вступает в игру после получения access_token, refresh_token.
     - хранить и передавать *_tokenб в данный мент нет куда.
     От лица/аккаунта  пользователя далаем запросы с интервалом в минуту.
    - -
    Person чтоб платформа не:
     - зависила от от пользователей,
     - и не несла ответственности за действия пользователей
Через сигнал в задаче
"""

import asyncio
import json
import logging
import threading
from collections import UserDict
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from aiohttp import client_ws

from cryptomarket.errors import DeribitValueError
from cryptomarket.errors.person_errors import (
    PersonDictionaryError,
    PersonNotFoundAccessError,
)
from cryptomarket.project.encrypt_manager import EncryptManager
from cryptomarket.project.functions import run_asyncio_debug, time_now_to_seconds
from cryptomarket.project.settings.core import settings
from cryptomarket.type import DeribitClient
from cryptomarket.type.deribit_type import Person

log = logging.getLogger(__name__)
setting = settings()


class PersonDictionary(UserDict):
    def __init__(
        self,
        maxsize: int | None = None,
    ):
        """
        :param maxsize: (int|None) When dictionary would get a length == maxsize mean
        remove a first element.
        """
        self.maxsize = maxsize
        super().__init__()

    def __setitem__(self, key, value):

        try:
            if (
                key is None
                or value is None
                or not isinstance(key, str)
                or not isinstance(value, Person)
            ):
                raise PersonDictionaryError()

            if self.maxsize is not None and len(self) >= self.maxsize:
                self.pop(list(self.keys())[0])
            super().__setitem__(key, value)
        except PersonDictionaryError as e:
            raise e

    def __has__(self, key) -> bool:
        """Check presence a key in the dictionary.
        True mean the key was found and False if not found the incoming key.,
        """
        try:
            if key is None:
                raise DeribitValueError()
            if key in self:
                return True
            return False

        except DeribitValueError as e:
            raise e


class PersonManager:
    # We created the person image. He was added to the cache by the key 'deribit:person' &
    # value: '{'deribit:person:< person_id >': {..p.e.r.s.o.n..}}"
    person_dict = PersonDictionary(maxsize=setting.DERIBIT_QUEUE_SIZE)
    client: DeribitClient | None = None
    SUPPORTED_CURRENCIES = {
        "BTC": [
            "BTC-PERPETUAL",
            "BTC-USDT-PERPETUAL",
            "BTC_USD",
        ],
        "ETH": [
            "ETH-PERPETUAL",
            "ETH-USDT-PERPETUAL",
            "ETH_USD",
        ],
        "DOT": ["DOT-PERPETUAL", "DOT_USDC"],
    }

    def __init__(self):
        self.log_t = f"{self.__class__.__name__}.%s"

    def add(
        self,
        client_id,
        person_id,
        last_activity=time_now_to_seconds(),
        client_secret=None,
    ) -> None:
        try:
            person = self.Person(
                client_id,
                person_id,
                last_activity,
            )
            if client_secret is not None:
                person.client_secret_encrypt = client_secret
            self.person_dict.__setitem__(person_id, person)
        except Exception as e:
            raise e

    class Person(Person):
        """
        TODO: В данный момент  'person_is' отсутствует.
            Получить его через MIDDLEWARE и JWT токен
        """

        encrypt_manager = EncryptManager()

        def __init__(
            self,
            client_id,
            person_id,
            last_activity=time_now_to_seconds(),
        ):
            self.person_id = person_id
            self.__deribit_client_id = client_id
            self.__access_token: str | None = None
            self.expires_in: int | None = None
            self.__refresh_token: str | None = None
            self.last_activity: float = last_activity  # last time when
            # self.timeinterval_query: int | float = 0.0
            self.last_data_query: dict = {}

            self.active: bool = True
            self.__deribit_client_secret_encrypt: bytes | None = None
            self.__key_encrypt: bytes | None = None
            self.key_of_queue: str | None = None
            self.scope: str | None = None
            self.token_type: str | None = None
            self.email: str | None = None
            self.is_password: bool | None = None
            self.system_name: str | None = None
            self.username: str | None = None
            # self.msg: dict | None = None

            self.log_t = f"{self.__class__.__name__}.%s"
            super().__init__(client_id, person_id, last_activity)

        @property
        def access_token(self) -> str | None:
            return self.__access_token

        @access_token.setter
        def access_token(self, access_token: str) -> None:
            self.__access_token = access_token

        @property
        def client_id(self) -> str | None:
            return self.__deribit_client_id

        @client_id.setter
        def client_id(self, client_id: str) -> int | str | None:
            self.__deribit_client_id = client_id

        @property
        def client_secret_encrypt(self) -> str | None:
            return (
                self.__deribit_client_secret_encrypt.decode()
                if self.__deribit_client_secret_encrypt
                else None
            )

        @property
        def key_encrypt(self):
            return self.__key_encrypt

        @client_secret_encrypt.setter
        def client_secret_encrypt(self, client_secret: str) -> None:
            """
            Async
            :param client_secret:
            :return:
            """
            try:

                client_secret_encrypt: dict[str, str] = {}
                self.func(client_secret, client_secret_encrypt)

                self.__key_encrypt = list(client_secret_encrypt.keys())[0].encode()
                self.__deribit_client_secret_encrypt = list(
                    client_secret_encrypt.values()
                )[0].encode()
            except Exception as e:
                log_err = "%s ERROR => %s" % (
                    self.log_t % "sclient_secret_encrypt",
                    e.args[0] if e.args else str(e),
                )
                log.error(str(log_err))
                raise ValueError(str(log_err))

        @property
        def refresh_token(self) -> str | None:
            return self.__refresh_token

        @refresh_token.setter
        def refresh_token(self, refresh_token: str) -> str:
            self.__refresh_token = refresh_token

        def get_autantication_data(
            self, client_id: int | str, client_secret_key: str, index: int | None = None
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
            if client_id is None or client_secret_key is None:
                log_err = (
                    "[%s]: ERROR => Client id and secret key are required variables!"
                    % (self.log_t % self.get_autantication_data.__name__)
                )
                log.error(str(log_err))
                raise ValueError(str(log_err))

            res = {
                "jsonrpc": "2.0",
                "method": "public/auth",
                "params": {
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret_key,
                },
            }
            if index:
                res.__setitem__("id", index)
            return res

        def func(self, client_secret: str, client_secret_encrypt):
            try:
                loop = asyncio.new_event_loop()
                # loop.set_debug(True)
                # loop.slow_callback_duration = 0.08
                run_asyncio_debug(loop)
                asyncio.set_event_loop(loop)

                result = threading.Thread(
                    target=lambda: client_secret_encrypt.update(
                        **(
                            loop.run_until_complete(
                                self.encrypt_manager.str_to_encrypt(client_secret)
                            )
                        ),
                    )
                )
                result.start()
                result.join()
                loop.close()
            except Exception as e:
                raise e

    @asynccontextmanager
    async def ws_json(
        self, callback=None, asynccallback=None, *arqs, **kwargs
    ) -> AsyncGenerator[client_ws.ClientWebSocketResponse, None]:
        """

        :param callback and asynccallback: 'await asynccallback(ws, *arqs, **kwargs)' You can send the handler in body\
            this method (the ws_json).Then al the data would be processed inside of method
            When you leave the function callback of empty you will get  the ws attribute.
             You will be able to write the code (example) 'ws.send_json(auth_data)', when the 'auth_data' is a type dictionary.
             You can wrap to the loop and your logic repeat more.
        timinterval - проводим ping на внешний сервер с интервалом в 'timinterval'
        """
        try:
            client_ws = self.client
            with client_ws.initialize() as session:
                async with client_ws.ws_send(session) as conn:
                    async with conn as ws:
                        try:
                            if asynccallback is not None:
                                await asynccallback(ws, *arqs, **kwargs)
                            elif callback is not None:
                                callback(ws, *arqs, **kwargs)
                            else:
                                yield ws

                        finally:
                            await ws.close()
                            await session.close()
        except Exception as e:
            log_err = "[%s]: ERROR => %s" % (
                self.log_t % self.ws_json.__name__,
                e.args[0] if e.args else str(e),
            )
            log.error(str(log_err))
            raise ValueError(str(log_err))

    async def safe_receive_json(self, ws) -> None | dict:
        """
        Безопасное получение JSON с защитой от конкурентного доступа.

        ВАЖНО: В системе должен быть только ОДИН получатель сообщений на WebSocket!
        """
        try:
            # Используем wait_for с обработкой таймаута
            msg = await ws.receive_json()

            if isinstance(msg, dict) and "error" not in msg:
                return msg
            elif isinstance(msg, dict) and "error" in msg:
                log.error(f"WebSocket error: {json.dumps(msg)}")
                return msg
            else:
                # Пинг/понг или бинарные сообщения
                return {}

        except Exception as e:
            log.error(f"Error receiving message: {e}")
            return {}

    def get_subaccount_data(
        self,
        request_id: str | int | None = None,
        access_t: str | None = None,
        with_portfolio=False,
    ) -> dict:
        """
        :param request_id: This is an index your request.
        :param with_portfolio: (bool) True - including data of portfolio or False.
        :return: example ```json
            {
                "jsonrpc": "2.0",
                "id": 4947,
                "method": "private/get_subaccounts",
                "params": { "with_portfolio": True }
            }
            ```
        """
        try:

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "private/get_subaccounts",
                "access_token": access_t,
                "params": {"with_portfolio": with_portfolio},
            }
        except PersonNotFoundAccessError as e:
            log.error(f"PersonNotFoundAccessError: {e}")
            raise e
