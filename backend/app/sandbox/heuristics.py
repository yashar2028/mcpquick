"""Deterministic heuristic evaluation logic for sandbox execution."""

from __future__ import annotations

from app.sandbox.contracts import SandboxExecutionResult


def _clamp(value: float) -> float:
    """Clamp a metric-like value into the inclusive [0.0, 1.0] range."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def build_heuristic_result(
    prompt: str,
    output_text: str,
    token_input: int,
    token_output: int,
    latency_ms: int,
    max_steps: int,
    has_external_mcp: bool,
    tool_trace: list[dict[str, object]] | None = None,
) -> SandboxExecutionResult:
    """Build deterministic heuristic metrics from provider call output."""
    normalized_prompt_len = max(1, len(prompt))
    normalized_output_len = len(output_text.strip())
    total_tokens = max(token_input + token_output, 1)

    # Deterministic metric construction for non-judge evaluation:
    # - task_success: penalize very short/likely-refusal outputs
    # - tool_correctness: slightly stricter when external MCP is enabled
    # - latency/cost efficiency: normalized penalties with bounded caps
    # - step_efficiency: small reward for having room to reason across steps
    # - reliability_recovery: verbosity proxy relative to prompt size
    task_success = 0.45 if normalized_output_len < 20 else 0.9
    text_lc = output_text.lower()
    if "unable" in text_lc or "i can't" in text_lc or "i cannot" in text_lc:
        task_success = min(task_success, 0.4)

    tool_correctness = 0.62 if has_external_mcp else 0.75
    latency_efficiency = _clamp(1.0 - (latency_ms / 12000.0))
    cost_efficiency = _clamp(1.0 - (max(total_tokens - 600, 0) / 5000.0))
    step_efficiency = _clamp(1.0 - (1.0 / max(max_steps, 1)) * 0.25)

    verbosity_factor = _clamp((normalized_output_len / normalized_prompt_len) * 0.8)
    reliability_recovery = _clamp(0.55 + 0.35 * verbosity_factor)

    return SandboxExecutionResult(
        step_count=1,
        token_input=token_input,
        token_output=token_output,
        latency_ms=latency_ms,
        output_text=output_text,
        tool_trace=tool_trace or [],
        metrics={
            "task_success": task_success,
            "tool_correctness": tool_correctness,
            "latency_efficiency": latency_efficiency,
            "cost_efficiency": cost_efficiency,
            "step_efficiency": step_efficiency,
            "reliability_recovery": reliability_recovery,
        },
    )
