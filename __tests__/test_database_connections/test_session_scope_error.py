"""
__tests__/test_database_connections/test_init_engine_error.py
"""
import logging
from unittest.mock import MagicMock

import pytest
from more_itertools.more import side_effect

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

log = logging.getLogger(__name__)


class TestSessionScope:

    def test_session_scope_parameter_is_async_error(self, monkeypatch, fix_mock_iS_ASYNC_True,
                                                    fixt_DatabaseConnection, fixt_START_work,
                                                      fixt_start_TEST, fixt_end_TEST, ):
        """Check error in session scope 'Cannot get sync session from async engine'"""
        fixt_start_TEST(self.test_session_scope_parameter_is_async_error.__name__)
        # =====================
        # test the 'db_url' not is string parameter return error
        # =====================
        monkeypatch.setattr(
            DatabaseConnection,
            "_is_check_async_url",
            fix_mock_iS_ASYNC_True()
        )

        with pytest.raises(ValueError) as test_session:
            connection = fixt_DatabaseConnection(None)

            with connection.session_scope() as session:
                pass
        assert test_session.type == ValueError
        assert test_session.value is not None
        assert test_session.value.args is not None
        assert test_session.value.args[0] is not None
        error_message = test_session.value.args[0]
        result_bool = "Cannot get sync session from async engine".startswith(error_message)
        assert result_bool == True
        fixt_end_TEST(self.test_session_scope_parameter_is_async_error.__name__)

    @pytest.mark.current
    def test_session_scope_parameter_session_error(self, monkeypatch, fix_mock_iS_ASYNC_False, fixt_DatabaseConnection, fixt_START_work,
                                                      fixt_start_TEST, fixt_end_TEST, ):
        """Check error in session scope '[%s.%s]: session ERROR => %s'"""

        fixt_start_TEST(self.test_session_scope_parameter_session_error.__name__)
        # =====================
        # test the 'self.is_async'  return False
        # =====================
        monkeypatch.setattr(
            DatabaseConnection,
            "_is_check_async_url",
            fix_mock_iS_ASYNC_False()
        )

        connection = fixt_DatabaseConnection(None)

        mock_session = MagicMock(return_value=True)
        mock_session.close = MagicMock(return_value=None)
        mock_session.reset_mock = MagicMock(return_value=None)
        mock_session.rollback = MagicMock(return_value=None)
        mock_session.commit = MagicMock(side_effect=ValueError("My error in commit"))

        mock_session_factory = MagicMock(return_value=mock_session)
        connection.session_factory = mock_session_factory

        try:
            log.warning("-------- 1 -------- ")
            with connection.session_scope() as session:
                pass
                log.warning("-------- 2 -------- ")
        except Exception as err:
            log.warning("-------- 3 -------- ")
            log_error = err.args[0] if err.args else str(err)
            assert log_error is not None
            result_bool = "Cannot get sync session from async engine" not in log_error
            assert result_bool == True
            log.warning(log_error)
            result_bool = "]: session ERROR =>" in log_error
            assert result_bool == True
            fixt_end_TEST(self.test_session_scope_parameter_session_error.__name__)
