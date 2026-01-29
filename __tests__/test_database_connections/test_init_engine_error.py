"""
__tests__/test_database_connections/test_init_engine_error.py
"""
import logging
from unittest.mock import MagicMock

import pytest

from __tests__.fixtures.fixt_mock import (
    fix_mock_iS_ASYNC_False,
    fixt_DatabaseConnection,
)
from __tests__.fixtures.fixture_test_log import (
    fixt_end_TEST,
    fixt_start_TEST,
    fixt_START_work,
)
from cryptomarket.database.connection import DatabaseConnection
from cryptomarket.project.settings.core import settings

log = logging.getLogger(__name__)


class TestInitEngines:



    def test_init_engines_parameter_max_overflow_error_none(self, fixt_START_work, fixt_start_TEST, fixt_end_TEST):

        """The 'max_overflow_' parameter contain value the None. This must be a ValueError'"""
        connection = DatabaseConnection(settings().get_database_url_sqlite)
        # =====================
        # test the 'max_overflow_' =None parameter return error
        # =====================
        fixt_start_TEST(self.test_init_engines_parameter_max_overflow_error_none.__name__)
        with pytest.raises(ValueError) as test_session:

            connection.init_engine(max_overflow_=None)
        assert test_session.type == ValueError
        assert test_session.value is not None
        assert test_session.value.args is not None
        assert test_session.value.args[0] is not None
        error_message = test_session.value.args[0]
        result_bool  = "ERROR => The variables is invalid: 'pool_size_'" in str(error_message)
        assert  result_bool == True
        fixt_end_TEST(self.test_init_engines_parameter_max_overflow_error_none.__name__)

    def test_init_engines_parameter_max_overflow_error_zero(self, fixt_START_work, fixt_start_TEST, fixt_end_TEST):
        """The 'max_overflow_' parameter contain value < 0 (less than zero). This must be a ValueError'"""
        connection = DatabaseConnection(settings().get_database_url_sqlite)
        # =====================
        # test the 'max_overflow_' =(-1) parameter return error
        # =====================
        fixt_start_TEST(self.test_init_engines_parameter_max_overflow_error_zero.__name__)
        with pytest.raises(ValueError) as test_session:
            connection.init_engine(max_overflow_=(-1))

        assert test_session.type == ValueError
        assert test_session.value is not None
        assert test_session.value.args is not None
        assert test_session.value.args[0] is not None
        error_message = test_session.value.args[0]
        result_bool = "ERROR => The variables is invalid: 'pool_size_'" in str(error_message)
        assert result_bool == True
        fixt_end_TEST(self.test_init_engines_parameter_max_overflow_error_zero.__name__)


    def test_init_engines_parameter_pool_size_error_none(self, fixt_START_work, fixt_start_TEST, fixt_end_TEST):
        """The 'pool_size_' parameter contain value the None. This must be a ValueError'"""
        connection = DatabaseConnection(settings().get_database_url_sqlite)
        # =====================
        # test the 'pool_size_' =None parameter return error
        # =====================
        fixt_start_TEST(self.test_init_engines_parameter_pool_size_error_none.__name__)
        with pytest.raises(ValueError) as test_session:
            connection.init_engine(pool_size_=None)
        assert test_session.type == ValueError
        assert test_session.value is not None
        assert test_session.value.args is not None
        assert test_session.value.args[0] is not None
        error_message = test_session.value.args[0]
        result_bool = "ERROR => The variables is invalid: 'pool_size_'" in str(error_message)
        assert result_bool == True
        fixt_end_TEST(self.test_init_engines_parameter_pool_size_error_none.__name__)

    def test_init_engines_parameter_pool_size_error_zero(self, fixt_START_work, fixt_start_TEST, fixt_end_TEST):
        """The 'pool_size_' parameter contain value < 0 (less than zero). This must be a ValueError'"""
        connection = DatabaseConnection(settings().get_database_url_sqlite)
        # =====================
        # test the 'pool_size_' =(-1) parameter return error
        # =====================
        fixt_start_TEST(self.test_init_engines_parameter_pool_size_error_zero.__name__)
        with pytest.raises(ValueError) as test_session:
            connection.init_engine(pool_size_=(-1))

        assert test_session.type == ValueError
        assert test_session.value is not None
        assert test_session.value.args is not None
        assert test_session.value.args[0] is not None
        error_message = test_session.value.args[0]
        result_bool = "ERROR => The variables is invalid: 'pool_size_'" in str(error_message)
        assert result_bool == True
        fixt_end_TEST(self.test_init_engines_parameter_pool_size_error_zero.__name__)

    def test_init_engines_parameter_async_db_ur_error(self,monkeypatch, fixt_START_work, fixt_start_TEST, fixt_end_TEST, ):

        # =====================
        # Mock self._is_check_async_url
        # =====================
        mock_is_check_async_url = MagicMock(return_value = True)
        monkeypatch.setattr(
            DatabaseConnection,
            "_is_check_async_url",
            mock_is_check_async_url
        )
        # =====================
        # test the 'pool_size_' =(-1) parameter return error
        # =====================
        fixt_start_TEST(self.test_init_engines_parameter_async_db_ur_error.__name__)
        with pytest.raises(ValueError) as test_session:
            connection = DatabaseConnection(None)
            connection.init_engine()

        assert test_session.type == ValueError
        assert test_session.value is not None
        assert test_session.value.args is not None
        assert test_session.value.args[0] is not None
        error_message = test_session.value.args[0]
        result_bool = "ERROR => The variables is invalid: 'pool_size_'" not in str(error_message)
        assert result_bool == True
        result_bool = "async ERROR => " in str(error_message)
        assert result_bool == True
        fixt_end_TEST(self.test_init_engines_parameter_async_db_ur_error.__name__)

    def test_init_engines_parameter_sync_db_ur_error(self, monkeypatch, fix_mock_iS_ASYNC_False, fixt_DatabaseConnection, fixt_START_work, fixt_start_TEST, fixt_end_TEST, ):

        # =====================
        # test the 'db_url' not is string parameter return error
        # =====================

        monkeypatch.setattr(
            DatabaseConnection,
            "_is_check_async_url",
            fix_mock_iS_ASYNC_False()
        )
        fixt_start_TEST(self.test_init_engines_parameter_sync_db_ur_error.__name__)
        with pytest.raises(ValueError) as test_session:
            connection = fixt_DatabaseConnection(None)
            connection.init_engine()
        log.info("Is_async_url: %s" % connection._is_check_async_url)
        assert test_session.type == ValueError
        assert test_session.value is not None
        assert test_session.value.args is not None
        assert test_session.value.args[0] is not None
        error_message = test_session.value.args[0]
        result_bool = "ERROR => The variables is invalid: 'pool_size_'" not in str(error_message)
        assert result_bool == True
        result_bool = "]: sync ERROR =>" in str(error_message)
        assert result_bool == True
        fixt_end_TEST(self.test_init_engines_parameter_sync_db_ur_error.__name__)
