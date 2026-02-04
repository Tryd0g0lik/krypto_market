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
from cryptomarket.project.functions import connection_database, str_to_json
from cryptomarket.project.signals import signal
from cryptomarket.type import DeribitClientType

log = logging.getLogger(__name__)


async def task_account(*args, **kwargs) -> bool:
    """
    TODO Пользователь получает токены . Внести данные в базу данных в момент удачного соединения.
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
            task_id = await queue_keys.get()
            data_str: str = await redis.get(task_id)
            dataVar_token = dataVar.set(data_str)
    except Exception as e:
        log.error("%s RedisError => %s" % (log_t, e.args[0] if e.args else str(e)))
    # ===============================
    # ---- STR TO JSON
    # {'index': < index_for_request_to_deribit_copy_of_index_of_request>,
    # 'request_id': < index_of_request >, 'api_key': 'wss://....', 'client_id': < deribit_account_index >,
    # 'deribit_secret_encrypt': < secret_key_of_account_from_deribit >}
    # ===============================
    data_str = dataVar.get()
    user_meta_json = str_to_json(data_str)
    del data_str
    dataVar.reset(dataVar_token)
    api_key = user_meta_json.get("api_key")
    index = user_meta_json.get("index")

    # ============ 2/2 ===================
    # ---- CACHE - RECEIVE THE USER DATA (user key of cipher)
    #  "{ 'client_id': < deribit_account_index >, 'encrypt_key': < key_cipher > }"
    #  Get keys: 'client_id' & 'encrypt_key' and delete the old data cache.
    # ===============================
    try:
        async with context_redis_connection() as redis:
            data_str: str = await redis.get(
                RadisKeysEnum.AES_REDIS_KEY.value % user_meta_json.get("client_id")
            )
            await redis.delete(
                RadisKeysEnum.AES_REDIS_KEY.value % user_meta_json.get("client_id")
            )
            dataVar_token = dataVar.set(data_str)

    except Exception as e:
        log.error("%s RedisError => %s" % (log_t, e.args[0] if e.args else str(e)))

    # ===============================
    # ---- STR TO JSON
    # ===============================
    data_str = dataVar.get()
    data_json = str_to_json(data_str)
    del data_str
    dataVar.reset(dataVar_token)
    # ===============================
    # DECRYPT MANAGER 'EncryptManager'
    # ===============================
    key_cipher_b = (data_json.get("encrypt_key")).encode()  # Key/cipher
    deribit_user_secret_encrypt_b = (data_json.get("deribit_secret_encrypt")).encode()

    # ===============================
    # ---- DECRYPTION TO STR
    # ===============================
    decrypt_manager = EncryptManager()
    deribit_user_secret_encrypt = decrypt_manager.descrypt_to_str(
        {key_cipher_b: deribit_user_secret_encrypt_b}
    )
    client_id = data_json.get("client_id")
    del data_json
    try:
        # ===============================
        # ---- USER CONNECTION WITH THE DERIBIT SERVER
        # ===============================
        with client.initialize(_url=api_key) as session:

            try:

                async with semaphore:
                    async with client.ws_send(session) as ws:
                        user_meta_json = client._get_autantication_data(
                            index, client_id, deribit_user_secret_encrypt
                        )
                        from cryptomarket.tasks.queues.task_user_data_to_cache import (
                            task_caching_user_data,
                        )

                        try:
                            # WSS REQUEST
                            await asyncio.wait_for(ws.send_json(user_meta_json), 10)
                            async for msg in ws:
                                # WSS RESPONSE
                                if msg.type == WSMsgType.TEXT:
                                    # ===============================
                                    # ---- RAN SIGNAL - THE USER DATA (
                                    # user data (after authenticate) send to the cache server)
                                    # ===============================
                                    data_json = json.loads(msg.data)
                                    client_id = user_meta_json.get("client_id")
                                    args = [
                                        RadisKeysEnum.DERIBIT_USER_AUTHENTICATED.value
                                        % client_id
                                    ]

                                    if "error" not in data_json:
                                        kwargs_new: dict = {
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
                                        try:
                                            await signal.schedule_with_delay(
                                                client_id[:],
                                                None,
                                                task_caching_user_data,
                                                0.2,
                                                *args,
                                                **kwargs_new
                                            )
                                        except Exception as e:
                                            log.error(
                                                "[task_account]: 'signal' ERROR => %s"
                                                % e.args[0]
                                                if e.args
                                                else str(e)
                                            )

                                    # ===============================
                                    # ---- RUN THE SSE
                                    # ===============================
                                    kwargs = json.loads(msg.data)
                                    _extract_ticker_from_message = (
                                        sse_manager._extract_ticker_from_message
                                    )
                                    args = ["connection"]

                                    with _extract_ticker_from_message(
                                        *args, **kwargs
                                    ) as ticker:
                                        kwargs_new.__setitem__("state" "auth_result")
                                        sse_manager.broadcast(
                                            client_id, ticker, kwargs_new
                                        )
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

                        except RuntimeError as e:
                            log_err = (
                                "%s RuntimeError Connection is not started or closing => %s"
                                % (log_t, e.args[0] if e.args else str(e))
                            )
                            log.error(str(log_err))
                            raise RuntimeError(str(log_err))
                        except ValueError as e:
                            log_err = (
                                "%s ValueError Data is not serializable object => %s"
                                % (log_t, e.args[0] if e.args else str(e))
                            )
                            log.error(str(log_err))
                            raise ValueError(str(log_err))
                        except TypeError as e:
                            log_err = (
                                "%s Value returned by dumps(data) is not str => %s"
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
