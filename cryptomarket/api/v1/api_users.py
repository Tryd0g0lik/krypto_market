"""
cryptomarket/api/v1/api_users.py
"""

from fastapi import APIRouter, Request, Response, openapi, status

from cryptomarket.api.v1.api_get_index_price import get_index_price_child
from cryptomarket.deribit_client.deribit_currency import CryptoCurrency
from cryptomarket.tasks.celery.task_add_every_60_seconds import (
    task_celery_monitoring_currency,
)
from cryptomarket.tasks.celery.task_send_every_60_seconds import (
    task_celery_postman_currency,
)

crypto_currency = CryptoCurrency()
router_v1 = APIRouter(
    prefix="/market",
    tags=["market"],
    responses={
        404: {"description": "Not found"},
        200: {"description": "Success"},
        500: {"description": "Internal server error"},
    },
)


@router_v1.get(
    "/{user_id}/create_order/{ticker}",
    description="""


                **Required parameters of Headers**

                |HEADER|TYPE|REQUIRED|DESCRIPTION|
                |------|----|--------|-----------|
                |X-Requested-ID|string|False|<uuid> - X-Requested-ID is not required|
                |access_token|string|True|JWT token of authorization is required. Key is 'access_token'|
                """,
    # response_model=CreateAccountBase,
    summary="Create a new Stripe's account",
    status_code=status.HTTP_200_OK,
)
async def create_order(request: Request):
    """
    Добавляем пользователя в список и пользователь должен получаеть данные каждую минуту
    """
    response = await crypto_currency.create_order(request)
    return response


@router_v1.get("/{user_id}/cancel_order/{ticker}")
async def cancel_order(request: Request):
    response = await crypto_currency.cancel_order(request)
    return response


@router_v1.get("/{user_id}/cancel_all_orders")
async def cancel_all_orders(request: Request):
    response = crypto_currency.cancel_all_orders(request)
    return response
