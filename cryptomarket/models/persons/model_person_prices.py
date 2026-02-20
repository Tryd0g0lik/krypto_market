"""
cryptomarket/models/persons/model_person_prices.py
"""

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cryptomarket.models import BaseModel
from cryptomarket.project.functions import connection_db
from cryptomarket.project.settings.core import DEBUG, settings

setting = settings()

url_str = (
    setting.get_database_url_sqlite if DEBUG else setting.get_database_url_external
)


class PersonPricesModel(BaseModel):
    if DEBUG:
        __tablename__ = "crypto_person_prices"
    else:
        __tablename__ = "person_prices"
        __table_args__ = ({"schema": "crypto"},)

    currency: Mapped[str] = mapped_column(
        String(20),
    )
    person_id = mapped_column(
        ForeignKey(
            ("crypto_person.id" if DEBUG else "person.id"),
            name="fk_person_prices_person_id",
        ),
        comment="Reference to the person database.",
    )
    price_ticker_id = mapped_column(
        ForeignKey(
            ("crypto_price_tickers.id" if DEBUG else "price_tickers.id"),
            name="fk_person_prices_price_ticker_id",
        ),
        comment="Reference to the price ticker database.",
    )
    person = relationship(
        "PersonModel",
        back_populates="person_price",
    )
    price_ticker = relationship(
        "PriceTicker",
        back_populates="person_price",
    )
