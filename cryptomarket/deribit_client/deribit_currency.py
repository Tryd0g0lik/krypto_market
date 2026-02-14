"""
cryptomarket/deribit_client/deribit_currency.py
"""

import asyncio
import json
from collections import UserDict
from uuid import uuid4

from fastapi import Request, Response, status

from cryptomarket.deribit_client.deribit_person import PersonDictionary
from cryptomarket.errors import DeribitValueError
from cryptomarket.errors.person_errors import PersonDictionaryError
from cryptomarket.project.settings.core import settings

setting = settings()


class CurrencyDictionary(UserDict):
    def __init__(
        self,
        maxsize: int | None = None,
    ):
        """
        :param maxsize: (int|None) When dictionary would get a length == maxsize mean
        remove a first element.
        """
        self.maxsize = maxsize
        super().__init__()

    def __setitem__(self, key, value):
        try:
            if (
                key is None
                or value is None
                or not isinstance(key, str)
                or not isinstance(value, list)
            ):
                raise PersonDictionaryError()

            if self.maxsize is not None and len(self) >= self.maxsize:
                self.pop(list(self.keys())[0])
            super().__setitem__(key, value)
        except PersonDictionaryError as e:
            raise e

    def __vhas__(self, key, val) -> bool:
        """Check presence a key in the dictionary.
        True mean the key was found and False if not found the incoming key.,
        """
        try:
            if val is None:
                raise DeribitValueError()
            if val in list(self.get(key)):
                return True
            return False

        except DeribitValueError as e:
            raise e


# ===============================
# ---- RESPONSE HTTP
# ==============================
class CryptoCurrency:
    # Template "{'btc_usd': [< person >, ...], 'eth_usd': [< person >, ...]}"
    currency_dict = CurrencyDictionary(maxsize=setting.DERIBIT_QUEUE_SIZE)

    def __init__(self):
        self.response = Response()

    def create_order(self, request: Request):
        from cryptomarket.project.app import manager

        persons = manager.person_manager.person_dict
        ticker = request.path_params.get("ticker")
        person_id = request.path_params.get("user_id")
        # person_id = request.headers.get('"X-User-ID"')
        headers_request_id = request.headers.get('"X-Request-ID"')
        self.__check_received_data(person_id, persons, ticker, request)
        if self.response.status_code >= status.HTTP_300_MULTIPLE_CHOICES:
            return self.response

        if headers_request_id is None:
            headers_request_id = str(uuid4())
        self.response.status_code = status.HTTP_201_CREATED
        self.response.content = json.dumps(
            {"detail": "Ticker was added (in queue for monitoring) successfully!"}
        )
        if ticker not in self.currency_dict:
            self.currency_dict.__setitem__(ticker.lower(), [person_id.strip()])
        elif self.currency_dict.__vhas__(ticker.lower(), person_id):
            self.response.content = json.dumps({"detail": "Ticker was added before!"})
            self.response.status_code = status.HTTP_200_OK
        else:
            v: list = self.currency_dict.get(ticker.lower())
            v.append(headers_request_id)
            self.currency_dict.__setitem__(ticker.lower(), v)
        return self.response

    def update_order(self, request: Request):
        pass

    def cancel_order(self, request: Request):
        from cryptomarket.project.app import manager

        persons = manager.person_manager.person_dict
        ticker = request.query_params.get("ticker")
        person_id = request.query_params.get("user_id")
        # person_id = request.headers.get('"X-User-ID"')
        # headers_request_id = request.headers.get('"X-Request-ID"')
        self.__check_received_data(person_id, persons, ticker, request)
        if self.response.status_code >= status.HTTP_300_MULTIPLE_CHOICES:
            return self.response

        self.currency_dict.get(ticker.lower(), []).remove(person_id.strip())
        self.response.content = json.dumps(
            {"detail": f"Order per ticker: {ticker} cancel was successfully!"}
        )
        self.response.status_code = status.HTTP_200_OK
        return self.response

    def cancel_all_orders(self, request: Request):
        from cryptomarket.project.app import manager

        persons = manager.person_manager.person_dict
        ticker = request.query_params.get("ticker")
        person_id = request.query_params.get("user_id")
        # person_id = request.headers.get('"X-User-ID"')
        # headers_request_id = request.headers.get('"X-Request-ID"')
        self.__check_received_data(person_id, persons, ticker, request)
        if self.response.status_code >= status.HTTP_300_MULTIPLE_CHOICES:
            return self.response

        found_person_id_list = [
            {k: v} for k, v in self.currency_dict.items() if person_id in v
        ]
        clean_list = [
            {k: v.remove(person_id)}
            for view in found_person_id_list
            for k, v in view.items()
        ]
        [self.currency_dict.__setitem__(k, v) for k, v in clean_list]
        self.response.content = json.dumps({"detail": "Person was removed successful!"})
        self.response.status_code = status.HTTP_200_OK
        return self.response

    def __check_received_data(
        self, person_id: str, persons: dict, ticker: str, request: Request
    ):
        if person_id is None or person_id not in persons:
            self.response.content = json.dumps({"detail": "User not found!"})
            self.response.status_code = status.HTTP_401_UNAUTHORIZED
            return self.response
        person = persons.get(person_id)
        if not person.active:
            self.response.content = json.dumps(
                {"detail": "User not active! Connect profile (SSE canal)"}
            )
            self.response.status_code = status.HTTP_400_BAD_REQUEST
            return self.response
        if ticker not in setting.CURRENCY_FOR_CHOOSING:
            self.response.content = json.dumps({"detail": "Ticker not found!"})
            self.response.status_code = status.HTTP_404_NOT_FOUND
            return self.response
        self.response.status_code = status.HTTP_200_OK
        return self.response
