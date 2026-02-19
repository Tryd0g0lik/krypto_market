"""
cryptomarket/type/task_register.py
"""


import asyncio
import logging
import weakref
from typing import Set

log = logging.getLogger(__name__)


class TaskRegisteryType:
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
        pass

    def cleanup_task(
        self,
        worker_name,
    ) -> None:
        """
        Cleaning a data's task after completion/
        """
        pass

    async def wait_free_slot(self, time=None) -> None:
        pass

    def get_stats(self) -> dict:
        """Static sdata by use a memory"""
        pass

    def get_active_task(self) -> Set[asyncio.Task]:
        pass
