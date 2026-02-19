"""
cryptomarket/errors/database_errors.py
"""


class DatabaseConnectionCoroutineError(Exception):
    def __init__(self, log_message=None):
        self.log_message = log_message
        message = f"{self.__class__.__name__} => Database connection coroutine error! Does not use 'await' anywhere."
        if log_message is not None:
            message += f"\n => {log_message} \n"
        super().__init__(message)
