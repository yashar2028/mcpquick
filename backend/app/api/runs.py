"""Run orchestration API endpoints.

This module exposes the public HTTP surface used by the frontend to:
- submit a run
- inspect run state
- inspect event timeline
- fetch final score reports
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.run import EvaluationRun, RunEvent, RunStatus
from app.models.user import User
from app.schemas.run import (
    RunCreateRequest,
    RunDetailResponse,
    RunEventResponse,
    RunListResponse,
    RunLogsResponse,
    RunRetryRequest,
    RunReportResponse,
)
from app.services.api_keys import stash_run_api_key
from app.services.run_logs import read_run_log_tails
from app.services.run_presenters import to_run_detail, to_run_event_response
from app.workers.run_worker import enqueue_run

router = APIRouter(prefix="/v1/runs", tags=["runs"])


async def _get_run_or_404(
    db: AsyncSession,
    run_id: str,
    user_id: str,
) -> EvaluationRun:
    """Load run by id or raise 404 if not found."""
    result = await db.execute(
        select(EvaluationRun).where(
            EvaluationRun.id == run_id,
            EvaluationRun.user_id == user_id,
        )
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )
    return run


def _normalize_status_filter(raw_status: str | None) -> RunStatus | None:
    if not raw_status:
        return None

    try:
        return RunStatus(raw_status.strip().lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be one of: queued, running, completed, failed",
        ) from exc


def _build_created_after_datetime(raw_date: date | None) -> datetime | None:
    if raw_date is None:
        return None
    return datetime.combine(raw_date, time.min, tzinfo=UTC)


def _build_created_before_datetime(raw_date: date | None) -> datetime | None:
    if raw_date is None:
        return None
    return datetime.combine(raw_date, time.max, tzinfo=UTC)


@router.post("", response_model=RunDetailResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    payload: RunCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a run record and enqueue asynchronous sandbox execution."""
    if payload.enable_external_mcp and not payload.external_mcp_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="external_mcp_url is required when enable_external_mcp is true",
        )

    if payload.enable_external_mcp and not settings.ENABLE_GITHUB_MCP_INGESTION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="External GitHub MCP ingestion is disabled in v1.",
        )

    run = EvaluationRun(
        user_id=current_user.id,
        provider=payload.provider,
        model=payload.model,
        prompt=payload.prompt,
        status=RunStatus.QUEUED,
        max_steps=payload.max_steps,
        api_key_provided=bool(payload.api_key),
        requested_external_mcp_url=(
            str(payload.external_mcp_url) if payload.external_mcp_url else None
        ),
        external_mcp_enabled=payload.enable_external_mcp,
        sandbox_profile=settings.SANDBOX_PROFILE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    run.events.append(
        RunEvent(
            event_type="run_queued",
            message="Run queued for isolated sandbox execution.",
            payload={
                "sandbox_profile": settings.SANDBOX_PROFILE,
                "external_mcp_in_same_boundary": True,
            },
        )
    )

    db.add(run)
    await db.flush()
    await stash_run_api_key(run.id, payload.api_key)
    await db.commit()
    await db.refresh(run)

    enqueue_run(run.id)
    return to_run_detail(run)


@router.get("", response_model=RunListResponse)
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    provider: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    created_after: date | None = Query(default=None),
    created_before: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return paginated runs ordered by most recent creation timestamp."""
    normalized_status = _normalize_status_filter(status_filter)

    statement = select(EvaluationRun).where(EvaluationRun.user_id == current_user.id)

    if provider:
        statement = statement.where(EvaluationRun.provider == provider.strip().lower())
    if normalized_status is not None:
        statement = statement.where(EvaluationRun.status == normalized_status)
    if search:
        statement = statement.where(EvaluationRun.prompt.ilike(f"%{search.strip()}%"))

    created_after_dt = _build_created_after_datetime(created_after)
    created_before_dt = _build_created_before_datetime(created_before)

    if created_after_dt is not None:
        statement = statement.where(EvaluationRun.created_at >= created_after_dt)
    if created_before_dt is not None:
        statement = statement.where(EvaluationRun.created_at <= created_before_dt)

    result = await db.execute(
        statement.order_by(desc(EvaluationRun.created_at)).offset(offset).limit(limit)
    )
    items = [to_run_detail(run) for run in result.scalars().all()]

    count_result = await db.execute(
        select(func.count()).select_from(statement.order_by(None).subquery())
    )
    total = count_result.scalar_one()
    return RunListResponse(items=items, total=int(total))


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return run details for a single run id."""
    run = await _get_run_or_404(db, run_id, current_user.id)
    return to_run_detail(run)


@router.get("/{run_id}/events", response_model=list[RunEventResponse])
async def list_run_events(
    run_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return chronological event timeline for a run."""
    await _get_run_or_404(db, run_id, current_user.id)

    events_result = await db.execute(
        select(RunEvent)
        .where(RunEvent.run_id == run_id)
        .order_by(RunEvent.created_at.asc())
        .limit(limit)
    )

    events = events_result.scalars().all()
    return [to_run_event_response(event) for event in events]


@router.get("/{run_id}/logs", response_model=RunLogsResponse)
async def get_run_logs(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return sandbox stdout/stderr tails for a run if available."""
    await _get_run_or_404(db, run_id, current_user.id)

    backend_root = Path(__file__).resolve().parents[2]
    stdout_tail, stderr_tail = read_run_log_tails(
        backend_root=backend_root,
        runs_base_dir=settings.SANDBOX_RUN_BASE_DIR,
        run_id=run_id,
    )

    return RunLogsResponse(
        run_id=run_id,
        stdout_tail=stdout_tail,
        stderr_tail=stderr_tail,
    )


@router.get("/{run_id}/report", response_model=RunReportResponse)
async def get_run_report(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return final report once a run has completed successfully."""
    run = await _get_run_or_404(db, run_id, current_user.id)

    if run.status in {RunStatus.QUEUED, RunStatus.RUNNING}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Run is still in progress. Report will be available after completion.",
        )

    if (
        run.status == RunStatus.FAILED
        or run.total_score is None
        or not run.score_breakdown
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=run.error_message or "Run did not produce a score report",
        )

    metric_scores = run.score_breakdown.get("metric_scores", {})
    recommendations = run.score_breakdown.get("recommendations") or []

    return RunReportResponse(
        run_id=run.id,
        status=run.status.value,
        total_score=run.total_score,
        score_breakdown=run.score_breakdown,
        evaluation_summary=run.evaluation_summary or "Completed",
        metrics=metric_scores,
        recommendations=recommendations,
    )


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete one run and all associated events for the current user."""
    run = await _get_run_or_404(db, run_id, current_user.id)
    await db.delete(run)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{run_id}/retry", response_model=RunDetailResponse)
async def retry_run(
    run_id: str,
    payload: RunRetryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new queued run by reusing configuration from a previous run."""
    previous_run = await _get_run_or_404(db, run_id, current_user.id)

    retry_run_item = EvaluationRun(
        user_id=current_user.id,
        provider=previous_run.provider,
        model=previous_run.model,
        prompt=previous_run.prompt,
        status=RunStatus.QUEUED,
        max_steps=previous_run.max_steps,
        api_key_provided=bool(payload.api_key),
        requested_external_mcp_url=previous_run.requested_external_mcp_url,
        external_mcp_enabled=previous_run.external_mcp_enabled,
        sandbox_profile=previous_run.sandbox_profile,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    retry_run_item.events.append(
        RunEvent(
            event_type="run_queued",
            message="Retry queued from previous run configuration.",
            payload={
                "retry_of_run_id": previous_run.id,
                "sandbox_profile": previous_run.sandbox_profile,
                "external_mcp_in_same_boundary": True,
            },
        )
    )

    db.add(retry_run_item)
    await db.flush()
    await stash_run_api_key(retry_run_item.id, payload.api_key)
    await db.commit()
    await db.refresh(retry_run_item)

    enqueue_run(retry_run_item.id)
    return to_run_detail(retry_run_item)
