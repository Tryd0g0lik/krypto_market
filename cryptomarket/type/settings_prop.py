"""
cryptomarket/type/settings_prop.py
"""

from typing import Protocol


# -----------------------------------------
# Settings
# -----------------------------------------
class SettingsProps(Protocol):
    PROJECT_NAME: str = "KryptoMarket"
    PROJECT_VERSION: str = "0.1.0"
    DEFAULT_LANGUAGE: str = "en"
    POSTGRES_PORT: str = "8000"
    POSTGRES_DB: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_USER: str = "postgres"
    POSTGRES_HOST: str = "127.0.0.1"
    __SQLITE_DB_PATH: str = "cryptomarket_db.sqlit3"
    __SQLALCHEMY_DATABASE_URL: str | None = None
    ALLOWED_ORIGINS: list[str] = []
    ALLOWED_METHODS: list[str] = []
    ALLOWED_HEADERS: list[str] = []
    CURRENCY_FOR_CHOOSING = []
    SSE_MAX_CONNECTION: int = 5000
    SSE_MAX_PER_IP: int = 50
    DERIBIT_MAX_QUANTITY_WORKERS = 10
    DERIBIT_MAX_CONCURRENT = 40
    DERIBIT_QUEUE_SIZE = 5000
    CACHE_AUTHENTICATION_DATA_LIVE = 97200

    def get_allowed_hosts(self, allowed_hosts: str) -> list[str]:
        """
        The function is for the securite connection to the allowed hosts
        """

        pass

    def set_database_url_external(self, url: str) -> None:
        """Set up the new url to the connection_database"""
        self.__SQLALCHEMY_DATABASE_URL = url

    @property
    def get_database_url_external(self) -> str:
        """The async path to the connection_database postgresql"""
        # POSTGRES
        return self.__SQLALCHEMY_DATABASE_URL

    def set_database_url_sqlite(self, url: str) -> None:
        self.__SQLITE_DB_PATH = url

    @property
    def get_database_url_sqlite(self) -> str:
        """The async path to the connection_database sqlite"""
        return self.__SQLITE_DB_PATH
