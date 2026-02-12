"""
cryptomarket/models/persons/model_person.py
"""

import logging

from more_itertools.more import map_except
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cryptomarket.models import BaseModel
from cryptomarket.project.enums import PersoneRoles
from cryptomarket.project.settings.core import DEBUG, settings

log = logging.getLogger(__name__)
setting = settings()
url_str = (
    setting.get_database_url_sqlite if DEBUG else setting.get_database_url_external
)


class PersonModel(BaseModel):

    if DEBUG:
        __tablename__ = "crypto_person"

    else:
        __tablename__ = "crypto.person"
        __table_args__ = ({"schema": "crypto"},)

    primary_role: Mapped[str] = mapped_column(
        "person_role",
        default=PersoneRoles.PERSONE.value,
    )
    email: Mapped[str] = mapped_column(
        "email",
        doc="""Email address of the account owner. The person’s email address.""",
    )
    client_id: Mapped[str] = mapped_column(
        "client_id", doc="""This is attribute from the deribit service."""
    )
    client_secret: Mapped[str] = mapped_column(
        "client_secret",
        doc="""This is attribute from the deribit service. Here the string is in encrypted state""",
    )
    is_access: Mapped[bool] = mapped_column("is_access", default=False)
    is_active: Mapped[bool] = mapped_column("is_active", default=False)
