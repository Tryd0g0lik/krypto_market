"""
cryptomarket/tasks/queues/task_user_data_to_cache.py:1
"""

import asyncio
import json
import logging

from cryptomarket.project.sse_manager import setting

log = logging.getLogger(__name__)


async def task_caching_user_data(
    *args,
    **kwargs,
) -> None:
    """
    :param args: [< ticker_name >]
    :param kwargs: {< client_id: str > : json.dumps([ ... ])}
    :param kwargs[client_id]: (str) The client id of the user. This client index from the deribit account.
        That is the required variable!
    """
    log.info(
        "TEST DEBUG The type 'args': %s & 'args': %s and type 'kwargs': %s & 'kwargs': %s ",
        (type(args), args, type(kwargs), kwargs),
    )
    if (
        args is None
        or not isinstance(args, list | tuple)
        or kwargs is None
        or not isinstance(kwargs, dict)
    ):
        raise TypeError(
            "%s TypeError => The type 'args' or 'kwargs' variable is incorrect!",
            (task_caching_user_data.__name__,),
        )
    if (
        args[0] is None
        or not isinstance(args[0], str)
        or len(kwargs) < 1
        or kwargs.get("client_id") is None
    ):
        raise ValueError(
            "%s ERROR => The 'args' is incorrect or 'kwargs' value is not defined or 'kwargs[client_id]' was not found!",
            (task_caching_user_data.__name__,),
        )
    try:
        await get_record(*args, **kwargs)
    except asyncio.TimeoutError as e:
        log.error(
            "%s TimeoutError => %s"
            % (task_caching_user_data.__name__, e.args[0] if e.args else str(e))
        )

    except Exception as e:
        log.error(
            "%s TypeError => %s"
            % (task_caching_user_data.__name__, e.args[0] if e.args else str(e))
        )


async def get_record(
    *args,
    **kwargs,
) -> None:
    from cryptomarket.deribit_client import DeribitLimited

    deribit_limited = DeribitLimited()
    context_redis_connection = deribit_limited.context_redis_connection

    try:

        async with context_redis_connection() as redis_client:
            result_ = await asyncio.wait_for(
                redis_client.setex(
                    args[0],
                    setting.CACHE_AUTHENTICATION_DATA_LIVE,
                    json.dumps(kwargs),
                ),
                10,
            )
            return result_
    except Exception as e:
        log.error(
            "%s ERROR => %s" % (get_record.__name__, e.args[0] if e.args else str(e))
        )
