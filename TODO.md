# Next Steps

Running list of in-flight ideas. Order is rough, not strict priority.

## 1. Switch CLI-tool bootstrap from Node to Bun

Today `surfaced bootstrap` installs Node.js (brew/apt/dnf) when no JS runtime is present, then npm-installs three CLI providers: `@anthropic-ai/claude-code`, `@openai/codex`, `@google/gemini-cli`. The runtime preference order in `bootstrap.py:144` is already `bun` > `pnpm` > `npm`; only the fallback installs Node.

**Research (2026-04-30):**

- `claude-code` — ships per-platform native binaries via `optionalDependencies` since v2.1.115. Install runtime is just a downloader; Bun/npm/Deno all produce a working `claude`.
- `codex` — Node shim that downloads a Rust binary. Works on Bun and Deno; no compat issues filed.
- `gemini-cli` — pure JS. Works on Bun for our use (non-interactive prompt → stdout), but has open child-process / PTY bugs around shell tools and MCP. **Broken on Deno** (`Dirent.isCharacterDevice` unimplemented).

**Action:** in the no-runtime branch (`bootstrap.py:152`), install Bun (`curl -fsSL https://bun.sh/install | bash`) instead of Node. Keep Node/npm path as fallback if Bun install fails. Do not auto-select Deno.

**Refs:**
- gemini-cli Bun PTY bug: https://github.com/google-gemini/gemini-cli/issues/18066
- gemini-cli Deno broken: https://github.com/google-gemini/gemini-cli/issues/18805
- claude-code historical Bun shebang issue (now resolved): https://github.com/anthropics/claude-code/issues/3108

## 2. Rework prompt categories; add a `branded` field

**Problem:** `category` is currently a hardcoded enum (`brand_query`, `competitor_comparison`, `industry_query`, `feature_query`, `problem_solving`) in `cli/prompts.py:11`. That captures prompt *type*, not a useful analytics dimension.

**Intent:** categories should be *user-defined* groupings by use case, so a user can answer "how am I performing on the X use case?". For ClickHouse that might be `data_warehouse`, `observability`, `realtime_analytics`. The user defines them; the system just stores and groups by them.

**Also add `branded` (boolean):** does the prompt text itself contain the brand name (or alias)? "What's the best tool for X?" → unbranded. "How does ClickHouse compare to Snowflake for X?" → branded. Splits discovery performance from consideration performance.

**Action:**
- Drop `VALID_CATEGORIES` enum; allow free-form strings.
- Add `branded BOOL` column to `prompts`. At add-time, auto-suggest the value by case-insensitive match of prompt text against the brand's name + aliases; let the user override.
- Update analytics queries to group by category and filter/group by `branded`.

**Files:** `src/surfaced/cli/prompts.py`, `src/surfaced/models/prompt.py`, `clickhouse/tables/prompts.sql`, `clickhouse/queries/`.

**Open question:** rename `category` → `use_case` to signal the new semantics, or keep the column name?

## 3. Recommendation metric — was the mention positive?

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

## 4. Alignment metric — does the response reflect the canonical position?

**Problem:** LLMs cite stale training data. ClickHouse JOINs used to be weak; the product has improved a lot, but training data still says "ClickHouse is bad at JOINs". The user needs to detect when AI responses are misaligned with the *current* canonical truth so they can prioritise content/SEO to correct it.

**Action:**
- Introduce *canonical positions* — user-supplied statements about specific topics ("ClickHouse JOINs support X, Y, Z; performance is competitive with…"). One brand, many positions.
- Mark certain prompts as alignment-checks linked to a specific canonical position.
- For those prompts, the analyzer LLM-judges the response against the statement: `aligned` / `partial` / `misaligned` / `silent`, with a short rationale.
- New analytics query: alignment rate over time, by provider, by position.

**Schema sketch:**
- New `canonical_positions(id, brand_id, topic, statement, created_at)` ReplacingMergeTree
- `prompts.alignment_position_id Nullable(UUID)` linking prompt → canonical position
- `answers.alignment_score Enum8('aligned','partial','misaligned','silent')` + `alignment_rationale String`

**Files:** `clickhouse/tables/canonical_positions.sql` (new), `clickhouse/tables/prompts.sql`, `clickhouse/tables/answers.sql`, `src/surfaced/models/`, `src/surfaced/engine/analyzer.py`, new `src/surfaced/cli/positions.py` for CRUD.
