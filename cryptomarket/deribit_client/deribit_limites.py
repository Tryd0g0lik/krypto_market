"""
cryptomarket/deribit_client/deribit_limites.py
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from redis.asyncio import Redis

from cryptomarket.project.enums import RadisKeysEnum
from cryptomarket.project.settings.core import settings
from cryptomarket.project.settings.settings_env import REDIS_DB, REDIS_HOST, REDIS_PORT
from cryptomarket.type import DeribitLimitedType

log = logging.getLogger(__name__)

setting = settings()


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
        key = RadisKeysEnum.DERIBIT_STRIPE_RATELIMIT_TASK.value % (
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
