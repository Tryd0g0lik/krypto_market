"""
cryptomarket/models/model_base.py
"""

from datetime import datetime

from sqlalchemy.orm import (Mapped, mapped_column)

from cryptomarket.models import Base


class BaseModel(Base):
    """Base class is abstract the model"""

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        name="id",
        primary_key=True,
        autoincrement=True,
        comment="Account index",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        name="date_registered",
        comment="Date and time of registration, it is by server",
        info={
            "help_text": "Date and time of registration, it is by server",
        },
        default=lambda: datetime.now(),
        index=True,
        # server_default=lambda: datetime.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        name="date_updated",
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
        comment="Date and time last updated",
        info={
            "help_text": "Date and time last updated",
        },
        index=True,
    )


target_metadata = Base.metadata
