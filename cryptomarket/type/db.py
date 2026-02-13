"""
cryptomarket/type/db.py
"""

from contextlib import asynccontextmanager, contextmanager
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
        Here is to the getting the ASYNC connection on connection_database and creating all tables.
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
        ASYNC method. His task is to check the existence of connection_database.
        """
        pass

    async def drop_tables(self) -> None:
        """ "Drop tables from connection_database"""
        pass

    @property
    def is_sqlitetype(self) -> bool:
        """This method determine a type of the connected connection_database.\
            It is 'sqlite' (True) or False """
        pass


@dataclass
class BaseSession:
    session_id: int = None
    created_at: Mapped[DateTime] = None
    expires_at: Mapped[DateTime] = None
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)


class DatabaseConnection(Database):
    """
    This is the collection of methods for processing the connection to the connection_database/db.
    Here, we have min 2 connection_database and more four the mode connection with db:
    - the app settings have variable 'PROJECT_MODE:str' ('cryptomarket/project/settings/core.py' of four mode);
    - plus variable  'DEBUG:bool' (mode).
    - we can have the async/sync connection with db;
    - And.When we are running our app we have difference between the time of creating connection_database and \
        time when our app reads models of db's tables. So, this collection of methods make a time buffer - it is \
        responsible checking  and restarting (if needed).
    This is the methods collection check:
     - async/sync or type of connection to the db;
     - type of db. this is sqlit or postgres;
     - creating db and self determinate the view of connection. that is 'sqlite+aiosqlite' or 'postgresql+asyncpg';
     - already exists a db.
     - and more.


    """

    def __init__(self, db_url: str = None):
        """
        :param db_url: str This is url/path to the connection_database
        :param is_async: bool
        engine = None
        session_factory = None
        :param db_url:
        Example:
        # ````text
        # db = DatabaseConnection(settings.DATABASE_URL_SQLITE)
        #
        # async def test_records():
        #     db() # Here we define the engine.
        #     session = Session(db.engine)
        #     async with db.session_factory() as session:
        #         session_user_ = SessionUserModel( session_id="dsasda")
        #         session.add(session_user_)
        #         await session.commit()
        # ```
        """
        self.db_url: str = db_url
        self.is_async = self._is_check_async_url(db_url)
        self.engine = None
        self.session_factory = None

    def init_engine(self, pool_size_: int = 5, max_overflow_: int = 10) -> None:
        """
         Connection to the database
        Here we define the engine. It could be how async or sync.
        Type of engine be depend from url to the db file.
        '.table_exists_create()' - create the tables from models.
        :param pool_size_: int Default value is 5.
            https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.create_engine.params.pool_size
            This is the number of connections to keep open inside the connection pool.

        :param max_overflow_: int Default value is 10.
             https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.create_engine.params.max_overflow
             the number of connections to allow in connection pool “overflow”, that is connections that can be opened \
             above and beyond the pool_size setting, which defaults to five. this is only used with QueuePool.
        Example: ```python
            db = DatabaseConnection(settings.DATABASE_URL_SQLITE)
            db.init_engine() # Here we definning and gets the engine.
            # further
            db.engine # <sqlalchemy.ext.asyncio.engine.AsyncEngine object at 0x0000028691D50690>
        ````
        :return:
        """
        pass

    @contextmanager
    def session_scope(self):
        """
        Sync contex manager of session
        :return:
        """
        pass

    @asynccontextmanager
    async def asyncsession_scope(self):
        """
        Async contex manager of session
        :return:
        """
        pass

    @property
    def __db_type(self) -> str:
        """
        This method determines the connection_database type.
        Everytime,  we have to determination the connection_database through the string 'postgresql+asyncpg: ...'\
            or 'sqlite+aiosqlite: ...' or '...+...: ...'.
        And, the 'self.db_url' must be the character '+' (plus).
        Everytime we look the character '+' for determine a connection_database type.
        """
        pass

    @property
    def is_postgresqltype(self) -> bool:
        """This method determine a type of the connected connection_database.\
         It is 'postgresql' (True) or False """
        pass

    @property
    def is_sqlitetype(self) -> bool:
        """This method determine a type of the connected connection_database.\
            It is 'sqlite' (True) or False """
        pass

    def _is_check_async_url(self, db_url: str) -> bool:
        """Checking by URL What we have - async (it if True) or sync (False) engine"""

        pass

    async def __create_all_async(self) -> None:
        """
        Here we have getting the ASYNC connection on connection_database and creating all tables.
        :return: None
        """
        pass

    def __create_all(self) -> None:
        """
        Here we create all tables. Engine need only SYNC.
        :return: None
        """
        pass

    async def is_table_exists_async(
        self, engine, table_nane: str = "session", col_name: str = "id"
    ) -> bool:
        """
        ASYNC method. His task is to check the existence of table.
        RUn only if engine is async.
        :param engine: async of engine.
        :param table_nane: str. Default is value 'session'.

        Example:\
        '''
        # Get engine\
        db.init_engine()\
        # Check the table 'session'.\
        result = await db.is_table_exists_async(db.engine)\
        # If false, means what we will be creating the tables from models.\
        if not result:\
            await db.table_exists_create()\
        '''
        :return: True or Fasle
        """
        pass

    @property
    def is_sqlite_exists(self) -> bool:
        """
        Sync method.
        This is method. Checking sqlite connection_database exists or not exists. It is using a local path.
        Example: '/my/pathe/name/to/file_db.sqlit3'"""
        pass

    async def is_postgres_exists_async(self, engine, db_nane: str = None) -> bool:
        """
        ASYNC method. His task is to check the existence of connection_database.
        :param 'engine': async of engine.
        :param 'db_nane': str. Default is value 'session'. Default value is setting.POSTGRES_DB.
            If  db_nane not is None it means wath use value of db_nane.
        :param settings: app settings = 'app_settings' from the 'cryptomarket/project/settings/core.py'
        :return: True - this if the connection_database 'db_nane' would found or Fasle
        """
        pass

    async def drop_tables(self) -> None:
        """Drop to the every connection_database tables."""
        pass

    async def create_table(self) -> None:
        """
        This method Check exists the engine and if the engine is not exists wil be run '.init_engine()'.
        Further, creates the tables (from models).
        DOTO: Создать чистый SQL для запуска таблиц.
        :return:None
        """
        pass
