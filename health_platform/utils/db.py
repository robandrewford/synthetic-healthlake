import os
from typing import Any

import snowflake.connector


class SnowflakeConnection:
    """Wrapper for Snowflake Connection."""

    def __init__(self):
        self.user = os.environ.get("DB_USER")
        self.password = os.environ.get("DB_PASSWORD")
        self.account = os.environ.get("DB_ACCOUNT")
        self.warehouse = os.environ.get("DB_WAREHOUSE")
        self.database = os.environ.get("DB_DATABASE")
        self.schema = os.environ.get("DB_SCHEMA")

        if not all([self.user, self.password, self.account]):
            raise ValueError("Missing required DB environment variables")

    def get_connection(self):
        return snowflake.connector.connect(
            user=self.user,
            password=self.password,
            account=self.account,
            warehouse=self.warehouse,
            database=self.database,
            schema=self.schema,
        )


def execute_query(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    """
    Execute a query and return results as list of dicts.
    """
    conn = SnowflakeConnection().get_connection()
    try:
        cursor = conn.cursor(snowflake.connector.DictCursor)
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()
    finally:
        conn.close()
