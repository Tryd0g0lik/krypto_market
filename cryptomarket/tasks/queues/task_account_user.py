"""
cryptomarket/tasks/queues/task_account_user.py
"""

import asyncio
import json
import logging
from contextvars import ContextVar

from aiohttp import WSMsgType

from cryptomarket.project.encrypt_manager import EncryptManager
from cryptomarket.project.enums import RadisKeysEnum
from cryptomarket.project.functions import str_to_json
from cryptomarket.project.signals import signal
from cryptomarket.type import DeribitClientType

log = logging.getLogger(__name__)
lock = asyncio.Lock()


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
    client: DeribitClientType = await list(coroutine.values())[0]
    queue_keys = manager.queue  # list of keys
    semaphore = manager.rate_limit.semaphore
    sse_manager = manager.sse_manager
    context_redis_connection = (
        manager.rate_limit.context_redis_connection
    )  # coroutine of the redis asynccontextmanager
    # ============= 1/2 ==================
    # ---- CACHE - RECEIVE THE USER DATA (classic a user data)
    # ===============================

    try:
        async with context_redis_connection() as redis:
            key_of_queue = await queue_keys.get()
            data_str: str = await redis.get(key_of_queue)
            dataVar_token = dataVar.set(data_str)
    except Exception as e:
        log.error("%s RedisError => %s" % (log_t, e.args[0] if e.args else str(e)))
    # ===============================
    # ---- STR TO JSON
    # ===============================
    data_str = dataVar.get()
    user_meta_json = str_to_json(data_str)

    dataVar.reset(dataVar_token)
    api_key = user_meta_json.get("api_key")
    index = user_meta_json.get("index")

    # ============ 2/2 ===================
    # ---- CACHE - RECEIVE THE USER DATA (user key )
    # ===============================
    try:
        async with context_redis_connection() as redis:
            # ROUTER
            method_name = user_meta_json.get("method")
            key_of_cache = ""
            data_str = ""
            # Get the key of cipher
            # 'user_id' is mapping between the SSE and the cache server
            # key_of_cache += RadisKeysEnum.AES_REDIS_KEY.value % user_meta_json.get("client_id")
            if method_name == "public/auth":
                key_of_cache += RadisKeysEnum.AES_REDIS_KEY.value % user_meta_json.get(
                    "user_id"
                )
                data_str: str = await redis.get(key_of_cache)
                await redis.delete(
                    RadisKeysEnum.AES_REDIS_KEY.value % user_meta_json.get("user_id")
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
        log.error("%s RedisError => %s" % (log_t, e.args[0] if e.args else str(e)))

    # ===============================
    # ---- STR TO JSON
    # ===============================
    # if method_name == "public/auth":
    data_str = dataVar.get()
    data_json = str_to_json(data_str)
    # elif method_name == "private/get_subaccounts"
    del data_str
    del dataVar

    try:
        # ===============================
        # ---- USER CONNECTION WITH THE DERIBIT SERVER
        # ===============================
        with client.initialize(_url=api_key) as session:

            try:

                async with semaphore:
                    ws = None

                    if manager.client_pool.is_ws:
                        ws = await manager.client_pool.ws_session.clear()
                    else:
                        async with client.ws_send(session) as ws_new:
                            manager.client_pool.ws_session = ws_new
                            manager.client_pool.is_ws = True
                            ws = ws_new

                    from cryptomarket.tasks.queues.task_user_data_to_cache import (
                        task_caching_user_data,
                    )

                    user_auth_json: dict = {}
                    if method_name == "public/auth":  # Authenticate
                        # ===============================
                        # DECRYPT MANAGER 'EncryptManager'
                        # ===============================
                        #
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
                            {key_cipher_b[:]: deribit_user_secret_encrypt_b[:]}
                        )
                        client_id = data_json.get("client_id")[:]
                        del deribit_user_secret_encrypt_b
                        del key_cipher_b
                        del data_json
                        user_auth_json = client._get_autantication_data(
                            index, client_id, deribit_user_secret_encrypt[:]
                        )
                        del index
                        del deribit_user_secret_encrypt
                    elif method_name == "private/get_subaccounts":  # Get subaccounts
                        user_auth_json = data_json.copy()
                        del user_auth_json["client_id"]
                        del user_auth_json["user_id"]
                        user_auth_json.__setitem__(
                            "method", user_meta_json.get("method")
                        )
                        user_auth_json.__setitem__("jsonrpc", "2.0")
                        user_auth_json.__setitem__("id", user_meta_json.get("index"))
                        user_auth_json.__setitem__(
                            "params",
                            {
                                "with_portfolio": False,
                                "access_token": user_auth_json.get("access_token"),
                            },
                        )
                        del user_auth_json["access_token"]

                        del data_json

                    try:
                        log.warning("DEBUG REQUEST => %s " % str(user_auth_json))
                        # WSS REQUEST
                        await asyncio.wait_for(ws.send_json(user_auth_json), 10)

                        async for msg in ws:
                            # WSS RESPONSE
                            if msg.type == WSMsgType.TEXT:

                                # ===============================
                                # ---- RAN SIGNAL - THE USER DATA (
                                # user data (after authenticate) send to the cache server)
                                # ===============================
                                data_json = json.loads(msg.data)

                                if "error" not in data_json:
                                    log.warning(
                                        "DEBUG RESPONSE NOT ERROR => %s "
                                        % str(data_json)
                                    )
                                    result_kwargs_new: dict = {}
                                    if method_name == "public/auth":  # Authenticate
                                        # async with lock:
                                        # try:
                                        del user_meta_json["client_id"]
                                        del user_meta_json["api_key"]
                                        del user_meta_json["method"]
                                        result_kwargs_new: dict = {
                                            "client_id": client_id,
                                            "access_token": data_json.get("result").get(
                                                "access_token"
                                            ),
                                            "expires_in": data_json.get("result").get(
                                                "expires_in"
                                            ),
                                            "refresh_token": data_json.get(
                                                "result"
                                            ).get("refresh_token"),
                                            "scope": data_json.get("result").get(
                                                "scope"
                                            ),
                                            "token_type": data_json.get("result").get(
                                                "token_type"
                                            ),
                                        }

                                    elif (
                                        method_name == "private/get_subaccounts"
                                    ):  # Get subaccounts
                                        result_kwargs_new: dict = {**data_json}
                                        # args = [
                                        #     args[0]
                                        #     % data_json.get("result").get("id")
                                        # ]
                                    else:
                                        log.warning(
                                            "DEBUG RESPONSE ERROR => %s "
                                            % str(data_json)
                                        )
                                        result_kwargs_new: dict = {**data_json}

                                    result_kwargs_new.__setitem__(
                                        "user_meta", user_meta_json
                                    )

                                    result_kwargs_new.__setitem__(
                                        "state", "auth_result"
                                    )

                                    await sse_manager.broadcast(result_kwargs_new)
                                    del client_id
                                    """
                                    Полбховтелю надо сообщить об удачном подключении.
                                    Нужен ключ пользователя.
                                    Ключ пользователя - нужен шифр.

                                    После создать endpoint для отправления connection.
                                    """
                                    """
                                        add the new user line in db.


                                    """
                                else:
                                    log.warning(
                                        "DEBUG RESPONSE ERROR => %s " % str(data_json)
                                    )

                            elif msg.type == WSMsgType.ERROR:
                                log_err = "%s ERROR connection. Code: %s" % (
                                    log_t,
                                    msg.value,
                                )
                                log.error(str(log_err))
                                pass

                            elif msg.type == WSMsgType.CLOSED:
                                log.warning(
                                    "%s Closing connection. Code: %s"
                                    % (log_t, msg.data)
                                )
                                pass
                            else:
                                log.warning(
                                    "DEBUG RESPONSE ERROR => %s " % str(data_json)
                                )
                                result_kwargs_new: dict = {**data_json}
                            # await ws.close()
                    except RuntimeError as e:
                        log_err = (
                            "%s RuntimeError Connection is not started or closing => %s"
                            % (log_t, e.args[0] if e.args else str(e))
                        )
                        log.error(str(log_err))
                        raise RuntimeError(str(log_err))
                    except ValueError as e:
                        await ws.close()
                        log_err = (
                            "%s ValueError Data is not serializable object => %s \n Session is closed!"
                            % (log_t, e.args[0] if e.args else str(e))
                        )
                        log.error(str(log_err))
                        raise ValueError(str(log_err))
                    except TypeError as e:
                        await ws.close()
                        log_err = (
                            "%s Value returned by dumps(data) is not str => %s \n Session is closed!"
                            % (log_t, e.args[0] if e.args else str(e))
                        )
                        log.error(str(log_err))
                        raise TypeError(str(log_err))

            finally:
                pass
                # await session.close()

                # if connection_db.engine is None:
                #     connection_db.init_engine()
    except Exception as e:
        log.error("%s ERROR => %s" % (log_t, e.args[0] if e.args else str(e)))
        return False

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
