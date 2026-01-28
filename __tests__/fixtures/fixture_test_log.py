"""
__tests__/fixtures/fixture_test_log.py
"""
import logging

import pytest

log = logging.getLogger(__name__)



@pytest.fixture
def fixt_START_work():
    """Start test - mark for the log file. It is the 'log_putout.log'"""
    log.info("------ START  ------")


@pytest.fixture(scope="function")
def fixt_start_TEST():
    """Start test - mark for the log file.  It is the 'log_putout.log'"""

    def test_wrap(method_name: str):
        log.info("------ START %s  ------" % method_name)

    return test_wrap


@pytest.fixture(scope="function")
def fixt_end_TEST():
    """ End test - mark for the log file. It is the 'log_putout.log'"""

    def test_wrap(method_name: str):
        log.info("------ END %s  ------" % method_name)

    return test_wrap
