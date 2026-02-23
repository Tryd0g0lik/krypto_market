"""
cryptomarket/main.py
"""

import asyncio

import uvicorn

from cryptomarket.project.settings.settings_env import APP_HOST_, APP_PORT_


async def main() -> None:
    uvicorn.run(
        "cryptomarket.project.app:app",
        host=APP_HOST_,
        port=int(APP_PORT_),
        workers=2,
        limit_max_requests=1000,
        reload=True,
        reload_dirs=["cryptomarket"],
    )


if __name__ == "__main__":
    asyncio.run(main())
