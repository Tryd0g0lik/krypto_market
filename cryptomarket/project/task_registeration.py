"""
cryptomarket/project/task_registeration.py:1
"""

import asyncio
import logging
import weakref
from typing import Set

log = logging.getLogger(__name__)


class TaskRegistery:
    """
    This is registry of memory for the asyncio tasks/
    """

    _workers = weakref.WeakSet()

    def __init__(self, max_size: int = 500):
        # self.workers = weakref.WeakSet()
        self.task_names = {}
        self._max_size = max_size
        self.log_t = f"[{self.__class__.__name__}.%s]:"

    def register(self, worker, index=None) -> None:
        task_id = f"worker_{str(index)}"

        TaskRegistery._workers.add(worker)
        if index is not None:
            self.task_names[task_id] = index
        #
        log.info(
            "%s Worker: %s registered. Activ tasks is now: %s"
            % (
                self.log_t % self.register.__name__,
                worker or task_id,
                len(TaskRegistery._workers),
            )
        )

    def cleanup_task(
        self,
        worker_name,
    ) -> None:
        """
        Cleaning a data's task after completion/
        """

        if worker_name in self.task_names:

            del self.task_names[worker_name]
            log.info(
                "%s Task: %s was removed"
                % (
                    self.log_t % self.cleanup_task.__name__,
                    worker_name,
                )
            )

    async def wait_free_slot(self, time=None) -> None:
        if len(TaskRegistery._workers) >= 0:
            while len(TaskRegistery._workers) >= self._max_size:
                if time:
                    await asyncio.sleep(time)
                else:
                    await asyncio.sleep(0.1)

    def get_stats(self) -> dict:
        """Static sdata by use a memory"""
        log.warning(
            """%s Static of memory: \n
         active_tasks: %s \n max_size: %s \n task_names: %s
         """
            % (
                self.log_t % self.get_stats.__name__,
                len(TaskRegistery._workers),
                self._max_size,
                list(self.task_names.keys()),
            )
        )
        return {
            "active_tasks": len(TaskRegistery._workers),
            "max_size": self._max_size,
            "task_names": list(self.task_names.values()),
        }

    def get_active_task(self) -> Set[asyncio.Task]:
        return set(TaskRegistery._workers)
