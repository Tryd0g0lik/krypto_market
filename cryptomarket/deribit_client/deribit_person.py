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
from datetime import datetime
from sys import maxsize

from aiohttp import client_ws

from cryptomarket.errors import DeribitValueError
from cryptomarket.errors.person_errors import (
    PersonDictionaryError,
    PersonNotFoundAccessError,
)
from cryptomarket.project.encrypt_manager import EncryptManager
from cryptomarket.project.functions import wrapper_delayed_task
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
            key = key.lower() if () else key
            if maxsize is not None and len(self) >= maxsize:
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
    person_dict = PersonDictionary(maxsize=setting.DERIBIT_QUEUE_SIZE)

    def add(
        self,
        client_id,
        person_id,
        last_activity=datetime.now().timestamp(),
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
            last_activity=datetime.now().timestamp(),
        ):
            self.person_id = person_id
            self.__deribit_client_id = client_id
            self.__access_token: str | None = None
            self.expires_in: int | None = None
            self.__refresh_token: str | None = None
            self.last_activity: float = last_activity  # last time when
            self.ws: client_ws.ClientWebSocketResponse | None = None
            self.active: bool = True
            self.__client_secret_encrypt: bytes | None = None
            self.__key_encrypt: bytes | None = None
            self.key_of_queue: str | None = None
            self.scope: str | None = None
            self.token_type: str | None = None
            self.msg: dict | None = None
            self.client: DeribitClient | None = None
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
                self.__client_secret_encrypt.decode()
                if self.__client_secret_encrypt
                else None
            )

        @client_secret_encrypt.setter
        def client_secret_encrypt(self, client_secret: str) -> None:
            """
            Async
            :param client_secret:
            :return:
            """
            try:

                client_secret_encrypt: dict[str, str] = {}

                def func():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        result = threading.Thread(
                            target=lambda: client_secret_encrypt.update(
                                **(
                                    loop.run_until_complete(
                                        self.encrypt_manager.str_to_encrypt(
                                            client_secret
                                        )
                                    )
                                ),
                            )
                        )
                        result.start()
                        result.join()
                        loop.close()
                    except Exception as e:
                        raise e

                func()

                self.__key_encrypt = list(client_secret_encrypt.keys())[0].encode()
                self.__client_secret_encrypt = list(client_secret_encrypt.values())[
                    0
                ].encode()
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

        async def ws_json(self, timinterval: float = 15.0, **kwargs) -> None:
            """
            :param _json: (dict) {"method": < deribit private or public >
                "params":{....}, "id": < request index >
            }
            """
            from cryptomarket.project.app import manager

            _json = kwargs.copy()
            sse_manager = manager.sse_manager
            try:
                client_ws = self.client
                user_meta_json = _json.copy()
                user_meta_json.pop("request_data")
                _json = _json.pop("request_data")
                with client_ws.initialize() as session:
                    async with client_ws.ws_send(session) as ws:
                        while self.active:
                            pool_pool: float = (
                                datetime.now().timestamp() - self.last_activity
                            )

                            access_t = self.access_token
                            refresh_t = self.refresh_token
                            auth_data = {}
                            if (
                                access_t is None
                                and refresh_t is None
                                and self.__client_secret_encrypt is not None
                                and self.__key_encrypt is not None
                            ):
                                # ===============================
                                # ---- AUTHENTICATE
                                # ===============================
                                user_secret = self.encrypt_manager.descrypt_to_str(
                                    {self.__key_encrypt: self.__client_secret_encrypt}
                                )
                                auth_data = self._get_autantication_data(
                                    self.client_id, user_secret
                                )
                            elif access_t and _json is not None and "jsonrpc" in _json:
                                if (
                                    self.__access_token is None
                                    or len(self.__access_token) < 10
                                ):
                                    log.info(
                                        "DEBUG WS 1 ERROR %s.%s  ",
                                        self.__class__.__name__,
                                        self.ws_json.__name__,
                                    )
                                    raise PersonNotFoundAccessError()
                                _json.__setitem__("access_token", access_t)
                                auth_data = _json.copy()

                            if len(_json) == 0 and pool_pool >= timinterval:
                                log.info(
                                    "DEBUG WS PING %s.%s ",
                                    self.__class__.__name__,
                                    self.ws_json.__name__,
                                )
                                await ws.ping()
                                continue

                            if "jsonrpc" not in _json:
                                continue
                            await asyncio.wait_for(ws.send_json(auth_data), timeout=10)
                            msg_data = await self._safe_receive_json(ws)
                            if msg_data is not None and "error" not in msg_data.keys():
                                log.info(
                                    "DEBUG MESSAGE %s.%s ",
                                    (self.__class__.__name__, self.ws_json.__name__),
                                )
                                method = auth_data.get("method")
                                # ===============================
                                # ---- SENDING DATA
                                # ===============================
                                if method == "public/auth":
                                    self.access_token = msg_data["result"][
                                        "access_token"
                                    ]
                                    self.refresh_token = msg_data["result"][
                                        "refresh_token"
                                    ]
                                    self.expires_in = msg_data["result"]["expires_in"]
                                    self.scope = msg_data["result"]["scope"]
                                    self.token_type = msg_data["result"]["token_type"]

                                    self.msg = msg_data.copy()

                                else:
                                    self.msg = msg_data.copy()

                            elif msg_data is not None and "error" in msg_data.keys():
                                self.msg = msg_data.copy()
                            else:
                                pass
                            if self.msg is not None and len(self.msg) > 0:
                                msg = self.msg.copy()
                                result_kwargs_new: dict = {**msg}
                                result_kwargs_new.__setitem__(
                                    "user_meta", user_meta_json
                                )

                                await sse_manager.broadcast(result_kwargs_new)
                                self.msg.clear()
                            del msg_data
                            _json = {}

            except Exception as e:
                self.active = False
                log.info(
                    "DEBUG WS 2 ERROR %s.%s  ",
                    self.__class__.__name__,
                    self.ws_json.__name__,
                )
                log_err = "[%s]: ERROR => %s" % (
                    self.log_t % self.ws_json.__name__,
                    e.args[0] if e.args else str(e),
                )
                log.error(str(log_err))
                raise ValueError(str(log_err))

        def _get_autantication_data(
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
                    % (self.log_t % self.ws_json.__name__)
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

        def get_subaccount_data(
            self, request_id: str | int | None = None, with_portfolio=False
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

                access_t = self.access_token
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

        async def _safe_receive_json(self, ws) -> None | dict:
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
                    return None

            except Exception as e:
                log.error(f"Error receiving message: {e}")
                return None
