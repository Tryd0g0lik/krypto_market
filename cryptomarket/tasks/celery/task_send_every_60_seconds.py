"""
cryptomarket/tasks/celery/task_send_every_60_seconds.py
"""

import asyncio
import json
import logging
import tracemalloc

from sqlalchemy import and_, desc, or_, select, update

from cryptomarket.deribit_client import DeribitLimited
from cryptomarket.errors import DatabaseConnectionCoroutineError
from cryptomarket.models import PriceTicker
from cryptomarket.project import celery_deribit
from cryptomarket.project.enums import RadisKeysEnum
from cryptomarket.project.functions import (
    get_memory_size,
    luo_script_find_key,
    run_asyncio_debug,
)
from cryptomarket.project.task_registeration import TaskRegistery

lock = asyncio.Lock()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


async def func(*args, **kwargs):
    [manager, workers, connection_db, task_register, rate_limit] = args
    task_register: TaskRegistery
    rate_limit: DeribitLimited
    async with rate_limit.context_redis_connection() as redis:
        try:
            async with rate_limit.semaphore:
                # =====================
                # ---- REDIS 1/4
                # =====================
                deribit_currency = RadisKeysEnum.DERIBIT_CURRENCY.value
                response: None | str = await asyncio.wait_for(
                    redis.get(deribit_currency.strip()), 7
                )
                if response is None:
                    return None
                response_json = json.loads(response)
                keys = list(response_json.keys())
                address_for_send = [
                    {key: p} for key in keys for p in response_json[key]
                ]
                # =====================
                # ---- DISPATCH USER DATA PER QUEUE
                # 'address_for_send' Template: '{< ticker name> : [< person/user id >]}'
                # Everyone user/person, who hase (passed ) 'ServerSSEManager.subscribe' are locate here (in 'address_for_send')
                # =====================
                result = None
                serialize_json = {}
                for viwe_dict in address_for_send:
                    # =====================
                    # ---- DATABASE
                    # This is not be cache server
                    # =====================
                    async with lock:
                        connection_db.init_engine()
                        connection_db.session_factory()
                        if (
                            connection_db.is_postgresqltype
                            or connection_db.is_sqlitetype
                        ):
                            stmt = (
                                select(PriceTicker)
                                .where(PriceTicker.ticker == list(viwe_dict.keys())[0])
                                .order_by(desc(PriceTicker.id))
                                .limit(1)
                            )
                            try:

                                # =====================
                                # ---- DATABASE SYNC CONNECTION 1/2
                                # =====================
                                with connection_db.session_scope() as session:
                                    rows = session.execute(
                                        stmt,
                                    ).fitchall()
                                    # =====================
                                    # ---- USER DATA - SYNC
                                    # Async connection
                                    # =====================
                                    if (
                                        rows
                                        and rows[0] is not None
                                        and rows[0][0] is not None
                                    ):
                                        row = rows[0][0]
                                        serialize_json = {
                                            k: v
                                            for k, v in row.__dict__.items()
                                            if k != "created_at"
                                            and not k.startswith("_")
                                        }
                                        serialize_json.__setitem__(
                                            "created_at",
                                            row.created_at.strftime(
                                                "%Y-%m-%d %H:%M:%S"
                                            ),
                                        )
                                        serialize_json.__setitem__(
                                            "updated_at",
                                            (
                                                row.updated_at.strftime(
                                                    "%Y-%m-%d %H:%M:%S"
                                                )
                                                if row.updated_at is not None
                                                else None
                                            ),
                                        )
                                    else:
                                        log.warning(
                                            """SYNC Command SELECT is empty & Data not was found in\n
                                             database rows: %s!"""
                                            % (str(rows),)
                                        )

                            except DatabaseConnectionCoroutineError as e:
                                log.warning(e.args[0] if e.args else str(e))
                                # =====================
                                # ---- DATABASE ASYNC CONNECTION 2/2
                                # =====================
                                async with connection_db.asyncsession_scope() as session:
                                    result = await session.execute(stmt)
                                    rows = result.fetchall()
                                    # =====================
                                    # ---- USER DATA - ASYNC
                                    # Async connection
                                    # =====================
                                    if (
                                        rows
                                        and rows[0] is not None
                                        and rows[0][0] is not None
                                    ):
                                        row = rows[0][0]
                                        serialize_json = {
                                            k: v
                                            for k, v in row.__dict__.items()
                                            if k != "created_at"
                                            and not k.startswith("_")
                                        }
                                        serialize_json.__setitem__(
                                            "created_at",
                                            row.created_at.strftime(
                                                "%Y-%m-%d %H:%M:%S"
                                            ),
                                        )
                                        serialize_json.__setitem__(
                                            "updated_at",
                                            (
                                                row.updated_at.strftime(
                                                    "%Y-%m-%d %H:%M:%S"
                                                )
                                                if row.updated_at is not None
                                                else None
                                            ),
                                        )
                                    else:
                                        log.warning(
                                            """ASYNC Command SELECT is empty & Data not was found in\n
                                             database rows: %s!"""
                                            % (str(rows),)
                                        )

                            # =====================
                            # ---- USER DATA  & User Meta DATA
                            # =====================
                            for person_id in list(viwe_dict.values()):
                                # key_of_queue: str = (
                                #     RadisKeysEnum.DERIBIT_PERSON_RESULT.value
                                #     % person_id
                                # )

                                user_meta_data = {}
                                log.warning(
                                    f"DEBUG CELERY TASK SEND PERSON: 'key_of_queue' {list(viwe_dict.keys())[0]}"
                                )
                                user_meta_data.__setitem__(
                                    "mapped_key",
                                    ":".join(["sse_connection", person_id]),
                                )
                                user_meta_data.__setitem__("method", "public/ticker")
                                user_meta_data.__setitem__("user_id", person_id)
                                user_meta_data.__setitem__("request_id", "None")
                                user_meta_data.__setitem__(
                                    "ticker", serialize_json["ticker"]
                                )
                                serialize_json.__setitem__("user_meta", user_meta_data)

                                try:
                                    # =====================
                                    # ---- REDIS & GET KEY USER's QUEUE 2/4
                                    # =====================
                                    # result = await luo_script_find_key(redis, f"{user_meta_data['mapped_key']}:*")
                                    result = await luo_script_find_key(
                                        redis,
                                        f"{user_meta_data['mapped_key']}:*",
                                    )

                                    result = json.loads(result)
                                    log.info(
                                        f"DEBUG LUA SCRIPT Keys: {str(result['keys'])}"
                                    )
                                    log.info(
                                        f"DEBUG LUA SCRIPT Debug: {str(result['debug'])}"
                                    )
                                    if list(result.keys())[0] is None:
                                        return None
                                    key = result["keys"][-1]
                                    # =====================
                                    # ---- REDIS & GET OLD DATA BY KEY USER's QUEUE 3/4
                                    # =====================
                                    old_data_str = await asyncio.wait_for(
                                        redis.get(key), 7
                                    )
                                    if old_data_str is None:
                                        return None
                                    old_data_json = json.loads(old_data_str)

                                    # =====================
                                    # ---- REDIS &  SEND DATA TO THE CACHE SERVER BY KEY USER's QUEUE 4/4
                                    # =====================
                                    old_data_json.__setitem__("message", serialize_json)
                                    await redis.setex(
                                        key,
                                        27 * 60 * 60,
                                        json.dumps(old_data_json),
                                    )
                                    log.info(
                                        f"Celery 'task_celery_postman_currency' => User key: {key} data was sent successful!"
                                    )
                                except Exception as e:
                                    log.warning(
                                        f"Redis luo script failed, Result: {str(result)} Error: {e.args[0] if e.args else str(e)}"
                                    )
                                    return None
                            log.info(
                                "Celery 'task_celery_postman_currency' => data was added successfully!"
                            )

                        else:
                            pass
        except Exception as e:
            log.error(f"""ERROR => '{e.args[0] if e.args else str(e)}'""")

        return None


@celery_deribit.task(
    name="cryptomarket.tasks.celery.task_send_every_60_seconds.task_celery_postman_currency",
    bind=True,
    ignore_result=False,
    autoretry_for=(TimeoutError, OSError, ConnectionError),
    retry_backoff=True,
    max_retries=3,
    retry_backoff_max=30,
)
def task_celery_postman_currency(self, *args, **kwargs):
    from cryptomarket.deribit_client import DeribitLimited, DeribitWebsocketPool
    from cryptomarket.project.app import manager
    from cryptomarket.project.functions import (
        connection_db,
    )

    rate_limit: DeribitLimited = DeribitLimited()
    task_register = TaskRegistery()

    workers = DeribitWebsocketPool()
    loop = asyncio.new_event_loop()
    run_asyncio_debug(loop)
    try:

        asyncio.set_event_loop(loop)
        args = [manager, workers, connection_db, task_register, rate_limit]
        task = asyncio.ensure_future(
            func(*args),
        )
        loop.run_until_complete(task)
        return True
    except Exception as e:
        loop.close()
        log.error(
            f"""'task_celery_monitoring_curency': {e.args[0] if e.args else str(e)} \n"""
        )
    finally:
        pass
    return False
