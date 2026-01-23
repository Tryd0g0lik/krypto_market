"""
kryptomarket/api/v1/api_users.py
"""

from fastapi import (APIRouter, Request, Response, openapi, status)


# from kryptomarket.type import (
#     CreateAccountBase,
# )

router_v1 = APIRouter(
    prefix="/accounts",
    tags=["account"],
    responses={
        404: {"description": "Not found"},
        200: {"description": "Success"},
        500: {"description": "Internal server error"},
    },
)


@router_v1.post(
    "/create",
    description="""
                We receive data (the type CreateAccountProp for account registration) through \
                AccountCreationMiddleware. There, the data is sent to the cache and then processed \
                in turn/queue via the StripCreationQueue.
                Stripe API: https://docs.stripe.com/api/accounts/create?api-version=2025-12-15.preview&rds=1&architecture-style=services

                **Required parameters of Headers**

                |HEADER|TYPE|REQUIRED|DESCRIPTION|
                |------|----|--------|-----------|
                |X-Requested-ID|string|False|<uuid> - X-Requested-ID is not required|
                |access_token|string|True|JWT token of authorization is required. Key is 'access_token'|



                """,
    # response_model=CreateAccountBase,
    summary="Create a new Stripe's account",
    tags=["account"],
    status_code=status.HTTP_201_CREATED,
)
def create_account(request: Request, *args, **kwargs: CreateAccountBase):
    """Create a new Stripe's account"""

    if "data" in list(request.__dict__.keys()):
        response = Response(status_code=status.HTTP_201_CREATED)
        response.content = request.body()
        return response
    return request


