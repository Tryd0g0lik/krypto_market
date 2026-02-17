"""
cryptomarket/api/v1/api_get_index_price.py
"""

import asyncio
import json
import re
from datetime import datetime
from uuid import uuid4

from fastapi import Request, Response, status

from cryptomarket.errors.deribit_errors import DeribitRangeDatetimeError
from cryptomarket.project.enums import ExternalAPIEnum
from cryptomarket.project.settings.core import settings
from cryptomarket.project.signals import signal
from cryptomarket.tasks.queues.task_account_user import task_account


async def get_index_price_child(
    request: Request,
):
    """
    TODO tiket можно заполнять "eth_usd" and "eth_usd,  ada_usdc"
    Раюботает с:
    - public/get_index_price
    - public/get_tradingview_chart_data"

    :param ticker:
    The list for signature:  ticker: ДАННЫЕ КОТОРЫЕ ПОЛУЧИТЬ
            btc_usd", "eth_usd", "ada_usdc", "algo_usdc", "avax_usdc", "bch_usdc", "bnb_usdc", "btc_usdc",
                       "btcdvol_usdc", "buidl_usdc", "doge_usdc", "dot_usdc", "eurr_usdc", "eth_usdc", "ethdvol_usdc",
                       "link_usdc", "ltc_usdc", "near_usdc", "paxg_usdc", "shib_usdc", "sol_usdc", "steth_usdc",
                       "ton_usdc", "trump_usdc", "trx_usdc", "uni_usdc", "usde_usdc", "usyc_usdc", "xrp_usdc",
                       "btc_usdt", "eth_usdt", "eurr_usdt", "sol_usdt", "steth_usdt", "usdc_usdt", "usde_usdt",
                       "btc_eurr", "btc_usde", "btc_usyc", "eth_btc", "eth_eurr", "eth_usde", "eth_usyc",
                       "steth_eth", "paxg_btc", "drbfix-btc_usdc", "drbfix-eth_usdc"
    :param tiket:
    :param request:
    :return:
    """
    # ===============================
    # ---- OPTIONS
    # ===============================
    from cryptomarket.project.app import manager
    from cryptomarket.type import Person

    setting = settings()

    regex_date = r"^(\d{1,2}-\d{1,2}-\d{4})$"
    renge_time = r"^(\d+.?\d{0,2})$"
    person_manager = manager.person_manager
    response = Response(
        status_code=status.HTTP_200_OK,
    )
    headers_person_id = request.headers.get("X-User-ID")
    headers_request_id = request.headers.get("X-Request-ID")
    tickers = request.query_params.get("tickers")
    method = request.query_params.get("method")
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")
    timer = request.query_params.get("timer")
    p: Person = person_manager.person_dict.get(headers_person_id)
    user_interval: int = (
        (int(timer) if re.search(renge_time, str(timer)) else 0.0)
        if timer is not None and timer >= 0
        else 0.0
    )

    if tickers not in setting.CURRENCY_FOR_CHOOSING:
        # ===============================
        # ---- RESPONSE HTTP
        # ==============================
        response.content = json.dumps({"detail": "Ticker not found!"})
        response.status_code = status.HTTP_404_NOT_FOUND
        return response

    try:
        request_id = (
            str(uuid4()) if headers_request_id is None else str(headers_request_id)
        )

        # =====================
        # ---- User Meta DATA
        # =====================
        user_meta_data = {
            "user_id": headers_person_id,  # This is the user id from app
            "method": (
                method.replace("public_", "public/")
                if "public_" in method
                else method.replace("private_", "private/")
            ),  # This is attribute for a request
            "request_id": request_id[:],  # This is an index of request
            "api_key": ExternalAPIEnum.WS_COMMON_URL.value,  # API key
            "mapped_key": p.key_of_queue,  # Key for the cache server
            "tickers": tickers,
            "timeinterval_query": user_interval,
        }
        # =====================
        # ---- CHECK DATES OF FILTERS & CREATE THE SECONDS
        # =====================

        date_list = [start_date, end_date]
        date_list_bool = [
            (True if re.search(regex_date, str(date_list[i])) else False)
            for i in range(2)
        ]
        if all(date_list_bool):
            user_meta_data.__setitem__(
                "dates",
                json.dumps(
                    {
                        datetime.strptime(date_list[0], "%d-%m-%Y")
                        .timestamp(): datetime.strptime(date_list[1], "%d-%m-%Y")
                        .timestamp()
                    }
                ),
            )

        elif date_list_bool[0] and not date_list_bool[1]:
            user_meta_data.__setitem__(
                "dates",
                json.dumps(
                    {
                        datetime.strptime(date_list[0], "%d-%m.%Y")
                        .timestamp(): datetime.now()
                        .timestamp()
                    }
                ),
            )

        method = user_meta_data.get("method")
        if method == "public/get_index_price":
            user_meta_data.__setitem__("timeinterval", "60.0")

        # ===============================
        # ---- TASKS
        # ==============================
        task_1 = asyncio.create_task(manager.enqueue(3600, **user_meta_data))
        task_2 = asyncio.create_task(
            signal.schedule_with_delay(callback_=None, asynccallback_=task_account)
        )
        manager.register_tasks.register(task_1, task_2)
        await asyncio.gather(task_1, task_2)
        del [user_meta_data, task_1, task_2]
        manager.register_tasks.get_stats()
        # ===============================
        # ---- RESPONSE HTTP
        # ==============================
        detail_dict = {
            "detail": (
                "Ok. Data in proces!"
                if headers_person_id[0] is not None
                else f"Ok. Data in proces! Data not found: {str(headers_person_id)}"
            )
        }
        response.content = json.dumps(detail_dict)
        return response
    except Exception as e:
        # ===============================
        # ---- RESPONSE HTTP
        # ==============================
        response.content = str(e)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return response
