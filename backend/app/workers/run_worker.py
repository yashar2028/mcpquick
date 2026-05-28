"""Asynchronous run worker.

This worker executes the run lifecycle:
1) transition queued -> running
2) invoke sandbox boundary
3) compute weighted scoring
4) persist report and timeline events
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.run import EvaluationRun, RunEvent, RunStatus
from app.services.api_keys import pop_run_api_key
from app.services.judge import run_judge
from app.services.run_failures import classify_run_failure
from app.services.sandbox import SandboxRunRequest, get_sandbox_adapter
from app.services.scoring import (
    build_heuristic_summary,
    build_recommendations,
    compute_weighted_score,
    estimate_token_cost_usd,
)


logger = logging.getLogger(__name__)


def enqueue_run(run_id: str) -> None:
    """Schedule background run processing on the current event loop."""
    asyncio.create_task(process_run(run_id))


async def _add_event(
    session: AsyncSession,
    run: EvaluationRun,
    event_type: str,
    message: str,
    payload: dict,
    step_index: int | None = None,
) -> None:
    """Append a timeline event to the run aggregate before commit.

    `step_index` is optional because some events are run-level (allocation,
    key loading, failures) rather than step-scoped model execution events.
    """
    session.add(
        RunEvent(
            run_id=run.id,
            event_type=event_type,
            message=message,
            payload=payload,
            step_index=step_index,
        )
    )


def _collect_mcp_repo_urls(
    mcp_config: dict | None,
    fallback_url: str | None,
) -> list[str]:
    repo_urls: list[str] = []
    if isinstance(mcp_config, dict):
        repos_raw = mcp_config.get("repos")
        if isinstance(repos_raw, list):
            for repo in repos_raw:
                if isinstance(repo, dict) and repo.get("repo_url"):
                    repo_urls.append(str(repo.get("repo_url")))

    if not repo_urls and fallback_url:
        repo_urls.append(fallback_url)

    return repo_urls


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
                session,
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

            repo_urls = _collect_mcp_repo_urls(
                run.mcp_config, run.requested_external_mcp_url
            )

            if repo_urls:
                await _add_event(
                    session,
                    run,
                    event_type="mcp_repo_configured",
                    message="MCP repo configuration recorded for sandbox tool execution.",
                    payload={
                        "repo_urls": repo_urls,
                        "config": run.mcp_config or {},
                    },
                )

            await asyncio.sleep(0.2)
            await _add_event(
                session,
                run,
                event_type="model_execution_started",
                message="Started provider model loop inside sandbox.",
                payload={"provider": run.provider, "model": run.model},
                step_index=1,
            )

            provider_api_key = await pop_run_api_key(
                run.id
            )  # Pop the key from memory and return
            if not provider_api_key:
                raise RuntimeError(
                    "Run API key was missing from the in-memory session store. "
                    "Re-submit this run with a provider key."
                )

            await _add_event(
                session,
                run,
                event_type="provider_key_loaded",
                message="Loaded session API key for provider call.",
                payload={"provider": run.provider, "key_present": True},
            )

            await asyncio.sleep(0.2)
            sandbox_adapter = get_sandbox_adapter()
            sandbox_result = await sandbox_adapter.execute(
                SandboxRunRequest(
                    run_id=run.id,
                    prompt=run.prompt,
                    provider=run.provider,
                    model=run.model,
                    api_key=provider_api_key,
                    max_steps=run.max_steps,
                    external_mcp_url=run.requested_external_mcp_url,
                    mcp_config=run.mcp_config,
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
            run.estimated_cost_usd = estimate_token_cost_usd(
                provider=run.provider,
                model=run.model,
                token_input=run.token_input,
                token_output=run.token_output,
            )
            run.latency_ms = sandbox_result.latency_ms
            run.total_score = total_score
            recommendations = build_recommendations(metric_scores)
            run.score_breakdown = {
                "weights": weights,
                "metric_scores": metric_scores,
                "metrics": metrics,
                "computation": "weighted_score_sum",
                "recommendations": recommendations,
            }
            run.evaluation_summary = build_heuristic_summary(total_score, metric_scores)

            if settings.JUDGE_ANTHROPIC_API_KEY:
                try:
                    judge_report, judge_model, judge_latency_ms = run_judge(
                        prompt=run.prompt,
                        output_text=sandbox_result.output_text,
                        tool_trace=sandbox_result.tool_trace,
                        repo_urls=repo_urls,
                    )
                    run.judge_report = judge_report
                    run.judge_model = judge_model
                    await _add_event(
                        session,
                        run,
                        event_type="judge_completed",
                        message="Judge evaluation completed.",
                        payload={
                            "model": judge_model,
                            "latency_ms": judge_latency_ms,
                        },
                    )
                except Exception as exc:
                    await _add_event(
                        session,
                        run,
                        event_type="judge_failed",
                        message="Judge evaluation failed; heuristic report used.",
                        payload={"error": str(exc)[:500]},
                    )
            else:
                await _add_event(
                    session,
                    run,
                    event_type="judge_skipped",
                    message="Judge evaluation skipped (no judge API key).",
                    payload={},
                )

            run.status = RunStatus.COMPLETED
            run.finished_at = datetime.now(UTC)

            await _add_event(
                session,
                run,
                event_type="evaluation_completed",
                message="Calculated weighted scorecard and generated report.",
                payload={"score": total_score, "metrics": metric_scores},
                step_index=run.step_count,
            )

            await session.commit()
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            diagnostics = classify_run_failure(str(exc))

            logger.exception("Run %s failed: %s", run_id, diagnostics.summary)

            run.status = RunStatus.FAILED
            run.error_message = diagnostics.summary
            run.finished_at = datetime.now(UTC)
            await _add_event(
                session,
                run,
                event_type="run_failed",
                message=f"Run failed: {diagnostics.summary}",
                payload={
                    "error_summary": diagnostics.summary,
                    "next_action": diagnostics.next_action,
                    "error_raw": diagnostics.raw_error[:2000],
                },
            )
            await session.commit()
