"""
cryptomarket/project/signals.py
"""

import asyncio
import logging
import threading
import uuid
from contextlib import asynccontextmanager

import backoff

from cryptomarket.project.functions import (
    wrapper_delayed_task,
)
from cryptomarket.type.type_signal import UserSignalHandlerProp

log = logging.getLogger(__name__)


class Signal:

    def __init__(self, max_concurrent_batches=1, batch_size=10) -> None:
        """
        :param max_task: int. Max quantity of tasks will run parallel.
        # :param max_patch: int. Max quantity of tasks will run parallel.
        :param batch_size: int. Quantity of tasks will run parallel.
        :param max_task:
        :param controller: bool. Default value is False.  This is control for time when is stopped the works by tasks
        """
        self._tasks = {}
        self.semaphore = asyncio.Semaphore(max_concurrent_batches)
        self._batch_size = batch_size
        self.controller = False
        self.lock = asyncio.Lock()

    class UserSignalHandler:
        def __init__(
            self,
            semaphore: asyncio.Semaphore,
        ):
            """
            :param semaphore:
            :param controller: bool. Default value is False.  This is control for time when is stopped the works by tasks
            # :param max_concurrent_batches: int. Quantity of tasks will run parallel.

            :param user_id: int| str |None. This is an index of user. User which sent a task. If user does not have own index
                this mean he will get index.
            :param __tasks:int | str | None. default value is None. [{<USER_ID>: <USER_IMAGE>}, ]
            """
            self._semaphore = semaphore
            self.controller = False
            self.__tasks: list[asyncio.Task] = []
            self.user_id: int | str | None = None
            self.lock = threading.RLock()

        def add(self, task: asyncio.Task) -> None:
            self.__tasks.append(task)

        def tasks(self) -> list[asyncio.Task]:
            return self.__tasks

        @property
        def semaphore(self) -> asyncio.Semaphore:
            return self._semaphore

    def __user(self, user_id: int | str | None = None) -> UserSignalHandlerProp:
        """
        :param user_id: int| str |None. This is an index of user
        :return: here a user object/image return which sent of tasks
        """
        user = self.UserSignalHandler(
            semaphore=self.semaphore,
        )
        user.user_id = user_id if user_id else str(uuid.uuid4())

        return user

    async def schedule_with_delay(
        self,
        user_id=None,
        callback_=None,
        asynccallback_=None,
        delay_seconds: int = 0.2,
        *args,
        **kwargs,
    ) -> None:
        """
        :param user_id: int| str |None. This is an index of user
        :param asynccallback_: The async handler which we run in process after the 'delay_seconds' seconds.
        :param callback_: The sync handler which we run in process after the 'delay_seconds' seconds.
        :param delay_seconds: int. This is time when we wait before the start. default 0.2 second.
        :param user_id: int Index of user.
        :param kwargs:
        :return:
        """

        # ===============================
        # ---- CREATE THE ONE/TEMPLATE TASK
        # ===============================
        delayed_task = wrapper_delayed_task(callback_, asynccallback_, delay_seconds)

        try:
            # ===============================
            # ---- CLONE MORE OF TASK
            # ===============================
            if user_id is None or self._tasks.get(user_id) is None:
                # New user
                user = self.__user(user_id)
                user.add(asyncio.create_task(delayed_task(*args, **kwargs)))
                self._tasks[user.user_id]: UserSignalHandlerProp = user
                self.controller = True
            else:
                # User updated
                self._tasks[user_id].add(
                    asyncio.create_task(delayed_task(*args, **kwargs))
                )
                self.controller = True
            await self.handler_tasks()
        except KeyError:
            log.error(
                """[Signal.%s]: KeyError => User id: %s The key ('user_id') does not found
                                            in a dictionary body!"""
                % (
                    self.schedule_with_delay.__name__,
                    user_id,
                )
            )
        except Exception as e:
            log.error(
                "[Signal.%s]: User id: %s Error => %s"
                % (
                    self.schedule_with_delay.__name__,
                    user_id,
                    e.args[0] if e.args else str(e),
                )
            )

    async def handler_tasks(self, delay_seconds: int = 0.3):
        """

        :param delay_seconds:
        :return:
        """

        while self.controller:
            # Waite 'delay_seconds' seconds
            await asyncio.sleep(delay_seconds)
            try:
                await self.__schedule_at_interval()
            except Exception:
                self.controller = False if len(self._tasks) <= 1 else True
                continue
            self.controller = False if len(self._tasks) == 0 else True

    async def __schedule_at_interval(self):
        """
        TODO: 1. Получаем ошибку когда пользователь открывает две вкладки/устройства.
            Как вариант, причина ошибки это два разных loop в одной очерели!!
            2. В строке " del self._tasks[user_id]" возможно можем потерять данные в случае не стандартном развитии.
            >>ERROR - cryptomarket.project.signals:180 - Signal User ID: 224e84ed-65f6-42ca-9f2a-c477d2a40ad7 Error
                => 224e84ed-65f6-42ca-9f2a-c477d2a40ad7
            Ошибку (в логах) видно после получения данных пользователя об успешной авторизации.
        here the all list 'self.__tasks' of tasks is separated by patch.
        :param batch_size:  COmmom list we separate on a batch. Everything batch could be contain per 'batch_size' tasks.

        :return:
        """
        _tasks = self._tasks.copy()
        for user_id, user in _tasks.items():
            # user_id  This index of the own task
            if user.tasks() is None or len(user.tasks()) == 0:
                del self._tasks[user_id]
                continue
            try:
                async with self._get_user_handler(user_id, user) as tasks:
                    async with self.lock:
                        for task in tasks:
                            await self.__get_one_task(task)

                            del self._tasks[user_id]
            except Exception as e:
                log_t = "Signal User ID: %s Error => %s" % (
                    user_id,
                    e.args[0] if e.args else str(e),
                )
                log.error(str(log_t))
                raise ValueError(str(log_t))

    @asynccontextmanager
    async def _get_user_handler(self, user_id: int | str, user: UserSignalHandlerProp):
        """REturn per one task"""

        async with user.semaphore:  # by 2 a parallel tasks
            yield user.tasks()

    @backoff.on_exception(
        backoff.expo,
        (asyncio.TimeoutError,),
        max_tries=5,
        on_backoff=lambda user_id: time_out_warning(user_id),
    )
    async def __get_one_task(
        self, task: asyncio.Task, delay_seconds: int = 7
    ) -> asyncio.wait_for:
        """
        Max count trying is 5 for  complete task.
        :param delay_seconds: int Seconds. It is the deadline by work task
        :return:
        """
        return await asyncio.wait_for(task, timeout=delay_seconds)


def time_out_warning(user_id: int | str):
    return log.warning(
        "Signal Warning => One task was not completed for user id %s" % (user_id,)
    )


signal = Signal(10)
