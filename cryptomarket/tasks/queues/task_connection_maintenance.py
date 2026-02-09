"""
cryptomarket/tasks/queues/task_connection_maintenance.py
"""

import asyncio
import logging

from cryptomarket.project.signals import signal

log = logging.getLogger(__name__)


async def connection_maintenance_task(*args, **kwargs):
    """Run periodic connection maintenance."""
    from cryptomarket.tasks.queues.task_account_user import task_account

    interval_seconds: int = 15
    while True:

        try:
            # 1. Cleanup old connections
            # await manager.ws_connection_manager.cleanup()
            # await task_account([], {})
            # ===============================
            # ---- RAN SIGNAL
            # ===============================
            # await  task_account([], {})
            await signal.schedule_with_delay(
                callback_=None, asynccallback_=task_account
            )
            # # 2. Log statistics (optional)
            # stats = await manager.ws_connection_manager.get_stats()
            # log.info(f"Connection stats: {stats['total_connections']} active connections")

        except Exception as e:
            log.error(f"Connection maintenance error: {e}")
        await asyncio.sleep(interval_seconds)
