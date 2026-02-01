"""
cryptomarket/project/functions.py
"""

import asyncio
import json
import logging
import pickle
import threading

from cryptomarket.project.settings.core import DEBUG, settings

log = logging.getLogger(__name__)


def run_async_worker(callback_, *args, **kwargs):
    """
    :param callback_: This is your function is handler of data.
    :param args:
    :param kwargs:
    :return:
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if kwargs:
            return loop.run_until_complete(callback_(**kwargs))
        else:
            return loop.run_until_complete(callback_(*args))
    except Exception as e:
        log.error(e.args[0] if e.args else str(e))
    finally:
        loop.close()


def run_sync_worker(callback_, *args, **kwargs):
    """
    :param callback_: This is your function is handler of data.
    :param args:
    :param kwargs:
    :return:
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if kwargs:
            return loop.run_in_executor(None, lambda: callback_(**kwargs))
        else:
            return loop.run_in_executor(None, lambda: callback_(*args))

    except Exception as e:
        log.error(e.args[0] if e.args else str(e))

    finally:
        loop.close()


# ===============================
# ---- CREATE THE ONE/TEMPLATE TASK
# ===============================
def wrapper_delayed_task(
    callback_=None,
    asynccallback_=None,
    delay_seconds: int = 0.2,
):
    """Running handle of tasks. This is else one a worker."""
    livetime_ = 5

    async def delayed_task(*args, **kwargs):
        await asyncio.sleep(delay_seconds)
        try:
            """
            This code is opening a 'door' in the new flow/pool for an async (or a sync) function with new loop.
            The timeout (or deadline or expect) is the 5 second after start. \
            This function  (the 'asynccallback_' name or 'callback_')accept other (else one)\
             the async ( or the sync) function on the entry-point and '**kwargs'.
            """
            if asynccallback_ is not None:

                threading_result = threading.Thread(
                    target=lambda: (
                        run_async_worker(asynccallback_, *args, **kwargs)
                        if args and kwargs
                        else (
                            run_async_worker(asynccallback_, *args)
                            if args
                            else run_async_worker(asynccallback_, **kwargs)
                        )
                    ),
                    daemon=True,
                )
                threading_result.start()
                threading_result.join(timeout=livetime_)

                if not threading_result.daemon:
                    log.error(
                        """[%s]: Signal ThreadError => %s deos not found! """
                        % (
                            delayed_task.__name__,
                            threading_result.name,
                        )
                    )
                pass
            elif callback_ is not None:
                threading_result = threading.Thread(
                    target=lambda: (
                        run_sync_worker(callback_, *args, **kwargs)
                        if args and kwargs
                        else (
                            run_sync_worker(callback_, *args)
                            if args
                            else run_sync_worker(callback_, **kwargs)
                        )
                    ),
                    daemon=True,
                )
                threading_result.start()
                threading_result.join(timeout=7)
                if not threading_result.daemon:
                    log.error(
                        """[%s]: Signal ThreadError => %s deos not found! """
                        % (
                            delayed_task.__name__,
                            threading_result.name,
                        )
                    )
            else:
                log_t = (
                    """[%s]: Signal ValueError => Callback deos not found! """
                    % delayed_task.__name__
                )
                log.error(log_t)
                raise ValueError(log_t)
        except TypeError as e:
            log_t = """[%s]: Signal TypeError => Data is not correct! %s""" % (
                delayed_task.__name__,
                e.args[0] if e.args else str(e),
            )
            log.error(log_t)
            raise TypeError(log_t)
        except Exception as e:
            log_t = "[%s]: Signal Error => : %s" % (
                delayed_task.__name__,
                e.args[0] if e.args else str(e),
            )
            log.error(log_t)
            raise TypeError(log_t)

    return delayed_task


url_str = (
    settings().get_database_url_sqlite
    if DEBUG
    else settings().get_database_url_external
)


def connection_database():
    from cryptomarket.database.connection import DatabaseConnection

    return DatabaseConnection(url_str)


def obj_to_byte(odj) -> bytes:
    import pickle

    return pickle.dumps(odj)


def byte_to_obj(byte_odj):
    return pickle.loads(byte_odj)
