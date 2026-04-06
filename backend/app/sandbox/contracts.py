"""Typed contracts shared between control-plane and sandbox runtime process."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class SandboxExecutionRequest:
    """Serialized request payload written by control-plane for sandbox runtime."""

    run_id: str
    prompt: str
    provider: str
    model: str
    max_steps: int
    external_mcp_url: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert request model to JSON-serializable mapping."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SandboxExecutionResult:
    """Serialized result payload emitted by sandbox runtime process."""

    step_count: int
    token_input: int
    token_output: int
    latency_ms: int
    metrics: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        """Convert result model to JSON-serializable mapping."""
        return asdict(self)


def parse_execution_request(data: Mapping[str, Any]) -> SandboxExecutionRequest:
    """Validate and parse raw JSON mapping into a request contract."""
    run_id = _require_str(data, "run_id")
    prompt = _require_str(data, "prompt")
    provider = _require_str(data, "provider")
    model = _require_str(data, "model")
    max_steps = _require_int(data, "max_steps", minimum=1)

    external_mcp_url_raw = data.get("external_mcp_url")
    external_mcp_url: str | None
    if external_mcp_url_raw is None:
        external_mcp_url = None
    elif isinstance(external_mcp_url_raw, str):
        external_mcp_url = external_mcp_url_raw
    else:
        raise ValueError("external_mcp_url must be a string or null")

    return SandboxExecutionRequest(
        run_id=run_id,
        prompt=prompt,
        provider=provider,
        model=model,
        max_steps=max_steps,
        external_mcp_url=external_mcp_url,
    )


def parse_execution_result(data: Mapping[str, Any]) -> SandboxExecutionResult:
    """Validate and parse raw JSON mapping into a result contract."""
    step_count = _require_int(data, "step_count", minimum=1)
    token_input = _require_int(data, "token_input", minimum=0)
    token_output = _require_int(data, "token_output", minimum=0)
    latency_ms = _require_int(data, "latency_ms", minimum=0)

    metrics_raw = data.get("metrics")
    if not isinstance(metrics_raw, Mapping):
        raise ValueError("metrics must be an object")

    metrics: dict[str, float] = {}
    for key, value in metrics_raw.items():
        if not isinstance(key, str) or not key:
            raise ValueError("metrics keys must be non-empty strings")
        if not isinstance(value, (int, float)):
            raise ValueError(f"metrics[{key}] must be numeric")

        metric = float(value)
        if metric < 0.0 or metric > 1.0:
            raise ValueError(f"metrics[{key}] must be between 0.0 and 1.0")
        metrics[key] = metric

    return SandboxExecutionResult(
        step_count=step_count,
        token_input=token_input,
        token_output=token_output,
        latency_ms=latency_ms,
        metrics=metrics,
    )


def _require_str(data: Mapping[str, Any], key: str) -> str:
    """Require non-empty string value by key."""
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _require_int(data: Mapping[str, Any], key: str, minimum: int) -> int:
    """Require integer value by key and enforce minimum bound."""
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    if value < minimum:
        raise ValueError(f"{key} must be >= {minimum}")
    return value
