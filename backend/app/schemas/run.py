from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class RunCreateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20000)
    provider: str = Field(default="anthropic", min_length=1, max_length=64)
    model: str = Field(default="claude-3-5-sonnet-latest", min_length=1, max_length=128)
    api_key: str = Field(min_length=1, max_length=500)
    max_steps: int = Field(default=20, ge=1, le=200)

    enable_external_mcp: bool = Field(default=False)
    external_mcp_url: HttpUrl | None = None

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {"claude", "anthropic"}:
            return "anthropic"
        if normalized in {"openai", "gpt"}:
            return "openai"
        if normalized in {"google", "gemini"}:
            return "gemini"
        raise ValueError(
            "provider must be one of: openai, anthropic, claude, google, gemini"
        )


class RunRetryRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=500)


class RunDetailResponse(BaseModel):
    id: str
    provider: str
    model: str
    status: str
    prompt: str
    max_steps: int
    sandbox_profile: str

    requested_external_mcp_url: str | None
    external_mcp_enabled: bool

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
    id: str
    run_id: str
    event_type: str
    message: str
    step_index: int | None
    payload: dict[str, Any]
    created_at: datetime


class RunLogsResponse(BaseModel):
    run_id: str
    stdout_tail: str | None
    stderr_tail: str | None


class RunReportResponse(BaseModel):
    run_id: str
    status: str
    total_score: float
    score_breakdown: dict[str, Any]
    evaluation_summary: str
    metrics: dict[str, float]
    recommendations: list[str]


class RunListResponse(BaseModel):
    items: list[RunDetailResponse]
    total: int
