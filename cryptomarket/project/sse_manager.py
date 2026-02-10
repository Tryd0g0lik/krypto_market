"""
cryptomarket/project/sse_manager.py

This is the manager for the Server Sent Events
"""

import asyncio
import json
import logging
from collections import defaultdict
from contextlib import contextmanager
from typing import Set

from cryptomarket.project.settings.core import settings

log = logging.getLogger(__name__)
setting = settings()


# class SSEConnectionLimiter:
#     def __init__(
#         self,
#         max_connections: int = setting.SSE_MAX_CONNECTION,
#         max_per_ip: int = setting.SSE_MAX_PER_IP,
#     ):
#         self.max_connections = max_connections
#         self.max_per_api = max_per_ip
#         self.active_connections: int = 0
#         self.connections_per_api = defaultdict(int)
#         self.lock = asyncio.Lock()
#
#     async def limiter(self, client_id: str) -> bool:
#         async with self.lock:
#             # Quantity of every connection
#             if self.active_connections >= self.max_connections:
#                 raise ValueError(
#                     "Max connections reached: %s" % self.active_connections
#                 )
#             # Quantity connection per IP
#             if self.connections_per_api[client_id] >= self.max_per_api:
#                 raise ValueError(
#                     "Max connections per IP '%s' reached: %s",
#                     (client_id, self.connections_per_api[client_id]),
#                 )
#             self.active_connections += 1
#             self.connections_per_api[client_id] += 1
#             return True
#
#     async def release(self, client_id: str):
#         async with self.lock:
#             self.active_connections = max(0, self.active_connections - 1)
#             self.connections_per_api[client_id] -= max(
#                 0, self.connections_per_api[client_id] - 1
#             )


class ServerSSEManager:
    _connections: dict[str, Set[asyncio.Queue]] = {}
    lock: asyncio.Lock = asyncio.Lock()

    def __init__(self, *args):
        self.log_t = f"[{self.__class__.__name__}.%s]:"
        self._connections.update({title: set() for title in args if args is not None})

    async def subscribe(self, key_of_queue: str):
        """Here we create a new queue for subscribe"""
        queue = asyncio.Queue(maxsize=setting.DERIBIT_QUEUE_SIZE)
        async with self.lock:
            if key_of_queue not in self._connections:
                self._connections[key_of_queue] = set()
            self._connections[key_of_queue].add(queue)
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

    async def broadcast(self, data: dict):
        # async def broadcast(self, user_id: str, ticker: str, data: dict):
        """
        Here we broadcast a message to all subscribers by ticker. Template: 'queue.put(json.dumps({user_id: data}))'
        :param user_id: (str) Client ID This is the index for the deribit's api key
        :param ticker: (str) The attribute that the user subscribed to and the response will be sent by SSE.
        """
        user_meta = data.get("user_meta")
        mapped_key = user_meta.get("mapped_key")
        del data["user_meta"]

        async with self.lock:
            if mapped_key not in self._connections:
                log.warning(
                    "%s The ticker: '%s' not defined!",
                    (self.log_t % self.broadcast, mapped_key),
                )
                return

            message_data = json.dumps(data)
            dead_queues = []

            for queue in self._connections[mapped_key]:
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
                self._connections[mapped_key].remove(queue)
                log.warning(
                    "%s The bad queue: %s was removed successfully!",
                    (self.log_t % self.broadcast.__name__, queue),
                )

    @contextmanager
    def _extract_ticker_from_message(self, *args: list[str], **kwargs: dict):
        """
        This is the simple function. It don't have the close session - by default.
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
