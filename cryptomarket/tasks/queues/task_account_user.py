"""
cryptomarket/tasks/queues/task_account_user.py
"""

import json
import logging
from contextvars import ContextVar

from aiohttp import WSMsgType

from cryptomarket.project.functions import connection_database
from cryptomarket.type import DeribitClientType

log = logging.getLogger(__name__)


async def task_account(*args, **kwargs) -> bool:
    """
    TODO ЗАдача для сохранения в базе после получения ответа
    Check cache on the cache server and record data in connection_database
    Running in 'cryptomarket.deribit_client.deribit_clients.DeribitCreationQueue.enqueue'
    :param args: list[str] This is list of keys for the data. They were caching on the cache server.
    :param kwargs:dictionary. Template '{"task_id": [< key >] }' The < key > this is list of keys on the cache server.
    :return:
    """
    from cryptomarket.deribit_client import DeribitLimited

    connection_db = connection_database()
    task_id = kwargs.get("task_id")
    log_commo_t = "[%s.%s]: Task: %s" % (
        __file__,
        task_account.__name__,
        task_id,
    )
    client: DeribitClientType = args[0]

    if connection_db.engine is None:
        connection_db.init_engine()

    deribit_limited = DeribitLimited()
    dataVar = ContextVar("data_srt", default="")
    dataVar_token = None
    async with connection_db.asyncsession_scope() as session:
        # ===============================
        # ---- CACHE - RECEIVE THE USER DATA
        # ===============================
        # for key in tasks_id:
        try:
            get_redis_session = deribit_limited.context_redis_connection
            async with get_redis_session() as redis:
                data_str: str = redis.get(task_id)
                dataVar_token = dataVar.set(data_str)
        except Exception as e:
            log.error(
                "%s RedisError => %s" % (log_commo_t, e.args[0] if e.args else str(e))
            )
        user_meta_json = {}
        data_str_ = dataVar.get()
        dataVar.reset(dataVar_token)
        try:

            # ---- Check data
            user_meta_json.clear()
            if isinstance(data_str_, bytes):
                user_meta_json.update(json.loads(data_str_.decode("utf-8")))
            else:
                try:
                    user_meta_json.update(json.loads(data_str_))
                except json.decoder.JSONDecodeError as e:
                    log.error(
                        "%s JSONDecodeError => %s"
                        % (log_commo_t, e.args[0] if e.args else str(e))
                    )
                    return False
            # соединение с DERIBIT
            api_key = kwargs.get("api_key")
            index = kwargs.get("index")
            client_secret_key = kwargs.get("client_secret_key")
            client_id = kwargs.get("client_id")
            with client.initialize(_url=api_key) as session:
                try:

                    async with client.semaphore:
                        async with client.ws_send(session) as ws:
                            user_meta_json = client._get_autantication_data(
                                index, client_id, client_secret_key
                            )
                            try:
                                # Data sending
                                await ws.send_json(user_meta_json)
                                async for msg in ws:
                                    if msg.type == WSMsgType.TEXT:
                                        print(f"Received: {msg.data}")
                                        log.warning(f"WS Received: {msg.data}")
                                    elif msg.type == WSMsgType.ERROR:
                                        log_err = "%s ERROR connection. Code: %s" % (
                                            log_commo_t,
                                            msg.value,
                                        )
                                        log.error(str(log_err))
                                        raise ValueError(str(log_err))

                                    elif msg.type == WSMsgType.CLOSED:
                                        log.warning(
                                            "%s Closing connection. Code: %s"
                                            % (log_commo_t, msg.data)
                                        )
                                        break

                            except RuntimeError as e:
                                log_err = (
                                    "%s RuntimeError Connection is not started or closing => %s"
                                    % (log_commo_t, e.args[0] if e.args else str(e))
                                )
                                log.error(str(log_err))
                                raise RuntimeError(str(log_err))
                            except ValueError as e:
                                log_err = (
                                    "%s ValueError Data is not serializable object => %s"
                                    % (log_commo_t, e.args[0] if e.args else str(e))
                                )
                                log.error(str(log_err))
                                raise ValueError(str(log_err))
                            except TypeError as e:
                                log_err = (
                                    "%s Value returned by dumps(data) is not str => %s"
                                    % (log_commo_t, e.args[0] if e.args else str(e))
                                )
                                log.error(str(log_err))
                                raise TypeError(str(log_err))
                finally:
                    session.close()

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

            return True

        except json.decoder.JSONDecodeError as e:
            log.error(
                "%s JSONDecodeError => %s"
                % (log_commo_t, e.args[0] if e.args else str(e))
            )
        except Exception as e:
            log.error("%s ERROR => %s" % (log_commo_t, e.args[0] if e.args else str(e)))
            return False
