"""
cryptomarket/api/v1/api_get_index_price.py
"""

import json
import re
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Request, Response, openapi, status

from cryptomarket.project.enums import ExternalAPIEnum
from cryptomarket.project.signals import signal
from cryptomarket.tasks.queues.task_account_user import task_account


async def get_index_price_child(
    request: Request,
):
    """
    TODO tiket можно заполнять "eth_usd" and "eth_usd,  ada_usdc"
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
    from cryptomarket.project.app import manager
    from cryptomarket.type import Person

    # sse_manager = manager.sse_manager
    person_manager = manager.person_manager
    response = Response(
        status_code=status.HTTP_200_OK,
    )
    # =====================
    # ---- BASIS SETTING
    # =====================
    headers_user_id = request.headers.get("X-User-ID")
    headers_request_id = request.headers.get("X-Request-ID")
    tickers = request.query_params.get("tickers")
    p: Person = person_manager.person_dict.get(headers_user_id)

    list_for_choosing = [
        "btc_usd",
        "eth_usd",
        "ada_usdc",
        "algo_usdc",
        "avax_usdc",
        "bch_usdc",
        "bnb_usdc",
        "btc_usdc",
        "btcdvol_usdc",
        "buidl_usdc",
        "doge_usdc",
        "dot_usdc",
        "eurr_usdc",
        "eth_usdc",
        "ethdvol_usdc",
        "link_usdc",
        "ltc_usdc",
        "near_usdc",
        "paxg_usdc",
        "shib_usdc",
        "sol_usdc",
        "steth_usdc",
        "ton_usdc",
        "trump_usdc",
        "trx_usdc",
        "uni_usdc",
        "usde_usdc",
        "usyc_usdc",
        "xrp_usdc",
        "btc_usdt",
        "eth_usdt",
        "eurr_usdt",
        "sol_usdt",
        "steth_usdt",
        "usdc_usdt",
        "usde_usdt",
        "btc_eurr",
        "btc_usde",
        "btc_usyc",
        "eth_btc",
        "eth_eurr",
        "eth_usde",
        "eth_usyc",
        "steth_eth",
        "paxg_btc",
        "drbfix-btc_usdc",
        "drbfix-eth_usdc",
    ]
    if tickers not in list_for_choosing:
        response.detail = json.dumps({"detail": "Ticker not found!"})
        response.status_code = status.HTTP_404_NOT_FOUND
        return response
    # not_foound = [view for view in tickers_list if  view not in list_for_choosing]
    # list_for_choosing = [view.strip() for view in list_for_choosing]
    # str_for_choosing = ", ".join(list_for_choosing)
    # timer = request.query_params.get("timer")

    try:
        request_id = (
            str(uuid4()) if headers_request_id is None else str(headers_request_id)
        )

        # key_of_queue = "sse_tickers:%s:%s" % (
        #     headers_user_id,
        #     datetime.now().strftime("%Y%m%d%H%M%S"),
        # )
        # await sse_manager.subscribe(p.key_of_queue)
        # =====================
        # ---- User Meta DATA
        # =====================
        user_meta_data = {
            "user_id": headers_user_id,  # This is the user id from app
            "method": "public/get_index_price",  # This is attribute for a request
            "request_id": request_id[:],  # This is an index of request
            "api_key": ExternalAPIEnum.WS_COMMON_URL.value,  # API key
            "mapped_key": p.key_of_queue,  # Key for the cache server
            "tickers": tickers,
        }
        # =====================
        # ---- PERSON
        # =====================
        # person_manager = manager.person_manager
        # if user_id not in person_manager.person_dict:
        #     person_manager.add(person_id=user_id, client_id=client_id)
        #     p_dict = person_manager.person_dict
        #     p: Person = p_dict.get(user_id)
        #     p.client_secret_encrypt = client_secret
        #     p_dict.__setitem__(user_id, p)
        # REGULAR EXPRESSION
        # user_interval: int = (
        #     (int(timer) if re.search(r"^(\d+)$", str(timer)) else 60)
        #     if timer is not None
        #     else 60
        # )
        # del timer
        # user_meta_data.__setitem__("user_interval", str(user_interval))
        # ticke_r = ticker if ticker else "btc_usd"
        # user_meta_data.setdefault("ticker", ticke_r)
        await manager.enqueue(3600, **user_meta_data)
        del user_meta_data

        # ===============================
        # ---- RAN SIGNAL
        # ==============================
        # Note: The 'task_account' was relocated from 'self.enqueue'.
        # await  task_account([], {})
        await signal.schedule_with_delay(callback_=None, asynccallback_=task_account)
        # ===============================
        # ---- RESPONSE HTTP
        # ==============================
        detail_dict = {
            "detail": (
                "Ok. Data in proces!"
                if headers_user_id[0] is None
                else f"Ok. Data in proces! Data not found: {str(headers_user_id)}"
            )
        }
        response.detail = json.dumps(detail_dict)
        return response
    except Exception as e:
        response.detail = str(e)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return response
