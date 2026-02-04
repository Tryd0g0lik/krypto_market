"""
__tests__/test_derbit_clients/test_derbitlimited.py

Comment out in line '@pytest.mark.skip' by number 113 & 134.
"""
import asyncio
import logging
from collections import deque
from contextlib import asynccontextmanager
from unittest.mock import MagicMock

import pytest

from __tests__.fixtures.fixture_test_log import (
    fixt_end_TEST,
    fixt_start_TEST,
    fixt_START_work,
)
from cryptomarket.deribit_client.deribit_clients import DeribitLimited
from cryptomarket.project.enums import RadisKeysEnum
from cryptomarket.project.settings.core import settings

log = logging.getLogger(__name__)

class TestDeribitLimited:
    semaphore = asyncio.Semaphore(10)
    sleep = 0.1
    concurrent_counter = 0
    max_concurrent = 0
    counter_lock = asyncio.Lock()


    @asynccontextmanager
    async def acquire(self,  redis, task_id: str, user_id: str, cache_limit: int = 95):
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
        key = RadisKeysEnum.DERIBIT_STRIPE_RATELIMIT_TASK.value % (
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

                async with self.counter_lock:
                    self.concurrent_counter += 1
                    max_concurrent = max(self.max_concurrent, self.concurrent_counter)
                    # create 0 or  +1 (if key exists) request in th total quantity of user requests
                    # This is 100 in second for one task
                    await asyncio.to_thread(lambda: redis.incr(key, 1))
                    await asyncio.to_thread(lambda: redis.expire(key, 1))
                    try:
                        yield task_id
                    finally:
                        # write logic of code by less current/calculater if all successfully.
                        self.max_concurrent = max_concurrent
        except ValueError as e:
            log_t = "[%s.%s]: ValueError => %s" % (
                self.__class__.__name__,
                self.acquire.__name__,
                e.args[0] if e.args else str(e),
            )
            # log.error(log_t)
            raise
        except Exception as e:
            log_t = "[%s.%s]: Error => %s" % (
                self.__class__.__name__,
                self.acquire.__name__,
                e.args[0] if e.args else str(e),
            )
            # log.error(log_t)
            print(log_t)
            raise

    @pytest.mark.parametrize("json_data,taskId, expect", [
        ({"email": "example@example.com",
          "country": "US", "user_id": "dasdasewqewfxcv"}, "acc_create:202601171148210", True),
    ])
    @pytest.mark.asyncio
    @pytest.mark.skip
    async def test_semaphore(self, fixt_START_work, fixt_start_TEST, fixt_end_TEST, json_data, taskId, expect):
        """This is a semaphore checking from the parent method"""
        count_concurent_tasks = 120
        deribit_limited = DeribitLimited()
        fixt_start_TEST(self.test_semaphore.__name__)
        # =============================
        # MOCK REDIS
        # =============================
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True

        async def newtest_function():
            async with deribit_limited.acquire(mock_redis, f"acc_create:20260117114821", f"dasdasewqewfxcv"):
                await asyncio.sleep(0.8)

        tasks = deque(maxlen=count_concurent_tasks)
        for _ in range(count_concurent_tasks):
          tasks.append(asyncio.create_task(newtest_function()))

        await asyncio.gather(*tasks)
        assert settings().DERIBIT_MAX_CONCURRENT is not None, 'We have a limit by parallels/concurrents tasks'
        assert deribit_limited.semaphore._value <=  settings().DERIBIT_MAX_CONCURRENT, "Re-check of counter through \
            the Semaphore"

        fixt_end_TEST(self.test_semaphore.__name__)

    @pytest.mark.parametrize("json_data,taskId, expect", [
        ({"email": "example@example.com",
          "country": "US", "user_id": "dasdasewqewfxcv"}, "acc_create:202601171148210", True),
    ])
    @pytest.mark.asyncio
    @pytest.mark.skip
    async def test_semaphore_internal_content(self, fixt_START_work, fixt_start_TEST, fixt_end_TEST, json_data, taskId, expect):
        """This is a semaphore checking from the TestDeribitLimited.acquire. It hase an additional variable/counter \
        the 'self.concurrent_counter'.
        Additional descript you can see below.
        """
        count_concurent_tasks = 120
        fixt_start_TEST(self.test_semaphore.__name__)
        # =============================
        # MOCK REDIS
        # =============================
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True

        async def newtest_function():
            try:
                async with self.acquire(mock_redis, f"acc_create:20260117114821", f"dasdasewqewfxcv"):
                    await asyncio.sleep(0.8)

            finally:
                log.info("Check of counter on the maximum \
                                               by parallels/works tasks: %s" % self.concurrent_counter)
                async with self.counter_lock:
                    self.concurrent_counter -= 1


        tasks = deque(maxlen=count_concurent_tasks)
        for _ in range(count_concurent_tasks):
            tasks.append(asyncio.create_task(newtest_function()))

        await asyncio.gather(*tasks)
        assert self.concurrent_counter is not None, "The 'concurrent_counter' is exists"
        assert settings().DERIBIT_MAX_CONCURRENT is not None, 'We have a limit by parallels/concurrents tasks'
        assert self.concurrent_counter <= settings().DERIBIT_MAX_CONCURRENT, f"Check of counter on the maximum \
               by parallels/works tasks: {self.concurrent_counter}"
        log.info("Check of counter on Semaphore value: %s " % self.semaphore._value)
        assert self.semaphore._value <= settings().DERIBIT_MAX_CONCURRENT, "Re-check of counter through \
               the Semaphore"

        fixt_end_TEST(self.test_semaphore.__name__)
