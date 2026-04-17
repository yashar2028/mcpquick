from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.run import EvaluationRun, RunStatus
from app.models.user import User
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    ProviderModelUsage,
    RunsOverTimePoint,
)

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_runs = int(
        (
            await db.execute(
                select(func.count(EvaluationRun.id)).where(
                    EvaluationRun.user_id == current_user.id
                )
            )
        ).scalar_one()
        or 0
    )

    completed_runs = int(
        (
            await db.execute(
                select(func.count(EvaluationRun.id)).where(
                    EvaluationRun.user_id == current_user.id,
                    EvaluationRun.status == RunStatus.COMPLETED,
                )
            )
        ).scalar_one()
        or 0
    )

    failed_runs = int(
        (
            await db.execute(
                select(func.count(EvaluationRun.id)).where(
                    EvaluationRun.user_id == current_user.id,
                    EvaluationRun.status == RunStatus.FAILED,
                )
            )
        ).scalar_one()
        or 0
    )

    success_rate = round((completed_runs / total_runs), 4) if total_runs else 0.0

    average_latency_ms_raw = (
        await db.execute(
            select(func.avg(EvaluationRun.latency_ms)).where(
                EvaluationRun.user_id == current_user.id,
                EvaluationRun.latency_ms.is_not(None),
            )
        )
    ).scalar_one()
    average_latency_ms = (
        round(float(average_latency_ms_raw), 2)
        if average_latency_ms_raw is not None
        else None
    )

    latest_run_at = (
        await db.execute(
            select(func.max(EvaluationRun.created_at)).where(
                EvaluationRun.user_id == current_user.id
            )
        )
    ).scalar_one()

    runs_over_time_rows = (
        await db.execute(
            select(
                func.date(EvaluationRun.created_at).label("run_date"),
                func.count(EvaluationRun.id).label("run_count"),
            )
            .where(EvaluationRun.user_id == current_user.id)
            .group_by(func.date(EvaluationRun.created_at))
            .order_by(func.date(EvaluationRun.created_at).asc())
        )
    ).all()

    runs_over_time = [
        RunsOverTimePoint(date=str(row.run_date), count=int(row.run_count))
        for row in runs_over_time_rows
    ]

    provider_usage_rows = (
        await db.execute(
            select(
                EvaluationRun.provider,
                EvaluationRun.model,
                func.count(EvaluationRun.id).label("run_count"),
                func.avg(EvaluationRun.total_score).label("avg_score"),
                func.avg(EvaluationRun.latency_ms).label("avg_latency_ms"),
            )
            .where(EvaluationRun.user_id == current_user.id)
            .group_by(EvaluationRun.provider, EvaluationRun.model)
            .order_by(func.count(EvaluationRun.id).desc())
        )
    ).all()

    provider_model_usage = [
        ProviderModelUsage(
            provider=row.provider,
            model=row.model,
            run_count=int(row.run_count),
            avg_score=(
                round(float(row.avg_score), 4) if row.avg_score is not None else None
            ),
            avg_latency_ms=(
                round(float(row.avg_latency_ms), 2)
                if row.avg_latency_ms is not None
                else None
            ),
        )
        for row in provider_usage_rows
    ]

    return DashboardSummaryResponse(
        total_runs=total_runs,
        completed_runs=completed_runs,
        failed_runs=failed_runs,
        success_rate=success_rate,
        average_latency_ms=average_latency_ms,
        latest_run_at=latest_run_at if isinstance(latest_run_at, datetime) else None,
        runs_over_time=runs_over_time,
        provider_model_usage=provider_model_usage,
    )
