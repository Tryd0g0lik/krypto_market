"""
cryptomarket/api/v1/api_users.py
"""

from fastapi import APIRouter, Request, Response, openapi, status

from cryptomarket.deribit_client.deribit_currency import CryptoCurrency

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
    Маршрут получает "{{x_user_id}}" тот самый ( "X-User-id")который используем при подключении SSE.
    Ticker:
        - "btc_usd"
        - "eth_usd"

    Ticker должен присутствовать в списке возможных "Settings.CURRENCY_FOR_CHOOSING". по маршруту "cryptomarket/project/settings/core.py". Иначе не пройдёт проверку.



    **Required parameters of Headers**

    |HEADER|TYPE|REQUIRED|DESCRIPTION|
    |------|----|--------|-----------|
    |X-Requested-ID|string|False|<uuid> - X-Requested-ID is not required|

    **Params**
    |PARAMS|TYPE|REQUIRED|DESCRIPTION|
    |------|----|--------|-----------|
    |timer|integer|False|Пример: 60 |
    """,
    tags=["market"],
    summary="Create new subscription",
    status_code=status.HTTP_200_OK,
)
async def create_order(request: Request):
    """
    Добавляем пользователя в список и пользователь должен получаеть данные каждую минуту
    """
    response = await crypto_currency.create_order(request)
    return response


@router_v1.get(
    "/{{x_user_id}}/cancel_order/{{ticker}}",
    description="""
    Маршрут получает "{{x_user_id}}" тот самый ( "X-User-id")который используем при подключении SSE.
    Ticker:
        - "btc_usd"
        - "eth_usd"

    Ticker должен присутствовать в списке возможных "Settings.CURRENCY_FOR_CHOOSING". по маршруту "cryptomarket/project/settings/core.py". Иначе не пройдёт проверку.



    **Required parameters of Headers**

    |HEADER|TYPE|REQUIRED|DESCRIPTION|
    |------|----|--------|-----------|
    |X-Requested-ID|string|False|<uuid> - X-Requested-ID is not required|

    """,
    tags=["market"],
    summary="Remove one subscription",
    status_code=status.HTTP_200_OK,
)
async def cancel_order(request: Request):
    response = await crypto_currency.cancel_order(request)
    return response


@router_v1.get(
    "/{user_id}/get_order/{ticker}",
    description="""
    Маршрут получает "{{x_user_id}}" тот самый ( "X-User-id")который используем при подключении SSE.
    Ticker:
        - "btc_usd"
        - "eth_usd"

    Ticker должен присутствовать в списке возможных "Settings.CURRENCY_FOR_CHOOSING". по маршруту "cryptomarket/project/settings/core.py". Иначе не пройдёт проверку.



    **Required parameters of Headers**

    |HEADER|TYPE|REQUIRED|DESCRIPTION|
    |------|----|--------|-----------|
    |X-Requested-ID|string|False|<uuid> - X-Requested-ID is not required|

    **Params**

    |PARAMS|TYPE|REQUIRED|DESCRIPTION|
    |------|----|--------|-----------|
    |start_date|string|True|Пример: 2026-02-18_0:0:0 |
    |end_date|string|False|Пример: 2026-02-24_0:0:0 |

    """,
    tags=["market"],
    summary="Get data by one subscription",
    status_code=status.HTTP_200_OK,
)
async def cancel_order(request: Request):
    response = await crypto_currency.get_order(request)
    return response


@router_v1.get(
    "/{user_id}/cancel_all_orders",
    description="""
    **Required parameters of Headers**

    |HEADER|TYPE|REQUIRED|DESCRIPTION|
    |------|----|--------|-----------|
    |X-Requested-ID|string|False|<uuid> - X-Requested-ID is not required|

    """,
    tags=["market"],
    summary="Remove all subscriptions",
    status_code=status.HTTP_200_OK,
)
async def cancel_all_orders(request: Request):
    response = crypto_currency.cancel_all_orders(request)
    return response
