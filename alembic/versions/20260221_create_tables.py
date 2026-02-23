"""create person, price_tickers and person_prices tables

Revision ID: create_tables_20260221
Revises:
Create Date: 2026-02-21

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260221_create_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===== 1. SOZDAEM SKHEMU DLIA POSTGRES =====
    op.execute("CREATE SCHEMA IF NOT EXISTS crypto")

    # ===== 2. TABLITCY BEZ VNESHNIKH CLIUCHEI` =====

    # PersonModel - таблица person
    op.create_table(
        "person",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("index_app", sa.String(length=50), nullable=False),
        sa.Column(
            "person_role", sa.String(length=25), nullable=False, server_default="person"
        ),
        sa.Column("email", sa.String(length=50), nullable=False),
        sa.Column("system_name", sa.String(length=50), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("is_password", sa.Boolean(), nullable=False),
        sa.Column("client_id", sa.String(length=50), nullable=False),
        sa.Column("client_secret", sa.String(length=150), nullable=False),
        sa.Column("is_access", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("date_registered", sa.DateTime(), nullable=True),
        sa.Column("date_updated", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="user_email_unique"),
        schema="crypto",
    )

    # Indeksy` dlia person
    op.create_index("ix_user_email", "person", ["email"], unique=True, schema="crypto")
    op.create_index(
        "ix_index_app", "person", ["index_app"], unique=True, schema="crypto"
    )

    # PriceTicker - таблица price_tickers
    op.create_table(
        "price_tickers",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("instrument_name", sa.String(length=15), nullable=False),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("timestamp", sa.Integer(), nullable=False),
        sa.Column("stats_value", sa.Float(), nullable=False),
        sa.Column("stats_low", sa.Float(), nullable=False),
        sa.Column("stats_high", sa.Float(), nullable=False),
        sa.Column("price_change", sa.Float(), nullable=True),
        sa.Column("volume_usd", sa.Float(), nullable=False),
        sa.Column("settlement_price", sa.Float(), nullable=True),
        sa.Column("delivery_price", sa.Float(), nullable=True),
        sa.Column("open_interest", sa.Integer(), nullable=False),
        sa.Column("best_bid_price", sa.Float(), nullable=False),
        sa.Column("best_bid_amount", sa.Integer(), nullable=True),
        sa.Column("best_ask_price", sa.Integer(), nullable=True),
        sa.Column("best_ask_amount", sa.Integer(), nullable=True),
        sa.Column("index_price", sa.Float(), nullable=True),
        sa.Column("min_price", sa.Float(), nullable=False),
        sa.Column("max_price", sa.Float(), nullable=False),
        sa.Column("mark_price", sa.Float(), nullable=False),
        sa.Column("last_price", sa.Float(), nullable=True),
        sa.Column("date_registered", sa.DateTime(), nullable=True),
        sa.Column("date_updated", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("price >= 0", name="price_check"),
        sa.CheckConstraint("timestamp >= 0", name="timestamp_check"),
        sa.CheckConstraint("stats_value >= 0", name="stats_value_check"),
        schema="crypto",
    )

    # Индекс для price_tickers
    op.create_index(
        "ix_price_tickers_ticker", "price_tickers", ["ticker"], schema="crypto"
    )

    # ===== 3. ТАБЛИЦЫ С ВНЕШНИМИ CLЮЧАМИ =====

    # PersonPricesModel - tablitca person_prices
    op.create_table(
        "person_prices",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("currency", sa.String(length=20), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=True),
        sa.Column("price_ticker_id", sa.Integer(), nullable=True),
        sa.Column("date_registered", sa.DateTime(), nullable=True),
        sa.Column("date_updated", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["person_id"], ["crypto.person.id"], name="fk_person_prices_person_id"
        ),
        sa.ForeignKeyConstraint(
            ["price_ticker_id"],
            ["crypto.price_tickers.id"],
            name="fk_person_prices_price_ticker_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="crypto",
    )


def downgrade() -> None:

    op.drop_table("person_prices", schema="crypto")

    op.drop_index(
        "ix_price_tickers_ticker", table_name="price_tickers", schema="crypto"
    )
    op.drop_table("price_tickers", schema="crypto")

    op.drop_index("ix_user_email", table_name="person", schema="crypto")
    op.drop_index("ix_index_app", table_name="person", schema="crypto")
    op.drop_table("person", schema="crypto")

    # Удаляем схему (опционально - закомментируйте если не нужно)
    # op.execute("DROP SCHEMA IF EXISTS crypto CASCADE")
