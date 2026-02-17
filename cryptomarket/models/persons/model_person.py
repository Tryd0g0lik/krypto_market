"""
cryptomarket/models/persons/model_person.py
"""

import logging

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
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
    __table_args_some = (
        UniqueConstraint("email", name="user_email_unique"),
        Index("ix_user_email", "email", unique=True),
        Index("ix_index_app", "index_app", unique=True),
    )
    if DEBUG:
        __tablename__ = "crypto_person"
        __table_args__ = __table_args_some
    else:
        __tablename__ = "crypto.person"
        __table_args__ = __table_args_some + ({"schema": "crypto"},)
    index_app: Mapped[str] = mapped_column(
        "index_app",
        String(50),
        doc="""The user index from the app database. THe user index from the basic database (external app database""",
    )
    primary_role: Mapped[str] = mapped_column(
        "person_role",
        String(25),
        default=PersoneRoles.PERSONE.value,
    )
    email: Mapped[str] = mapped_column(
        "email",
        String(50),
        doc="""Email address of the account owner. The person’s email address.""",
    )
    system_name: Mapped[str] = mapped_column(
        "system_name",
        String(50),
        doc="""system_name address of the account owner.""",
    )
    username: Mapped[str] = mapped_column(
        "username",
        String(50),
        doc="""username of the account owner. """,
    )
    is_password: Mapped[bool] = mapped_column(
        "is_password",
        Boolean,
        doc=""".""",
    )
    client_id: Mapped[str] = mapped_column(
        "client_id",
        String(50),
        doc="""This is attribute from the deribit service.""",
    )
    client_secret: Mapped[str] = mapped_column(
        "client_secret",
        String(150),
        doc="""This is attribute from the deribit service. Here the string is in encrypted state""",
    )
    is_access: Mapped[bool] = mapped_column("is_access", Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(
        "is_active",
        Boolean,
        default=False,
        comment="If value has the True mean that an account is active and SSE canal was connected!",
    )
    person_price = relationship(
        "PersonPricesModel",
        back_populates="fk_person_prices_person_id",
        lazy="joined",
        uselist=False,
        passive_deletes=False,
        cascade="save-update, merge",
    )
