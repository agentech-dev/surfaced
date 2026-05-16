"""ClickHouse database client."""

from __future__ import annotations

import os

import clickhouse_connect


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class DBClient:
    """Wrapper around clickhouse-connect for app database operations.

    Reads connection settings from environment variables when not passed
    explicitly:

      CLICKHOUSE_HOST      (default: localhost)
      CLICKHOUSE_PORT      (default: 8443 if secure else 8123)
      CLICKHOUSE_USER      (default: default)
      CLICKHOUSE_PASSWORD  (default: empty)
      CLICKHOUSE_DATABASE  (default: default)
      CLICKHOUSE_SECURE    (default: false; set true for ClickHouse Cloud)
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        database: str | None = None,
        secure: bool | None = None,
    ):
        self.host = host or os.environ.get("CLICKHOUSE_HOST", "localhost")
        self.username = username or os.environ.get("CLICKHOUSE_USER", "default")
        self.password = password if password is not None else os.environ.get("CLICKHOUSE_PASSWORD", "")
        self.database = database or os.environ.get("CLICKHOUSE_DATABASE", "default")
        self.secure = secure if secure is not None else _env_bool("CLICKHOUSE_SECURE", False)
        default_port = 8443 if self.secure else 8123
        self.port = port or int(os.environ.get("CLICKHOUSE_PORT", str(default_port)))
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                database=self.database,
                secure=self.secure,
            )
        return self._client

    def execute(self, query: str, parameters: dict | None = None) -> list[dict]:
        """Execute a query and return results as list of dicts."""
        result = self.client.query(query, parameters=parameters)
        columns = result.column_names
        return [dict(zip(columns, row)) for row in result.result_rows]

    def execute_no_result(self, query: str, parameters: dict | None = None) -> None:
        """Execute a query that returns no results (INSERT, CREATE, etc.)."""
        self.client.command(query, parameters=parameters)

    def insert_rows(
        self, table: str, data: list[list], column_names: list[str]
    ) -> None:
        """Bulk insert rows via native protocol."""
        self.client.insert(table, data, column_names=column_names)
