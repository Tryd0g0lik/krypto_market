"""
cryptomarket/api/v1/api_users.py
"""

from fastapi import APIRouter, Request, Response, openapi, status

from cryptomarket.api.v1.api_get_index_price import get_index_price_child

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
    "/get_index_price",
    description="""
                We receive data (the type CreateAccountProp for account registration) through \
                AccountCreationMiddleware. There, the data is sent to the cache and then processed \
                in turn/queue via the StripCreationQueue.


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
async def get_index_price(request: Request):
    """Create a new Stripe's account
        :param headers.user_id: (str|int)ю Required. This is the user index from app. FOr test, you can inter any number.
        :param tickers: (str) Required. This is the on title or some titles for monitoring.
            Example: One it is "btc_usd" or some "btc_usd%&eth_usd&ada_usdc&algo_usdc"

    """
    response = await get_index_price_child(request)
    # if "data" in list(request.__dict__.keys()):
    #     response = Response(status_code=status.HTTP_201_CREATED)
    #     response.content = request.body()
    #     return response
    return response
