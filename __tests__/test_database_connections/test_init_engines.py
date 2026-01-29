"""
__tests__/test_database_connections/test_init_engines.py
"""
import logging

from cryptomarket.database.connection import DatabaseConnection
from cryptomarket.project.settings.core import settings

# from cryptomarket.project.settings.core import settings

log = logging.getLogger(__name__)

class TestInitEngines:

    def test_init_engines_parameter_session_factory_async(self):
        """The 'session_factory' parameter contain value the SQLAlchemy session factory. First we check a connection.
        That (connection) should be 'is_async' """

        from sqlalchemy.ext.asyncio import AsyncSession
        connection = DatabaseConnection(settings().get_database_url_sqlite)
        connection.init_engine()
        assert connection.is_async
        assert isinstance(connection.session_factory(), AsyncSession)
        # session_factory

    def test_init_engines_parameter_session_factory_sync(self):
        """The 'session_factory' parameter contain value the SQLAlchemy session factory. First we check a connection.
        That (connection) should be not 'is_async' """

        from sqlalchemy.ext.asyncio import AsyncSession
        url_db = settings().get_database_url_sqlite.replace('+aiosqlite', "")
        assert url_db.startswith("sqlite://")
        connection = DatabaseConnection(url_db)
        connection.init_engine()
        assert not connection.is_async
        assert not isinstance(connection.session_factory(), AsyncSession)
        # session_factory
