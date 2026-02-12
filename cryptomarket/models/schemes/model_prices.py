"""
cryptomarket/models/schemes/model_prices.py:
"""

import logging

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from cryptomarket.models import BaseModel
from cryptomarket.project.settings.core import DEBUG

log = logging.getLogger(__name__)


class PriceTicker(BaseModel):
    __table_args__some = (
        UniqueConstraint(
            "instrument_name",
            name="instrument_name_unique",
        ),
        Index("ix_price_tickers_ticker", "ticker"),
    )
    if DEBUG:
        __tablename__ = "crypto_price_tickers"
        __table_args__ = __table_args__some
    else:
        __tablename__ = "crypto.price_tickers"
        __table_args__ = __table_args__some + ({"schema": "crypto"},)

    ticker: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="Ticker of currency (Example: BTC_USD). This column is indexed.",
        # index=True,
    )
    instrument_name: Mapped[str] = mapped_column(
        String(15),
        # unique=True,
        doc="""Unique instrument identifier/ Example:'BTC-PERPETUAL'. Required""",
    )

    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    timestamp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="""The timestamp (milliseconds since the Unix epoch)
    Example: 1536569522277. Required
    """,
    )
    stats_value: Mapped[float] = mapped_column(
        "stats_value",
        Float,
        nullable=False,
        doc="Volume during last 24h in base currency",
    )
    stats_low: Mapped[float] = mapped_column(
        Float, nullable=False, doc="""Lowest price during 24h. Required"""
    )
    stats_high: Mapped[float] = mapped_column(
        Float, nullable=False, doc="""Lowest price during 24h Required."""
    )
    stats_price_change: Mapped[float] = mapped_column(
        "price_change",
        Float,
        nullable=True,
        doc="""24-hour price change expressed as a percentage, null if there weren't any trades""",
    )
    stats_volume_usd: Mapped[float] = mapped_column(
        "volume_usd", Float, nullable=False, doc="""Volume in USD (futures only)"""
    )
    settlement_price: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="""Optional (not added for spot). The settlement price for the instrument. Only when state = open""",
    )
    delivery_price: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="""The settlement price for the instrument. Only when state = closed""",
    )
    open_interest: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="""
        The total amount of outstanding contracts in the corresponding amount units. For perpetual and inverse \
        futures the amount is in USD units. For options and linear futures it is the underlying base currency coin.
        Required/
        """,
    )
    best_bid_price: Mapped[Float] = mapped_column(
        Float,
        nullable=False,
        doc="""The current best bid price, null if there aren't any bids, Example: 3955.75 or null""",
    )

    best_bid_amount: Mapped[Integer] = mapped_column(
        Integer,
        nullable=True,
        doc="""It represents the requested order size of all best bids. Example: 30 or null.""",
    )
    best_ask_price: Mapped[Integer] = mapped_column(
        Integer,
        nullable=True,
        doc="""The current best ask price, null if there aren't any asks, Example: 0 or null""",
    )
    best_ask_amount: Mapped[Integer] = mapped_column(
        Integer,
        nullable=True,
        doc="""It represents the requested order size of all best asks, Example: 30 or null.""",
    )
    index_price: Mapped[Float] = mapped_column(
        Float, nullable=True, doc="""Current index price, Example: 3955.75 or null"""
    )
    min_price: Mapped[Float] = mapped_column(
        Float,
        nullable=False,
        doc="""The minimum price for the future. Any sell orders you submit lower than this price will be\
         clamped to this minimum.Example: 3955.75 or null, Required.""",
    )
    max_price: Mapped[Float] = mapped_column(
        Float,
        nullable=False,
        doc="""The maximum price for the future. Any buy orders you submit higher than this price, will be clamped \
        to this maximum..Example: 3955.75 or null, Required.""",
    )
    mark_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="""The mark price for the instrument. Example: 3955.75 or null. Required.""",
    )
    last_price: Mapped[float] = mapped_column(Float, nullable=True)

    updated_at = None
    created_at = None
