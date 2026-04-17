"""Service layer adapter that bridges run worker and sandbox boundary runner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.sandbox.contracts import SandboxExecutionRequest
from app.sandbox.nix_runner import NixSandboxRunner, NixSandboxRunnerConfig


@dataclass(slots=True)
class SandboxRunRequest:
    """Worker-facing input contract for sandbox execution."""

    run_id: str
    prompt: str
    provider: str
    model: str
    api_key: str
    max_steps: int
    external_mcp_url: str | None


@dataclass(slots=True)
class SandboxRunResult:
    """Worker-facing output contract produced by sandbox execution."""

    step_count: int
    token_input: int
    token_output: int
    latency_ms: int
    metrics: dict[str, float]


class SandboxAdapter(Protocol):
    """Protocol for pluggable sandbox implementations."""

    async def execute(self, request: SandboxRunRequest) -> SandboxRunResult: ...


class NixSandboxAdapter:
    """Adapter backed by a Nix sandbox process boundary."""

    def __init__(self) -> None:
        backend_root = Path(__file__).resolve().parents[2]
        runs_base_dir = (backend_root / settings.SANDBOX_RUN_BASE_DIR).resolve()
        self._runner = NixSandboxRunner(
            NixSandboxRunnerConfig(
                backend_workdir=backend_root,
                runs_base_dir=runs_base_dir,
                command_prefix=settings.SANDBOX_COMMAND_PREFIX,
                nix_binary=settings.SANDBOX_NIX_BINARY,
                nix_flake_ref=settings.SANDBOX_NIX_FLAKE_REF,
                runtime_module=settings.SANDBOX_RUNTIME_MODULE,
                timeout_seconds=settings.SANDBOX_TIMEOUT_SECONDS,
                allow_local_fallback=settings.SANDBOX_ALLOW_LOCAL_FALLBACK,
                local_python_binary=settings.SANDBOX_LOCAL_PYTHON_BINARY,
            )
        )

    async def execute(self, request: SandboxRunRequest) -> SandboxRunResult:
        """Execute a run in Nix boundary and map to worker-facing result type."""
        execution_result = await self._runner.run(
            SandboxExecutionRequest(
                run_id=request.run_id,
                prompt=request.prompt,
                provider=request.provider,
                model=request.model,
                max_steps=request.max_steps,
                external_mcp_url=request.external_mcp_url,
            ),
            provider_api_key=request.api_key,
        )

        return SandboxRunResult(
            step_count=execution_result.step_count,
            token_input=execution_result.token_input,
            token_output=execution_result.token_output,
            latency_ms=execution_result.latency_ms,
            metrics=execution_result.metrics,
        )


def get_sandbox_adapter() -> SandboxAdapter:
    """Return the default sandbox adapter used by worker execution."""
    return NixSandboxAdapter()
