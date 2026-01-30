"""
cryptomarket/project/enums.py
"""

from enum import Enum


class ExternalAPIEnum(Enum):
    WS_COMMON_URL = "wss://test.deribit.com/ws/api/v2/"


class RadisKeysEnum(Enum):
    REDIS_KEY_REQUESTiD_DATA = "%s:working_request"  # "< REQUEST_ID >:working_request"
    DERBIT_STRIPE_RATELIMIT_TASK = (
        "deribit:ratelimit:%s:%s"  # stripe:ratelimit:<USER_ID>:<TASK_ID>>
    )
