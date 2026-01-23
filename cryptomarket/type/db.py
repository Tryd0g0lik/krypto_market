"""
cryptomarket/type/db.py
"""
from dataclasses import dataclass
from typing import Protocol
from pydantic import ConfigDict
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped

from cryptomarket.type.settings_prop import SettingsProps


class Database(Protocol):

    def init_engine(self) -> None:
        """
        Here we define the engine. It could be how async or sync.
        """
        self.db_url: str | None = None
        self.engine = None

    async def __create_all_async(self) -> None:
        """
        Here is to the getting the ASYNC connection on database and creating all tables.
        """
        pass

    def __create_all(self) -> None:
        """
        Here we create all tables. Engine need only SYNC.
        """
        pass

    async def create_table(self) -> None:
        """
        Check exists the engine and if the engine is not exists wil be run '.init_engine()'.
        Further, creates the tables (from models).
        """
        pass

    def _is_check_async_url(self, db_url: str) -> bool:
        """Checking by URL What we have - sync or async engine"""
        pass

    async def is_table_exists_async(self, engine, table_nane: str = "session") -> bool:
        """This is to check the existence of table."""
        pass

    async def is_postgres_exists_async(
        self, engine, db_nane: str = None, settings: SettingsProps | None = None
    ) -> bool:
        """
        ASYNC method. His task is to check the existence of database.
        """
        pass

    async def drop_tables(self) -> None:
        """ "Drop tables from database"""
        pass

    @property
    def is_sqlitetype(self) -> bool:
        """This method determine a type of the connected database.\
            It is 'sqlite' (True) or False """
        pass


@dataclass
class BaseSession:
    session_id: int = None
    created_at: Mapped[DateTime] = None
    expires_at: Mapped[DateTime] = None
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
