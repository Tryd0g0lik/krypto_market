"""
cryptomarket/models/schemes/validates.py
"""

import logging
import re

log = logging.getLogger(__name__)


def validate_all_requiredFields(**value: dict) -> bool:
    """
    :param value:dict.  Example: '{"user_id": 12}'
    """
    # ==========================
    # ----- USER_ID
    # ==========================
    user_id = value["user_id"]

    if user_id is None or len(user_id) == 0:
        logg_t = "[%s]: Validate Error =>  %s" % (
            validate_all_requiredFields.__name__,
            "models_errors.userModel.validate_user_id.0",
        )
        log.error(logg_t)
        raise ValueError(logg_t)

    return True
