"""
cryptomarket/project/sse_manager.py

This is the manager for the Server Sent Events
"""

import asyncio
import json
import logging
from contextlib import contextmanager
from pyexpat.errors import messages
from typing import Set

from cryptomarket.project.settings.core import settings

log = logging.getLogger(__name__)
setting = settings()


class SSEManager:
    _connections: dict[str, Set[asyncio.Queue]] = {}
    lock: asyncio.Lock = asyncio.Lock()

    def __init__(self, *args):
        self.log_t = f"[{self.__class__.__name__}.%s]:"
        self._connections.update({title: set() for title in args if args is not None})

    async def subscribe(self, ticker: str):
        """Here we create a new queue for subscribe"""
        queue = asyncio.Queue(maxsize=setting.DERIBIT_QUEUE_SIZE)
        async with self.lock:
            if ticker not in self._connections:
                self._connections[ticker] = set()
            self._connections[ticker].add(queue)
        log.info(
            "%s The new subscribe was created successfully!",
            (self.log_t % self.subscribe.__name__),
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
                (self.log_t % self.unsubscribe.__name__),
            )

    async def broadcast(self, client_id: str, ticker: str, data: dict):
        """
        Here we broadcast a message to all subscribers by ticker. Template: 'queue.put(json.dumps({client_id: data}))'
        :param client_id: (str) Client ID This is the index of the deribit's account/client
        :param ticker: (str) The attribute that the user subscribed to and the response will be sent by SSE.
        """
        async with self.lock:
            if ticker not in self._connections:
                log.warning(
                    "%s The ticker: '%s' not defined!",
                    (self.log_t % self.broadcast, ticker),
                )
                return

            message_data = json.dumps({client_id: data})
            dead_queues = []

            for queue in self._connections[ticker]:
                try:
                    queue.put_nowait(message_data)
                except asyncio.QueueFull:
                    await queue.put(message_data)

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
                    (self.log_t % self.broadcast, queue),
                )

    @contextmanager
    def _extract_ticker_from_message(self, *args: list[str], **kwargs: dict):
        """
        :param data: (dict)
        :param args: (list[str]) Example "['connection', ]"
        :param kwargs: (dict[str, Set[asyncio.Queue]] ) Example "{'eth_usd': < set() >}"
        :return:
        """
        if args is None and kwargs is None:
            raise ValueError(
                "%s The parameter 'args' or 'kwargs' is required!",
                (self.log_t % self._extract_ticker_from_message),
            )

        data_keys: list = []
        if kwargs is not None:
            # keys_total = list(kwargs.values())
            data_keys.extend([key for key in args if key in json.dumps(kwargs).lower()])
        else:
            data_keys = [*args]

        try:
            for key in data_keys:
                yield key
        except Exception as e:
            raise ValueError(
                "%s ERROR => %s",
                (
                    self.log_t % self._extract_ticker_from_message,
                    e.args[0] if e.args else str(e),
                ),
            )
