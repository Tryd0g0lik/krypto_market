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
        The '%s' is 'client_id' (example: "aserediskey:_XcQ7xuV") , it for the deribit api key.
        Note: We have created the cache.
        When we use this key.
        After we delete the used key. We don't saving the old keys.
        Every user have own unique key for the single request.
        Example; "{\"client_id\": \"_XcQ7xuV\", \"encrypt_key\": \"0YNfS0SSYWwCRTNrWxfioH3dkhP0YaCxrNqwpOA1HLI=\"}"
    :param 'DERIBIT_USER_RESULT' - The deribit data \
           we are receiving from the cache server/. This parameter is a key of cache/
           Template "deribit:authenticated:< client_id >"
    :param 'DERIBIT_GET_SUBACCOUNTS' "data_to_send_to_apiDeribit["params"]["grant_type"] is 'get_subaccounts'"
           # Get subaccounts
    """

    DERIBIT_STRIPE_RATELIMIT_TASK = "deribit:ratelimit:%s:%s"
    AES_REDIS_KEY = "aserediskey:%s"
    DERIBIT_USER_RESULT = "deribit:result:%s"
    DERIBIT_GET_SUBACCOUNTS = "deribit:get_subaccounts:%s"
