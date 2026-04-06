"""Run orchestration API endpoints.

This module exposes the public HTTP surface used by the frontend to:
- submit a run
- inspect run state
- inspect event timeline
- fetch final score reports
"""

from __future__ import annotations

from datetime import UTC, datetime

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
    RunReportResponse,
)
from app.workers.run_worker import enqueue_run

router = APIRouter(prefix="/v1/runs", tags=["runs"])


def _to_run_detail(run: EvaluationRun) -> RunDetailResponse:
    """Map ORM run model to the API detail response schema."""
    return RunDetailResponse(
        id=run.id,
        provider=run.provider,
        model=run.model,
        status=run.status.value,
        prompt=run.prompt,
        max_steps=run.max_steps,
        sandbox_profile=run.sandbox_profile,
        requested_external_mcp_url=run.requested_external_mcp_url,
        external_mcp_enabled=run.external_mcp_enabled,
        step_count=run.step_count,
        token_input=run.token_input,
        token_output=run.token_output,
        estimated_cost_usd=run.estimated_cost_usd,
        latency_ms=run.latency_ms,
        total_score=run.total_score,
        score_breakdown=run.score_breakdown,
        evaluation_summary=run.evaluation_summary,
        error_message=run.error_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


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
    await db.commit()
    await db.refresh(run)

    enqueue_run(
        run.id
    )  # Handling of the run is delegated to the asynchronous worker which will update the run status and metrics upon completion.
    # This will also add events to the run timeline (event_type) which can be queried by the frontend for real-time updates.
    return _to_run_detail(run)


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
    items = [_to_run_detail(run) for run in result.scalars().all()]

    count_result = await db.execute(select(func.count(EvaluationRun.id)))
    total = count_result.scalar_one()
    return RunListResponse(items=items, total=int(total))


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    """Return run details for a single run id."""
    result = await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )
    return _to_run_detail(run)


@router.get("/{run_id}/events", response_model=list[RunEventResponse])
async def list_run_events(
    run_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Return chronological event timeline for a run."""
    run_result = await db.execute(
        select(EvaluationRun.id).where(EvaluationRun.id == run_id)
    )
    if run_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )

    events_result = await db.execute(
        select(RunEvent)
        .where(RunEvent.run_id == run_id)
        .order_by(RunEvent.created_at.asc())
        .limit(limit)
    )

    events = events_result.scalars().all()
    return [
        RunEventResponse(
            id=event.id,
            run_id=event.run_id,
            event_type=event.event_type,
            message=event.message,
            step_index=event.step_index,
            payload=event.payload,
            created_at=event.created_at,
        )
        for event in events
    ]


@router.get("/{run_id}/report", response_model=RunReportResponse)
async def get_run_report(run_id: str, db: AsyncSession = Depends(get_db)):
    """Return final report once a run has completed successfully."""
    result = await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )

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
    recommendations = [
        "Improve tool selection precision to raise tool correctness score.",
        "Reduce exploratory steps when the answer is already sufficiently grounded.",
        "Track latency by step and cap non-essential tool calls.",
    ]

    return RunReportResponse(
        run_id=run.id,
        status=run.status.value,
        total_score=run.total_score,
        score_breakdown=run.score_breakdown,
        evaluation_summary=run.evaluation_summary or "Completed",
        metrics=metric_scores,
        recommendations=recommendations,
    )
