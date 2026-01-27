"""
cryptomarket/type/type_signal.py
"""

import asyncio
import threading
from typing import Protocol, runtime_checkable


@runtime_checkable
class UserSignalHandlerProp(Protocol):

    _semaphore: asyncio.Semaphore
    __batch_size: int
    max_concurrent_batches: int
    controller: bool
    __tasks: list[asyncio.Task]
    user_id: int | str | None
    lock: threading.RLock

    def add(self, task: asyncio.Task) -> None:
        pass

    def tasks(self) -> list:
        pass

    @property
    def semaphore(self):
        pass
