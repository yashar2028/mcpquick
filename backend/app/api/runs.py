"""Run orchestration API endpoints.

This module exposes the public HTTP surface used by the frontend to:
- submit a run
- inspect run state
- inspect event timeline
- fetch final score reports
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.run import EvaluationRun, RunEvent, RunStatus
from app.schemas.run import (
    RunCreateRequest,
    RunDetailResponse,
    RunEventResponse,
    RunListResponse,
    RunLogsResponse,
    RunReportResponse,
)
from app.services.api_keys import stash_run_api_key
from app.services.run_logs import read_run_log_tails
from app.services.run_presenters import to_run_detail, to_run_event_response
from app.workers.run_worker import enqueue_run

router = APIRouter(prefix="/v1/runs", tags=["runs"])


async def _get_run_or_404(db: AsyncSession, run_id: str) -> EvaluationRun:
    """Load run by id or raise 404 if not found."""
    result = await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )
    return run


@router.post("", response_model=RunDetailResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_run(payload: RunCreateRequest, db: AsyncSession = Depends(get_db)):
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
    db: AsyncSession = Depends(get_db),
):
    """Return paginated runs ordered by most recent creation timestamp."""
    result = await db.execute(
        select(EvaluationRun)
        .order_by(desc(EvaluationRun.created_at))
        .offset(offset)
        .limit(limit)
    )
    items = [to_run_detail(run) for run in result.scalars().all()]

    count_result = await db.execute(select(func.count(EvaluationRun.id)))
    total = count_result.scalar_one()
    return RunListResponse(items=items, total=int(total))


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    """Return run details for a single run id."""
    run = await _get_run_or_404(db, run_id)
    return to_run_detail(run)


@router.get("/{run_id}/events", response_model=list[RunEventResponse])
async def list_run_events(
    run_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Return chronological event timeline for a run."""
    await _get_run_or_404(db, run_id)

    events_result = await db.execute(
        select(RunEvent)
        .where(RunEvent.run_id == run_id)
        .order_by(RunEvent.created_at.asc())
        .limit(limit)
    )

    events = events_result.scalars().all()
    return [to_run_event_response(event) for event in events]


@router.get("/{run_id}/logs", response_model=RunLogsResponse)
async def get_run_logs(run_id: str, db: AsyncSession = Depends(get_db)):
    """Return sandbox stdout/stderr tails for a run if available."""
    await _get_run_or_404(db, run_id)

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
async def get_run_report(run_id: str, db: AsyncSession = Depends(get_db)):
    """Return final report once a run has completed successfully."""
    run = await _get_run_or_404(db, run_id)

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
