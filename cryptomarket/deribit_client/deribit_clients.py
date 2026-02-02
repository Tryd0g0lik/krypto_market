"""
cryptomarket/deribit_client/deribit_clients.py
"""

import asyncio
import json
import logging
from collections import deque
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from datetime import datetime

from aiohttp import (
    ClientSession,
)
from redis.asyncio import Redis

from cryptomarket.deribit_client.deribit_person import PersonManager
from cryptomarket.project.enums import ExternalAPIEnum, RadisKeysEnum
from cryptomarket.project.settings.core import settings
from cryptomarket.project.settings.settings_env import (
    REDIS_DB,
    REDIS_HOST,
    REDIS_PORT,
)
from cryptomarket.project.signals import signal
from cryptomarket.project.sse_manager import SSEManager
from cryptomarket.tasks.queues.task_account_user import task_account
from cryptomarket.type import (
    DeribitClientType,
    DeribitLimitedType,
    DeribitManageType,
    DeribitWebsocketPoolType,
)

log = logging.getLogger(__name__)

setting = settings()


# ==============================
# ---- WEBSOCKET ENVIRONMENT
# ==============================
class DeribitWebsocketPool(DeribitWebsocketPoolType):
    _instance = None
    # This list is the list[coroutine].
    _clients: list = deque(maxlen=setting.DERIBIT_QUEUE_SIZE)
    # Below (DeribitWebsocketPool.__new__) he will receive the coroutine for a connection with the Deribit API.
    # The length of list will be containe the quantity of elements == 'setting.STRIPE_MAX_QUANTITY_WORKERS'.
    # Everything coroutine/connection will require the:
    # - OAuth 2.0;
    # - client_id from the Deribit;
    # - client_secret from the Deribit.
    _current_index = 0
    _auth_tokens = {}

    # ==============================
    # ---- CLIENT FOR THE BASIC CONNECTION
    # ==============================
    class DeribitClient(DeribitClientType):
        _semaphore = asyncio.Semaphore(value=1)

        # def __init__(
        #     self,
        # ):
        #     """
        #    Here we generate of the clients for connection with the Deribit server.
        #    https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request
        #    https://docs.deribit.com/articles/deribit-quickstart#websocket-recommended
        #    Here is creating a list  of the stripe's connections.
        #    :param _client_id (str|None) This is the secret 'client_id' key from Deribit. Default value is \
        #        the value of variable the 'DERIBIT_CLIENT_ID'.
        #    :param _client_secret (str|None) This is the secret 'client_secret' key from Deribit.  Default value is \
        #        the value of variable the 'DERIBIT_SECRET_KEY'.
        #     # :param _limit (int) This is controller per a joint requests, Default value is 1.
        #    """
        #     super().__init__()

        # self.client_id: str|None = None
        # self.__client_secret: str| None = None

        @contextmanager
        def initialize(
            self,
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
                # ==============================
                # ---- CREATE CONNECTION TO THE DERIBIT SERVER
                # ==============================
                log_t = "[%s.%s]:" % (
                    self.__class__.__name__,
                    self.client_session.__name__,
                )
                _client_session = ClientSession(_url)
                log.info("%s %s" % (log_t, "Client session opening!"))
                try:
                    yield _client_session
                except Exception as e:
                    log.error(
                        "%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e))
                    )
                finally:
                    _client_session.close()
                    pass
                # __connection = self.__client_session(_url)
                # try:
                #     yield __connection
                # finally:
                #     pass
            except Exception as e:
                log_err = "%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e))
                log.error(str(log_err))
                raise ValueError(str(log_err))

        # def __client_session(self, base_ur):
        #     log_t = "[%s.%s]:" % (self.__class__.__name__, self.client_session.__name__)
        #     _client_session = ClientSession(base_ur)
        #     log.info("%s %s" % (log_t, "Client session opening!"))
        #     try:
        #         return _client_session
        #     except Exception as e:
        #         log.error("%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e)))
        #     finally:
        #         _client_session.close()
        #         pass

        @asynccontextmanager
        async def ws_send(
            self,
            _client_session: ClientSession,
            _heartbeat: int = 30,
            _timeout: int = 10,
            _url: str = ExternalAPIEnum.WS_COMMON_URL.value,
            _method: str = "GET",
            _autoping: bool = True,
        ):
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
            if _client_session is None:
                raise ValueError(
                    "[%s]: ERROR => The '_client_session' is required variable!",
                    (DeribitWebsocketPool.__class__.__name__,),
                )

            log_t = "[%s.%s]:" % (self.__class__.__name__, self.ws_send.__name__)
            log.info("%s %s" % (log_t, "WebSocket connection is successfully!"))
            ws_connect = _client_session.ws_connect(
                url=_url,
                heartbeat=_heartbeat,
                timeout=_timeout,
                method=_method,
                autoping=_autoping,
            )
            async with ws_connect as ws:
                try:
                    log.info("%s %s" % (log_t, "WebSocket connection is closed!"))
                    yield ws
                except Exception as e:
                    log.error(
                        "%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e))
                    )
                finally:
                    await ws.close()
                    log.info("%s %s" % (log_t, "WebSocket connection is closed!"))

        @staticmethod
        def _get_autantication_data(
            index: int, client_id: int | str, client_secret_key: str
        ) -> dict:
            if client_id is None or client_secret_key is None:
                raise ValueError(
                    "[%s]: ERROR => Client id and secret key are required variables!",
                    (DeribitWebsocketPool.__class__.__name__,),
                )

            return {
                "jsonrpc": "2.0",
                "id": index,
                "method": "public/auth",
                "params": {
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret_key,
                },
            }

    def __new__(
        cls,
        # _client_id: str = None,
        # _client_secret: str = None,
        _heartbeat=30,
        _timeout=10,
    ):
        """
        Here we generate of the clients for connection with the Deribit server.
        https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request
        https://docs.deribit.com/articles/deribit-quickstart#websocket-recommended
        Here is creating a list  of the stripe's connections.

        :param _client_id: str|None This is the secret 'client_id' key from Deribit.
        :param _client_secret: str|None This is the secret 'client_secret' key from Deribit.
        :param _heartbeat (float) – Send ping message every heartbeat seconds and wait pong response, if pong response\
             is not received then close connection. The timer is reset on any data reception.(optional).\
              Default value 30 seconds.
        :param _timeout - timeout – a ClientWSTimeout timeout for websocket. By default, the value \
            ClientWSTimeout(ws_receive=None, ws_close=10.0) is used (10.0 seconds for the websocket to close).\
            None means no timeout will be used. Default value is 10 second.


        """
        if not cls._instance:
            cls._instance = super().__new__(cls)
            # This is creating the coroutines for clients (entry points or entry windows).
            # Everyone coroutine for connections with the Deribit.
            # Max quantity of coroutines contain value require - the 'setting.DERIBIT_MAX_QUANTITY_WORKERS',
            # it is the max number of connection.
            for i in range(setting.DERIBIT_MAX_QUANTITY_WORKERS):
                client_ = cls.DeribitClient()
                cls._clients.append(client_)
        return cls._instance

    def get_clients(self) -> DeribitClient.initialize:
        """
        HEre we received the one coroutine for connection to the Deribit server.
        Coroutine receive by index. It's from 0 before 'setting.DERIBIT_MAX_QUANTITY_WORKERS'.
        :return: DeribitClient.initialize (coroutine).
        10 clients is everything
        """
        conn = self._clients[
            (
                self._current_index
                if self._current_index < setting.DERIBIT_MAX_QUANTITY_WORKERS
                and self._current_index
                < setting.DERIBIT_MAX_QUANTITY_WORKERS
                <= setting.DERIBIT_MAX_CONCURRENT
                else setting.DERIBIT_MAX_CONCURRENT - 1
            )
        ]

        # Resent the cls._current_index
        self._current_index = (self._current_index + 1) % len(self._clients)
        return conn


# ==============================
# ---- LIMIT BY USE
# ==============================
class DeribitLimited(DeribitLimitedType):
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
        self, max_conrurrents: int = setting.DERIBIT_MAX_CONCURRENT, _sleep=0.1
    ):
        self.semaphore = asyncio.Semaphore(max_conrurrents)
        self.sleep = _sleep

    @asynccontextmanager
    async def context_redis_connection(self):
        redis = Redis(
            host=f"{REDIS_HOST}",
            port=int(REDIS_PORT),
            db=int((lambda: f"{REDIS_DB}")()),
        )
        try:
            yield redis
        except Exception as e:
            log.error(
                "[%s.%s]: RedisError => %s"
                % (
                    self.__class__.__name__,
                    self.context_redis_connection.__name__,
                    e.args[0] if e.args else str(e),
                )
            )
        finally:
            await redis.close()

    @asynccontextmanager
    async def acquire(self, redis, task_id: str, user_id: str, cache_limit: int = 95):
        """
        TODO: Не использован (рабочий и протестирован). но хороший контролер за количество запросов в секунду и
            количеством запросов от одного пользователя в секунду
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
        current_request = await redis.get(key)
        try:
            # Checking our limits per a parallel requests
            if current_request and int(current_request) > cache_limit:
                key_current_sleep = await redis.get(f"sleep:{key}")
                await asyncio.sleep(self.sleep)
                if key_current_sleep:
                    self.sleep += 0.1
                    await redis.incr(f"sleep:{key}", 1)
                    await redis.expire(f"sleep:{key}", 2)

            async with self.semaphore:
                # create 0 or  +1 (if key exists) request in th total quantity of user requests
                # This is 100 in second for one task
                await redis.incr(key, 1)
                await redis.expire(key, 1)
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


# ==============================
# ---- DERIBIT MENEGE
# ==============================
class DeribitManage(DeribitManageType):
    _deque_postman = deque(maxlen=setting.DERIBIT_QUEUE_SIZE)
    _deque_error = deque(maxlen=10000)  # Which have not passed caching
    _deque_coroutines = deque(
        maxlen=500
    )  # Coroutine of workers / Look to the 'self.start_worker' & and the tasks.
    # Tasks this are place where we can use the '_deque_coroutines'
    _sleep = 1  # second

    def __init__(self, max_concurrent=None) -> None:
        """
        :param max_concurrent: int.  This is our calculater/limiter for the one user's requests to the Stripe server. \
            Rate/ limitation quantities of requests per 1 second from one user (it is request to the Stripe server) .
            Default value is number from  the variable of 'setting.STRIPE_MAX_CONCURRENT'.
        :param 'sse_manager' THis is manager of queue

        """
        super().__init__()

        self.queue = asyncio.Queue(maxsize=setting.DERIBIT_QUEUE_SIZE)
        self.rate_limit: DeribitLimited | None = DeribitLimited()
        self.client_pool: DeribitWebsocketPoolType | None = DeribitWebsocketPool(
            _heartbeat=30,
            _timeout=10,
        )
        if max_concurrent is not None:
            self.rate_limit = DeribitLimited(max_concurrent)
        self.stripe_response_var = ContextVar("deribit_response", default=None)
        self.stripe_response_var_token = None
        args = ("btc_usd", "eth_usd", "connection")
        self.sse_manager = SSEManager(*args)
        self.person_manager = PersonManager()

    async def enqueue(self, cache_live: int, **kwargs) -> None:
        """
        We can have a big flow of requests. Means make a limit on the server through caching and queues.
        :param kwargs:
            - OAuthAutenticationType type of kwargs data if we wanted the user to authenticate.
        :param cache_live: int - second. This is live time of cache.
        :return:
        """
        log_t = "[%s.%s]:" % (self.__class__.__name__, self.enqueue.__name__)
        register_id = kwargs.get("request_id")
        try:
            loog_err = "%s RequestID %s ERROR => %s" % (
                log_t,
                register_id,
                "API URL did not find!",
            )
            if kwargs is not None:
                # Remove an aPI key from kwargs and we leave the kwargs without url
                api_key = kwargs.get("api_key")
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
                self._deque_postman.append({str(task_id): kwargs})

        except ValueError as err:
            raise err.args[0] if err.args else str(err)
        # (lambda: "%s" % kwargs["client_id"])(),
        # (lambda: "%s" % kwargs["deribit_secret_encrypt"])(),
        try:
            self.client_pool = DeribitWebsocketPool(
                _heartbeat=30,
                _timeout=10,
            )
            if len(self._deque_postman) > 0:
                # ===============================
                # ---- CACHE RAQUEST's BODY DATA
                # ===============================
                # cache of the user data
                context_redis_connection = self.rate_limit.context_redis_connection

                async with context_redis_connection() as redis:
                    redis_setex = redis.setex
                    # List a coroutines for send to the caching server
                    # k - key common between the cache data and queue
                    # v - the cache data
                    # tasks_collections - gather results after cache on the server.
                    tasks_collections = deque(maxlen=setting.DERIBIT_QUEUE_SIZE)
                    result_list = [
                        redis_setex(
                            k,
                            cache_live,
                            json.dumps(v),
                        )
                        for view in list(self._deque_postman)
                        for k, v in view.items()
                    ]
                    result = await asyncio.gather(*result_list)
                    tasks_collections.append(result)

                    # Checking the 'tasks_collections' after caching.
                    if not all(tasks_collections):
                        self.__error_passed_cached(list(tasks_collections))

                    # The list of keys from the data cached on the server
                    keys_in_leave_queue = [
                        key
                        for view in list(self._deque_postman)
                        for key, val in view.items()
                        if val is not None and key not in list(self._deque_error)
                    ]

                    # ===============================
                    # ---- CREATE THE QUEUE FROM THE CACHE KEYS
                    # ===============================
                    for view in list(keys_in_leave_queue):
                        await self.queue.put(view)
                    self._deque_postman.clear()
                    tasks_collections.clear()
                    # ===============================
                    # ---- RAN SIGNAL
                    # ===============================
                    await signal.schedule_with_delay(
                        callback_=None, asynccallback_=task_account
                    )
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
            self._deque_error.append(self._deque_postman[position_in_postman])

    async def _process_queue_worker(
        self,
        work_id: str,
    ) -> DeribitClientType | None:
        """
        TODO: Протестировать!!
        Only Requests for keys with names 'wss:...' & 'http:...'
        :param work_id:
        :return:
        """
        log_t = "[%s.%s]:" % (
            self.__class__.__name__,
            self._process_queue_worker.__name__,
        )

        try:
            client: DeribitClientType = self.client_pool.get_clients()
            return client
        except Exception as e:
            log.error(str("%s ERROR => %s" % (log_t, e.args[0] if e else str(e))))

    async def start_worker(
        self,
        limitations: int = 10,
    ) -> None:
        """
        This is controller of the workers.
        This controller starting through parameter of the FastAPI.lifespan
        :param limitations:int This is number for limitation the parallels tasks at the cache moment
        :param limitations:
        :return: None
        """
        log_t = "[%s.%s]:" % (self.__class__.__name__, self.start_worker.__name__)
        try:
            while True:
                context_redis_connection = self.rate_limit.context_redis_connection
                async with context_redis_connection() as redis:
                    get_sleeptime = await redis.get("sleeptime")
                    if get_sleeptime:
                        self._sleep += 0.1
                        await redis.incr("sleeptime", 1)
                        await redis.expire("sleeptime", 1)

                    for i in range(limitations):
                        if len(self._deque_coroutines) == limitations:
                            await asyncio.sleep(self._sleep)
                            continue
                        task = asyncio.create_task(
                            self._process_queue_worker(work_id=f"worker_{i}")
                        )
                        self._deque_coroutines.append(
                            {f"worker_{i}": task}
                        )  # coroutine caching

                    await redis.incr("sleeptime", 1)
                    await redis.expire("sleeptime", 1)
        except Exception as err:
            loog_err = "%s ERROR => %s" % (
                str(log_t),
                err.args[0] if err.args else str(err),
            )
            log.error(str(loog_err))
