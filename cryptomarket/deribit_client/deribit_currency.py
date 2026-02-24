"""
cryptomarket/deribit_client/deribit_currency.py
"""

import json
from collections import UserDict
from uuid import uuid4

from fastapi import Request, Response, status
from watchfiles import awatch

from cryptomarket.api.v1.api_get_index_price import get_index_price_child
from cryptomarket.errors import DeribitValueError
from cryptomarket.errors.person_errors import PersonDictionaryError
from cryptomarket.project.enums import RadisKeysEnum
from cryptomarket.project.functions import set_record
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
# ---- RESPONSE HTTP LOCAL API
# This is the sub-function
# ==============================
class CryptoCurrency:
    # Template "{'btc_usd': [< person >, ...], 'eth_usd': [< person >, ...]}"
    currency_dict = CurrencyDictionary(maxsize=setting.DERIBIT_QUEUE_SIZE)

    def __init__(self):
        self.response = Response(media_type="application/json")

    async def create_order(self, request: Request):
        from cryptomarket.project.app import manager

        try:

            self.response.status_code = status.HTTP_201_CREATED
            persons = manager.person_manager.person_dict
            ticker = request.path_params.get("ticker")
            person_id = request.path_params.get("user_id")
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
                result = self.currency_dict.get(ticker.lower(), [])
                (
                    self.currency_dict.__setitem__(ticker.lower(), [person_id.strip()])
                    if result is None or len(result) == 0
                    else self.currency_dict[ticker.lower()].append(person_id.strip())
                )

                await self.set_cache()
            elif self.currency_dict.__vhas__(ticker.lower(), person_id):
                self.response.content = json.dumps(
                    {"detail": "Ticker was added before!"}
                )
                self.response.status_code = status.HTTP_200_OK
            else:
                v: list = self.currency_dict.get(ticker.lower())
                v.append(headers_request_id)
                self.currency_dict.__setitem__(ticker.lower(), v)

            return self.response
        except Exception as e:
            self.response.content = json.dumps(
                {"detail": str(e.args[0] if e.args else str(e))}
            )
            self.response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return self.response

    async def get_order(self, request: Request):
        from cryptomarket.project.app import manager

        ticker = request.path_params.get("ticker")
        person_id = request.path_params.get("user_id")
        persons = manager.person_manager.person_dict
        self.__check_received_data(person_id, persons, ticker, request)
        if self.response.status_code >= status.HTTP_300_MULTIPLE_CHOICES:
            return self.response
        result = self.currency_dict.get(ticker.lower(), {})
        if len(result) == 0:
            self.response.status_code = status.HTTP_404_NOT_FOUND
            return self.response
        try:
            response = await get_index_price_child(request)
            return response
        except Exception as e:
            self.response.content = json.dumps(
                {"detail": str(e.args[0] if e.args else str(e))}
            )
            self.response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return self.response

    def update_order(self, request: Request):
        pass

    async def cancel_order(self, request: Request):

        from cryptomarket.project.app import manager

        try:
            persons = manager.person_manager.person_dict
            ticker = request.path_params.get("ticker")
            person_id = request.path_params.get("user_id")
            self.__check_received_data(person_id, persons, ticker, request)
            if self.response.status_code >= status.HTTP_300_MULTIPLE_CHOICES:
                return self.response

            result = self.currency_dict.get(ticker.lower(), {})
            if len(result) == 0:
                self.response.status_code = status.HTTP_404_NOT_FOUND
                return self.response
            del self.currency_dict[ticker.lower()]
            await self.set_cache()
            self.response.content = json.dumps(
                {"detail": f"Order per ticker: {ticker} cancel was successfully!"}
            )
            await self.set_cache()
            self.response.status_code = status.HTTP_200_OK
            return self.response
        except Exception as e:
            self.response.content = json.dumps(
                {"detail": str(e.args[0] if e.args else str(e))}
            )
            self.response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return self.response

    def cancel_all_orders(self, request: Request):
        try:
            from cryptomarket.project.app import manager

            persons = manager.person_manager.person_dict
            ticker = request.query_params.get("ticker")
            person_id = request.query_params.get("user_id")
            self.__check_received_data(person_id, persons, ticker, request)
            if self.response.status_code >= status.HTTP_300_MULTIPLE_CHOICES:
                return self.response

            found_person_id_list = [
                {k: v} for k, v in self.currency_dict.items() if person_id in v
            ]
            if len(found_person_id_list) == 0:
                self.response.status_code = status.HTTP_404_NOT_FOUND
                return self.response

            clean_list = [
                {k: v.remove(person_id)}
                for view in found_person_id_list
                for k, v in view.items()
            ]
            [self.currency_dict.__setitem__(k, v) for k, v in clean_list]
            self.response.content = json.dumps(
                {"detail": "Person was removed successful!"}
            )
            self.response.status_code = status.HTTP_200_OK
            return self.response
        except Exception as e:
            self.response.content = json.dumps(
                {"detail": str(e.args[0] if e.args else str(e))}
            )
            self.response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
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

    async def set_cache(self):
        # from cryptomarket.project.app import manager

        # context_redis_connection = manager.rate_limit.context_redis_connection
        # ===============================
        # ---- CACHE SERVER
        # ===============================
        await set_record(
            RadisKeysEnum.DERIBIT_CURRENCY.value.strip(), **self.currency_dict
        )
        # async with context_redis_connection() as redis:
        #     await redis.setex(
        #         ,
        #         27 * 60 * 60,
        #         json.dumps({**self.currency_dict}),
        #     )

        pass
