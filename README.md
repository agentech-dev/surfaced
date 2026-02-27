# Surfaced

Open-source AI visibility tracking - monitor how brands appear in AI-generated responses.

## What it does

Surfaced tracks whether and how brands are mentioned when users ask AI assistants questions. It runs prompts against AI providers on a schedule, captures results in ClickHouse, and provides analytics on brand visibility over time.

## Setup

```bash
# Install dependencies
uv sync

# Start ClickHouse and initialize schema
chv run server
surfaced init

# Add your brand and provider, then start tracking
surfaced brands add --name "YourBrand" --aliases "YB,Your Brand" --competitors "Comp1,Comp2"
surfaced providers add --name "Claude" --type anthropic_api --mode api --model claude-sonnet-4-20250514
surfaced prompts add --text "What are the best tools for X?" --category brand_query --brand <id>
surfaced run --brand "YourBrand"
surfaced analytics summary --brand "YourBrand"
```

See [CLAUDE.md](CLAUDE.md) for complete documentation.
