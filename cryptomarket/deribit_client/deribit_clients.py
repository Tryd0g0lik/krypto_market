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

import aiohttp
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
from cryptomarket.type.deribit_type import OAuthAutenticationType

log = logging.getLogger(__name__)


# ==============================
# WEBSOCKET ENVIRONMENT
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
    # CLIENT FOR THE BASIC CONNECTION
    # ==============================
    class DeribitClient:
        def __init__(
            self,
            _client_id: str = None,
            _client_secret: str = None,
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
           """
            self.client_id: str = (
                "%s" % DERIBIT_CLIENT_ID if _client_id is None else "%s" % _client_id
            )
            self.client_secret: str = (
                "%s" % DERIBIT_SECRET_KEY
                if _client_secret is None
                else "%s" % _client_secret
            )

        def __new__(cls):
            cls.client_session = aiohttp.ClientSession()
            return super().__new__(cls)

        async def initialize(
            self,
            index,
            _heartbeat=30,
            _timeout=10,
            _url=ExternalAPIEnum.WS_COMMON_URL.value,
        ) -> websockets.WebSocket:
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

            :return:
            """
            log_t = "[%s.%s]: " % (self.__class__.__name__, self.initialize.__name__)
            try:
                ws = self.client_session.ws_connect(
                    url=_url,
                    heartbeat=_heartbeat,
                    timeout=_timeout,
                )
                auth_msg = {
                    "jsonrpc": "2.0",
                    "id": index + 1,
                    "method": "public/auth",
                    "params": {
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                }

                await ws.send_json(auth_msg)
                ws_response = await ws.receive_json()
                return ws_response
            except RuntimeError as e:
                log_tesx = (
                    "%s RuntimeError Connection is not started or closing=> %s"
                    % (log_t, e.args[0] if e.args else str(e))
                )
                log.error(log_tesx)
                raise RuntimeError(log_tesx)
            except ValueError as e:
                log_tesx = "%s ValueError Data is not serializable object => %s" % (
                    log_t,
                    e.args[0] if e.args else str(e),
                )
                log.error(log_tesx)
                raise ValueError(log_tesx)
            except TypeError as e:
                log_tesx = (
                    "%s TypeError Value returned by dumps(data) is not str  => %s"
                    % (log_t, e.args[0] if e.args else str(e))
                )
                log.error(log_tesx)
                raise TypeError(log_tesx)

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

    def __init__(self, max_concurrent=None):
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

    async def enqueue(self, cache_live: int, **kwargs):
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
                # CACHE RAQUEST's BODY DATA
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
                    # CREATE THE QUEUE FROM THE CACHE KEYS
                    # ===============================
                    [self.queue.put(view) for view in keys_in_leave_queue]
                    tasks_collections.clear()

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

    def __error_passed_cached(self, tasks_collections: list):
        """When the value False received from caching. Every error we save in separately list"""
        count_false = tasks_collections.count(False)
        for i in range(count_false):
            position_in_postman = tasks_collections.index(False, i if i == 0 else i + 1)
            # Array from the '_postman' Here is data which have not passed caching on the server
            self._deque_error.append(self._postman[position_in_postman])

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
