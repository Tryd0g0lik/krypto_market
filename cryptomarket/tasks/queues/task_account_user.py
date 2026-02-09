"""
cryptomarket/tasks/queues/task_account_user.py
"""

import asyncio
import json
import logging
from contextvars import ContextVar

from aiohttp import WSMsgType
from sqlalchemy.sql.operators import truediv

from cryptomarket.project.encrypt_manager import EncryptManager
from cryptomarket.project.enums import ExternalAPIEnum, RadisKeysEnum
from cryptomarket.project.functions import str_to_json
from cryptomarket.project.signals import signal
from cryptomarket.type import DeribitClient

log = logging.getLogger(__name__)
lock = asyncio.Lock()


# отследить пошагово всю логику работы
# Как из connection_maintenance_task убрать цикл и запускать по мере ззапроса
# Из старой версии кода вернуть  - user_meta_json - который после поллучения токена
async def task_account(*args, **kwargs) -> bool:
    """
    TODO Пользователь получает токены . Внести данные в базу данных в момент удачного соединения.
        Везде где встречается 'client_id' в качестве (уникальнного ориентируа ,например на кеш) убрать/заменить
    Check cache on the cache server and record data in connection_database
    Running in 'cryptomarket.deribit_client.deribit_clients.DeribitCreationQueue.enqueue'
    :param args: list[str] This is list of keys for the data. They were caching on the cache server.
    :param kwargs:dictionary. Template '{"task_id": [< key >] }' The < key > this is list of keys on the cache server.
    :return:
    """

    from cryptomarket.project.app import manager

    log_t = "[%s.%s]:" % (
        __name__.split(".")[-1],
        task_account.__name__,
    )
    dataVar = ContextVar("data_srt", default="")
    dataVar_token = None
    _deque_coroutines = manager._deque_coroutines

    coroutine = _deque_coroutines.popleft()
    client: DeribitClient = await list(coroutine.values())[0]

    queue_keys = manager.queue  # list of keys

    sse_manager = manager.sse_manager
    context_redis_connection = (
        manager.rate_limit.context_redis_connection
    )  # coroutine of the redis asynccontextmanager
    person = manager.person
    # ============= 1/2 ==================
    # ---- CACHE - RECEIVE THE USER DATA (classic a user data)
    # ===============================
    _session = None
    # ws_connection_manager = manager.ws_connection_manager
    # semaphore = ws_connection_manager.semafore
    lock_ = asyncio.Lock()
    user_meta_json = {}
    controller = True
    # with client.initialize(_url=ExternalAPIEnum.WS_COMMON_URL.value) as session:
    #     async with client.ws_send(session) as ws:
    async with person.ws_send(client) as ws:
        if True:
            if True:
                while controller:
                    # async with lock_:
                    try:
                        size = queue_keys.qsize()
                        if size is not None and size == 0:
                            return False
                        async with context_redis_connection() as redis:
                            key_of_queue = await queue_keys.get()

                            data_str: str = await redis.get(key_of_queue)
                            dataVar_token = dataVar.set(data_str)
                            # ============ 2/2 ===================
                            # ---- CACHE - RECEIVE THE USER DATA (user key )
                            # ===============================
                            user_meta_json = str_to_json(data_str)
                            method_name = user_meta_json.get("method")
                            key_of_cache = ""
                            data_str = ""
                            # Get the key of cipher
                            # 'user_id' is mapping between the SSE and the cache server
                            if method_name == "public/auth":
                                key_of_cache += (
                                    RadisKeysEnum.AES_REDIS_KEY.value
                                    % user_meta_json.get("user_id")
                                )
                                data_str: str = await redis.get(key_of_cache)
                                await redis.delete(
                                    RadisKeysEnum.AES_REDIS_KEY.value
                                    % user_meta_json.get("user_id")
                                )
                            elif method_name == "private/get_subaccounts":
                                key_of_cache += (
                                    RadisKeysEnum.DERIBIT_GET_SUBACCOUNTS.value
                                    % user_meta_json.get("user_id")
                                )
                                data_str: str = await redis.get(key_of_cache)
                                await redis.delete(
                                    RadisKeysEnum.DERIBIT_GET_SUBACCOUNTS.value
                                    % user_meta_json.get("user_id")
                                )
                            dataVar.set(data_str)

                    except Exception as e:
                        log.error(
                            "%s RedisError => %s"
                            % (log_t, e.args[0] if e.args else str(e))
                        )
                        controller = False
                        return False
                    api_key = user_meta_json.get("api_key")
                    index = user_meta_json.get("index")

                    # ===============================
                    # ---- STR TO JSON
                    # ===============================
                    data_str = dataVar.get()
                    data_json = str_to_json(data_str)
                    del data_str
                    del dataVar
                    try:
                        from cryptomarket.tasks.queues.task_user_data_to_cache import (
                            task_caching_user_data,
                        )

                        client_id = data_json.get("client_id")[:]
                        user_auth_json: dict = {}
                        try:

                            try:

                                # ===============================
                                # ---- WSS CLIENT
                                # ===============================
                                if True:
                                    # ===============================
                                    # ---- WSS CONNECTION
                                    # ===============================
                                    if True:
                                        if method_name == "public/auth":  # Authenticate
                                            # ===============================
                                            # DECRYPT MANAGER 'EncryptManager'
                                            # ===============================
                                            key_cipher_b = (
                                                data_json.get("encrypt_key")
                                            ).encode()  # Key/cipher
                                            deribit_user_secret_encrypt_b = (
                                                data_json.get("deribit_secret_encrypt")
                                            ).encode()

                                            # ===============================
                                            # ---- DECRYPTION TO STR
                                            # ===============================
                                            decrypt_manager = EncryptManager()
                                            deribit_user_secret_encrypt = decrypt_manager.descrypt_to_str(
                                                {
                                                    key_cipher_b[
                                                        :
                                                    ]: deribit_user_secret_encrypt_b[:]
                                                }
                                            )

                                            del deribit_user_secret_encrypt_b
                                            del key_cipher_b
                                            del data_json
                                            user_auth_json = (
                                                client._get_autantication_data(
                                                    index,
                                                    client_id,
                                                    deribit_user_secret_encrypt[:],
                                                )
                                            )
                                            del index
                                            del deribit_user_secret_encrypt
                                            # ===============================
                                            # ---- WSS CONNECTION
                                            # ===============================
                                            # async with client.ws_send(session) as ws:

                                            await asyncio.wait_for(
                                                ws.send_json(user_auth_json), 10
                                            )
                                        elif (
                                            method_name == "private/get_subaccounts"
                                        ):  # Get subaccounts
                                            user_auth_json = data_json.copy()
                                            del user_auth_json["client_id"]
                                            del user_auth_json["user_id"]
                                            user_auth_json.__setitem__(
                                                "method", user_meta_json.get("method")
                                            )
                                            user_auth_json.__setitem__("jsonrpc", "2.0")
                                            user_auth_json.__setitem__(
                                                "id", user_meta_json.get("index")
                                            )
                                            at = (user_auth_json.get("access_token"),)
                                            user_auth_json.__setitem__(
                                                "params",
                                                {
                                                    "with_portfolio": False,
                                                    "access_token": at[0],
                                                },
                                            )

                                            # ws connection manager
                                            del user_auth_json["access_token"]
                                            del data_json
                                            access_token = user_auth_json.get(
                                                "params", {}
                                            ).get(
                                                "access_token",
                                                "a9d735ef9d46456f94ffe287ef4ff3b3",
                                            )
                                            if access_token:
                                                __key = access_token.split(".")[0]
                                        else:
                                            ws.ping()
                                        # async for msg in ws:
                                        msg = await ws.receive_json()
                                        if True:
                                            # WSS RESPONSE
                                            # if msg.type == WSMsgType.TEXT:
                                            if (
                                                isinstance(msg, dict)
                                                and "error" not in msg.keys()
                                            ):

                                                # ===============================
                                                # ---- RAN SIGNAL - THE USER DATA (
                                                # user data (after authenticate) send to the cache server)
                                                # ===============================
                                                # data_json = json.loads(msg.data)
                                                data_json = msg.copy()

                                                if "error" not in data_json:
                                                    log.warning(
                                                        "DEBUG RESPONSE NOT ERROR => %s "
                                                        % str(data_json)
                                                    )
                                                    result_kwargs_new: dict = {}
                                                    # if method_name == "public/auth":  # Authenticate
                                                    # async with lock:
                                                    # try:
                                                    del user_meta_json["client_id"]
                                                    del user_meta_json["api_key"]
                                                    del user_meta_json["method"]
                                                    result_json = data_json.get(
                                                        "result"
                                                    )
                                                    result_kwargs_new: dict = {
                                                        "client_id": client_id,
                                                        **result_json,
                                                    }

                                                    # __key = result_kwargs_new["access_token"].split(".")[0]
                                                    # ws connection manager
                                                    # loop = asyncio.get_event_loop()
                                                    # await ws_connection_manager.save(
                                                    #     __key, ws, loop, session,client,
                                                    #     result_kwargs_new["access_token"])

                                            elif (
                                                isinstance(msg, dict)
                                                and "error" in msg.keys()
                                            ):
                                                # elif msg.type == WSMsgType.ERROR:
                                                log_err = "%s ERROR connection. " % (
                                                    log_t,
                                                )
                                                log.error(str(log_err))

                                            # elif msg.type == WSMsgType.CLOSED:
                                            #     log.warning(
                                            #         "%s Closing connection. Code: %s"
                                            #         % (log_t, msg.data)
                                            #     )
                                            #     pass
                                            else:
                                                log.warning(
                                                    "DEBUG RESPONSE ERROR => %s "
                                                    % str(data_json)
                                                )

                            except RuntimeError as e:
                                log_err = (
                                    "%s RuntimeError Connection is not started or closing => %s"
                                    % (log_t, e.args[0] if e.args else str(e))
                                )
                                log.error(str(log_err))
                                controller = False
                                raise RuntimeError(str(log_err))

                            except Exception as e:
                                log_err = "%s  => %s " % (
                                    log_t,
                                    e.args[0] if e.args else str(e),
                                )
                                log.error(str(log_err))
                                controller = False
                                raise ValueError(str(log_err))
                        except Exception:
                            controller = False
                            raise
                        finally:
                            pass
                            # await session.close()

                            # if connection_db.engine is None:
                            #     connection_db.init_engine()
                    except Exception as e:
                        controller = False
                        log.error(
                            "%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e))
                        )
                        # return False
                    await asyncio.sleep(2)

    # ЗАПИСЬ В БАЗУ
    # if user_meta_json:
    #     pass
    # if not isinstance(user_meta_json["user_id"], str):
    #     user_meta_json["user_id"] = str(user_meta_json["user_id"])
    # try:
    #     # Validate
    #     validate_all_requiredFields(**user_meta_json)
    # except Exception as e:
    #     log.error(e)
    #     return False
    # user_meta_json["primary_role"] = (
    #     "MASTER"  # user_meta["primary_role"]
    # )
    # user = (
    #     insert(UserModel)
    #     .values(**user_meta_json)
    #     .on_conflict_do_nothing()
    # )
    # await session.execute(user)

    # return True

    # except json.decoder.JSONDecodeError as e:
    #     log.error(
    #         "%s JSONDecodeError => %s"
    #         % (log_t, e.args[0] if e.args else str(e))
    #     )
    # except Exception as e:
    #     log.error("%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e)))
    #     return False
