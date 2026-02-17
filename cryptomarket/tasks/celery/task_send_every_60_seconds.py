"""
cryptomarket/tasks/celery/task_send_every_60_seconds.py
"""

import asyncio
import json
import logging
import sys
import threading
from datetime import datetime

from sqlalchemy import and_, desc, or_, select, update

from cryptomarket.deribit_client import DeribitLimited
from cryptomarket.errors import DatabaseConnectionCoroutineError
from cryptomarket.models import PriceTicker
from cryptomarket.project import celery_deribit
from cryptomarket.project.enums import RadisKeysEnum
from cryptomarket.project.functions import run_asyncio_debug
from cryptomarket.project.task_registeration import TaskRegistery
from cryptomarket.type import DeribitLimitedType, Person, ServerSSEManager

# semaphore = asyncio.Semaphore(40)
lock = asyncio.Lock()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


async def func(*args, **kwargs):
    [manager, workers, connection_db, task_register, rate_limit] = args
    task_register: TaskRegistery
    rate_limit: DeribitLimited
    sse_manager: ServerSSEManager = manager.sse_manager
    person_manager = manager.person_manager

    async with rate_limit.context_redis_connection() as redis:
        try:
            async with rate_limit.semaphore:
                deribit_currency = RadisKeysEnum.DERIBIT_CURRENCY.value
                response: None | str = await asyncio.wait_for(
                    redis.get(deribit_currency), 7
                )
                if response is None:
                    log.warning(
                        f"""\n That header: '{deribit_currency}' did not found in cache server! \n"""
                    )
                    return None
                response_json = json.loads(response)
                keys = list(response_json.keys())
                address_for_send = [
                    {key: p} for key in keys for p in response_json[key]
                ]
                # =====================
                # ---- DISPATCH USER DATA PER QUEUE
                # 'address_for_send' Template: '{< ticker name> : < person/user id >}'
                # Everyone user/person, who hase (passed ) 'ServerSSEManager.subscribe' are locate here (in 'address_for_send')
                # =====================
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
                            try:
                                stmt = (
                                    select(PriceTicker)
                                    .where(
                                        PriceTicker.ticker == list(viwe_dict.keys())[0]
                                    )
                                    .order_by(desc(PriceTicker.id))
                                    .limit(1)
                                )
                                result = None
                                # =====================
                                # ---- DATABASE SYNC CONNECTION
                                # =====================
                                with connection_db.session_scope() as session:

                                    rows = session.execute(
                                        stmt,
                                    ).fitchall()
                                log.info(
                                    "Celery 'task_celery_postman_currency' => data was added successfully!"
                                )
                            except DatabaseConnectionCoroutineError as e:
                                log.warning(e.args[0] if e.args else str(e))
                                # =====================
                                # ---- DATABASE ASYNC CONNECTION
                                # =====================
                                async with connection_db.asyncsession_scope() as session:
                                    result = await session.execute(stmt)
                                    rows = result.fetchall()
                                # =====================
                                # ---- USER DATA
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
                                        if k != "created_at" and not k.startswith("_")
                                    }
                                    serialize_json.__setitem__(
                                        "created_at",
                                        row.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                                    )
                                    serialize_json.__setitem__(
                                        "updated_at",
                                        (
                                            row.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                                            if row.updated_at is not None
                                            else None
                                        ),
                                    )
                                    # =====================
                                    # ---- USER DATA  & User Meta DATA
                                    # =====================
                                    person_id = list(viwe_dict.values())[0]
                                    p: Person = person_manager.person_dict.get(
                                        person_id
                                    )
                                    user_meta_data = {}
                                    user_meta_data.__setitem__(
                                        "mapped_key", p.key_of_queue
                                    )
                                    user_meta_data.__setitem__(
                                        "method", "public/ticker"
                                    )
                                    user_meta_data.__setitem__("user_id", person_id)
                                    user_meta_data.__setitem__("request_id", "None")
                                    user_meta_data.__setitem__(
                                        "tickers", serialize_json["ticker"]
                                    )
                                    serialize_json.__setitem__(
                                        "user_meta", user_meta_data
                                    )
                                    # =====================
                                    # ---- USER QUEUE
                                    # =====================
                                    await sse_manager.broadcast(serialize_json)

                                log.info(
                                    "Celery 'task_celery_postman_currency' => data was added successfully!"
                                )

                        else:
                            pass

                # user_list = response_json
        except Exception as e:
            log.error(f"""ERROR => '{e.args[0] if e.args else str(e)}'""")
        return None


@celery_deribit.task(
    name="cryptomarket.tasks.celery.task_add_every_60_seconds.task_celery_postman_currency",
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
    # loop.set_debug(True)
    # loop.slow_callback_duration = 0.08
    try:

        asyncio.set_event_loop(loop)
        args = [manager, workers, connection_db, task_register, rate_limit]  # loop=loop
        task = asyncio.ensure_future(
            func(*args),
        )
        loop.run_until_complete(task)

        # threading.Thread(target=loop.run_forever).start()
        return True
    except Exception as e:
        loop.close()
        log.error(
            f"""'task_celery_monitoring_curency': {e.args[0] if e.args else str(e)} \n"""
        )
    finally:
        pass
    return False
