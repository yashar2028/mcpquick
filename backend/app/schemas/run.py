from __future__ import annotations

"""Pydantic schemas for run creation, querying, logs, and reports."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class McpRepoRequest(BaseModel):
    repo_url: HttpUrl | None = None
    server_json: dict[str, Any] | None = None
    server_path: str = Field(default="server.json", min_length=1, max_length=240)
    env: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source(self):
        has_repo = self.repo_url is not None
        has_inline = self.server_json is not None
        if has_repo == has_inline:
            raise ValueError("Provide either repo_url or server_json for MCP entries")
        return self


class RunCreateRequest(BaseModel):
    """Request payload used to queue a new evaluation run."""

    prompt: str = Field(min_length=1, max_length=20000)
    provider: str = Field(default="anthropic", min_length=1, max_length=64)
    model: str = Field(default="claude-3-haiku-20240307", min_length=1, max_length=128)
    api_key: str = Field(min_length=1, max_length=500)
    max_steps: int = Field(default=20, ge=1, le=200)

    enable_external_mcp: bool = Field(default=False)
    external_mcp_url: HttpUrl | None = None
    mcp_repos: list[McpRepoRequest] = Field(default_factory=list)
    mcp_server_path: str = Field(default="server.json", min_length=1, max_length=240)
    mcp_env: dict[str, str] = Field(default_factory=dict)
    mcp_headers: dict[str, str] = Field(default_factory=dict)
    mcp_failure_policy: str = Field(default="fail", min_length=1, max_length=20)

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {"claude", "anthropic"}:
            return "anthropic"
        if normalized in {"openai", "gpt"}:
            return "openai"
        raise ValueError("provider must be one of: openai, anthropic, claude")

    @field_validator("mcp_failure_policy")
    @classmethod
    def validate_failure_policy(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"fail", "continue"}:
            raise ValueError("mcp_failure_policy must be 'fail' or 'continue'")
        return normalized


class RunRetryRequest(BaseModel):
    """Request payload used to retry an existing run with a fresh API key."""

    api_key: str = Field(min_length=1, max_length=500)


class RunDetailResponse(BaseModel):
    """Detailed run view returned by create/list/get APIs."""

    id: str
    provider: str
    model: str
    status: str
    prompt: str
    max_steps: int
    sandbox_profile: str

    requested_external_mcp_url: str | None
    external_mcp_enabled: bool
    mcp_config: dict[str, Any] | None

    step_count: int
    token_input: int
    token_output: int
    estimated_cost_usd: float
    latency_ms: int | None

    total_score: float | None
    score_breakdown: dict[str, Any] | None
    evaluation_summary: str | None
    error_message: str | None

    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RunEventResponse(BaseModel):
    """Serialized timeline event row for run history UI."""

    id: str
    run_id: str
    event_type: str
    message: str
    step_index: int | None
    payload: dict[str, Any]
    created_at: datetime


class RunLogsResponse(BaseModel):
    """Tail view of sandbox stdout/stderr logs for one run."""

    run_id: str
    stdout_tail: str | None
    stderr_tail: str | None


class RunReportResponse(BaseModel):
    """Final scorecard payload for completed runs."""

    run_id: str
    status: str
    total_score: float
    score_breakdown: dict[str, Any]
    evaluation_summary: str
    metrics: dict[str, float]
    recommendations: list[str]
    judge_report: dict[str, Any] | None = None
    judge_model: str | None = None


class RunListResponse(BaseModel):
    """Paginated run collection response."""

    items: list[RunDetailResponse]
    total: int
