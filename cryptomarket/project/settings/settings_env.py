"""
cryptomarket/models/__init__.py
"""
import os
import dotenv

dotenv.load_dotenv()
APP_PROTOCOL_: str = os.getenv("APP_PROTOCOL", "http")
APP_HOST_: str = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT_: str = os.getenv("APP_PORT", "8003")
PROJECT_MODE_: str = os.getenv("PROJECT_MODE", "8003")
POSTGRES_DB_: str = os.getenv("POSTGRES_DB", "cryptomarket_db")
POSTGRES_PASSWORD_: str = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_USER_: str = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_HOST_: str = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT_: str = os.getenv("POSTGRES_PORT", "5432")

# Redis
REDIS_HOST: str = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT: str = os.getenv("REDIS_PORT", "6379")
REDIS_URL: str = os.getenv("REDIS_URL", "http://127.0.0.1:6379")

# Deribit
DERIBIT_SECRET_KEY: str = os.getenv("DERIBIT_SECRET_KEY")

