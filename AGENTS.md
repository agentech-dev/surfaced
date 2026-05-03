Use uv for all Python commands.

Run tests with `uv run pytest tests/ -v`.

For ClickHouse:
- Use clickhousectl to interact with ClickHouse for development
- Only use ReplacingMergeTree when necessary: SQL standard UPDATEs are viable

## Project Structure

- `src/surfaced/cli/` - Click CLI commands
- `src/surfaced/models/` - Data models (dataclasses)
- `src/surfaced/db/` - ClickHouse client and query service
- `src/surfaced/providers/` - AI provider implementations
- `src/surfaced/engine/` - Execution engine, analyzer, rate limiter
- `clickhouse/tables/` - Schema SQL files
- `clickhouse/queries/` - Analytics SQL queries
- `clickhouse/seed/` - Sample data
