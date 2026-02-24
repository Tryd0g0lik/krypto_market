"""
cryptomarket/api/v1/api_get_index_price.py
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import Request, Response, status
from sqlalchemy import DateTime, between, cast

from cryptomarket.project.settings.core import settings

log = logging.getLogger(__name__)


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
    from sqlalchemy import and_, desc, or_, select, update

    from cryptomarket.models.schemes.model_prices import PriceTicker
    from cryptomarket.project.app import manager
    from cryptomarket.project.functions import (
        connection_db,
    )
    from cryptomarket.type import Person

    rate_limit = manager.rate_limit
    lock = manager.sse_manager.lock
    setting = settings()
    serialize_json = {}
    regex_date = r"^(\d{1,4}-\d{1,2}-\d{1,2}_\d{1,4}:\d{1,2}:\d{1,2})$"
    person_manager = manager.person_manager
    response = Response(
        status_code=status.HTTP_200_OK,
    )
    headers_request_id = request.headers.get("X-Request-ID")
    ticker = request.path_params.get("ticker")
    user_id = request.path_params.get("user_id")
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")
    timer = request.query_params.get("timer")

    p: Person = person_manager.person_dict.get(user_id)
    # user_interval: int = (
    #     (int(timer) if re.search(renge_time, str(timer)) else 0.0)
    #     if timer is not None and timer >= 0
    #     else 0.0
    # )
    if ticker not in setting.CURRENCY_FOR_CHOOSING:
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
            "user_id": user_id,  # This is the user id from app
            "request_id": request_id[:],  # This is an index of request
            "mapped_key": p.key_of_queue,  # Key for the cache server
            "tickers": ticker,
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
            start_date = datetime.strptime(
                start_date.replace("_", " "), "%Y-%m-%d %H:%M:%S"
            )
            end_date = datetime.strptime(
                end_date.replace("_", " "), "%Y-%m-%d %H:%M:%S"
            )
            user_meta_data.__setitem__("dates", {start_date: end_date})

        elif date_list_bool[0] and not date_list_bool[1]:
            start_date = datetime.strptime(
                start_date.replace("_", " "), "%Y-%m-%d %H:%M:%S"
            )
            user_meta_data.__setitem__(
                "dates", {start_date: datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            )
        else:
            response.content = json.dumps({"detail": "Check the dates!"})
            response.status_code = status.HTTP_400_BAD_REQUEST
            return response
        start_date = list((user_meta_data["dates"]).keys())[0]
        end_date = list((user_meta_data["dates"]).values())[0]
        if start_date > end_date:
            response.content = json.dumps(
                {"detail": "Start date cannot be greater than end date!"}
            )
            response.status_code = status.HTTP_400_BAD_REQUEST
            return response

        async with rate_limit.semaphore:
            async with lock:
                connection_db.init_engine()
                connection_db.session_factory()
                if connection_db.is_postgresqltype or connection_db.is_sqlitetype:
                    stmt = select(PriceTicker).where(
                        and_(
                            PriceTicker.ticker == ticker,
                            between(PriceTicker.created_at, start_date, end_date),
                        )
                    )

                    try:
                        # =====================
                        # ---- DATABASE SYNC CONNECTION 1/2
                        # =====================
                        with connection_db.session_scope() as session:
                            rows = session.execute(
                                stmt,
                            ).fitchall()
                        if rows and rows[0] is not None and rows[0][0] is not None:
                            for row in rows:
                                k = datetime.strftime(
                                    row[0].created_at, "%Y-%m-%d %H:%M:%S"
                                )
                                serialize_json.update(
                                    {
                                        k: {
                                            k: v
                                            for k, v in row[0].__dict__.items()
                                            if not k.startswith("_")
                                            and k != "created_at"
                                        }
                                    }
                                )

                    except Exception as e:
                        log.warning(e.args[0] if e.args else str(e))
                        async with connection_db.asyncsession_scope() as session:
                            result = await session.execute(stmt)
                            rows = result.fetchall()
                            # =====================
                            # ---- USER DATA - ASYNC
                            # Async connection
                            # =====================
                            if rows and rows[0] is not None and rows[0][0] is not None:
                                for row in rows:
                                    k = datetime.strftime(
                                        row[0].created_at, "%Y-%m-%d %H:%M:%S"
                                    )
                                    serialize_json.update(
                                        {
                                            k: {
                                                k: v
                                                for k, v in row[0].__dict__.items()
                                                if not k.startswith("_")
                                                and not isinstance(k, datetime)
                                            }
                                        }
                                    )
                                    del serialize_json[k]["created_at"]

                user_meta_data.__setitem__("message", {**serialize_json})
        # ===============================
        # ---- RESPONSE HTTP
        # ==============================
        del user_meta_data["dates"]
        response.content = json.dumps({"detail": {**user_meta_data}})
        return response
    except Exception as e:
        print(str(e))
        # ===============================
        # ---- RESPONSE HTTP
        # ==============================
        response.content = str(e)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return response
