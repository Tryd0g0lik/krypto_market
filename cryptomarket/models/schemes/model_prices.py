"""
cryptomarket/models/schemes/model_prices.py:
"""
import logging

from sqlalchemy import (Boolean, ForeignKey, Integer, Index, String, Float)
from sqlalchemy.orm import (Mapped, mapped_column, relationship, validates)
from cryptomarket.models import BaseModel
from cryptomarket.project.settings.core import DEBUG

log = logging.getLogger(__name__)

class PriceTicker(BaseModel):
    __table_args__some = (
        Index("ticker", "tickers", unique=True),
        Index("timestamp", "time_stamp", unique=True),
    )

    if DEBUG:
        __tablename__ = 'crypto_price_tickers'
        __table_args__ = __table_args__some
    else:
        __tablename__ = 'crypto.price_tickers'
        __table_args__= __table_args__some + ({"scheme": "crypto"},)

    ticker: Mapped[str] = mapped_column(
        String(10), nullable=False, doc="Ticker of currency (Example: BTC_USD). This column is indexed.",
    )
    price: Mapped[float] = mapped_column(
        Float, nullable=False,
    )
    timestamp: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at = None


