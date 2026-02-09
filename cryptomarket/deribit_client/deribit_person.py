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

import logging
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from types import coroutine

from aiohttp import client_ws
from blib2to3.pgen2.parse import contextmanager

from cryptomarket.project.enums import ExternalAPIEnum
from cryptomarket.project.functions import obj_to_byte

log = logging.getLogger(__name__)


class Person:
    """
    TODO: В данный момент  'person_is' отсутствует.
        Получить его через MIDDLEWARE и JWT токен
    """

    def __init__(
        self,
        _access_token,
        _refresh_token,
        expires_in,
        last_activity=datetime.now().timestamp(),
        person_id=None,
    ):
        self.person_id = person_id
        self.__access_token: str = _access_token
        self.expires_in: int = expires_in
        self.__refresh_token: str = _refresh_token
        self.lact_activity: float = last_activity
        self.ws: client_ws.ClientWebSocketResponse | None = None

    @asynccontextmanager
    async def ws_send(self, client: coroutine):
        session = client.initialize(_url=ExternalAPIEnum.WS_COMMON_URL.value)
        ws = await client.ws_send(session)
        try:
            yield ws
        except Exception as e:
            pass
        finally:
            pass

    @property
    def get_access_token(self) -> str:
        return self.__access_token

    @property
    def get_refresh_token(self) -> str:
        return self.__refresh_token


# class PersonManager:
#     def __init__(self):
#         """
#         TODO: Timeout создать через кеш .
#             Как только в set() добавляем образ от person, в кеш заносим ключ от person с timeout/
#             При каждом новосм обращении  к PersonManager - отдельным потоком запустить
#             проверку ключа в кеше. Если ключ в кеше не найден, удалить персону из set().
#             Время жизни  ключа в кеше взять мз access_token.
#         """
#
#         self.__access_persons: deque = deque(
#             maxlen=10000
#         )  # {< KEY:person_id >: < Peron's Image >}
#
#
#
#     def add(self, _access_token, _refresh_token,expires_in,  lact_activity, person_id=None):
#         person = self.Person(_access_token, _refresh_token,expires_in,  lact_activity, person_id)
#
#         self.__access_persons.append({person.person_id: obj_to_byte(person)})

# async def get(self, person_id: int) -> Person:
#     """
#     TODO: Добавить проверку ключ от person в кеш
#     """
#     pass
# index = self.__access_persons.count()
# if person_id is None :
# self.__access_persons
# return
#
# def is_person(self, person_id):
#     if person_id is None and self.__access_persons.count(person_id):
#         log.info("The person was an existing one!")
#         return
