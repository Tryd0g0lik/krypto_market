"""
cryptomarket/models/schemes/model_prices.py:
"""

import logging

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from cryptomarket.models import BaseModel
from cryptomarket.project.settings.core import DEBUG

log = logging.getLogger(__name__)


class PriceTicker(BaseModel):

    if DEBUG:
        __tablename__ = "crypto_price_tickers"

    else:
        __tablename__ = "crypto.price_tickers"
        __table_args__ = ({"scheme": "crypto"},)

    ticker: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="Ticker of currency (Example: BTC_USD). This column is indexed.",
        index=True,
    )
    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    timestamp: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    updated_at = None
