"""
cryptomarket/tasks/queues/task_user_data_to_cache.py:1
"""

import asyncio
import json
import logging

from cryptomarket.project.functions import set_record

log = logging.getLogger(__name__)


async def task_caching_user_data(
    *args,
    **kwargs,
) -> None:
    """
    :param args: This is key for the cache server/
    :param kwargs: {< client_id: str > : json.dumps([ ... ])}
    :param kwargs[client_id]: (str) The client id for the deribit api key..
        That is the required variable!
    """

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
        await set_record(*args, **kwargs)
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
