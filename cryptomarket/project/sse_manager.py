"""
cryptomarket/project/sse_manager.py

This is the manager for the Server Sent Events
"""

import asyncio
import json
import logging
from pyexpat.errors import messages
from typing import Set

from cryptomarket.project.settings.core import settings

log = logging.getLogger(__name__)
setting = settings()


class SSEManager:
    def __init__(self):
        self._connections: dict[str, Set[str, Set[asyncio.Queue]]] = {}
        self.lock: asyncio.Lock = asyncio.Lock()
        self.log_t = f"[{self.__class__.__name__}.%s]:"

    async def subscribe(self, ticker: str):
        """Here we create a new queue for subscribe"""
        queue = asyncio.Queue(maxsize=setting.DERIBIT_QUEUE_SIZE)
        async with self.lock:
            if ticker not in self._connections:
                self._connections[ticker] = set()
            self._connections[ticker].add(queue)
        log.info(
            "%s The new subscribe was created successfully!",
            (self.log_t, self.subscribe.__name__),
        )
        return queue

    async def unsubscribe(self, ticker: str, queue: asyncio.Queue):
        async with self.lock:
            if ticker in self._connections:
                self._connections[ticker].discard(queue)
                if not self._connections[ticker]:
                    del self._connections[ticker]
            log.info(
                "%s The subscribe was removed successfully!",
                (self.log_t, self.unsubscribe.__name__),
            )

    async def broadcast(self, ticker: str, data: dict):
        """Here we broadcast a message to all subscribers by ticker"""
        async with self.lock:
            if ticker not in self._connections:
                log.warning(
                    "%s The ticker: '%s' not defined!",
                    (self.log_t, self.broadcast, ticker),
                )
                return

            message_data = json.dumps({"detail": data})
            dead_queues = []

            for queue in self._connections[ticker]:
                try:
                    queue.put_nowait(message_data)
                except asyncio.QueueFull:
                    queue.put(message_data)
                except Exception as e:
                    log.error(
                        "%s ERROR on the sending in the queue: %s  => %s. The data: %s not to be added!",
                        (
                            self.log_t,
                            self.broadcast.__name__,
                            queue,
                            e.args[0] if e.args else str(e),
                        ),
                        message_data,
                    )
                    dead_queues.append(queue)

            for queue in dead_queues:
                self._connections[ticker].remove(queue)
                log.warning(
                    "%s The bad queue: %s was removed successfully!",
                    (self.log_t, self.broadcast, queue),
                )
