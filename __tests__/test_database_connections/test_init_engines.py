"""
__tests__/test_database_connections/test_init_engines_parameter_max_overflow_error_None.py
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

    def test_init_engines_parameter_max_overflow_error_None(self, fixt_START_work, fixt_start_TEST, fixt_end_TEST):
        connection = DatabaseConnection(app_settings.get_database_url_sqlite)
        # =====================
        # test the 'max_overflow_' =None parameter return error
        # =====================
        fixt_start_TEST(self.test_init_engines_parameter_max_overflow_error_None.__name__)
        with pytest.raises(ValueError) as test_session:

            connection.init_engine(max_overflow_=None)
        assert test_session.type == ValueError
        assert test_session.value is not None
        assert test_session.value.args is not None
        assert test_session.value.args[0] is not None
        error_message = test_session.value.args[0]
        result_bool  = "ERROR => The variables is invalid: 'pool_size_'" in str(error_message)
        assert  result_bool == True
        fixt_end_TEST(self.test_init_engines_parameter_max_overflow_error_None.__name__)

    def test_init_engines_parameter_max_overflow_error_zero(self, fixt_START_work, fixt_start_TEST, fixt_end_TEST):
        connection = DatabaseConnection(app_settings.get_database_url_sqlite)
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
        connection = DatabaseConnection(app_settings.get_database_url_sqlite)
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
        connection = DatabaseConnection(app_settings.get_database_url_sqlite)
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
