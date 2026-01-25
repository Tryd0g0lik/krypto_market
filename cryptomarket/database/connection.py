"""
cryptomarket/database/connection.py
"""

import asyncio
import logging
import re
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import (
    create_engine,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    AsyncSessionTransaction,
    create_async_engine,
)
from sqlalchemy.orm import Session, SessionTransaction, sessionmaker

from cryptomarket.database.sql_text import SQLText
from cryptomarket.project.settings.core import app_settings
from cryptomarket.type.db import Database
from cryptomarket.type.settings_prop import SettingsProps

log = logging.getLogger(__name__)


class DatabaseConnection(Database):
    """
    This is the collection of methods for processing the connection to the database/db.
    Here, we have min 2 database and more four the mode connection with db:
    - the app settings have variable 'PROJECT_MODE:str' ('cryptomarket/project/settings/core.py' of four mode);
    - plus variable  'DEBUG:bool' (mode).
    - we can have the async/sync connection with db;
    - And.When we are running our app we have difference between the time of creating database and \
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
        :param db_url: str This is url/path to the database
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
        if (
            max_overflow_ is None
            or (max_overflow_ is not None and max_overflow_ < 0)
            or (pool_size_ is None)
            or (pool_size_ is not None and pool_size_ < 0)
        ):

            log_t = (
                "[%s.%s]: ERROR => The variables is invalid: 'pool_size_' & 'max_overflow_'.",
                (
                    self.__class__.__name__,
                    self.init_engine.__name__,
                ),
            )
            log.error(log_t)
            raise ValueError(log_t)

        if self.is_async:
            try:
                #
                engine = create_async_engine(
                    self.db_url,
                    echo=True,
                    pool_size=pool_size_,
                    max_overflow=max_overflow_,
                )
                self.session_factory: AsyncSessionTransaction | AsyncSession = (
                    sessionmaker(
                        bind=engine,
                        class_=AsyncSession,
                        autocommit=False,
                        autoflush=False,
                    )
                )

                self.engine = engine
            except Exception as e:
                log_t = "[%s.%s]: ERROR => %s", (
                    self.__class__.__name__,
                    self.init_engine.__name__,
                    e,
                )
                log.error(log_t)
                raise ValueError(log_t)
        else:
            engine = create_engine(
                self.db_url, echo=True, pool_size=5, max_overflow=max_overflow_
            )
            self.session_factory: Session | SessionTransaction = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
            )
            self.engine = engine

    @contextmanager
    def session_scope(self):
        """
        Sync contex manager of session
        :return:
        """
        if self.is_async:
            raise ValueError("Cannot get sync session from async engine")
        session: AsyncSession | Session = self.session_factory()
        log.info(
            "[%s.%s]: Sync session open!"
            % (
                self.__class__.__name__,
                self.session_scope.__name__,
            )
        )
        try:
            yield session
            session.commit()
        except Exception as e:
            log.error(
                "[%s.%s] ERROR => %s"
                % (
                    self.__class__.__name__,
                    self.session_scope.__name__,
                    e.args[0] if e.args else str(e),
                )
            )
            session.rollback()
            raise
        finally:
            if self.session_factory:
                self.session_factory = None
            session.close()
            self.engine = None
            log.info(
                "[%s.%s]: Sync session closed!"
                % (
                    self.__class__.__name__,
                    self.session_scope.__name__,
                )
            )

    @asynccontextmanager
    async def asyncsession_scope(self):
        """
        Async contex manager of session
        :return:
        """
        if not self.is_async:
            raise ValueError("Cannot get async session from sync engine")
        session = self.session_factory()
        log.info(
            "[%s.%s]: Sync session open!"
            % (
                self.__class__.__name__,
                self.asyncsession_scope.__name__,
            )
        )
        try:
            yield session
            await session.commit()

        except Exception as e:
            log.error(
                "[%s.%s] ERROR => %s"
                % (
                    self.__class__.__name__,
                    self.asyncsession_scope.__name__,
                    e.args[0] if e.args else str(e),
                )
            )
            await session.rollback()
            raise
        finally:
            if self.session_factory:
                self.session_factory = None

            await session.close()
            self.engine = None
            log.info(
                "[%s.%s]: Sync session closed!"
                % (
                    self.__class__.__name__,
                    self.asyncsession_scope.__name__,
                )
            )

    @property
    def __db_type(self) -> str:
        """
        This method determines the database type.
        Everytime,  we have to determination the database through the string 'postgresql+asyncpg: ...'\
            or 'sqlite+aiosqlite: ...' or '...+...: ...'.
        And, the 'self.db_url' must be the character '+' (plus).
        Everytime we look the character '+' for determine a database type.
        """
        db_urls = self.db_url.strip().split("+")
        return db_urls[0]

    @property
    def is_postgresqltype(self) -> bool:
        """This method determine a type of the connected database.\
         It is 'postgresql' (True) or False """
        return self.__db_type == "postgresql"

    @property
    def is_sqlitetype(self) -> bool:
        """This method determine a type of the connected database.\
            It is 'sqlite' (True) or False """
        return self.__db_type == "sqlite"

    def _is_check_async_url(self, db_url: str) -> bool:
        """Checking by URL What we have - async (it if True) or sync (False) engine"""

        return any(
            re.search(pattern, db_url)
            for pattern in [r"\+aiosqlite", r"\+asyncpg", r"\+asyncmy"]
        )

    async def __create_all_async(self) -> None:
        """
        Here we have getting the ASYNC connection on database and creating all tables.
        :return: None
        """
        from cryptomarket.models import Base

        try:
            engine: AsyncEngine = self.engine
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        except Exception as e:
            log_t = "[%s.%s]: ERROR => %s", (
                self.__class__.__name__,
                self.__create_all_async.__name__,
                e,
            )
            log.error(log_t)
            raise ValueError(log_t)

    def __create_all(self) -> None:
        """
        Here we create all tables. Engine need only SYNC.
        :return: None
        """
        from cryptomarket.models import Base

        try:
            with self.engine.begin():
                Base.metadata.create_all(bind=self.engine)
        except Exception as e:
            log_t = "[%s.%s]: ERROR => %s", (
                self.__class__.__name__,
                self.__create_all.__name__,
                e.args[0] if e.args else str(e),
            )
            log.error(log_t)
            raise ValueError(log_t)

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
        from sqlalchemy import text

        async with engine.connect() as conn:
            try:
                result = await conn.execute(
                    text(SQLText.FIND_DB_TABLE.value % (1, table_nane, col_name)),
                )
                if result and result.fetchone():
                    return True
            except ConnectionError as error:
                log_t = "[%s.%s]: ERROR => Connection is not successfully! %s" % (
                    self.__class__.__name__,
                    self.is_table_exists_async.__name__,
                    error.args[0],
                )
                log.error(log_t)
                raise ValueError(log_t)

            except Exception as error:
                log_t = "[%s.%s]: ERROR => %s" % (
                    self.__class__.__name__,
                    self.is_table_exists_async.__name__,
                    error.args[0],
                )
                log.error(log_t)
                raise ValueError(log_t)

        return False

    @property
    def is_sqlite_exists(self) -> bool:
        """
        Sync method.
        This is method. Checking sqlite database exists or not exists. It is using a local path.
        Example: '/my/pathe/name/to/file_db.sqlit3'"""
        try:
            import os

            path = self.db_url.split("///")[-1]
            return os.path.exists(path)
        except Exception as e:
            log_t = "[%s.%s]: ERROR => %s" % (
                self.__class__.__name__,
                self.is_postgres_exists_async.__name__,
                e.args[0] if e.args else str(e),
            )
            log.error(log_t)
            raise ValueError(log_t)

    async def is_postgres_exists_async(
        self, engine, db_nane: str = None, settings: SettingsProps = app_settings
    ) -> bool:
        """
        ASYNC method. His task is to check the existence of database.
        :param 'engine': async of engine.
        :param 'db_nane': str. Default is value 'session'. Default value is setting.POSTGRES_DB.
            If  db_nane not is None it means wath use value of db_nane.
        :param settings: app settings = 'app_settings' from the 'cryptomarket/project/settings/core.py'
        :return: True - this if the database 'db_nane' would found or Fasle
        """
        from sqlalchemy import text

        async with engine.connect() as conn:
            try:
                result = await conn.execute(
                    text(SQLText.FIND_DB.value), {"cryptomarket_db": "cryptomarket_db"}
                )
                if result and result.fetchone():
                    return True
            except ConnectionError as error:
                log_t = "[%s.%s]: ERROR => Connection is not successfully! %s" % (
                    self.__class__.__name__,
                    self.is_postgres_exists_async.__name__,
                    error.args[0],
                )
                log.error(log_t)
                raise ValueError(log_t)

            except Exception as error:
                log_t = "[%s.%s]: ERROR => %s" % (
                    self.__class__.__name__,
                    self.is_postgres_exists_async.__name__,
                    error.args[0],
                )
                log.error(log_t)
                raise ValueError(log_t)

        return False

    async def drop_tables(self) -> None:
        """Drop to the every database tables."""
        from cryptomarket.models import Base

        if not self.engine:
            self.init_engine()
        if self.is_async:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        else:
            Base.metadata.drop_all(bind=self.engine)

    async def create_table(self) -> None:
        """
        This method Check exists the engine and if the engine is not exists wil be run '.init_engine()'.
        Further, creates the tables (from models).
        DOTO: Создать чистый SQL для запуска таблиц.
        :return:None
        """
        try:
            if not self.session_factory:
                self.init_engine()

            if self.is_async:
                # for async engine
                try:
                    return await asyncio.create_task(self.__create_all_async())
                except Exception as e:
                    log_t = "[%s.%s]: ERROR => %s", (
                        self.__class__.__name__,
                        "create_table",
                        e.args[0] if e.args else str(e),
                    )
                    log.error(log_t)
                    raise ValueError(log_t)
            else:
                # For sync engine
                self.__create_all()

        except Exception as e:
            log_t = (
                "[%s.%s]: The databases tables were  created not successful! ERROR => %s",
                (
                    self.__class__.__name__,
                    "create_table",
                    e.args[0] if e.args else str(e),
                ),
            )
            log.error(log_t)
            raise ValueError(log_t)
