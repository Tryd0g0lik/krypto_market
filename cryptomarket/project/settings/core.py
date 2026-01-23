"""
cryptomarket/project/settings/core.py

"""

import logging
import os
from pathlib import Path
from typing import List

from cryptomarket.project.settings.settings_env import (
    APP_HOST_,
    APP_PORT_,
    POSTGRES_DB_,
    POSTGRES_HOST_,
    POSTGRES_PASSWORD_,
    POSTGRES_PORT_,
    POSTGRES_USER_,
    PROJECT_MODE_,
)
from cryptomarket.type.settings_prop import SettingsProps
from logs import configure_logging

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent

DEBUG = True
configure_logging(logging.INFO)


# ================ SETTINGS =================
class Settings(SettingsProps):
    """
    TODO: Добавить логику условй распределяющие 'development' or 'testing' or 'staging' or 'production'.
    :params:'PROJECT_NAME': str App name.
        'PROJECT_VERSION': str App version. Example '0.1.0'
        'PROJECT_MODE': str. Choice only one from the collection strings: the 'development' or 'testing' or 'staging' \
            or 'production'.
            - 'production' - we make choice the setting and the connection to the db when we make deployment.
            - 'development'- It is for the development.
            - 'testing' - It is for the testing.
            - 'staging' - and some.
        'DEFAULT_LANGUAGE': str This is a language model from the client/browser. Default value is 'en'.
        'BASE_DIR': str This is base directory of the project.
        'APP_HOST': str This is host of app/ Default value is '127.0.0.1'.
        'APP_PROTOCOL': str  This is the 'http' or 'https'. This depends from the IP of out the out/external server.
            Default value is 'http'.
        'APP_PORT': str Default value is '8003'.
        '__SQLITE_DB_PATH': str This is used as local path for connection to the SQLite database. Default value is the string.
            It is local path to the database 'cryptomarket_db.sqlit3'.
            You can make changes to dp.  There insert the value 'None' and use 'SQLALCHEMY_DATABASE_URL' (below)
        '__SQLALCHEMY_DATABASE_URL': str This is a full path/address to the external db. .
        'ALLOWED_ORIGINS': list[str]This is list of allowed URLs/source. App cant get receive requests from these sources.
            It is  a URL's list whom we trust
        'ALLOWED_METHODS': list[str] This is list of allowed methods. Example: 'GET', 'POST'.
        'ALLOWED_HEADERS': list[str] This is list of allowed headers. Example: 'X-Language', 'Accept-Language'.
        `DEBUG`: bool  The True it is mean project was run to the debug mode or not.
        'DERIBIT_MAX_QUANTITY_WORKERS' - This is the fix worker's quantity for protecting the Deribit server from \
            a unlimited flow of requests. You can chang the max number.
        'DERIBIT_MAX_CONCURRENT' = The Deribit lock a work protection and API stability (it is tate limiting for \
            the concurrent requests)
    """

    # ---------------------------------------
    # DERIBIT
    # ---------------------------------------
    DERIBIT_MAX_QUANTITY_WORKERS = 10
    # ---------------------------------------
    #  COMMON
    # ---------------------------------------
    PROJECT_NAME: str = "cryptoMarket"
    PROJECT_VERSION: str = "0.1.0"
    PROJECT_MODE: str = PROJECT_MODE_
    DEFAULT_LANGUAGE: str = "en"
    # ---------------------------------------
    #  APP
    # ---------------------------------------
    APP_HOST: str = APP_HOST_
    APP_PORT: str = APP_PORT_
    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "")
    # ---------------------------------------
    #  POSTGRES
    # ---------------------------------------
    POSTGRES_PORT: str = POSTGRES_PORT_
    POSTGRES_DB: str = POSTGRES_DB_
    POSTGRES_PASSWORD: str = POSTGRES_PASSWORD_
    POSTGRES_USER: str = POSTGRES_USER_
    POSTGRES_HOST: str = POSTGRES_HOST_

    __SQLITE_DB_PATH: str = (
        f"sqlite+aiosqlite:///{os.path.join(BASE_DIR, "%s.sqlit3" % POSTGRES_DB)}".replace(
            "\\", "/"
        )
    )
    __SQLALCHEMY_DATABASE_URL: str | None = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}{POSTGRES_PORT if POSTGRES_PORT else ""}/{POSTGRES_DB}".replace(
            "\\", "/"
        )
    )
    ALLOWED_ORIGINS: List[str] = []
    ALLOWED_METHODS: List[str] = [
        "HEAD",
        "OPTIONS",
        "TRACE",
        "GET",
        "PUT",
        "DELETE",
        "PATCH",
        "POST",
    ]
    ALLOWED_HEADERS: List[str] = [
        "accept",
        "accept-encoding",
        "Authorization",
        "content-type",
        "dnt",
        "origin",
        "user-agent",
        "x-csrftoken",
        "x-requested-with",
        "Accept-Language",
        "Content-Language",
        "X-Language",
        "X-Request-ID",
    ]

    def get_allowed_hosts(self, allowed_hosts: str) -> list[str]:
        """
        The function is for the securite connection to the allowed hosts
        """

        hosts = allowed_hosts.split(", ")
        hosts = [h.strip() for h in hosts if h.strip()]

        if self.PROJECT_MODE == "production":
            hosts.insert(0, f"{self.APP_HOST}")
            hosts += [
                "db",
                "backend",
                "nginx",
                "celery",
                "redis",
                "[::1]",
            ]

        if not hosts and self.PROJECT_MODE == "production":
            text_e = (
                "[%s]: ALLOWED_HOSTS must be set in production"
                % self.get_allowed_hosts.__name__
            )
            log.error(text_e)
            raise ConnectionError(text_e)
        # The additional merged to an IP numbers for the Docker
        # IP of Docker is dynamic
        for third in range(16, 20):  # 172.16.0.0 - 172.19.255.255
            for fourth in range(0, 256):
                hosts.append(f"172.{third}.{fourth}")
        return hosts

    def set_database_url_external(self, url: str) -> None:
        """Set up the new url to the database"""
        self.__SQLALCHEMY_DATABASE_URL = url

    @property
    def get_database_url_external(self) -> str:
        """The async path to the database postgresql"""
        # POSTGRES
        return self.__SQLALCHEMY_DATABASE_URL

    def set_database_url_sqlite(self, url: str) -> None:
        self.__SQLITE_DB_PATH = url

    @property
    def get_database_url_sqlite(self) -> str:
        """The async path to the database sqlite"""
        return self.__SQLITE_DB_PATH


app_settings = Settings()
