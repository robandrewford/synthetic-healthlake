import os
from unittest.mock import MagicMock, patch

import pytest

from health_platform.utils.db import SnowflakeConnection, execute_query


class TestSnowflakeConnection:
    @patch.dict(
        os.environ,
        {
            "DB_USER": "user",
            "DB_PASSWORD": "pw",
            "DB_ACCOUNT": "acc",
            "DB_WAREHOUSE": "wh",
            "DB_DATABASE": "db",
            "DB_SCHEMA": "public",
        },
    )
    @patch("snowflake.connector.connect")
    def test_get_connection(self, mock_connect):
        conn = SnowflakeConnection()
        conn.get_connection()
        mock_connect.assert_called_with(
            user="user",
            password="pw",
            account="acc",
            warehouse="wh",
            database="db",
            schema="public",
        )

    @patch.dict(os.environ, {})
    def test_missing_env_vars(self):
        with pytest.raises(ValueError):
            SnowflakeConnection()


class TestExecuteQuery:
    @patch.dict(os.environ, {"DB_USER": "u", "DB_PASSWORD": "p", "DB_ACCOUNT": "a"})
    @patch("snowflake.connector.connect")
    def test_execute_query_success(self, mock_connect):
        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [{"col": "val"}]

        # Execute
        result = execute_query("SELECT * FROM table")

        # Verify
        mock_cursor.execute.assert_called_with("SELECT * FROM table", None)
        assert result == [{"col": "val"}]
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
