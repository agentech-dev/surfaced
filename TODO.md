# Next Steps

Running list of in-flight ideas. Order is rough, not strict priority.

## 1. [done] Use native installers or Bun for Agent CLIs

Claude Code can now be installed with a native installer: curl -fsSL https://claude.ai/install.sh | bash

Gemini and Codex still need to be installed using e.g. npm, but both should with Bun.

So install Bun and use Bun to install them. Do not have any fallback for nodejs. Clear up the code so its native where possible or Bun.

Implemented in `surfaced bootstrap`: Claude uses the native installer; Bun installs Codex and Gemini; Node/npm/pnpm fallbacks are removed.

## 2. [done] Rework prompt categories; add a `branded` field

**Problem:** `category` is currently a hardcoded enum (`brand_query`, `competitor_comparison`, `industry_query`, `feature_query`, `problem_solving`) in `cli/prompts.py:11`. That captures prompt *type*, not a useful analytics dimension.

**Intent:** categories should be *user-defined* groupings by use case, so a user can answer "how am I performing on the X use case?". For ClickHouse that might be `data_warehouse`, `observability`, `realtime_analytics`. The user defines them; the system just stores and groups by them.

**Also add `branded` (boolean):** does the prompt text itself contain the brand name (or alias)? "What's the best tool for X?" → unbranded. "How does ClickHouse compare to Snowflake for X?" → branded. Splits discovery performance from consideration performance.

Implemented: prompt categories are free-form use-case groupings, prompts track a `branded` boolean, and analytics can split by category plus branded/unbranded prompts. The starter prompt set is also trimmed for easier testing.

## 3. [done] Use markdown tables in CLI output for tabular

Some commands have tabular style output. e.g. prompts list. We should use markdown style tabular output for this. We should look through all CLI commands and use where appropriate for the output.

Implemented: shared CLI markdown table formatting is used for list-style output in brands, prompts, providers, runs, and analytics table output.

## 4. Recommendation metric — was the mention positive?

**Problem:** current analytics show whether a brand is *mentioned*, not whether the AI is *recommending* it. "I'd avoid ClickHouse for X" mentions the brand the same as "I recommend ClickHouse for X".

**Action:**
- Per answer, classify the brand reference as `recommended` / `neutral` / `negative` / `not_mentioned`. Likely an LLM judge over answer text + brand name + aliases.
- Plug into `engine/analyzer.py` alongside the existing mention detection.
- New analytics query: `recommendation_rate`. Add to `summary` output.

**Open questions:**
- Which judge model? Haiku is probably the right cost/quality point.
- Multi-brand answers (own brand + competitors): score each separately.
- Need a small labelled set to validate the judge before trusting outputs.

**Files:** `src/surfaced/engine/analyzer.py`, `src/surfaced/models/answer.py`, `clickhouse/tables/answers.sql` (new column), `clickhouse/queries/`.

## 5. Alignment metric — does the response reflect the canonical position?

**Problem:** LLMs cite stale training data. ClickHouse JOINs used to be weak; the product has improved a lot, but training data still says "ClickHouse is bad at JOINs". The user needs to detect when AI responses are misaligned with the *current* canonical truth so they can prioritise content/SEO to correct it.

**Action:**
- Introduce *canonical positions* — user-supplied statements about specific topics ("ClickHouse JOINs support X, Y, Z; performance is competitive with…"). One brand, many positions.
- Mark certain prompts as alignment-checks linked to a specific canonical position.
- For those prompts, the analyzer LLM-judges the response against the statement: `aligned` / `partial` / `misaligned` / `silent`, with a short rationale.
- New analytics query: alignment rate over time, by provider, by position.

**Schema sketch:**
- New `canonical_positions(id, brand_id, topic, statement, created_at)` standard MergeTree
- `prompts.alignment_position_id Nullable(UUID)` linking prompt → canonical position
- `answers.alignment_score Enum8('aligned','partial','misaligned','silent')` + `alignment_rationale String`

**Files:** `clickhouse/tables/canonical_positions.sql` (new), `clickhouse/tables/prompts.sql`, `clickhouse/tables/answers.sql`, `src/surfaced/models/`, `src/surfaced/engine/analyzer.py`, new `src/surfaced/cli/positions.py` for CRUD.
