"""
cryptomarket/project/sse_manager.py

This is the manager for the Server Sent Events
"""

import asyncio
import json
import logging
from contextlib import contextmanager
from typing import Set

from cryptomarket.project.functions import delete_key
from cryptomarket.project.settings.core import settings

log = logging.getLogger(__name__)
setting = settings()


class ServerSSEManager:
    _connections: dict[str, Set[asyncio.Queue]] = {}
    lock: asyncio.Lock = asyncio.Lock()

    def __init__(self, *args):
        self.log_t = f"[{self.__class__.__name__}.%s]:"
        # self._connections.update({title: set() for title in args if args is not None})

    async def subscribe(
        self,
        key_of_queue: str,
    ):
        """Here we create a new queue for subscribe"""
        queue = asyncio.Queue(maxsize=setting.DERIBIT_QUEUE_SIZE)
        async with self.lock:
            if key_of_queue not in self._connections:
                self._connections[key_of_queue] = set()

            if queue not in self._connections[key_of_queue]:
                # elif queue not in self._connections[key_of_queue]:
                self._connections[key_of_queue].add(queue)

        log.info(
            "%s The new subscribe was created successfully!",
            (self.log_t % self.subscribe.__name__),
        )
        return queue

    async def unsubscribe(self, key_of_queue: str, queue: asyncio.Queue):
        async with self.lock:
            if key_of_queue in self._connections:
                self._connections[key_of_queue].discard(queue)
                if not self._connections[key_of_queue]:
                    del self._connections[key_of_queue]
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
        mapped_key = data.get("mapped_key", {})
        user_message = data.get("message", {})
        # mapped_key = user_meta.get("mapped_key", "NuLL")
        if len(user_message) == 0:
            return

        person_id = data.get("user_id")

        log.warning(
            "DEBUG BROADCAST 'mapped_key': %s => '_connections': %s",
            mapped_key,
            str(self._connections),
        )
        async with self.lock:
            if mapped_key not in self._connections:
                await asyncio.wait_for(delete_key(mapped_key), 7)
                log.warning(
                    "%s The mapped_key: '%s' not defined in the user: %s!\n The subscription: %s was delete from cache"
                    % (
                        self.log_t % self.broadcast.__name__,
                        mapped_key,
                        person_id,
                        mapped_key,
                    )
                )
                return

            message_data = json.dumps(user_message)
            dead_queues = []
            for queue in self._connections[mapped_key]:
                try:
                    queue.put_nowait(message_data)
                except asyncio.QueueFull:
                    await queue.put(message_data)

                except Exception as e:
                    log.error(
                        "%s ERROR on the sending in the queue: %s  => %s. The data: %s not to be added!"
                        % (
                            self.log_t,
                            self.broadcast.__name__,
                            queue,
                            e.args[0] if e.args else str(e),
                        )
                    )
                    dead_queues.append(queue)

            for queue in dead_queues:
                self._connections[mapped_key].remove(queue)
                log.warning(
                    "%s The bad queue: %s was removed successfully!"
                    % (self.log_t % self.broadcast.__name__, queue),
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
