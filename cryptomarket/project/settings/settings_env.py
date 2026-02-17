"""
cryptomarket/models/__init__.py
"""

import os

import dotenv

dotenv.load_dotenv()
APP_PROTOCOL_: str = os.getenv("APP_PROTOCOL", "http")
APP_HOST_: str = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT_: str = os.getenv("APP_PORT", "8003")
# APP_SECRET_KEY: str = os.getenv(
#     "APP_SECRET_KEY", "Y)zogC38w1avXuTY2bUdxGmbw5egU6ai1LpQnWBba4vsUuG"
# )
PROJECT_MODE_: str = os.getenv("PROJECT_MODE", "8003")
POSTGRES_DB_: str = os.getenv("POSTGRES_DB", "cryptomarket_db")
POSTGRES_PASSWORD_: str = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_USER_: str = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_HOST_: str = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT_: str = os.getenv("POSTGRES_PORT", "5432")

# Redis
REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "Not_password")
REDIS_DB: str = os.getenv("REDIS_DB", "0")
REDIS_HOST: str = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT: str = os.getenv("REDIS_PORT", "6379")
REDIS_URL: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
REDIS_MASTER_NAME: str = os.getenv("REDIS_MASTER_NAME", "master")


# Deribit
# DERIBIT_SECRET_KEY: str = os.getenv("DERIBIT_SECRET_KEY")
# DERIBIT_CLIENT_ID: str = os.getenv("DERIBIT_CLIENT_ID")

# Celery
CELERY_BROKER_URL = REDIS_URL[:] + "/" + REDIS_DB[:]
CELERY_RESULT_BACKEND = REDIS_URL[:] + "/" + REDIS_DB[:]
# WebScoket
# Default value is the 'ws' protocol ('WS_PROTOCOL').
# You can have the protocol 'wss', if that is true, please make a comment for the 'WS_PROTOCOL' variable and remove
# the comment from 'WSS_PROTOCOL' variable.
# If you have wss  '.env' file (inside)
# WS_PROTOCOL = os.getenv("WS_PROTOCOL", None)
# WSS_PROTOCOL = os.getenv("WSS_PROTOCOL", None)
