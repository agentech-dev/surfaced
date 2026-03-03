# Surfaced

Open-source AI visibility tracking — monitor how brands appear in AI-generated responses.

## What it does

Surfaced tracks whether and how brands are mentioned when users ask AI assistants questions. It runs prompts against multiple AI providers on a schedule, stores results in ClickHouse, and provides analytics on brand visibility over time.

## Install

```bash
curl -sSL https://raw.githubusercontent.com/sdairs/surfaced/main/scripts/install.sh | sh
```

This installs `surfaced` as a globally available command. You never need to think about uv, venvs, or directories.

## Get Started

```bash
# 1. Set up infrastructure (ClickHouse, schema, CLI tools, cron)
surfaced bootstrap

# 2. Interactive wizard — API keys, brand, providers, prompts
surfaced setup

# 3. Run your first campaign
surfaced run --brand "YourBrand"

# 4. View results
surfaced analytics summary --brand "YourBrand" --days 30
```

## Commands

| Command | Description |
|---|---|
| `surfaced bootstrap` | Install and start all infrastructure |
| `surfaced setup` | Interactive configuration wizard |
| `surfaced init` | Initialize ClickHouse schema |
| `surfaced brands {add,list,show,edit,delete}` | Manage brands |
| `surfaced prompts {add,list,show,edit,delete,import}` | Manage prompts |
| `surfaced providers {add,list,show,delete}` | Manage AI providers |
| `surfaced run [--category X] [--provider Y] [--tag Z] [--brand B] [--dry-run]` | Execute campaign |
| `surfaced campaigns {list,show}` | View campaign history |
| `surfaced analytics <query> --brand <name> [--days 30] [--format table\|json\|csv]` | Run analytics |
| `surfaced purge` | Delete CLI provider history and memory stores |

All commands support `--format json` for machine-readable output.

## Providers

Surfaced supports 6 provider types across API and CLI modes:

| Type | Mode | Description |
|---|---|---|
| `anthropic_api` | api | Anthropic SDK — requires `ANTHROPIC_API_KEY` |
| `openai_api` | api | OpenAI SDK — requires `OPENAI_API_KEY` |
| `gemini_api` | api | Google Gemini SDK — requires `GEMINI_API_KEY` |
| `claude_cli` | cli | Claude Code CLI subprocess |
| `codex_cli` | cli | OpenAI Codex CLI subprocess |
| `gemini_cli` | cli | Google Gemini CLI subprocess |

`surfaced setup` auto-detects your API keys and installed CLI tools and creates providers for you.

## Analytics

Built-in queries available via `surfaced analytics <query>`:

- **summary** — overall dashboard metrics
- **mention_frequency** — mention rate over time by day
- **share_of_voice** — brand vs competitor mention share by category
- **provider_comparison** — visibility comparison across AI providers
- **consistency** — response stability for specific prompts

```bash
surfaced analytics mention_frequency --brand "YourBrand" --days 7
surfaced analytics provider_comparison --brand "YourBrand" --days 30
surfaced analytics share_of_voice --brand "YourBrand" --days 30
```

## Scheduling

`surfaced bootstrap` sets up cron entries automatically. To manage manually, tag prompts with `daily`, `weekly`, or `monthly` and use:

```
0 6 * * *   cd ~/.surfaced && ./scripts/run-campaign.sh daily
0 6 * * 1   cd ~/.surfaced && ./scripts/run-campaign.sh weekly
0 6 1 * *   cd ~/.surfaced && ./scripts/run-campaign.sh monthly
```

## Environment Variables

- `ANTHROPIC_API_KEY` — Anthropic API provider
- `OPENAI_API_KEY` — OpenAI API provider
- `GEMINI_API_KEY` — Google Gemini API provider
- `CLICKHOUSE_HOST` — ClickHouse host (default: `localhost`)
- `CLICKHOUSE_PORT` — ClickHouse HTTP port (default: `8123`)

## Development

```bash
git clone https://github.com/sdairs/surfaced.git
cd surfaced
uv sync
uv run pytest tests/ -v
```

## Project Structure

```
src/surfaced/
  cli/         Click CLI commands (init, bootstrap, setup, brands, ...)
  models/      Data models (dataclasses)
  db/          ClickHouse client and query service
  providers/   AI provider implementations (API + CLI)
  engine/      Execution engine, analyzer, rate limiter
clickhouse/
  tables/      Schema SQL files
  queries/     Analytics SQL queries
  seed/        Sample data
scripts/
  install.sh   Curl installer
  run-campaign.sh  Cron-friendly campaign runner
```

## License

MIT
