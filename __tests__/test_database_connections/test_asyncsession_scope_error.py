"""
__tests__/test_database_connections/test_asyncsession_scope_error.py
"""
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from __tests__.fixtures.fixt_mock import (
    fix_mock_iS_ASYNC_False,
    fix_mock_iS_ASYNC_True,
    fixt_DatabaseConnection,
)
from __tests__.fixtures.fixture_test_log import (
    fixt_end_TEST,
    fixt_start_TEST,
    fixt_START_work,
)
from cryptomarket.database.connection import DatabaseConnection
from cryptomarket.project.settings.core import app_settings

log = logging.getLogger(__name__)


class TestSessionScope:
    @pytest.mark.asyncio
    async def test_asyncsession_scope_parameter_is_async_error(self, monkeypatch, fix_mock_iS_ASYNC_False,
                                                    fixt_DatabaseConnection, fixt_START_work,
                                                      fixt_start_TEST, fixt_end_TEST, ):
        """Check error in session scope 'Cannot get sync session from async engine'"""
        fixt_start_TEST(self.test_asyncsession_scope_parameter_is_async_error.__name__)
        # =====================
        # test the 'db_url' not is string parameter return error
        # =====================
        monkeypatch.setattr(
            DatabaseConnection,
            "_is_check_async_url",
            fix_mock_iS_ASYNC_False()
        )

        with pytest.raises(ValueError) as test_session:
            connection = fixt_DatabaseConnection(None)
            # connection.session_factory = AsyncMock(return_value=True)
            # connection.close = AsyncMock(return_value=None)
            asyncsession_scope = connection.asyncsession_scope
            async with asyncsession_scope() as session:
                pass

        assert test_session.type == ValueError
        assert test_session.value is not None
        assert test_session.value.args is not None
        assert test_session.value.args[0] is not None
        error_message = test_session.value.args[0]
        result_bool = "Cannot get async session from sync engine".startswith(error_message)
        assert result_bool == True
        fixt_end_TEST(self.test_asyncsession_scope_parameter_is_async_error.__name__)

    @pytest.mark.asyncio
    async def test_asyncsession_scope_parameter_session_error(self, monkeypatch, fix_mock_iS_ASYNC_True,
                                                              fixt_DatabaseConnection, fixt_START_work,
                                                      fixt_start_TEST, fixt_end_TEST, ):
        """Check error in session scope '[%s.%s]: session ERROR => %s'"""

        fixt_start_TEST(self.test_asyncsession_scope_parameter_session_error.__name__)

        db_url = app_settings.get_database_url_sqlite
        mock_session = AsyncMock(return_value=True)
        mock_session.close = AsyncMock(return_value=None)
        mock_session.rollback = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock(return_value=None)
        log.warning("-------- 1 -------- ")
        # with pytest.raises(ValueError) as test_session:
        connection = fixt_DatabaseConnection(db_url)
        mock_session_factory = AsyncMock(return_value=mock_session)
        connection.session_factory = mock_session_factory
        asyncsession_scope = connection.asyncsession_scope

        try:
            async with asyncsession_scope() as session:
                log.warning("-------- 2 -------- ")
                pass
        except ValueError as err:
            log.warning("-------- 3 -------- ")
            log_error = err.args[0] if err.args else str(err)
            assert log_error is not None
            result_bool = "Cannot get async session from sync engine" not in log_error
            assert result_bool == True
            log.warning(result_bool)
            log.warning(log_error)
            result_bool = "]: ERROR =>" in log_error
            assert result_bool == True
            fixt_end_TEST(self.test_asyncsession_scope_parameter_session_error.__name__)
