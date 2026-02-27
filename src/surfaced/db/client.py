"""ClickHouse database client."""

from __future__ import annotations

import os

import clickhouse_connect


class DBClient:
    """Wrapper around clickhouse-connect for app database operations."""

    def __init__(self, host: str | None = None, port: int | None = None):
        self.host = host or os.environ.get("CLICKHOUSE_HOST", "localhost")
        self.port = port or int(os.environ.get("CLICKHOUSE_PORT", "8123"))
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = clickhouse_connect.get_client(
                host=self.host, port=self.port
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
