from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RunsOverTimePoint(BaseModel):
    date: str
    count: int


class ProviderModelUsage(BaseModel):
    provider: str
    model: str
    run_count: int
    avg_score: float | None
    avg_latency_ms: float | None


class DashboardSummaryResponse(BaseModel):
    total_runs: int
    completed_runs: int
    failed_runs: int
    success_rate: float
    average_latency_ms: float | None
    latest_run_at: datetime | None
    runs_over_time: list[RunsOverTimePoint]
    provider_model_usage: list[ProviderModelUsage]
