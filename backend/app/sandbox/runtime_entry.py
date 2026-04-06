"""Sandbox runtime entrypoint executed inside Nix boundary.

This script is intentionally simple and deterministic for now. It consumes the
request payload and emits a typed result payload to disk.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Final

from app.sandbox.contracts import (
    SandboxExecutionResult,
    parse_execution_request,
)


DEFAULT_LATENCY_MS: Final[int] = 2400


def _build_result(
    prompt: str, max_steps: int, has_external_mcp: bool
) -> SandboxExecutionResult:
    """Build deterministic placeholder metrics from request properties."""
    step_efficiency = max(0.3, min(1.0, 1.0 - (max_steps / 300)))
    tool_correctness = 0.82 if has_external_mcp else 0.8

    return SandboxExecutionResult(
        step_count=max(1, min(max_steps, 5)),
        token_input=max(100, len(prompt) * 2),
        token_output=max(120, len(prompt) // 2),
        latency_ms=DEFAULT_LATENCY_MS,
        metrics={
            "task_success": 0.74,
            "tool_correctness": tool_correctness,
            "latency_efficiency": 0.76,
            "cost_efficiency": 0.71,
            "step_efficiency": step_efficiency,
            "reliability_recovery": 0.83,
        },
    )


def main() -> int:
    """CLI entrypoint used by Nix runner command."""
    parser = argparse.ArgumentParser(description="Run sandbox task in Nix boundary")
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    request_payload = json.loads(args.request.read_text(encoding="utf-8"))
    request = parse_execution_request(request_payload)

    # Placeholder execution time to simulate isolated workload runtime.
    time.sleep(0.15)

    result = _build_result(
        prompt=request.prompt,
        max_steps=request.max_steps,
        has_external_mcp=bool(request.external_mcp_url),
    )

    args.output.write_text(
        json.dumps(result.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
