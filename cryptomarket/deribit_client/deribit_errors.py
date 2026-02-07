"""
cryptomarket/deribit_client/deribit_errors.py:1
"""

import logging

from aiohttp import ClientConnectionResetError
from aiohttp.client_ws import ClientWebSocketResponse
from starlette.websockets import WebSocketDisconnect

log = logging.getLogger(__name__)


class DeribitError(Exception):
    """Базовое исключение для DeribitSessionManager"""

    pass


class DeribitSaveError(DeribitError):
    def __init__(self, key, is_ws):
        self.is_ws: bool = is_ws
        self.key = key

        message = f"""{self.__class__.__name__} => Check the 'key' is {key}, 'is_ws' is {is_ws}.
        The 'is_ws' must be 'True' or  'key' is required variables"""
        super().__init__(message)


class DeribitGetError(DeribitError):
    def __init__(self, key):
        self.key = key

        message = f"""{self.__class__.__name__} => Check the 'key' is {key} is required variables"""
        super().__init__(message)


class DeribitSessionActiveError(DeribitError):
    def __init__(self, ws_session):
        self.ws_session: ClientWebSocketResponse = ws_session
        self.is_closed(ws_session)

        message = """%s => The WSS connection is closed!""" % (self.__class__.__name__,)
        super().__init__(message)

    async def is_closed(self, session: ClientWebSocketResponse = None) -> None:
        """
        :param session: ClientWebSocketResponse
        :return: False - Connection closed! or True Connection opened!
        """
        try:
            self.ws_session = await session.ping(b"Check connection")
        except ClientConnectionResetError:
            self.ws_session = False
        except RuntimeError as e:
            log_t = "%s.%s => %s" % (
                self.__class__.__name__,
                self.is_closed.__name__,
                e.args[0] if e.args else str(e),
            )
            log.error(str(log_t))
            self.ws_session = False
