"""
cryptomarket/deribit_client/deribit_websocket.py
"""

import asyncio
import logging
from collections import deque
from contextlib import asynccontextmanager, contextmanager

from aiohttp import ClientSession
from aiohttp.client_ws import ClientWebSocketResponse

from cryptomarket.project.enums import ExternalAPIEnum
from cryptomarket.project.settings.core import settings
from cryptomarket.type import DeribitClient, DeribitWebsocketPoolType

log = logging.getLogger(__name__)

setting = settings()


# ==============================
# ---- WEBSOCKET ENVIRONMENT
# ==============================
class DeribitWebsocketPool(DeribitWebsocketPoolType):
    _instance = None
    # This list is the list[coroutine].
    _clients: list = deque(maxlen=setting.DERIBIT_QUEUE_SIZE)

    # Below (DeribitWebsocketPool.__new__) he will receive the coroutine for a connection with the Deribit API.
    # The length of list will be containe the quantity of elements == 'setting.STRIPE_MAX_QUANTITY_WORKERS'.
    # Everything coroutine/connection will require the:
    # - OAuth 2.0;
    # - client_id from the Deribit;
    # - client_secret from the Deribit.
    _current_index = 0
    _auth_tokens = {}

    def __init__(self, _heartbeat=30, _timeout=10):
        self.__generate_workers(_heartbeat, _timeout)

    # ==============================
    # ---- CLIENT FOR THE BASIC CONNECTION
    # ==============================
    class DeribitClient(DeribitClient):
        _semaphore = asyncio.Semaphore(value=1)

        # self.client_id: str|None = None
        # self.__client_secret: str| None = None

        @contextmanager
        def initialize(
            self,
            _heartbeat: int = 30,
            _timeout: int = 10,
            _url: str = ExternalAPIEnum.WS_COMMON_URL.value,
            _method: str = "GET",
            _autoping: bool = False,
            _loop=None,
        ):
            """
            TODO  данные получить из кеша взамен 'auth_msg'
            https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession
            https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientWebSocketResponse.receive_json
            :param index: This is the 'index' of connection.
            :param _heartbeat (float) – Send ping message every heartbeat seconds and wait pong response, if pong response\
                 is not received then close connection. The timer is reset on any data reception.(optional).\
                  Default value 30 seconds.
            :param _timeout - timeout – a ClientWSTimeout timeout for websocket. By default, the value \
                ClientWSTimeout(ws_receive=None, ws_close=10.0) is used (10.0 seconds for the websocket to close).\
                None means no timeout will be used. Default value is 10 second.
            :param _url Websocket server url, URL or str that will be encoded with URL (see URL to skip encoding).
            :param _method (str) –HTTP method to establish WebSocket connection, 'GET' by default.
            :param _autoping (bool) – automatically send pong on ping message from server. True by default
            :return:
            """
            log_t = "[%s.%s]: " % (self.__class__.__name__, self.initialize.__name__)
            try:
                # ==============================
                # ---- CREATE CONNECTION TO THE DERIBIT SERVER
                # ==============================
                log_t = "[%s.%s]:" % (
                    self.__class__.__name__,
                    self.client_session.__name__,
                )
                # _client_session = ClientSession(_url, loop=_loop)
                _client_session = ClientSession(_url)
                log.info("%s %s" % (log_t, "Client session opening!"))
                try:
                    yield _client_session
                except Exception as e:
                    log.error(
                        "%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e))
                    )
                finally:

                    pass
            except Exception as e:
                log_err = "%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e))
                log.error(str(log_err))
                raise ValueError(str(log_err))

        @asynccontextmanager
        async def ws_send(
            self,
            _client_session: ClientSession,
            _heartbeat: int = 30,
            _timeout: int = 300,
            _url: str = ExternalAPIEnum.WS_COMMON_URL.value,
            _method: str = "GET",
            _autoping: bool = True,
        ) -> ClientWebSocketResponse:
            """
                **Note**: This is the context manager that close yourself!!
                    Why?
                    Respnse: The access token you could get only one connection (by wss). You don't  get
                        the access token for the all your account and connections.
                        That is a reason - why you will be yourself the close it.
                        Example:
                        ```py

                        async with client.ws_send(session) as ws:
                            try:
                                # ...
                            expect ... :
                                wail ws.close()

                        # or
                        # Note: Не проверено!!
                        await self.client_pool.client.ws_session.close()

                        ```


                WebvSocket connection on the Deribit server.
                :param index: This is the 'index' of connection.
                :param _heartbeat (float) – Send ping message every heartbeat seconds and wait pong response, if pong response\
                     is not received then close connection. The timer is reset on any data reception.(optional).\
                      Default value 30 seconds.
                :param _timeout - timeout – a ClientWSTimeout timeout for websocket. By default, the value \
                    ClientWSTimeout(ws_receive=None, ws_close=10.0) is used (10.0 seconds for the websocket to close).\
                    None means no timeout will be used. Default value is 10 second.
                :param _url Websocket server url, URL or str that will be encoded with URL (see URL to skip encoding).
                :param _method (str) –HTTP method to establish WebSocket connection, 'GET' by default.
                :param _autoping (bool) – automatically send pong on ping message from server. True by default
                :param _client_session:
                :return:
            """
            if _client_session is None:
                raise ValueError(
                    "[%s]: ERROR => The '_client_session' is required variable!",
                    (DeribitWebsocketPool.__class__.__name__,),
                )

            log_t = "[%s.%s]:" % (self.__class__.__name__, self.ws_send.__name__)
            ws_connect = _client_session.ws_connect(
                url=_url,
                heartbeat=_heartbeat,
                timeout=_timeout,
                # method=_method,
                autoping=_autoping,
            )
            # async with ws_connect as ws:
            try:
                log.info("%s %s" % (log_t, "WebSocket connection is open!"))
                yield ws_connect
            except Exception as e:
                log.error("%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e)))

            finally:
                pass
                #
                log.info(
                    "%s %s"
                    % (log_t, "WebSocket connection the end, but NOT is closed!")
                )

        # async def safe_receive_json(self, ws, timeout: float = 5.0):
        #     """
        #     Безопасное получение JSON с защитой от конкурентного доступа.
        #
        #     ВАЖНО: В системе должен быть только ОДИН получатель сообщений на WebSocket!
        #     """
        #     try:
        #         # Используем wait_for с обработкой таймаута
        #         msg = await ws.receive_json()
        #
        #         if msg.type == WSMsgType.TEXT:
        #             return json.loads(msg.data)
        #         elif msg.type == WSMsgType.ERROR:
        #             log.error(f"WebSocket error: {msg.data}")
        #             return None
        #         elif msg.type == WSMsgType.CLOSED:
        #             log.warning("WebSocket connection closed")
        #             return None
        #         else:
        #             # Пинг/понг или бинарные сообщения
        #             return None
        #
        #     except asyncio.TimeoutError:
        #         return None
        #     except Exception as e:
        #         log.error(f"Error receiving message: {e}")
        #         return None

    def __generate_workers(
        self,
        _heartbeat=30,
        _timeout=10,
    ):
        """
        TODO: Перед запуском приложения создаётся 10 рабочих(workers/clients). До момента использованя онни в asyncio.Queue
            На момент использования они в asyncio.Queue удаляются и в очереди появляется новый корутин.
            Проблема в том, что Deribit выдаёт assecc токен только для одного соединения/подключения.
            Вуше (в DeribitClient), само полючение к Deribit реализовано через asynccontextmanager. и главное. В этом asynccontextmanager,
            авто- закрытие соединения закомментировано. Закрывать (соединение) вручную.
        **Note**: This is the context manager that close yourself!!
                    Why?
                    Respnse: The access token you could get only one connection (by wss). You don't  get
                        the access token for the all your account and connections.
                        That is a reason - why you will be yourself the close it.
                        Example:
                        ```py

                        async with client.ws_send(session) as ws:
                            try:
                                # ...
                            expect ... :
                                wail ws.close()

                        # or
                        # Note: Не проверено!!
                        await self.client_pool.client.ws_session.close()

                        ```

        Here we generate of the clients for connection with the Deribit server.
        https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request
        https://docs.deribit.com/articles/deribit-quickstart#websocket-recommended
        Here is creating a list  of the stripe's connections.

        :param _client_id: str|None This is the secret 'client_id' key from Deribit.
        :param _client_secret: str|None This is the secret 'client_secret' key from Deribit.
        :param _heartbeat (float) – Send ping message every heartbeat seconds and wait pong response, if pong response\
             is not received then close connection. The timer is reset on any data reception.(optional).\
              Default value 30 seconds.
        :param _timeout - timeout – a ClientWSTimeout timeout for websocket. By default, the value \
            ClientWSTimeout(ws_receive=None, ws_close=10.0) is used (10.0 seconds for the websocket to close).\
            None means no timeout will be used. Default value is 10 second.


        """
        if not self._instance:
            # self._instance = super().__new__(cls)
            # This is creating the coroutines for clients (entry points or entry windows).
            # Everyone coroutine for connections with the Deribit.
            # Max quantity of coroutines contain value require - the 'setting.DERIBIT_MAX_QUANTITY_WORKERS',
            # it is the max number of connection.
            for i in range(setting.DERIBIT_MAX_CONCURRENT):
                client_ = self.DeribitClient()
                self._clients.append(client_)

        # return self._instance

    # def __init__(self):
    #     super().__init__()
    #
    def get_clients(self) -> DeribitClient.initialize:
        """
        HEre we received the one coroutine for connection to the Deribit server.
        Coroutine receive by index. It's from 0 before 'setting.DERIBIT_MAX_QUANTITY_WORKERS'.
        :return: DeribitClient.initialize (coroutine).
        10 clients is everything
        """
        # i = self._current_index \
        #     if self._current_index < setting.DERIBIT_MAX_QUANTITY_WORKERS \
        #        and (self._current_index <= setting.DERIBIT_MAX_CONCURRENT)\
        #     else setting.DERIBIT_MAX_CONCURRENT - 1
        #
        if len(self._clients) == 0:
            print("PUSTO")
            self.__generate_workers()

        # conn = self._clients.pop()
        # del self._clients.workers[list(self._clients.workers.keys())[0]]

        # Resent the cls._current_index
        # self._current_index = (self._current_index + 1) % len(self._clients.get_active_task())
        #
        return self._clients.pop()
