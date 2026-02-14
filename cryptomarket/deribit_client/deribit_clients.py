"""
cryptomarket/deribit_client/deribit_clients.py
"""

import asyncio
import json
import logging
from collections import deque
from contextvars import ContextVar

from cryptomarket.deribit_client.deribit_limites import DeribitLimited
from cryptomarket.deribit_client.deribit_person import PersonManager
from cryptomarket.deribit_client.deribit_websocket import DeribitWebsocketPool
from cryptomarket.project.settings.core import settings
from cryptomarket.project.sse_manager import ServerSSEManager
from cryptomarket.type import (
    DeribitClient,
    DeribitManageType,
    DeribitWebsocketPoolType,
)

log = logging.getLogger(__name__)

setting = settings()


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
        self.sse_manager = ServerSSEManager(*args)
        self.person_manager = PersonManager()
        # self.ws_connection_manager = DeribitWSSConnectionManager()

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
            if kwargs is not None:
                # Remove an aPI key from kwargs and we leave the kwargs without url
                key_of_queue = kwargs.get("mapped_key")
                self._deque_postman.append({key_of_queue: kwargs})

        except Exception as err:
            raise ValueError(err.args[0] if err.args else str(err))
        try:
            self.client_pool = DeribitWebsocketPool(
                _heartbeat=30,
                _timeout=10,
            )
            if len(self._deque_postman) > 0:
                # ===============================
                # ---- CACHE THE RAQUEST BODY DATA 1/2
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
                    # ---- CREATE THE QUEUE FROM THE CACHE KEYS 2/2
                    # ===============================
                    for view in list(keys_in_leave_queue):
                        await self.queue.put(view)
                    self._deque_postman.clear()
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
    ) -> DeribitClient | None:
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
            client: DeribitClient = self.client_pool.get_clients()
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
