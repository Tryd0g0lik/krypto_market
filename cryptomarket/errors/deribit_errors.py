"""
cryptomarket/errors/deribit_errors.py
"""

import logging

log = logging.getLogger(__name__)


class DeribitError(Exception):
    """Базовое исключение для DeribitSessionManager"""

    pass


class DeribitValueError(DeribitError):
    def __init__(self, log_message=None) -> None:
        self.log_message = log_message
        message = f"""{self.__class__.__name__} => Check incoming variable. They are not correct"""
        if log_message:
            message += f" => {log_message} \n"
        super().__init__(message)


class DeribitKeyError(DeribitError):
    def __init__(self, key, log_message=None) -> None:
        self.log_message = log_message
        self.key = key
        message = f"""{self.__class__.__name__} => Check the 'key'.
        That is the required variable"""
        if log_message:
            message += f" => {log_message} \n"
        super().__init__(message)


class DeribitConnectionError(DeribitError):
    def __init__(self, *args, log_message=None) -> None:
        self.log_message = log_message
        message = f"""{self.__class__.__name__} => Check the '{args[0]}' is required variable"""
        if log_message:
            message += f" => {log_message} \n"
        super().__init__(message)
