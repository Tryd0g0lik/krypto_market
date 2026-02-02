"""
cryptomarket/project/enums.py
"""

from enum import Enum


class ExternalAPIEnum(Enum):
    WS_COMMON_URL = "wss://test.deribit.com/ws/api/v2/"


class RadisKeysEnum(Enum):
    """
    :param 'DERBIT_STRIPE_RATELIMIT_TASK' - used for
        the controller ('deribit_client.deribit_clients.DeribitLimited.acquire').
    :param 'AES_REDIS_KEY' This key a dictionary type value to the cache server.
        The '%s' is 'client_id' (example: "aserediskey:_XcQ7xuV") , it's the deribit account index.
        Note: We have created the cache.
        When we use this key.
        After we delete the used key. We don't saving the old keys.
        Every user have own unique key for the single request.
        Example; "{\"client_id\": \"_XcQ7xuV\", \"encrypt_key\": \"0YNfS0SSYWwCRTNrWxfioH3dkhP0YaCxrNqwpOA1HLI=\"}"
    """

    DERBIT_STRIPE_RATELIMIT_TASK = "deribit:ratelimit:%s:%s"
    AES_REDIS_KEY = "aserediskey:%s"
