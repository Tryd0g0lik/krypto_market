"""
cryptomarket/connection_database/handler_create_db.py
"""

import asyncio
import logging
import os

from sqlalchemy.exc import InvalidRequestError

from cryptomarket.database.connection import DatabaseConnection
from cryptomarket.database.sql_text import SQLText
from cryptomarket.project.settings.core import BASE_DIR, DEBUG
from cryptomarket.project.settings.settings_env import POSTGRES_DB_, PROJECT_MODE_
from cryptomarket.type.db import Database
from cryptomarket.type.settings_prop import SettingsProps

log = logging.getLogger(__name__)


async def handler_restart_create_tables(
    db: Database, max_restart: int, restart_quantity: int, settings: SettingsProps
) -> bool:
    """
    This is child function for  the main function "checkOrCreateTables()".
    :param 'db': Database connection Example 'DatabaseConnection(settings.GET_DATABASE_URL_SQLITE)'.
    :param 'max_restart': Restart create connection_database if we have not  received from the initial.
    :param 'restart_quantity':int. Default value is 0. Variable is count  of current restart.
    :param 'settings': SettingsProps Properties Example 'Settings(settings.GET_DATABASE_URL_PS)'
    :return: True/False


    """
    await db.create_table()
    # Checking a connection_database - whose type already exists.
    is_postgresqltype = db.is_postgresqltype
    is_sqlitetype = db.is_sqlitetype
    # Check connection_database postgres
    if is_postgresqltype and restart_quantity < max_restart:
        restart_quantity += 1
        dbtable_bool = await db.is_postgres_exists_async(
            db.engine, settings.POSTGRES_DB, settings
        )
        if not dbtable_bool:
            await asyncio.sleep(2)
            await db.create_table()
            await handler_restart_create_tables(
                db, max_restart, restart_quantity, settings
            )
            return False
        return True
    elif is_sqlitetype and restart_quantity < max_restart:
        restart_quantity += 1
        dbtable_bool = db.is_sqlite_exists
        if not dbtable_bool:
            await asyncio.sleep(3)
            await db.create_table()
            await handler_restart_create_tables(
                db, max_restart, restart_quantity, settings
            )
            log_t = (
                "[%s]: RESTART number %d => the process of handling re-create the db table!"
                % (handler_restart_create_tables.__name__, restart_quantity)
            )
            log.warning(log_t)
            return False
        return True
    elif restart_quantity < max_restart:
        restart_quantity += 1
        await asyncio.sleep(3)
        try:
            with db.engine.connection:
                return True
        except Exception as e:
            await handler_restart_create_tables(
                db, max_restart, restart_quantity, settings
            )
            log_t = (
                "[%s]: ERROR => %s & RESTART number %d => the process of handling re-create the db table!"
                % (
                    handler_restart_create_tables.__name__,
                    e.args[0] if e.args else str(e),
                    restart_quantity,
                )
            )
            log.error(log_t)
            print(log_t)
            return False

    else:
        try:
            with db.engine.connection:
                return True
        except Exception as e:
            log_t = "[%s]: ERROR =>  %s" % (
                handler_restart_create_tables.__name__,
                e.args[0] if e.args else str(e),
            )
            log.error(log_t)
            return False


async def checkOrCreateTables(settings: SettingsProps, max_restart=3) -> None:
    """
    TODO: When, we have the 'except Exception as e:'  - we need to check the create of db to the sqlit3
        The the clean SQL insert to the under lines: 'except InvalidRequestError as e:' & 'InvalidRequestError as e'
    This is function for processing the checking or creating db tables.
    :param max_restart: Restart create connection_database if we have not  received from the initial.
    :param settings: 'cryptomarket.project.settings.core.Settings'.
        Settings Properties Example 'Settings(settings.GET_DATABASE_URL_PS)'.

    :return:
    """
    db = DatabaseConnection(settings.get_database_url_sqlite)

    try:
        # Defins the settings
        if PROJECT_MODE_ == "testing":
            # TESTING
            settings.POSTGRES_DB = "test_%s" % POSTGRES_DB_
            if not DEBUG and db.is_postgresqltype:
                settings.ALLOWED_ORIGINS = settings.get_allowed_hosts(
                    "http://127.0.0.1:8000, http://localhost:8000"
                )
                db = DatabaseConnection(settings.get_database_url_external)
        elif DEBUG and db.is_sqlitetype:
            settings.ALLOWED_ORIGINS = settings.get_allowed_hosts(
                "http://127.0.0.1:8000, http://localhost:8000"
            )
        else:
            # SOME
            settings.ALLOWED_ORIGINS = settings.get_allowed_hosts(
                "http://127.0.0.1:8000, http://localhost:8000"
            )
        restart_calculator = 0
        await handler_restart_create_tables(
            db, max_restart, restart_calculator, settings
        )
    except InvalidRequestError as e:
        log_t = "[%s]: ERROR => Connection is not successfully! %s" % (
            checkOrCreateTables.__name__,
            e.args[0] if e.args else str(e),
        )
        log.error(log_t)
        print(log_t)
        # insert the SQL
    except Exception as e:
        log_t = "[%s]: ERROR => Connection is not successfully! %s" % (
            checkOrCreateTables.__name__,
            e.args[0] if e.args else str(e),
        )
        log.error(log_t)
        from sqlalchemy import create_engine, text

        # sqlite_path = os.path.join(BASE_DIR, f"{settings.POSTGRES_DB}.sqlite3")
        # settings.set_database_url_sqlite(
        #     sqlite_path
        # )

        try:
            # НЕ РАБЬОЧЕЕю Вставить текст SQL и создать модель базы данных
            db = DatabaseConnection(settings.get_database_url_sqlite)
            db.init_engine()
            engine: create_engine = db.engine
            with engine.begin() as conn:
                sqltexts = SQLText
                sqlt = text(
                    sqltexts.is_sql_check_db(
                        settings.POSTGRES_DB, "cryptomarket_account", "created_at"
                    )
                )
                # The connection_database whose we want to check on the already exists.
                if conn.execute(sqlt).fetchone():
                    # If all successful and db exists.
                    return
                else:
                    # Create db
                    sqlt = text(sqltexts.sql_create_db(settings.POSTGRES_DB))
                    conn.execute(sqlt)
        except Exception as e:
            log_t = "[%s]: ERROR => Connection is not successfully! %s" % (
                checkOrCreateTables.__name__,
                e.args[0] if e.args else str(e),
            )
            log.error(log_t)
            print(log_t)
