"""
__tests__/test_database_connections/test_init_engines.py
"""
import logging

import pytest

from __tests__.fixtures.fixture_test_log import (
    fixt_end_TEST,
    fixt_start_TEST,
    fixt_START_work,
)
from cryptomarket.database.connection import DatabaseConnection
from cryptomarket.project.settings.core import app_settings

log = logging.getLogger(__name__)

class TestInitEngines:

    def test_init_engines_parameter_session_factory_async(self):
        """The 'session_factory' parameter contain value the SQLAlchemy session factory. First we check a connection.
        That (connection) should be 'is_async' """

        from sqlalchemy.ext.asyncio import AsyncSession
        connection = DatabaseConnection(app_settings.get_database_url_sqlite)
        connection.init_engine()
        assert connection.is_async
        assert isinstance(connection.session_factory(), AsyncSession)
        # session_factory

    def test_init_engines_parameter_session_factory_sync(self):
        """The 'session_factory' parameter contain value the SQLAlchemy session factory. First we check a connection.
        That (connection) should be not 'is_async' """

        from sqlalchemy.ext.asyncio import AsyncSession
        url_db = app_settings.get_database_url_sqlite.replace('+aiosqlite', "")
        assert url_db.startswith("sqlite://")
        connection = DatabaseConnection(url_db)
        connection.init_engine()
        assert not connection.is_async
        assert not isinstance(connection.session_factory(), AsyncSession)
        # session_factory
