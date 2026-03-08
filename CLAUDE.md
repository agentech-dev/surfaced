# Surfaced - AI Visibility Tracking

## Quick Start

```bash
# 1. Start ClickHouse
chv run server

# 2. Initialize schema
surfaced init

# 3. (Optional) Load sample data
chv run client -- --queries-file clickhouse/seed/sample_data.sql

# 4. Add a brand
surfaced brands add --name "YourBrand" --domain yourbrand.com \
  --aliases "YB,Your Brand" --competitors "Competitor1,Competitor2"

# 5. Add a provider
surfaced providers add --name "Claude Sonnet" --type anthropic_api --mode api \
  --model claude-sonnet-4-6

# 6. Add prompts
surfaced prompts add --text "What are the best tools for X?" \
  --category brand_query --brand <brand-id> --tags daily

# 7. Run prompts
surfaced run --brand "YourBrand"

# 8. View results
surfaced analytics summary --brand "YourBrand" --days 30
```

## Commands

| Command | Description |
|---|---|
| `surfaced init` | Initialize ClickHouse schema |
| `surfaced brands {add,list,show,edit,delete}` | Manage brands |
| `surfaced prompts {add,list,show,edit,delete,import}` | Manage prompts |
| `surfaced providers {add,list,show,delete}` | Manage AI providers |
| `surfaced run [--category X] [--provider Y] [--tag Z] [--brand B] [--dry-run]` | Execute prompts against providers |
| `surfaced runs {list,show}` | View run history |
| `surfaced analytics <query> --brand <id-or-name> [--days 30] [--format table\|json\|csv]` | Run analytics |

All commands support `--format json` for machine-readable output.

## Database Schema

**ReplacingMergeTree tables** (mutable, query with FINAL):
- `brands` - Brand definitions with aliases and competitors
- `providers` - AI provider configs (api/cli mode, model, rate limits)
- `prompts` - Prompt library with categories and tags
- `runs` - Execution run records

**MergeTree table** (append-only):
- `prompt_runs` - Individual execution results with denormalized fields

**Materialized view**:
- `brand_mention_daily` - Daily aggregates of mention rates

## Analytics Queries

Available in `clickhouse/queries/`:
- `summary` - Overall dashboard metrics
- `mention_frequency` - Mention rate over time by day
- `share_of_voice` - Brand vs competitor mention share by category
- `provider_comparison` - Visibility comparison across AI providers
- `consistency` - Response stability for specific prompts

## Provider Types

| Type | Mode | Description |
|---|---|---|
| `anthropic_api` | api | Anthropic SDK, requires ANTHROPIC_API_KEY |
| `claude_cli` | cli | Claude Code CLI subprocess |

## Prompt Categories

`brand_query`, `competitor_comparison`, `industry_query`, `feature_query`, `problem_solving`

## Scheduling

Tag prompts with frequency tags (`daily`, `weekly`, `monthly`), then use cron:

```
0 6 * * *   cd /path/to/surfaced && ./scripts/surfaced-runner.sh daily
0 6 * * 1   cd /path/to/surfaced && ./scripts/surfaced-runner.sh weekly
0 6 1 * *   cd /path/to/surfaced && ./scripts/surfaced-runner.sh monthly
```

## Common Workflows

**Check if brand is being mentioned by AI:**
```bash
surfaced analytics mention_frequency --brand "YourBrand" --days 7
```

**Compare visibility across providers:**
```bash
surfaced analytics provider_comparison --brand "YourBrand" --days 30
```

**Bulk import prompts:**
```bash
surfaced prompts import prompts.json
```
JSON format: `[{"text": "...", "category": "brand_query", "brand_id": "...", "tags": ["daily"]}]`

## Environment Variables

- `CLICKHOUSE_HOST` - ClickHouse host (default: localhost)
- `CLICKHOUSE_PORT` - ClickHouse HTTP port (default: 8123)
- `ANTHROPIC_API_KEY` - Required for anthropic_api provider

## Development

```bash
uv run pytest tests/ -v                    # Unit tests
uv run pytest tests/ -v -m integration     # Integration tests (needs ClickHouse)
```

## Project Structure

- `src/surfaced/cli/` - Click CLI commands
- `src/surfaced/models/` - Data models (dataclasses)
- `src/surfaced/db/` - ClickHouse client and query service
- `src/surfaced/providers/` - AI provider implementations
- `src/surfaced/engine/` - Execution engine, analyzer, rate limiter
- `clickhouse/tables/` - Schema SQL files
- `clickhouse/queries/` - Analytics SQL queries
- `clickhouse/seed/` - Sample data
