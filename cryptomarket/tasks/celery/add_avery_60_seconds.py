"""
cryptomarket/tasks/celery/add_avery_60_seconds.py
"""

import asyncio
import json
import logging
from datetime import datetime

from celery import shared_task

from cryptomarket.api.v1.api_users import crypto_currency
from cryptomarket.project.app import manager
from cryptomarket.project.functions import wrapper_delayed_task
from cryptomarket.type import DeribitClient

semaphore = asyncio.Semaphore(40)
lock = asyncio.Lock()
log = logging.getLogger(__name__)


@shared_task(
    name=__name__,
    bind=True,
    ignore_result=True,
    autoretry_for=(TimeoutError,),
    retry_backoff=True,
    max_retries=3,
    retry_backoff_max=60,
)
def task_celery_monitoring_curency(*args, **kwargs):
    person_manager = manager.person_manager
    SUPPORTED_CURRENCIES = person_manager.SUPPORTED_CURRENCIES
    currency_dict = crypto_currency.currency_dict
    full_list = {k: v for k, v in currency_dict.items() if len(v) > 0}

    if len(full_list) == 0:
        return False

    try:

        async def func():
            request_data = {
                "jsonrpc": "2.0",
                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                "method": "public/ticker",
                "params": {},
                # "params": {"instrument_name": args[0]} # "BTC-PERPETUAL"
            }
            # ===============================
            # ---- RECEIVE THE REBIT CLIENT FOR CONNECTION
            # ===============================
            _deque_coroutines = manager._deque_coroutines
            coroutine = _deque_coroutines.popleft()
            client: DeribitClient = await list(coroutine.values())[0]
            person_manager.client = client
            async with person_manager.ws_json() as ws:
                while len(full_list) > 0:
                    with semaphore:
                        k, v = full_list.popitem()[0]
                        header_currency = (k[0].split("_"))[0].upper()
                        if header_currency not in SUPPORTED_CURRENCIES:
                            log.error(
                                f"""\n That header: {header_currency} did not found in body 'SUPPORTED_CURRENCIES'! \n
                            The 'SUPPORTED_CURRENCIES' contain => {(json.dumps(SUPPORTED_CURRENCIES).lower())} <=.\n"""
                            )
                            continue
                        # ===============================
                        # WSS REQUEST TO  THE EXTERNAL SERVER.
                        # ===============================
                        request_data["params"].__setitem__(
                            "instrument_name",
                            SUPPORTED_CURRENCIES.get(header_currency)[0],
                        )
                        await ws.send_json(request_data)
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
                        if "errror" in response_data:
                            log.error(
                                f"""\n We get error from external deribit server!\
                             The response data contain an error.\n
                             Request data is: {json.dumps(request_data)}.\
                              & Response data is: {json.dumps(response_data)}.\n """
                            )
                            continue
                        # ===============================
                        # SAVE TO THE DATABASE.
                        # ===============================

        wdt = wrapper_delayed_task(callback_=None, asynccallback_=func)
        wdt.delayed_task(*args, **kwargs)
    except Exception as e:
        log.error(
            f"""'task_celery_monitoring_curency': {e.args[0] if e.args else str(e)} \n"""
        )
