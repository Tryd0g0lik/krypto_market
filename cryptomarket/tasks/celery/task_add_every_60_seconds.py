"""
cryptomarket/tasks/celery/task_add_every_60_seconds.py
"""

import asyncio
import json
import logging
import tracemalloc
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert

from cryptomarket.deribit_client import DeribitWebsocketPool
from cryptomarket.errors import DatabaseConnectionCoroutineError
from cryptomarket.models import PriceTicker
from cryptomarket.project import TaskRegisteryType, celery_deribit
from cryptomarket.project.enums import RadisKeysEnum
from cryptomarket.project.functions import (
    get_memory_size,
    get_record,
    run_asyncio_debug,
)
from cryptomarket.type import DeribitClient

semaphore = asyncio.Semaphore(40)
lock = asyncio.Lock()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


async def func(*args):
    tracemalloc.start()
    try:
        [manager, workers, connection_db, task_register] = args
        log.warning("DEBUG CELERY TASK START ...")
        currency_dict: str | None = await get_record(
            RadisKeysEnum.DERIBIT_CURRENCY.value
        )
        if currency_dict is None:
            log.info("""\n The var 'currency_dict' is empty""")
            return False
        currency_dict: dict = json.loads(currency_dict)
        person_manager = manager.person_manager
        SUPPORTED_CURRENCIES = person_manager.SUPPORTED_CURRENCIES

        log.warning(f"DEBUG CELERY TASK 'currency_dict': {currency_dict}")
        full_list = {k: v for k, v in currency_dict.items() if len(v) > 0}
        if len(full_list) == 0:
            return False

        request_data = {
            "jsonrpc": "2.0",
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "method": "public/ticker",
            "params": {},
        }
        # ===============================
        # ---- RECEIVE THE REBIT CLIENT FOR CONNECTION
        # ===============================
        client: DeribitClient = workers.get_clients()
        task_register.register(client)
        person_manager.client = client

        log.warning("DEBUG CELERY  TASK0")
        async with person_manager.ws_json() as ws:
            while len(full_list) > 0:
                async with semaphore:
                    log.warning("DEBUG CELERY  TASK1")
                    k, v = full_list.popitem()
                    header_currency = (k.split("_"))[0].upper()
                    if header_currency not in SUPPORTED_CURRENCIES:
                        log.error(
                            f"""\n That header: {header_currency} did not found in body 'SUPPORTED_CURRENCIES'! \n
                        The 'SUPPORTED_CURRENCIES' contain => {(json.dumps(SUPPORTED_CURRENCIES).lower())} <=.\n"""
                        )
                        continue
                    # ===============================
                    # WSS REQUEST TO  THE EXTERNAL SERVER.
                    # Get data from the Deribit server
                    # ===============================
                    request_data["params"].__setitem__(
                        "instrument_name",
                        SUPPORTED_CURRENCIES.get(header_currency)[0],
                    )
                    await ws.send_json(request_data)
                    log.warning("DEBUG CELERY  TASK3")
                    # ===============================
                    # WSS RESPONSE FROM THE EXTERNAL SERVER.
                    # ===============================
                    response_data = await person_manager.safe_receive_json(ws)
                    if len(response_data) == 0:
                        log.warning(
                            f"""\n Something what wrong! The response data is empty.\n
                         Request data is: {json.dumps(request_data)}.\n"""
                        )
                        continue
                    log.warning("DEBUG CELERY  TASK4")
                    if "errror" in response_data:
                        log.error(
                            f"""\n We get error from external deribit server!\
                         The response data contain an error.\n
                         Request data is: {json.dumps(request_data)}.\
                          & Response data is: {json.dumps(response_data)}.\n """
                        )
                        continue
                    log.warning("DEBUG CELERY  TASK5")
                    result = response_data.get("result")
                    # ----
                    async with lock:
                        connection_db.init_engine()
                        try:
                            log.warning("DEBUG CELERY  TASK6")
                            connection_db.session_factory()
                            stmt = insert(PriceTicker).values(
                                ticker=k,
                                instrument_name=result.get("instrument_name"),
                                last_price=result.get("last_price"),
                                mark_price=result.get("mark_price"),
                                max_price=result.get("max_price"),
                                min_price=result.get("min_price"),
                                index_price=result.get("index_price"),
                                best_ask_amount=result.get("best_ask_amount"),
                                best_ask_price=result.get("best_ask_price"),
                                best_bid_amount=result.get("best_bid_amount"),
                                best_bid_price=result.get("best_bid_price"),
                                open_interest=result.get("open_interest"),
                                delivery_price=result.get("estimated_delivery_price"),
                                settlement_price=result.get("settlement_price"),
                                stats_volume_usd=result.get("stats").get("volume_usd"),
                                stats_price_change=result.get("stats").get(
                                    "price_change"
                                ),
                                stats_high=result.get("stats").get("high"),
                                stats_low=result.get("stats").get("low"),
                                stats_value=result.get("stats").get("volume"),
                                timestamp=result.get("timestamp"),
                            )

                            if (
                                connection_db.is_postgresqltype
                                or connection_db.is_sqlitetype
                            ):
                                try:
                                    # Sync connection 1/2
                                    with connection_db.session_scope() as session:
                                        session.execute(
                                            stmt.on_conflict_do_nothing(
                                                index_elements=["id"]
                                            )
                                        )
                                    log.info(
                                        "Celery 'task_celery_monitoring_curency' => data was added successfully!"
                                    )
                                except DatabaseConnectionCoroutineError as e:
                                    log.warning(e.args[0] if e.args else str(e))
                                    # Async connection 2/2
                                    async with connection_db.asyncsession_scope() as session:
                                        await session.execute(
                                            stmt.on_conflict_do_nothing(
                                                index_elements=["id"]
                                            )
                                        )
                                    log.info(
                                        "Celery 'task_celery_monitoring_curency' => data was added successfully!"
                                    )
                            else:
                                # For some a database connection which does not including the 'POSTRGRES' & 'SQLITE'
                                pass
                            pass
                        except Exception as e:
                            log.error(
                                f"""Celery 'task_celery_monitoring_curency' ERROR => {e.args[0] if e.args else str(e)}\n
    Deribit response: {str(result)} \n"""
                            )
                            raise e
                        finally:
                            pass
                    # ===============================
                    # SAVE TO THE DATABASE.
                    # ===============================
    except IndexError as e:
        log.error(
            f"Deque is empty when trying to pop => {e.args[0] if e.args else str(e)}"
        )
        return False
    except Exception as e:
        log.error(f"CELERY ERROR => {e.args[0] if e.args else str(e)}")
        return False
    finally:
        get_memory_size(tracemalloc)


#
@celery_deribit.task(
    name="cryptomarket.tasks.celery.task_add_every_60_seconds.task_celery_monitoring_currency",
    bind=True,
    ignore_result=False,
    autoretry_for=(TimeoutError, OSError, ConnectionError),
    retry_backoff=True,
    max_retries=3,
    retry_backoff_max=30,
)
def task_celery_monitoring_currency(self, *args, **kwargs):

    from cryptomarket.project.app import manager
    from cryptomarket.project.functions import (
        connection_db,
    )

    task_register = TaskRegisteryType()

    workers = DeribitWebsocketPool()
    loop = asyncio.get_event_loop()
    run_asyncio_debug(loop)
    try:

        asyncio.set_event_loop(loop)
        args = [manager, workers, connection_db, task_register]  # loop=loop
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
