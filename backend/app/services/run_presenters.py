"""Presentation helpers for run-related API responses."""

from __future__ import annotations

from app.models.run import EvaluationRun, RunEvent, RunInstructionFile
from app.schemas.run import (
    InstructionFileMetadataResponse,
    RunDetailResponse,
    RunEventResponse,
)


def to_instruction_file_metadata(
    instruction_file: RunInstructionFile,
) -> InstructionFileMetadataResponse:
    """Map instruction file ORM entity into API-safe metadata payload."""
    return InstructionFileMetadataResponse(
        id=instruction_file.id,
        filename=instruction_file.filename,
        size_bytes=instruction_file.size_bytes,
        content_sha256=instruction_file.content_sha256,
        upload_order=instruction_file.upload_order,
        created_at=instruction_file.created_at,
    )


def to_run_detail(run: EvaluationRun) -> RunDetailResponse:
    """Map run ORM entity to API detail response."""
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
        mcp_config=run.mcp_config,
        instruction_files=[
            to_instruction_file_metadata(item)
            for item in sorted(
                run.instruction_files, key=lambda file_item: file_item.upload_order
            )
        ],
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


def to_run_event_response(event: RunEvent) -> RunEventResponse:
    """Map run event ORM entity to API event response."""
    return RunEventResponse(
        id=event.id,
        run_id=event.run_id,
        event_type=event.event_type,
        message=event.message,
        step_index=event.step_index,
        payload=event.payload,
        created_at=event.created_at,
    )
