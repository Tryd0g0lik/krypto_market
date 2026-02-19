"""
cryptomarket/errors/encrypt_error.py
"""

from cryptomarket.errors.deribit_errors import DeribitError


class EncryptTypeError(DeribitError):
    """
    For work with/in the 'cryptomarket.project.encrypt_manager.EncryptManager'
    """

    def __init__(self, log_message=None) -> None:
        self.log_message = log_message
        message = (
            f"""{self.__class__.__name__} => Check a type data from the entry point!"""
        )
        if log_message is not None:
            message += f" \n => {log_message} \n"
        super().__init__(message)
