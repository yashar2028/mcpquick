"""Run orchestration API endpoints.

This module exposes the public HTTP surface used by the frontend to:
- submit a run
- inspect run state
- inspect event timeline
- fetch final score reports
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
import hashlib
import io
import ipaddress
import json
from pathlib import Path
from urllib.parse import urlparse
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.run import EvaluationRun, RunEvent, RunInstructionFile, RunStatus
from app.models.user import User
from app.schemas.run import (
    InstructionFileContentResponse,
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
from app.services.run_presenters import (
    to_run_detail,
    to_run_event_response,
)
from app.workers.run_worker import enqueue_run

router = APIRouter(prefix="/v1/runs", tags=["runs"])


async def _get_run_or_404(
    db: AsyncSession,
    run_id: str,
    user_id: str,
) -> EvaluationRun:
    """Load run by id or raise 404 if not found."""
    result = await db.execute(
        select(EvaluationRun)
        .options(selectinload(EvaluationRun.instruction_files))
        .where(
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


async def _get_instruction_file_or_404(
    db: AsyncSession,
    run_id: str,
    file_id: str,
    user_id: str,
) -> RunInstructionFile:
    result = await db.execute(
        select(RunInstructionFile)
        .join(EvaluationRun, RunInstructionFile.run_id == EvaluationRun.id)
        .where(
            RunInstructionFile.id == file_id,
            RunInstructionFile.run_id == run_id,
            EvaluationRun.user_id == user_id,
        )
    )
    instruction_file = result.scalar_one_or_none()
    if instruction_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instruction file not found",
        )
    return instruction_file


def _to_instruction_file_record(
    filename: str,
    content: str,
    upload_order: int,
) -> RunInstructionFile:
    encoded = content.encode("utf-8")
    return RunInstructionFile(
        filename=filename,
        content=content,
        size_bytes=len(encoded),
        content_sha256=hashlib.sha256(encoded).hexdigest(),
        upload_order=upload_order,
    )


def _build_run_report_snapshot(run: EvaluationRun) -> dict[str, object]:
    """Build a report snapshot included in downloaded artifact archives."""
    return {
        "run_id": run.id,
        "status": run.status.value,
        "provider": run.provider,
        "model": run.model,
        "prompt": run.prompt,
        "max_steps": run.max_steps,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "step_count": run.step_count,
        "token_input": run.token_input,
        "token_output": run.token_output,
        "estimated_cost_usd": run.estimated_cost_usd,
        "latency_ms": run.latency_ms,
        "total_score": run.total_score,
        "score_breakdown": run.score_breakdown,
        "evaluation_summary": run.evaluation_summary,
        "judge_report": run.judge_report,
        "judge_model": run.judge_model,
        "error_message": run.error_message,
        "instruction_files": [
            {
                "filename": item.filename,
                "size_bytes": item.size_bytes,
                "content_sha256": item.content_sha256,
                "upload_order": item.upload_order,
            }
            for item in sorted(
                run.instruction_files, key=lambda file_item: file_item.upload_order
            )
        ],
    }


def _zip_run_artifacts(
    run_dir: Path,
    report_snapshot: dict[str, object],
) -> bytes:
    """Create a zip archive from one run sandbox directory and report snapshot."""
    archive = io.BytesIO()
    with zipfile.ZipFile(
        archive, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as zip_file:
        for file_path in sorted(run_dir.rglob("*")):
            if file_path.is_file():
                zip_file.write(
                    file_path, arcname=file_path.relative_to(run_dir).as_posix()
                )

        zip_file.writestr(
            "run_report.json",
            json.dumps(report_snapshot, ensure_ascii=True, indent=2),
        )

    return archive.getvalue()


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


def _validate_mcp_repo_url(raw_url: str) -> None:
    parsed = urlparse(raw_url)
    if parsed.scheme != "https":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MCP repo URL must use https",
        )

    hostname = parsed.hostname or ""
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MCP repo URL must be a public host",
        )

    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MCP repo URL must be a public host",
            )
    except ValueError:
        pass


@router.post("", response_model=RunDetailResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    payload: RunCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a run record and enqueue asynchronous sandbox execution."""
    if payload.enable_external_mcp and payload.provider != "anthropic":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MCP tool calling is only supported for Anthropic currently.",
        )
    mcp_repo_items: list[dict[str, object]] = []
    if payload.enable_external_mcp:
        if payload.mcp_repos:
            for repo in payload.mcp_repos:
                if repo.server_json is not None:
                    mcp_repo_items.append(
                        {
                            "server_json": repo.server_json,
                            "env": repo.env,
                            "headers": repo.headers,
                        }
                    )
                    continue

                repo_url = str(repo.repo_url)
                _validate_mcp_repo_url(repo_url)
                mcp_repo_items.append(
                    {
                        "repo_url": repo_url,
                        "server_path": repo.server_path,
                        "env": repo.env,
                        "headers": repo.headers,
                    }
                )
        elif payload.external_mcp_url:
            repo_url = str(payload.external_mcp_url)
            _validate_mcp_repo_url(repo_url)
            mcp_repo_items.append(
                {
                    "repo_url": repo_url,
                    "server_path": payload.mcp_server_path,
                    "env": payload.mcp_env,
                    "headers": payload.mcp_headers,
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one MCP repo is required when enable_external_mcp is true",
            )

    mcp_config = None
    if payload.enable_external_mcp:
        mcp_config = {
            "repos": mcp_repo_items,
            "failure_policy": payload.mcp_failure_policy,
        }

    instruction_file_records = [
        _to_instruction_file_record(
            filename=item.filename,
            content=item.content,
            upload_order=index,
        )
        for index, item in enumerate(payload.instruction_files)
    ]
    instruction_files_total_size = sum(
        item.size_bytes for item in instruction_file_records
    )

    mcp_repo_url = next(
        (
            item.get("repo_url")
            for item in mcp_repo_items
            if isinstance(item, dict) and item.get("repo_url")
        ),
        None,
    )

    run = EvaluationRun(
        user_id=current_user.id,
        provider=payload.provider,
        model=payload.model,
        prompt=payload.prompt,
        status=RunStatus.QUEUED,
        max_steps=payload.max_steps,
        api_key_provided=bool(payload.api_key),
        requested_external_mcp_url=str(mcp_repo_url) if mcp_repo_url else None,
        external_mcp_enabled=payload.enable_external_mcp,
        mcp_config=mcp_config,
        sandbox_profile=settings.SANDBOX_PROFILE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    run.instruction_files.extend(instruction_file_records)
    run.events.append(
        RunEvent(
            event_type="run_queued",
            message="Run queued for isolated sandbox execution.",
            payload={
                "sandbox_profile": settings.SANDBOX_PROFILE,
                "external_mcp_in_same_boundary": True,
                "instruction_files": {
                    "count": len(instruction_file_records),
                    "total_size_bytes": instruction_files_total_size,
                },
            },
        )
    )

    db.add(run)
    await db.flush()
    await stash_run_api_key(run.id, payload.api_key)
    await db.commit()
    created_result = await db.execute(
        select(EvaluationRun)
        .options(selectinload(EvaluationRun.instruction_files))
        .where(EvaluationRun.id == run.id)
    )
    created_run = created_result.scalar_one()

    enqueue_run(run.id)
    return to_run_detail(created_run)


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
    statement = statement.options(selectinload(EvaluationRun.instruction_files))

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


@router.get(
    "/{run_id}/instruction-files/{file_id}",
    response_model=InstructionFileContentResponse,
)
async def get_run_instruction_file(
    run_id: str,
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return one persisted instruction file content for an authorized run owner."""
    instruction_file = await _get_instruction_file_or_404(
        db=db,
        run_id=run_id,
        file_id=file_id,
        user_id=current_user.id,
    )
    return InstructionFileContentResponse(
        id=instruction_file.id,
        run_id=instruction_file.run_id,
        filename=instruction_file.filename,
        content=instruction_file.content,
        size_bytes=instruction_file.size_bytes,
        content_sha256=instruction_file.content_sha256,
        upload_order=instruction_file.upload_order,
        created_at=instruction_file.created_at,
    )


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


@router.get("/{run_id}/artifacts.zip")
async def download_run_artifacts_zip(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download one run's sandbox artifacts as a zip archive."""
    run = await _get_run_or_404(db, run_id, current_user.id)

    backend_root = Path(__file__).resolve().parents[2]
    runs_root = (backend_root / settings.SANDBOX_RUN_BASE_DIR).resolve()
    run_dir = (runs_root / run_id).resolve()

    if not run_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sandbox artifacts found for this run",
        )

    try:
        run_dir.relative_to(runs_root)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid run artifacts path",
        ) from exc

    zip_content = _zip_run_artifacts(run_dir, _build_run_report_snapshot(run))
    filename = f"run-{run_id}-artifacts.zip"
    return Response(
        content=zip_content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
        judge_report=run.judge_report,
        judge_model=run.judge_model,
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
        mcp_config=previous_run.mcp_config,
        sandbox_profile=previous_run.sandbox_profile,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    retry_run_item.instruction_files.extend(
        [
            _to_instruction_file_record(
                filename=item.filename,
                content=item.content,
                upload_order=item.upload_order,
            )
            for item in sorted(
                previous_run.instruction_files,
                key=lambda file_item: file_item.upload_order,
            )
        ]
    )

    instruction_files_total_size = sum(
        item.size_bytes for item in retry_run_item.instruction_files
    )

    retry_run_item.events.append(
        RunEvent(
            event_type="run_queued",
            message="Retry queued from previous run configuration.",
            payload={
                "retry_of_run_id": previous_run.id,
                "sandbox_profile": previous_run.sandbox_profile,
                "external_mcp_in_same_boundary": True,
                "instruction_files": {
                    "count": len(retry_run_item.instruction_files),
                    "total_size_bytes": instruction_files_total_size,
                    "items": [
                        {
                            "filename": item.filename,
                            "size_bytes": item.size_bytes,
                            "content_sha256": item.content_sha256,
                            "upload_order": item.upload_order,
                        }
                        for item in retry_run_item.instruction_files
                    ],
                },
            },
        )
    )

    db.add(retry_run_item)
    await db.flush()
    await stash_run_api_key(retry_run_item.id, payload.api_key)
    await db.commit()
    retried_result = await db.execute(
        select(EvaluationRun)
        .options(selectinload(EvaluationRun.instruction_files))
        .where(EvaluationRun.id == retry_run_item.id)
    )
    retried_run = retried_result.scalar_one()

    enqueue_run(retry_run_item.id)
    return to_run_detail(retried_run)
