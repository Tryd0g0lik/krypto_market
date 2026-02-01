"""
cryptomarket/tasks/queues/task_account_user.py
"""

import asyncio
import json
import logging
from contextvars import ContextVar

from aiohttp import WSMsgType

from cryptomarket.project.functions import connection_database
from cryptomarket.type import DeribitClientType

log = logging.getLogger(__name__)


async def task_account() -> bool:
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

    connection_db = connection_database()
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
    # ===============================
    # ---- CACHE - RECEIVE THE USER DATA
    # ===============================
    # for key in tasks_id:
    try:
        async with context_redis_connection() as redis:
            task_id = await queue_keys.get()
            data_str: str = await redis.get(task_id)
            dataVar_token = dataVar.set(data_str)
    except Exception as e:
        log.error("%s RedisError => %s" % (log_t, e.args[0] if e.args else str(e)))

    data_str_ = dataVar.get()
    user_meta_json = {}
    dataVar.reset(dataVar_token)
    try:
        connection_db.init_engine()  # Connection to the database
        async with connection_db.asyncsession_scope() as session:

            if isinstance(data_str_, bytes):
                user_meta_json.update(json.loads(data_str_.decode("utf-8")))
            else:
                try:
                    user_meta_json.update(json.loads(data_str_))
                except json.decoder.JSONDecodeError as e:
                    log.error(
                        "%s JSONDecodeError => %s"
                        % (log_t, e.args[0] if e.args else str(e))
                    )
                    return False
            api_key = user_meta_json.get("api_key")
            index = user_meta_json.get("index")
            client_secret_key = user_meta_json.get("client_secret")
            client_id = user_meta_json.get("client_id")
            # ===============================
            # ---- USER CONNECTION WITH THE DERIBIT SERVER
            # ===============================
            with client.initialize(_url=api_key) as session:

                try:

                    async with semaphore:
                        async with client.ws_send(session) as ws:
                            user_meta_json = client._get_autantication_data(
                                index, client_id, client_secret_key
                            )
                            try:
                                # WSS REQUEST
                                await asyncio.wait_for(ws.send_json(user_meta_json), 10)
                                async for msg in ws:
                                    # WSS RESPONSE
                                    if msg.type == WSMsgType.TEXT:
                                        print(f"Received: {msg.data}")
                                        log.warning(f"WS Received: {msg.data}")
                                        data = json.loads(msg.data)
                                        _extract_ticker_from_message = (
                                            sse_manager._extract_ticker_from_message
                                        )
                                        with _extract_ticker_from_message(
                                            data, ("connection",)
                                        ) as ticker:
                                            sse_manager.broadcast(ticker)
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
                    await session.close()

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
