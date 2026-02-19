"""
cryptomarket/project/enums.py
"""

from enum import Enum


class ExternalAPIEnum(Enum):
    WS_COMMON_URL = "wss://test.deribit.com/ws/api/v2/"


class RadisKeysEnum(Enum):
    """
    :param 'DERIBIT_STRIPE_RATELIMIT_TASK' -  used for
        the controller ('deribit_client.deribit_clients.DeribitLimited.acquire'). Template of key: "deribit:ratelimit:%s:%s"
    :param 'ADERIBIT_PERSON_RESULT' This key  to the cache server.
        That is the single user key.
        This key has a parent: This 'deribit:person' is key from cache. \
        It hase value (json str): "{'deribit:person:< person_id >': {'person_id': ...., ...}, ....}"
        TEmplate of key: "deribit:person:%s"
    :param 'DERIBIT_CURRENCY' This is a dictionary/ It contain the template data (json string) "{'btc_usd': [< person >, ...], 'eth_usd': [< person >, ...]}"
    TEmplate of key: "deribit:currency"
    """

    DERIBIT_STRIPE_RATELIMIT_TASK = "deribit:ratelimit:%s:%s"
    DERIBIT_PERSON_RESULT = "deribit:person:%s"
    DERIBIT_CURRENCY = "deribit:currency"


class PersoneRoles(Enum):
    PERSONE = "person"
    PERSONE_PRIVATE = "person_private"
    PERSONE_ADMIN = "person_admin"
    PERSONE_MANAGER = "person_manager"
