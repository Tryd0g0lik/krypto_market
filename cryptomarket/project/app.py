"""
cryptomarket/project/app.py
"""

import asyncio
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from cryptomarket.api.v1.api_users import router_v1
from cryptomarket.database.handler_create_db import checkOrCreateTables
from cryptomarket.deribit_client import DeribitManage
from cryptomarket.project.middleware.middleware_basic import DeribitMiddleware
from cryptomarket.project.settings.core import app_settings
from cryptomarket.type import DeribitManageType

manager: DeribitManageType = DeribitManage()

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan():
    await manager.start_worker(limitations=10)
    try:
        yield
    finally:
        pass
    await manager.stop_workers()


def app_cryptomarket():
    # ===============================
    # ---- RUN DATABASE
    # ===============================
    def run_asyncio_in_thread():
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(checkOrCreateTables(app_settings))
        except Exception as e:
            log.error(
                "[%s]: Error => %s"
                % (
                    run_asyncio_in_thread.__name__,
                    e.args[0] if e.args else str(e),
                )
            )
        finally:
            loop.close()

    try:
        threading_ = threading.Thread(target=run_asyncio_in_thread)
        threading_.start()
        threading_.join(timeout=30)
    except Exception as e:
        log.error(
            "[%s]: Error => %s"
            % (
                app_cryptomarket.__name__,
                e.args[0] if e.args else str(e),
            )
        )
    # ===============================
    # ---- APP
    # ===============================
    app_ = FastAPI(
        title=app_settings.PROJECT_NAME,
        version=app_settings.PROJECT_VERSION,
        description="""This project is the microservice and service for
        the payments between roles the OWNER & MASTER""",
        lifespan=lifespan,
    )
    # ===============================
    # ---- MIDDLEWARE
    # ===============================
    middleware = DeribitMiddleware(manager)
    app_.middleware("http")(middleware)


    # ===============================
    # ---- CORS MIDDLEWARE
    # ===============================
    @app_.middleware("http")
    async def cors_middleware(request: Request, call_next):
        # Имитируем CORSMiddleware или используем настоящий
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = ",".join(
            app_settings.ALLOWED_METHODS
        )
        response.headers["Access-Control-Allow-Headers"] = ",".join(
            app_settings.ALLOWED_HEADERS
        )

        return response

    # ===============================
    # ---- ROUTER OPENAPI
    # ===============================
    app_.include_router(router_v1, prefix="/api/v1")

    # root endpoint
    @app_.get("/")
    async def root():
        return {
            "message": "cryptomarket API",
            "version": app_settings.PROJECT_VERSION,
            "docs": "/docs",
            "redoc": "/redoc",
        }

    # Health check endpoint
    @app_.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app_


app = app_cryptomarket()
