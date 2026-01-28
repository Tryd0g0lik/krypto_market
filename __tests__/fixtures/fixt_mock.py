"""
__tests__/fixtures/fixt_mock.py:1
"""
from unittest.mock import MagicMock

import pytest

from cryptomarket.database.connection import DatabaseConnection


@pytest.fixture(scope="function")
def fixt_DatabaseConnection():
    def wrapper(*args):
        return  DatabaseConnection(args[0])
    return wrapper


@pytest.fixture(scope="function")
def fix_mock_iS_ASYNC_False():
    def wrapper():
        # =====================
        # Mock ._is_check_async_url
        # =====================
        mock_is_check_async_url = MagicMock(return_value=False)
        return mock_is_check_async_url
    return wrapper

@pytest.fixture(scope="function")
def fix_mock_iS_ASYNC_True():
    def wrapper():
        # =====================
        # Mock ._is_check_async_url
        # =====================
        mock_is_check_async_url = MagicMock(return_value=True)
        return mock_is_check_async_url

    return wrapper
