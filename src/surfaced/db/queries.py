"""Typed query methods for all database operations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from surfaced.db.client import DBClient
from surfaced.models.brand import Brand
from surfaced.models.alignment_judgment import AlignmentJudgment
from surfaced.models.prompt import Prompt
from surfaced.models.canonical_position import CanonicalPosition
from surfaced.models.answer import Answer
from surfaced.models.provider import Provider
from surfaced.models.recommendation_judgment import RecommendationJudgment
from surfaced.models.run import Run


NIL_UUID = "00000000-0000-0000-0000-000000000000"


class QueryService:
    """Typed query interface for all surfaced database operations."""

    def __init__(self, db: DBClient | None = None):
        self.db = db or DBClient()

    # --- Brands ---

    def insert_brand(self, brand: Brand) -> Brand:
        self.db.insert_rows(
            "brands",
            [[
                str(brand.id), brand.name, brand.domain, brand.description,
                brand.aliases, brand.competitors, brand.is_active,
                brand.created_at, brand.updated_at,
            ]],
            column_names=[
                "id", "name", "domain", "description",
                "aliases", "competitors", "is_active",
                "created_at", "updated_at",
            ],
        )
        return brand

    def get_brands(self, active_only: bool = True) -> list[Brand]:
        query = "SELECT * FROM brands FINAL"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"
        rows = self.db.execute(query)
        return [Brand.from_dict(r) for r in rows]

    def get_brand(self, brand_id: UUID) -> Brand | None:
        rows = self.db.execute(
            "SELECT * FROM brands FINAL WHERE id = {id:UUID}",
            parameters={"id": str(brand_id)},
        )
        return Brand.from_dict(rows[0]) if rows else None

    def get_brand_by_name(self, name: str) -> Brand | None:
        rows = self.db.execute(
            "SELECT * FROM brands FINAL WHERE name = {name:String} AND is_active = 1",
            parameters={"name": name},
        )
        return Brand.from_dict(rows[0]) if rows else None

    def update_brand(self, brand: Brand) -> Brand:
        brand.updated_at = datetime.now()
        return self.insert_brand(brand)

    def delete_brand(self, brand_id: UUID) -> None:
        brand = self.get_brand(brand_id)
        if brand:
            brand.is_active = 0
            self.update_brand(brand)

    # --- Providers ---

    def insert_provider(self, provider: Provider) -> Provider:
        self.db.insert_rows(
            "providers",
            [[
                str(provider.id), provider.name, provider.provider,
                provider.execution_mode, provider.model, provider.config,
                provider.rate_limit_rpm, provider.is_active,
                provider.created_at, provider.updated_at,
            ]],
            column_names=[
                "id", "name", "provider", "execution_mode",
                "model", "config", "rate_limit_rpm", "is_active",
                "created_at", "updated_at",
            ],
        )
        return provider

    def get_providers(self, active_only: bool = True) -> list[Provider]:
        query = "SELECT * FROM providers FINAL"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"
        rows = self.db.execute(query)
        return [Provider.from_dict(r) for r in rows]

    def get_provider(self, provider_id: UUID) -> Provider | None:
        rows = self.db.execute(
            "SELECT * FROM providers FINAL WHERE id = {id:UUID}",
            parameters={"id": str(provider_id)},
        )
        return Provider.from_dict(rows[0]) if rows else None

    def get_provider_by_name(self, name: str) -> Provider | None:
        rows = self.db.execute(
            "SELECT * FROM providers FINAL WHERE name = {name:String} AND is_active = 1",
            parameters={"name": name},
        )
        return Provider.from_dict(rows[0]) if rows else None

    def delete_provider(self, provider_id: UUID) -> None:
        provider = self.get_provider(provider_id)
        if provider:
            provider.is_active = 0
            provider.updated_at = datetime.now()
            self.insert_provider(provider)

    # --- Prompts ---

    def insert_prompt(self, prompt: Prompt) -> Prompt:
        self.db.insert_rows(
            "prompts",
            [[
                str(prompt.id), prompt.text, prompt.category,
                prompt.branded, prompt.recommendation_enabled,
                prompt.alignment_enabled,
                str(prompt.alignment_position_id or NIL_UUID),
                prompt.tags, str(prompt.brand_id),
                prompt.is_template, prompt.variables, prompt.is_active,
                prompt.created_at, prompt.updated_at,
            ]],
            column_names=[
                "id", "text", "category", "branded",
                "recommendation_enabled", "alignment_enabled",
                "alignment_position_id", "tags", "brand_id",
                "is_template", "variables", "is_active",
                "created_at", "updated_at",
            ],
        )
        return prompt

    # --- Canonical positions ---

    def insert_canonical_position(
        self, position: CanonicalPosition
    ) -> CanonicalPosition:
        self.db.insert_rows(
            "canonical_positions",
            [[
                str(position.id), str(position.brand_id), position.topic,
                position.statement, position.is_active,
                position.created_at, position.updated_at,
            ]],
            column_names=[
                "id", "brand_id", "topic", "statement", "is_active",
                "created_at", "updated_at",
            ],
        )
        return position

    def get_canonical_positions(
        self,
        active_only: bool = True,
        brand_id: UUID | None = None,
    ) -> list[CanonicalPosition]:
        conditions = []
        params = {}
        if active_only:
            conditions.append("is_active = 1")
        if brand_id:
            conditions.append("brand_id = {brand_id:UUID}")
            params["brand_id"] = str(brand_id)

        query = "SELECT * FROM canonical_positions"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY brand_id, topic"
        rows = self.db.execute(query, parameters=params if params else None)
        return [CanonicalPosition.from_dict(r) for r in rows]

    def get_canonical_position(
        self,
        position_id: UUID,
        active_only: bool = True,
    ) -> CanonicalPosition | None:
        query = "SELECT * FROM canonical_positions WHERE id = {id:UUID}"
        if active_only:
            query += " AND is_active = 1"
        rows = self.db.execute(query, parameters={"id": str(position_id)})
        return CanonicalPosition.from_dict(rows[0]) if rows else None

    def update_canonical_position(
        self, position: CanonicalPosition
    ) -> CanonicalPosition:
        position.updated_at = datetime.now()
        self.db.execute_no_result(
            """
            UPDATE canonical_positions
            SET
                topic = {topic:String},
                statement = {statement:String},
                is_active = {is_active:UInt8},
                updated_at = {updated_at:DateTime64(3)}
            WHERE id = {id:UUID}
            """,
            parameters={
                "id": str(position.id),
                "topic": position.topic,
                "statement": position.statement,
                "is_active": position.is_active,
                "updated_at": position.updated_at,
            },
        )
        return position

    def delete_canonical_position(self, position_id: UUID) -> None:
        self.db.execute_no_result(
            """
            UPDATE canonical_positions
            SET
                is_active = 0,
                updated_at = {updated_at:DateTime64(3)}
            WHERE id = {id:UUID}
            """,
            parameters={"id": str(position_id), "updated_at": datetime.now()},
        )

    def get_prompts(
        self,
        active_only: bool = True,
        category: str | None = None,
        tag: str | None = None,
        brand_id: UUID | None = None,
    ) -> list[Prompt]:
        conditions = []
        params = {}
        if active_only:
            conditions.append("is_active = 1")
        if category:
            conditions.append("category = {category:String}")
            params["category"] = category
        if tag:
            conditions.append("has(tags, {tag:String})")
            params["tag"] = tag
        if brand_id:
            conditions.append("brand_id = {brand_id:UUID}")
            params["brand_id"] = str(brand_id)

        query = "SELECT * FROM prompts FINAL"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC"
        rows = self.db.execute(query, parameters=params if params else None)
        return [Prompt.from_dict(r) for r in rows]

    def get_prompt(self, prompt_id: UUID) -> Prompt | None:
        rows = self.db.execute(
            "SELECT * FROM prompts FINAL WHERE id = {id:UUID}",
            parameters={"id": str(prompt_id)},
        )
        return Prompt.from_dict(rows[0]) if rows else None

    def update_prompt(self, prompt: Prompt) -> Prompt:
        prompt.updated_at = datetime.now()
        return self.insert_prompt(prompt)

    def delete_prompt(self, prompt_id: UUID) -> None:
        prompt = self.get_prompt(prompt_id)
        if prompt:
            prompt.is_active = 0
            self.update_prompt(prompt)

    # --- Runs ---

    def insert_run(self, run: Run) -> Run:
        self.db.insert_rows(
            "runs",
            [[
                str(run.id), run.name, run.status,
                run.filters, run.total_prompts,
                run.completed_prompts, run.started_at,
                run.finished_at or datetime(1970, 1, 1),
                run.created_at, run.updated_at,
            ]],
            column_names=[
                "id", "name", "status", "filters",
                "total_prompts", "completed_prompts",
                "started_at", "finished_at",
                "created_at", "updated_at",
            ],
        )
        return run

    def get_runs(self, limit: int = 20) -> list[Run]:
        rows = self.db.execute(
            f"SELECT * FROM runs FINAL ORDER BY created_at DESC LIMIT {limit}"
        )
        return [Run.from_dict(r) for r in rows]

    def get_run(self, run_id: UUID) -> Run | None:
        rows = self.db.execute(
            "SELECT * FROM runs FINAL WHERE id = {id:UUID}",
            parameters={"id": str(run_id)},
        )
        return Run.from_dict(rows[0]) if rows else None

    def update_run(self, run: Run) -> Run:
        run.updated_at = datetime.now()
        return self.insert_run(run)

    # --- Answers ---

    def insert_answer(self, answer: Answer) -> Answer:
        self.db.insert_rows(
            "answers",
            [[
                str(answer.id), str(answer.run_id), str(answer.prompt_id),
                str(answer.provider_id), str(answer.brand_id),
                answer.prompt_text, answer.prompt_category, answer.prompt_branded,
                answer.response_text, answer.model, answer.provider_name,
                answer.latency_ms,
                answer.input_tokens, answer.output_tokens,
                answer.status, answer.error_message,
                answer.brand_mentioned, answer.recommendation_status,
                answer.alignment_status,
                str(answer.alignment_position_id or NIL_UUID),
                answer.alignment_rationale,
                answer.competitors_mentioned,
                answer.created_at,
            ]],
            column_names=[
                "id", "run_id", "prompt_id", "provider_id", "brand_id",
                "prompt_text", "prompt_category", "prompt_branded", "response_text",
                "model", "provider_name", "latency_ms",
                "input_tokens", "output_tokens",
                "status", "error_message",
                "brand_mentioned", "recommendation_status",
                "alignment_status", "alignment_position_id", "alignment_rationale",
                "competitors_mentioned",
                "created_at",
            ],
        )
        return answer

    def get_answers(
        self,
        run_id: UUID | None = None,
        brand_id: UUID | None = None,
        limit: int = 100,
    ) -> list[Answer]:
        conditions = []
        params = {}
        if run_id:
            conditions.append("run_id = {run_id:UUID}")
            params["run_id"] = str(run_id)
        if brand_id:
            conditions.append("brand_id = {brand_id:UUID}")
            params["brand_id"] = str(brand_id)

        query = "SELECT * FROM answers"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += f" ORDER BY created_at DESC LIMIT {limit}"
        rows = self.db.execute(query, parameters=params if params else None)
        return [Answer.from_dict(r) for r in rows]

    # --- Recommendation judgments ---

    def insert_recommendation_judgment(
        self, judgment: RecommendationJudgment
    ) -> RecommendationJudgment:
        self.db.insert_rows(
            "recommendation_judgments",
            [[
                str(judgment.id), str(judgment.answer_id), str(judgment.run_id),
                str(judgment.prompt_id), str(judgment.provider_id),
                str(judgment.brand_id), judgment.judge_model,
                judgment.recommendation_status, judgment.raw_output,
                judgment.error_message, judgment.latency_ms,
                judgment.created_at,
            ]],
            column_names=[
                "id", "answer_id", "run_id", "prompt_id", "provider_id",
                "brand_id", "judge_model", "recommendation_status",
                "raw_output", "error_message", "latency_ms", "created_at",
            ],
        )
        return judgment

    # --- Alignment judgments ---

    def insert_alignment_judgment(
        self, judgment: AlignmentJudgment
    ) -> AlignmentJudgment:
        self.db.insert_rows(
            "alignment_judgments",
            [[
                str(judgment.id), str(judgment.answer_id), str(judgment.run_id),
                str(judgment.prompt_id), str(judgment.provider_id),
                str(judgment.brand_id), str(judgment.alignment_position_id),
                judgment.judge_model, judgment.alignment_status,
                judgment.rationale, judgment.raw_output,
                judgment.error_message, judgment.latency_ms,
                judgment.created_at,
            ]],
            column_names=[
                "id", "answer_id", "run_id", "prompt_id", "provider_id",
                "brand_id", "alignment_position_id", "judge_model",
                "alignment_status", "rationale", "raw_output",
                "error_message", "latency_ms", "created_at",
            ],
        )
        return judgment
