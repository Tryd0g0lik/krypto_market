"""
cryptomarket/tasks/queues/task_account_user.py
"""

import contextlib
import json
import logging

from cryptomarket.models.schemes.validates import validate_all_requiredFields
from cryptomarket.project.enum import RadisKeysEnum
from cryptomarket.project.functions import connection_db

user_meta = None
log = logging.getLogger(__name__)


@contextlib.contextmanager
def get_redis_session():

    from redis import Redis

    from cryptomarket.project.settings.settings_env import REDIS_HOST, REDIS_PORT

    redis = Redis(
        f"{REDIS_HOST}",
        f"{REDIS_PORT}",
    )

    try:
        yield redis

    except Exception as e:
        log.error(
            "[%s]: RedisError => %s"
            % (get_redis_session.__name__, e.args[0] if e.args else str(e))
        )
    finally:
        redis.reset()
        redis.close()
        log.info("[%s]TEST: task_account Redis close" % get_redis_session.__name__)


async def task_account__api():
    pass


async def task_account(*args, **kwargs) -> bool:
    """
    TODO ЗАдача для сохранения в базе после получения ответа
    Check cache on the cache server and record data in database
    Running in 'cryptomarket.deribit_client.deribit_clients.DeribitCreationQueue.enqueue'
    :param args: list[str] This is list of keys for the data. They were caching on the cache server.
    :param kwargs:dictionary. Template '{"task_id": [< key >] }' The < key > this is list of keys on the cache server.
    :return:
    """
    tasks_id = kwargs.get("task_id") if kwargs else args
    log_commo_t = "[%s.%s]: Task: %s" % (
        __file__,
        task_account.__name__,
        tasks_id,
    )

    if connection_db.engine is None:
        connection_db.init_engine()
    global user_meta
    async with connection_db.asyncsession_scope() as session:
        # ===============================
        # ---- CACHE - RECEIVE THE USER DATA
        # ===============================
        for key in tasks_id:
            try:
                with get_redis_session() as redis:
                    user_meta = redis.get(key)

            except Exception as e:
                log.error(
                    "%s RedisError => %s"
                    % (log_commo_t, e.args[0] if e.args else str(e))
                )
            user_meta_json = None
            if user_meta:
                try:
                    # ---- Check data
                    if isinstance(user_meta, bytes):
                        user_meta_json = json.loads(user_meta.decode("utf-8"))
                    else:
                        try:
                            user_meta_json = json.loads(user_meta)
                        except json.decoder.JSONDecodeError as e:
                            log.error(
                                "%s JSONDecodeError => %s"
                                % (log_commo_t, e.args[0] if e.args else str(e))
                            )
                            return False
                    # ЗАПИСЬ В БАЗУ
                    if user_meta_json:
                        if not isinstance(user_meta_json["user_id"], str):
                            user_meta_json["user_id"] = str(user_meta_json["user_id"])
                        try:
                            # Validate
                            validate_all_requiredFields(**user_meta_json)
                        except Exception as e:
                            log.error(e)
                            return False
                        user_meta_json["primary_role"] = (
                            "MASTER"  # user_meta["primary_role"]
                        )
                        user = (
                            insert(UserModel)
                            .values(**user_meta_json)
                            .on_conflict_do_nothing()
                        )
                        await session.execute(user)

                    return True
                except Exception as e:
                    log.error(
                        "%s Exception => %s"
                        % (log_commo_t, e.args[0] if e.args else str(e))
                    )

                    return False
        else:
            return False
