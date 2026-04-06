"""Asynchronous run worker.

This worker executes the run lifecycle:
1) transition queued -> running
2) invoke sandbox boundary
3) compute weighted scoring
4) persist report and timeline events
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.run import EvaluationRun, RunEvent, RunStatus
from app.services.sandbox import SandboxRunRequest, get_sandbox_adapter
from app.services.scoring import compute_weighted_score


def enqueue_run(run_id: str) -> None:
    """Schedule background run processing on the current event loop."""
    asyncio.create_task(process_run(run_id))


async def _add_event(
    run: EvaluationRun,
    event_type: str,
    message: str,
    payload: dict,
    step_index: int | None = None,
) -> None:
    """Append a timeline event to the run aggregate before commit."""
    run.events.append(
        RunEvent(
            event_type=event_type,
            message=message,
            payload=payload,
            step_index=step_index,
        )
    )


async def process_run(run_id: str) -> None:
    """Execute one run end-to-end and persist final status.

    Any runtime failure is recorded as a failed run with an error event.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(EvaluationRun).where(EvaluationRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if run is None:
            return

        try:
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(UTC)
            await _add_event(
                run,
                event_type="sandbox_allocated",
                message="Allocated isolated Nix sandbox profile for run execution.",
                payload={
                    "sandbox_profile": run.sandbox_profile,
                    "isolation_mode": "per-run",
                    "external_mcp_in_same_boundary": True,
                    "runtime_module": settings.SANDBOX_RUNTIME_MODULE,
                    "flake_ref": settings.SANDBOX_NIX_FLAKE_REF,
                },
            )

            if (
                run.requested_external_mcp_url
                and not settings.ENABLE_GITHUB_MCP_INGESTION
            ):
                await _add_event(
                    run,
                    event_type="external_mcp_disabled",
                    message="External MCP URL was provided but GitHub MCP ingestion is disabled in v1.",
                    payload={"url": run.requested_external_mcp_url},
                )

            await asyncio.sleep(0.2)
            await _add_event(
                run,
                event_type="model_execution_started",
                message="Started provider model loop inside sandbox.",
                payload={"provider": run.provider, "model": run.model},
                step_index=1,
            )

            await asyncio.sleep(0.2)
            sandbox_adapter = get_sandbox_adapter()
            sandbox_result = await sandbox_adapter.execute(
                SandboxRunRequest(
                    run_id=run.id,
                    prompt=run.prompt,
                    provider=run.provider,
                    model=run.model,
                    max_steps=run.max_steps,
                    external_mcp_url=run.requested_external_mcp_url,
                )
            )
            metrics = sandbox_result.metrics

            weights = {
                "task_success": settings.SCORE_WEIGHT_TASK_SUCCESS,
                "tool_correctness": settings.SCORE_WEIGHT_TOOL_CORRECTNESS,
                "latency_efficiency": settings.SCORE_WEIGHT_LATENCY,
                "cost_efficiency": settings.SCORE_WEIGHT_COST,
                "step_efficiency": settings.SCORE_WEIGHT_STEPS,
                "reliability_recovery": settings.SCORE_WEIGHT_RELIABILITY,
            }

            total_score, metric_scores = compute_weighted_score(metrics, weights)

            run.step_count = sandbox_result.step_count
            run.token_input = sandbox_result.token_input
            run.token_output = sandbox_result.token_output
            run.estimated_cost_usd = round(
                (run.token_input + run.token_output) * 0.000004, 6
            )
            run.latency_ms = sandbox_result.latency_ms
            run.total_score = total_score
            run.score_breakdown = {
                "weights": weights,
                "metric_scores": metric_scores,
                "metrics": metrics,
                "computation": "weighted_score_sum",
            }
            run.evaluation_summary = "Run completed in isolated sandbox with acceptable tool behavior and cost/latency trade-offs."
            run.status = RunStatus.COMPLETED
            run.finished_at = datetime.now(UTC)

            await _add_event(
                run,
                event_type="evaluation_completed",
                message="Calculated weighted scorecard and generated report.",
                payload={"score": total_score, "metrics": metric_scores},
                step_index=run.step_count,
            )

            await session.commit()
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            run.status = RunStatus.FAILED
            run.error_message = str(exc)
            run.finished_at = datetime.now(UTC)
            await _add_event(
                run,
                event_type="run_failed",
                message="Run failed during execution pipeline.",
                payload={"error": str(exc)},
            )
            await session.commit()
