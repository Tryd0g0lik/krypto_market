"""
cryptomarket/deribit_client/deribit_clients.py
"""

import asyncio
import json
import logging
from collections import deque
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import Any, AsyncGenerator, Generator

import backoff
from aiohttp import (
    ClientSession,
    ClientWebSocketResponse,
    WSMessageTypeError,
    WSMsgType,
)
from aiohttp.client import _BaseRequestContextManager
from fastapi import websockets
from redis.asyncio import Redis

from cryptomarket.project.enum import ExternalAPIEnum, RadisKeysEnum
from cryptomarket.project.settings.core import app_settings
from cryptomarket.project.settings.settings_env import (
    DERIBIT_CLIENT_ID,
    DERIBIT_SECRET_KEY,
    REDIS_HOST,
    REDIS_PORT,
)
from cryptomarket.project.signals import signal
from cryptomarket.tasks.queues.task_account_user import task_account
from cryptomarket.type.deribit_type import OAuthAutenticationType

log = logging.getLogger(__name__)


# ==============================
# ---- WEBSOCKET ENVIRONMENT
# ==============================
class DeribitWebsocketPool:
    _instance = None
    _connections: list = deque(
        maxlen=app_settings.DERIBIT_MAX_CONCURRENT
    )  # This list is the list[coroutine]. \
    # Below (DeribitWebsocketPool.__new__) he will receive the coroutine for a connection with the Deribit API.
    # The length of list will be containe the quantity of elements == 'app_settings.STRIPE_MAX_QUANTITY_WORKERS'.
    # Everything coroutine/connection will require the:
    # - OAuth 2.0;
    # - client_id from the Deribit;
    # - client_secret from the Deribit.
    _current_index = 0
    _auth_tokens = {}

    # ==============================
    # ---- CLIENT FOR THE BASIC CONNECTION
    # ==============================
    class DeribitClient:
        _semaphore = asyncio.Semaphore(value=1)

        def __init__(
            self, _client_id: str = None, _client_secret: str = None, _limit: int = 1
        ):
            """
           Here we generate of the clients for connection with the Deribit server.
           https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request
           https://docs.deribit.com/articles/deribit-quickstart#websocket-recommended
           Here is creating a list  of the stripe's connections.
           :param _client_id (str|None) This is the secret 'client_id' key from Deribit. Default value is \
               the value of variable the 'DERIBIT_CLIENT_ID'.
           :param _client_secret (str|None) This is the secret 'client_secret' key from Deribit.  Default value is \
               the value of variable the 'DERIBIT_SECRET_KEY'.
            :param _limit (int) This is controller per a joint requests, Default value is 1.
           """

            self.client_id: str = (
                "%s" % DERIBIT_CLIENT_ID if _client_id is None else "%s" % _client_id
            )
            self.__client_secret: str = (
                "%s" % DERIBIT_SECRET_KEY
                if _client_secret is None
                else "%s" % _client_secret
            )

        #
        # def __new__(cls):
        #     cls._client_session = ClientSession()
        #     return super().__new__(cls)

        @backoff.on_exception(
            backoff.expo,
            (ConnectionError,),
            max_tries=3,
            max_time=30,
        )
        async def initialize(
            self,
            index: int | str,
            _heartbeat: int = 30,
            _timeout: int = 10,
            _url: str = ExternalAPIEnum.WS_COMMON_URL.value,
            _method: str = "GET",
            _autoping: bool = False,
        ):
            """
            TODO  данные получить из кеша взамен 'auth_msg'
            https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession
            https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientWebSocketResponse.receive_json
            :param index: This is the 'index' of connection.
            :param _heartbeat (float) – Send ping message every heartbeat seconds and wait pong response, if pong response\
                 is not received then close connection. The timer is reset on any data reception.(optional).\
                  Default value 30 seconds.
            :param _timeout - timeout – a ClientWSTimeout timeout for websocket. By default, the value \
                ClientWSTimeout(ws_receive=None, ws_close=10.0) is used (10.0 seconds for the websocket to close).\
                None means no timeout will be used. Default value is 10 second.
            :param _url Websocket server url, URL or str that will be encoded with URL (see URL to skip encoding).
            :param _method (str) –HTTP method to establish WebSocket connection, 'GET' by default.
            :param _autoping (bool) – automatically send pong on ping message from server. True by default
            :return:
            """
            log_t = "[%s.%s]: " % (self.__class__.__name__, self.initialize.__name__)
            try:
                auth_msg = self.__get_autantication_data(
                    index, self.client_id, self.__client_secret
                )
                # ==============================
                # ---- CREATE CONNECTION TO THE DERIBIT SERVER
                # ==============================
                async with self.client_session() as session:
                    # Connection by the WebSocker cannel
                    async with self.ws_send(
                        session, _heartbeat, _timeout, _url, _method, _autoping
                    ) as ws:
                        # Controller
                        async with self._semaphore:
                            try:
                                # Data sending
                                await ws.send_json(auth_msg)
                                async for msg in ws:
                                    if msg.type == WSMsgType.TEXT:
                                        print(f"Received: {msg.data}")
                                        log.warning(f"WS Received: {msg.data}")
                                    elif msg.type == WSMsgType.ERROR:
                                        log_err = "%s ERROR connection. Code: %s" % (
                                            log_t,
                                            msg.value,
                                        )
                                        log.error(str(log_err))
                                        raise ValueError(str(log_err))

                                    elif msg.type == WSMsgType.CLOSED:
                                        log.warning(
                                            "%s Closing connection. Code: %s"
                                            % (log_t, msg.data)
                                        )
                                        break

                            except WSMessageTypeError as e:
                                log_err = (
                                    "%s WSMessageTypeError message is not TEXT => %s"
                                    % (log_t, e.args[0] if e.args else str(e))
                                )
                                log.error(str(log_err))
                                raise WSMessageTypeError(str(log_err))
                            except RuntimeError as e:
                                log_err = (
                                    "%s RuntimeError Connection is not started or closing => %s"
                                    % (log_t, e.args[0] if e.args else str(e))
                                )
                                log.error(str(log_err))
                                raise RuntimeError(str(log_err))
                            except ValueError as e:
                                log_err = (
                                    "%s ValueError Data is not serializable object => %s"
                                    % (log_t, e.args[0] if e.args else str(e))
                                )
                                log.error(str(log_err))
                                raise ValueError(str(log_err))
                            except TypeError as e:
                                log_err = (
                                    "%s Value returned by dumps(data) is not str => %s"
                                    % (log_t, e.args[0] if e.args else str(e))
                                )
                                log.error(str(log_err))
                                raise TypeError(str(log_err))
                """

                Check a connection and ???

                """

            except Exception as e:
                log_err = "%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e))
                log.error(str(log_err))
                raise ValueError(str(log_err))

        @asynccontextmanager
        async def client_session(self) -> AsyncGenerator[ClientSession, Any]:
            log_t = "[%s.%s]:" % (self.__class__.__name__, self.client_session.__name__)
            _client_session = ClientSession()
            log.info("%s %s" % (log_t, "Client session opening!"))
            try:
                yield _client_session
            except Exception as e:
                log.error("%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e)))
            finally:
                await _client_session.close()
                log.info("%s %s" % (log_t, "Client session closed!"))

        @asynccontextmanager
        async def ws_send(
            self,
            _client_session: ClientSession,
            _heartbeat: int = 30,
            _timeout: int = 10,
            _url: str = ExternalAPIEnum.WS_COMMON_URL.value,
            _method: str = "GET",
            _autoping: bool = True,
        ) -> AsyncGenerator[_BaseRequestContextManager[ClientWebSocketResponse], Any]:
            """
            WebvSocket connection on the Deribit server.
                :param index: This is the 'index' of connection.
                :param _heartbeat (float) – Send ping message every heartbeat seconds and wait pong response, if pong response\
                     is not received then close connection. The timer is reset on any data reception.(optional).\
                      Default value 30 seconds.
                :param _timeout - timeout – a ClientWSTimeout timeout for websocket. By default, the value \
                    ClientWSTimeout(ws_receive=None, ws_close=10.0) is used (10.0 seconds for the websocket to close).\
                    None means no timeout will be used. Default value is 10 second.
                :param _url Websocket server url, URL or str that will be encoded with URL (see URL to skip encoding).
                :param _method (str) –HTTP method to establish WebSocket connection, 'GET' by default.
                :param _autoping (bool) – automatically send pong on ping message from server. True by default
                :param _client_session:
                :return:
            """
            log_t = "[%s.%s]:" % (self.__class__.__name__, self.ws_send.__name__)
            log.info("%s %s" % (log_t, "WebSocket connection is successfully!"))
            ws = _client_session.ws_connect(
                url=_url,
                heartbeat=_heartbeat,
                timeout=_timeout,
                method=_method,
                autoping=_autoping,
            )
            try:
                log.info("%s %s" % (log_t, "WebSocket connection is closed!"))
                yield ws
            except Exception as e:
                log.error("%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e)))
            finally:
                ws.close()
                log.info("%s %s" % (log_t, "WebSocket connection is closed!"))

        @staticmethod
        def __get_autantication_data(
            index: int, client_id: int | str, client_secret_key: str
        ) -> dict:
            return {
                "jsonrpc": "2.0",
                "id": index + 1,
                "method": "public/auth",
                "params": {
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret_key,
                },
            }

    def __new__(
        cls,
        _client_id: str = None,
        _client_secret: str = None,
        _heartbeat=30,
        _timeout=10,
    ):
        """
        Here we generate of the clients for connection with the Deribit server.
        https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request
        https://docs.deribit.com/articles/deribit-quickstart#websocket-recommended
        Here is creating a list  of the stripe's connections.

        :param _client_id: str|None This is the secret 'client_id' key from Deribit. Default value is \
            the value of variable the 'DERIBIT_CLIENT_ID'.
        :param _client_secret: str|None This is the secret 'client_secret' key from Deribit.  Default value is \
            the value of variable the 'DERIBIT_SECRET_KEY'.
        :param _heartbeat (float) – Send ping message every heartbeat seconds and wait pong response, if pong response\
             is not received then close connection. The timer is reset on any data reception.(optional).\
              Default value 30 seconds.
        :param _timeout - timeout – a ClientWSTimeout timeout for websocket. By default, the value \
            ClientWSTimeout(ws_receive=None, ws_close=10.0) is used (10.0 seconds for the websocket to close).\
            None means no timeout will be used. Default value is 10 second.


        """
        if not cls._instance:
            cls._instance = super().__new__(cls)

            client_session = cls.DeribitClient(_client_id, _client_secret)
            # This is creating the coroutines for clients (entry points or entry windows).
            # Everyone coroutine for connections with the Deribit.
            # Max quantity of coroutines contain value require - the 'app_settings.DERIBIT_MAX_QUANTITY_WORKERS',
            # it is the max number of connection.
            for i in range(app_settings.DERIBIT_MAX_QUANTITY_WORKERS):
                ws = client_session.initialize(i, _heartbeat, _timeout)
                cls._connections.append(ws)
        return cls._instance

    def get_connection(self) -> DeribitClient.initialize:
        """
        HEre we received the one coroutine for connection to the Deribit server.
        Coroutine receive by index. It's from 0 before 'app_settings.DERIBIT_MAX_QUANTITY_WORKERS'.
        :return: DeribitClient.initialize (coroutine).
        """
        conn = self._connections[
            (
                self._current_index
                if self._current_index < app_settings.DERIBIT_MAX_QUANTITY_WORKERS
                and self._current_index
                < app_settings.DERIBIT_MAX_QUANTITY_WORKERS
                <= app_settings.DERIBIT_MAX_CONCURRENT
                else app_settings.DERIBIT_MAX_CONCURRENT - 1
            )
        ]

        # Resent the cls._current_index
        self._current_index = (self._current_index + 1) % len(self._connections)
        return conn


class DeribitLimited:
    """
    This is limiter for a one user and  protection the Stripe's server. Example. We often make requests to the server \
            and could  receive an error or waiting a long time. Here we begin to repeat it  \
            a single request more and more.
            So, the method 'DeribitLimited.acquire' is our calculater/limiter for the one user's request to \
                the Stripe server.
    :param max_concurrent: int. Default value is 40 means - app can send no more than 'max_concurrent' request\
            per one second.
    :param sleep: float. This is a delay in seconds. Everytime when our user exceeds the limit:
        - we add additional seconds for a sleep;
        - say him to sleep/relax.
    """

    def __init__(
        self, max_conrurrents: int = app_settings.DERIBIT_MAX_CONCURRENT, _sleep=0.1
    ):
        self.semaphore = asyncio.Semaphore(max_conrurrents)
        self.sleep = _sleep

    def context_redis_connection(self):
        redis = Redis(
            f"{REDIS_HOST}",
            f"{REDIS_PORT}",
        )
        try:
            yield redis
        except Exception as e:
            log.error(
                "[%s.%s]: RedisError => %s"
                % (
                    DeribitLimited.__class__.__name__,
                    self.context_redis_connection.__name__,
                    e.args[0] if e.args else str(e),
                )
            )
        finally:
            redis.close()

    @asynccontextmanager
    async def acquire(self, redis, task_id: str, user_id: str, cache_limit: int = 95):
        """
        This is the rate/request (it concurrently requests/websocket of one user) limited.
        This is counting what Radis has no more than 100 request per 1 second.
        - 'self.semaphore' Limits the number of simultaneous operations Default value in app \
            settings - the var/  'DERIBIT_MAX_CONCURRENT'.
        - "current_request"  Limit per a parallel resuest.
        :param task_id: This is index of task for which execution the user could be  to make a concurrent/parallel \
            request to Stripe. Here make a limit. It must be less than 'cache_limit'
        :param cache_limit: This is the redis's limit. 100 request in Redis is available on one second.
        :return:
        """
        # Параллельные запросы на оду задачу
        key = RadisKeysEnum.DERBIT_STRIPE_RATELIMIT_TASK.value % (
            user_id,
            task_id,
        )
        current_request = redis.get(key)
        try:
            # Checking our limits per a parallel requests
            if current_request and int(current_request) > cache_limit:
                key_current_sleep = redis.get(f"sleep:{key}")
                await asyncio.sleep(self.sleep)
                if key_current_sleep:
                    self.sleep += 0.1
                    await asyncio.to_thread(lambda: redis.incr(f"sleep:{key}", 1))
                    await asyncio.to_thread(lambda: redis.expire(f"sleep:{key}", 2))

            async with self.semaphore:
                # create 0 or  +1 (if key exists) request in th total quantity of user requests
                # This is 100 in second for one task
                await asyncio.to_thread(lambda: redis.incr(key, 1))
                await asyncio.to_thread(lambda: redis.expire(key, 1))
                try:
                    yield task_id
                finally:
                    # write logic of code by less current/calculater if all successfully.
                    pass

        except ValueError as e:
            log_t = "[%s.%s]: ValueError => %s" % (
                self.__class__.__name__,
                self.acquire.__name__,
                e.args[0] if e.args else str(e),
            )
            log.error(log_t)
            raise
        except Exception as e:
            log_t = "[%s.%s]: Error => %s" % (
                self.__class__.__name__,
                self.acquire.__name__,
                e.args[0] if e.args else str(e),
            )
            log.error(log_t)
            print(log_t)
            raise


class DeribitCreationQueue:
    _postman = deque(maxlen=5000)
    _deque_error = deque(maxlen=10000)  # Which have not passed caching

    def __init__(self, max_concurrent=None) -> None:
        """
        :param max_concurrent: int.  This is our calculater/limiter for the one user's requests to the Stripe server. \
            Rate/ limitation quantities of requests per 1 second from one user (it is request to the Stripe server) .
            Default value is number from  the variable of 'app_settings.STRIPE_MAX_CONCURRENT'.

        """
        self.queue = asyncio.Queue(maxsize=app_settings.STRIPE_QUEUE_SIZE)

        self.processing_tasks = set()
        self.rate_limit: DeribitLimited | None = DeribitLimited()
        self.connection_pool = DeribitWebsocketPool()
        if max_concurrent is not None:
            self.rate_limit = DeribitWebsocketPool(max_concurrent)
        self.stripe_response_var = ContextVar("deribit_response", default=None)
        self.stripe_response_var_token = None

    async def enqueue(self, cache_live: int, **kwargs) -> None:
        """
        We can have a big flow of requests. Means make a limit on the server through caching and queues.
        :param kwargs:
            - OAuthAutenticationType type of kwargs data if we wanted the user to authenticate.
        :param cache_live: int - second. This is live time of cache.
        :return:
        """
        log_t = "[%s.%s]:" % (self.__class__.__name__, self.enqueue.__name__)
        try:
            loog_err = "%s ERROR => %s" % (log_t, "API URL did not find!")
            if kwargs is not None and isinstance(kwargs, OAuthAutenticationType):
                # Remove an aPI key from kwargs and we leave the kwargs without url
                api_key = kwargs.pop("api_key")
                # This is key for queue and task
                task_id = "%s:%s" % (
                    (
                        (api_key.split("://"))[0]
                        if api_key is not None
                        else ValueError(str(loog_err))
                    ),
                    str(datetime.now().strftime("%Y%m%d%H%M%S")),
                )
                # The general key from a user data and the user data add in joint/general list
                self._postman.append({str(task_id): kwargs})

        except ValueError as err:
            raise err.args[0] if err.args else str(err)

        try:
            if len(self._postman) > 0:
                # ===============================
                # ---- CACHE RAQUEST's BODY DATA
                # ===============================
                # cache of the user data
                contex_redis_connection = self.rate_limit.context_redis_connection

                with contex_redis_connection() as redis:
                    redis_setex = redis.setex
                    # List a coroutines for send to the caching server
                    # k - key common between the cache data and queue
                    # v - the cache data
                    # tasks_collections - gather results after cache on the server.
                    tasks_collections = deque(maxlen=5000)
                    [
                        tasks_collections.append(
                            redis_setex(
                                k,
                                cache_live,
                                (
                                    json.dumps(v)
                                    if isinstance(v, dict | list | str | int | bool)
                                    else str(v)
                                ),
                            )
                        )
                        for view in self._postman
                        for k, v in [next(iter(view.items()))]
                    ]
                    # Checking the 'tasks_collections' after caching.
                    if not all(tasks_collections):
                        self.__error_passed_cached(list(tasks_collections))

                    # The list of keys from the data cached on the server
                    keys_in_leave_queue = [
                        key
                        for view in self._postman.pop()
                        for key, val in [next(iter(view.items()))]
                        if val is not None and key not in list(self._deque_error)
                    ]
                    # ===============================
                    # ---- CREATE THE QUEUE FROM THE CACHE KEYS
                    # ===============================
                    [self.queue.put(view) for view in keys_in_leave_queue]
                    tasks_collections.clear()
                    # ===============================
                    # ---- RAN SIGNAL
                    # ===============================
                    await signal.schedule_with_delay(task_account, *keys_in_leave_queue)
            else:
                log.warning(
                    str(
                        "%s WARNING => %s"
                        % (
                            log_t,
                            "Something what wrong. The '_postman' queue is empty!",
                        )
                    )
                )

        except Exception as e:
            log.error(str("%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e))))

    def __error_passed_cached(self, tasks_collections: list) -> None:
        """When the value False received from caching. Every error we save in separately list"""
        count_false = tasks_collections.count(False)
        for i in range(count_false):
            position_in_postman = tasks_collections.index(False, i if i == 0 else i + 1)
            # Array from the '_postman' Here is data which have not passed caching on the server
            self._deque_error.append(self._postman[position_in_postman])

    # async def _process_queue_worker(
    #     self,
    #     work_id: str,
    #     handler: QueueHandlerFunc = None,
    # ) -> None:

    # def _start_worker(self, tasks: list[], limitations=40,):
    #     """
    #     :param limitations:int This is number for limitation the parallels tasks at the cache moment
    #     :param limitations:
    #     :return:
    #     """
    #     try:
    #         # ===============================
    #         # RAN THE CACHE
    #         # ===============================
    #         # 40 This is number for limitations the parallels tasks at the cache moment.
    #         for i in range(0, len(tasks_collections), 40):
    #             new_list = []
    #             for patch in tasks_collections[i:i + 40]:
    #                 new_list.append(patch)
    #             await asyncio.gather(*new_list)
    #         tasks_collections.clear()
    #     except Exception as err:
    #         loog_err = "%s ERROR => %s" % (str(log_t), err.args[0] if err.args else str(err))
    #         log.error(str(loog_err))
