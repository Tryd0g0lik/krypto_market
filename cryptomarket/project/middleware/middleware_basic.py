"""
cryptomarket/project/middleware/middleware_basic.py
This the middleware mock is model of start for work by DERIBIT API.
"""

import asyncio
import logging
from uuid import uuid4

from fastapi import Request
from fastapi.responses import StreamingResponse

#
from cryptomarket.project.encrypt_manager import EncryptManager
from cryptomarket.project.enums import RadisKeysEnum
from cryptomarket.project.signals import signal
from cryptomarket.tasks.queues.task_user_data_to_cache import task_caching_user_data
from cryptomarket.type import DeribitManageType
from cryptomarket.type.deribit_type import DeribitMiddlewareType

log = logging.getLogger(__name__)


class DeribitMiddleware(DeribitMiddlewareType):
    def __init__(self, manager: DeribitManageType):
        super().__init__()
        self.manager: DeribitManageType = manager
        # self.encrypt_manager = EncryptManager()

    async def __call__(self, request: Request, call_next):

        response = await call_next(request)
        # client_id = str(request.headers.get("X-Client-Id"))
        # client_secret_key = str(request.headers.get("X-Secret-key"))
        is_sse_request = request.url.path.endswith("sse/auth-stream/connection/")

        # request.state.request_id = str(uuid4())
        # user_id = (request.state.request_id.split("-"))[0]
        # if is_sse_request:
        #     async with asyncio.Lock():
        #         if not hasattr(request.state, "encrypt_done"):
        #
        #
        #
        #             check_client_id = await self.check_client_id()
        #             if not check_client_id:
        # # ===============================
        # # START THE DERIBIT MANAGE
        # # ===============================

        # kwargs_new = {}
        # response.headers.__setattr__("X-User-Id", user_id)
        # kwargs_new.__setitem__("client_id", client_id)
        # kwargs_new.__setitem__("user_id", user_id)
        # result: dict = await self.encrypt_manager.str_to_encrypt(client_secret_key)
        #
        # kwargs_new.__setitem__("encrypt_key", list(result.keys()).pop())
        # kwargs_new.__setitem__("deribit_secret_encrypt", list(result.values()).pop())
        # args = [
        #     RadisKeysEnum.AES_REDIS_KEY.value % user_id,
        # ]
        # del result
        # ===============================
        # ---- RAN SIGNAL The encrypt key we savinf
        # ===============================
        # await signal.schedule_with_delay(
        #     None,
        #     task_caching_user_data,
        #     0.2,
        #     *args,
        #     **kwargs_new,
        # )

        # del user_id
        # del client_id
        # del client_secret_key
        # request.headers.__setattr__("X-Secret-key", "Null")
        # request.state.encrypt_done = True

        # return response
        # if not isinstance(response, StreamingResponse):
        #     response.headers.__setitem__("X-Request-Id", request.state.request_id)

        return response

    async def check_client_id(self):
        """
        TODO Check client id to the cache server befre the '_process_encryption' !
        :return:
        """
        pass
        return False

    # async def _process_encryption(
    #     self, user_id: str, client_id: str, client_secret_key
    # ):
    #     # # ===============================
    #     # # START THE DERIBIT MANAGE
    #     # # ===============================
    #
    #     kwargs_new = {}
    #     kwargs_new.__setitem__("client_id", client_id)
    #     kwargs_new.__setitem__("user_id", user_id)
    #     result: dict = await self.encrypt_manager.str_to_encrypt(client_secret_key)
    #
    #     kwargs_new.__setitem__("encrypt_key", list(result.keys()).pop())
    #     kwargs_new.__setitem__("deribit_secret_encrypt", list(result.values()).pop())
    #     args = [
    #         RadisKeysEnum.AES_REDIS_KEY.value % user_id,
    #     ]
    #     del result
    #     # ===============================
    #     # ---- RAN SIGNAL The encrypt key we savinf
    #     # ===============================
    #     await signal.schedule_with_delay(
    #         user_id,
    #         None,
    #         task_caching_user_data,
    #         0.2,
    #         *args,
    #         **kwargs_new,
    #     )
