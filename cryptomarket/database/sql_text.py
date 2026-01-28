from enum import Enum


class SQLText(Enum):
    CHECK_DB = """SELECT %s FROM %s WHERE %s IS NOT NULL;"""
    CREATE_DB = """CREATE DATABASE %s;"""
    CREATE_ONETABLE = """CREATE TABLE IF NOT EXISTS %s ( %s );"""
    FIND_DB = """SELECT 1 FROM pg_database WHERE datname = :cryptomarket_db"""
    FIND_DB_TABLE = """SELECT %d FROM %s WHERE %s IS NOT NULL;"""

    @classmethod
    def sql_create_db(cls, name: str):
        """
        Create a new database table
        :param 'name': str. Database name.
            Example: "cryptomarket_db".
        :return str. SQL rule/text.
        """
        return cls.CREATE_DB.value % name

    @classmethod
    def is_sql_check_db(cls, db_name: str, table_name: str, col_name: str):
        """
        This the SQL text is for checks - we have the already exists 'db_name' or not.
        :params 'db_name': str. Database's name whose we want to check on the existence.\
            Example: "cryptomarket_db".
            'table_name': str. Table name whose existence we will check.\
            Example: "cryptomarket_account".
            'col_name': str. Column name from 'table_name' whose existence we will check.\
                Example: 'account' or 'email' or 'created_at'
        :return: str. SQL text/rule.
        """
        return cls.CHECK_DB.value % (db_name, table_name, col_name)

    @classmethod
    def sql_create_onetable(cls, db_name: str, table_name: str, col_name: list[str]):
        """
        This the SQL text is for create the one table. This table without \
            refer of type: one-to-one and more.
        :params 'db_name': str Database's name.\
            Example: "cryptomarket_db".
            'col_name': lis[str]. This is list from the columns names. \
            Example:  ['id SERIAL PRIMARY KEY', 'account VARCHAR(50) NOT NULL', 'email ...']
        :return:
        """
        columns: str = ", ".join(col_name)
        return cls.CREATE_ONETABLE.value % (table_name, columns)

