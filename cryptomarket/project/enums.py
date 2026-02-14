"""
cryptomarket/project/enums.py
"""

from enum import Enum


class ExternalAPIEnum(Enum):
    WS_COMMON_URL = "wss://test.deribit.com/ws/api/v2/"


class RadisKeysEnum(Enum):
    """
    :param 'DERIBIT_STRIPE_RATELIMIT_TASK' - used for
        the controller ('deribit_client.deribit_clients.DeribitLimited.acquire').
    :param 'ADERIBIT_PERSON_RESULT' This key  to the cache server. Template is: 'deribit:person:< person_id >'
        That is the single user key.
        This key has a parent: This 'deribit:person' is key from cache. \
        It hase value (json str): "{'deribit:person:< person_id >': {'person_id': ...., ...}, ....}"

    """

    DERIBIT_STRIPE_RATELIMIT_TASK = "deribit:ratelimit:%s:%s"
    DERIBIT_PERSON_RESULT = "deribit:person:%s"


class PersoneRoles(Enum):
    PERSONE = "person"
    PERSONE_PRIVATE = "person_private"
    PERSONE_ADMIN = "person_admin"
    PERSONE_MANAGER = "person_manager"
