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

    def get_allowed_hosts(self, allowed_hosts: str) -> list[str]:
        """
        The function is for the securite connection to the allowed hosts
        """
        pass

    @property
    def GET_DATABASE_URL_EXTERNAL(self) -> str:
        """The async path to the connection_database postgresql"""
        pass

    @property
    def get_database_url_sqlite(self) -> str:
        """The async path to the connection_database sqlite"""
        pass
