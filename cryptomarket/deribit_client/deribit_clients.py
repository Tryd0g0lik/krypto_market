"""
cryptomarket/deribit_client/deribit_clients.py
"""

import logging

import aiohttp
from fastapi import websockets
from websockets import ClientConnection

from cryptomarket.project.enum import ExternalAPIEnum
from cryptomarket.project.settings.core import app_settings
from cryptomarket.project.settings.settings_env import (
    DERIBIT_CLIENT_ID,
    DERIBIT_SECRET_KEY,
)

log = logging.getLogger(__name__)


def type_coroutine():
    return 42


# ==============================
# WEBSOCKET ENVIRONMENT
# ==============================
class DeribitWebsocketPool:
    _instance = None
    _connections: list = []  # This list is the list[coroutine]. \
    # Below (DeribitWebsocketPool.__new__) he will receive the coroutine for a connection with the Deribit API.
    # The length of list will be containe the quantity of elements == 'app_settings.STRIPE_MAX_QUANTITY_WORKERS'.
    # Everything coroutine/connection will require the:
    # - OAuth 2.0;
    # - client_id from the Deribit;
    # - client_secret from the Deribit.
    _current_index = 0
    _auth_tokens = {}

    # ==============================
    # CLIENT FOR THE BASIC CONNECTION
    # ==============================
    class DeribitClient:
        def __init__(
            self,
            _client_id: str = None,
            _client_secret: str = None,
        ):
            """
           Here we generate of the clients for connection with the Deribit server.
           https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request
           https://docs.deribit.com/articles/deribit-quickstart#websocket-recommended
           Here is creating a list  of the stripe's connections.
           :param _client_id: str|None This is the secret 'client_id' key from Deribit. Default value is \
               the value of variable the 'DERIBIT_CLIENT_ID'.
           :param _client_secret: str|None This is the secret 'client_secret' key from Deribit.  Default value is \
               the value of variable the 'DERIBIT_SECRET_KEY'.
           """
            self.client_id: str = (
                "%s" % DERIBIT_CLIENT_ID if _client_id is None else "%s" % _client_id
            )
            self.client_secret: str = (
                "%s" % DERIBIT_SECRET_KEY
                if _client_secret is None
                else "%s" % _client_secret
            )

        def __new__(cls):
            cls.client_session = aiohttp.ClientSession()
            return super().__new__(cls)

        async def initialize(
            self,
            index,
            _heartbeat=30,
            _timeout=10,
            _url=ExternalAPIEnum.WS_COMMON_URL.value,
        ) -> websockets.WebSocket:
            """
            https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession
            https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientWebSocketResponse.receive_json
            :param index: This is the 'index' of connection.
            :param _heartbeat (float) – Send ping message every heartbeat seconds and wait pong response, if pong response\
                 is not received then close connection. The timer is reset on any data reception.(optional).\
                  Default value 30 seconds.
            :param _timeout - timeout – a ClientWSTimeout timeout for websocket. By default, the value \
                ClientWSTimeout(ws_receive=None, ws_close=10.0) is used (10.0 seconds for the websocket to close).\
                None means no timeout will be used. Default value is 10 second.

            :return:
            """
            log_t = "[%s.%s]: " % (self.__class__.__name__, self.initialize.__name__)
            try:
                ws = self.client_session.ws_connect(
                    url=_url,
                    heartbeat=_heartbeat,
                    timeout=_timeout,
                )
                auth_msg = {
                    "jsonrpc": "2.0",
                    "id": index + 1,
                    "method": "public/auth",
                    "params": {
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                }

                await ws.send_json(auth_msg)
                ws_response = await ws.receive_json()
                return ws_response
            except RuntimeError as e:
                log_tesx = (
                    "%s RuntimeError Connection is not started or closing=> %s"
                    % (log_t, e.args[0] if e.args else str(e))
                )
                log.error(log_tesx)
                raise RuntimeError(log_tesx)
            except ValueError as e:
                log_tesx = "%s ValueError Data is not serializable object => %s" % (
                    log_t,
                    e.args[0] if e.args else str(e),
                )
                log.error(log_tesx)
                raise ValueError(log_tesx)
            except TypeError as e:
                log_tesx = (
                    "%s TypeError Value returned by dumps(data) is not str  => %s"
                    % (log_t, e.args[0] if e.args else str(e))
                )
                log.error(log_tesx)
                raise TypeError(log_tesx)

    def __new__(
        cls,
        _client_id: str = None,
        _client_secret: str = None,
        _heartbeat=30,
        _timeout=10,
    ):
        """
        Here we generate of the clients for connection with the Deribit server.
        https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request
        https://docs.deribit.com/articles/deribit-quickstart#websocket-recommended
        Here is creating a list  of the stripe's connections.

        :param _client_id: str|None This is the secret 'client_id' key from Deribit. Default value is \
            the value of variable the 'DERIBIT_CLIENT_ID'.
        :param _client_secret: str|None This is the secret 'client_secret' key from Deribit.  Default value is \
            the value of variable the 'DERIBIT_SECRET_KEY'.
        :param _heartbeat (float) – Send ping message every heartbeat seconds and wait pong response, if pong response\
             is not received then close connection. The timer is reset on any data reception.(optional).\
              Default value 30 seconds.
        :param _timeout - timeout – a ClientWSTimeout timeout for websocket. By default, the value \
            ClientWSTimeout(ws_receive=None, ws_close=10.0) is used (10.0 seconds for the websocket to close).\
            None means no timeout will be used. Default value is 10 second.


        """
        if not cls._instance:
            cls._instance = super().__new__(cls)

            client_session = cls.DeribitClient(_client_id, _client_secret)
            # This is creating the coroutines for clients (entry points or entry windows).
            # Everyone coroutine for connections with the Deribit.
            # Max quantity of coroutines contain value require - the 'app_settings.STRIPE_MAX_QUANTITY_WORKERS',
            # it is the max number of connection.
            for i in range(app_settings.STRIPE_MAX_QUANTITY_WORKERS):
                ws = client_session.initialize(i, _heartbeat, _timeout)
                cls._connections.append(ws)
        return cls._instance

    def get_connection(self) -> DeribitClient.initialize:
        """
        HEre we received the one coroutine for connection to the Deribit server.
        Coroutine receive by index. It's from 0 before 'app_settings.DERIBIT_MAX_QUANTITY_WORKERS'.
        :return: DeribitClient.initialize (coroutine).
        """
        conn = self._connections[
            (
                self._current_index
                if self._current_index < app_settings.DERIBIT_MAX_QUANTITY_WORKERS
                else app_settings.DERIBIT_MAX_QUANTITY_WORKERS - 1
            )
        ]

        # Resent the cls._current_index
        self._current_index = (self._current_index + 1) % len(self._connections)
        return conn
