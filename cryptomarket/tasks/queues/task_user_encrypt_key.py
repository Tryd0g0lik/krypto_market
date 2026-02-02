"""
cryptomarket/tasks/queues/task_user_encrypt_key.py:1
"""

import asyncio
import base64
import json
import logging

import backoff
from celery.bin.result import result

from cryptomarket.project.enums import RadisKeysEnum

log = logging.getLogger(__name__)


async def task_record_user_encrypt_key(
    **kwargs,
) -> None:
    """
    :param kwargs: {< client_id: str > : json.dumps([ ... ])}
    :param kwargs[client_id]: (str) The client id of the user. This client index from the deribit account.
        That is the required variable!
    """
    if kwargs is None or not isinstance(kwargs, dict):
        raise TypeError(
            "%s TypeError => The 'kwargs' type is not successful!",
            (task_record_user_encrypt_key.__name__,),
        )
    if len(kwargs) < 1 or kwargs.get("client_id") is None:
        raise ValueError(
            "%s ERROR => The 'kwargs' value is not defined or 'kwargs[client_id]' was not found!",
            (task_record_user_encrypt_key.__name__,),
        )
    try:
        await get_record(**kwargs)
    except asyncio.TimeoutError as e:
        log.error(
            "%s TimeoutError => %s"
            % (task_record_user_encrypt_key.__name__, e.args[0] if e.args else str(e))
        )

    except Exception as e:
        log.error(
            "%s TypeError => %s"
            % (task_record_user_encrypt_key.__name__, e.args[0] if e.args else str(e))
        )


# @backoff.on_exception(
#         backoff.expo,
#         (asyncio.TimeoutError,),
#         max_tries=5,
#         max_time=5,
#     )
async def get_record(
    **kwargs,
) -> None:
    from cryptomarket.deribit_client import DeribitLimited

    deribit_limited = DeribitLimited()
    context_redis_connection = deribit_limited.context_redis_connection
    redis_key = RadisKeysEnum.AES_REDIS_KEY.value % kwargs["client_id"]
    try:

        async with context_redis_connection() as redis_client:
            result_ = await asyncio.wait_for(
                redis_client.setex(redis_key, 97200, json.dumps(kwargs)), 10
            )
            return result_
    except Exception as e:
        log.error(
            "%s ERROR => %s" % (get_record.__name__, e.args[0] if e.args else str(e))
        )
