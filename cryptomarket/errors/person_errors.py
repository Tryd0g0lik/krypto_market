"""
cryptomarket/errors/person_errors.py
"""

from poetry.console.commands import self

from cryptomarket.errors.deribit_errors import DeribitError


class PersonDictionaryError(DeribitError):
    def __init__(self, log_message=None):
        massage = f"""{self.__class__.__name__} => The entry point data is incorrect!"""
        if log_message is not None:
            massage += f" => {log_message}"

        super().__init__(massage)


class PersonNotFoundAccessError(DeribitError):
    """Not fount an access token"""

    def __init__(self, log_message=None):
        message = f"""{self.__class__.__name__} => The access-token not found! This is required to access your account!"""
        if log_message is not None:
            message += f" => {log_message}"
        super().__init__(message)
