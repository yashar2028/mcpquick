from __future__ import annotations

"""Pydantic schemas for dashboard aggregate metrics and trend slices."""

from datetime import datetime

from pydantic import BaseModel


class RunsOverTimePoint(BaseModel):
    """Daily run count point used in timeline charts."""

    date: str
    count: int


class ProviderModelUsage(BaseModel):
    """Provider/model aggregate usage and quality metrics."""

    provider: str
    model: str
    run_count: int
    avg_score: float | None
    avg_latency_ms: float | None


class DashboardSummaryResponse(BaseModel):
    """Top-level dashboard response for authenticated user summary."""

    total_runs: int
    completed_runs: int
    failed_runs: int
    success_rate: float
    average_latency_ms: float | None
    latest_run_at: datetime | None
    runs_over_time: list[RunsOverTimePoint]
    provider_model_usage: list[ProviderModelUsage]
