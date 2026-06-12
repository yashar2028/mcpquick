from __future__ import annotations

import json
import time
from typing import Any

from app.core.config import settings
from app.sandbox.provider_clients import _ensure_anthropic_client
from app.sandbox.text_blocks import blocks_to_text

MAX_JUDGE_TOKENS = 800
MAX_TOOL_INPUT_CHARS = 500
MAX_TOOL_TRACE_ITEMS = 12
MAX_OUTPUT_CHARS = 4000


def _truncate_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3] + "..."


def _summarize_input(value: object) -> str:
    if isinstance(value, str):
        return _truncate_text(value, MAX_TOOL_INPUT_CHARS)
    try:
        encoded = json.dumps(value, ensure_ascii=True)
    except TypeError:
        encoded = str(value)
    return _truncate_text(encoded, MAX_TOOL_INPUT_CHARS)


def _format_tool_trace(tool_trace: list[dict[str, object]]) -> list[dict[str, str]]:
    formatted: list[dict[str, str]] = []
    for entry in tool_trace[:MAX_TOOL_TRACE_ITEMS]:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        formatted.append(
            {
                "name": name,
                "input_summary": _summarize_input(entry.get("input")),
            }
        )
    return formatted


def _build_prompt(
    prompt: str,
    output_text: str,
    tool_trace: list[dict[str, object]],
    repo_urls: list[str],
) -> str:
    tools_payload = _format_tool_trace(tool_trace)
    tool_text = json.dumps(tools_payload, ensure_ascii=True)
    repo_text = ", ".join(repo_urls) if repo_urls else "(none)"
    truncated_output = _truncate_text(output_text, MAX_OUTPUT_CHARS)

    return (
        "You are a judge model. Review the run and return JSON only with keys: "
        "achieved (boolean), summary (string), tools_used (array of {name, input_summary}), "
        "notes (string, optional). Do not include extra keys.\n\n"
        f"Run prompt:\n{prompt}\n\n"
        f"Model output:\n{truncated_output}\n\n"
        f"MCP repos: {repo_text}\n\n"
        f"Tool usage (name + input summary JSON):\n{tool_text}\n"
    )


def run_judge(
    prompt: str,
    output_text: str,
    tool_trace: list[dict[str, object]],
    repo_urls: list[str],
) -> tuple[dict[str, Any], str, int]:
    """Run the Anthropic judge model and return (report, model, latency_ms)."""
    api_key = settings.JUDGE_ANTHROPIC_API_KEY
    if not api_key:
        raise RuntimeError("Judge API key is not configured")

    model = settings.JUDGE_ANTHROPIC_MODEL
    Anthropic = _ensure_anthropic_client()
    client = Anthropic(api_key=api_key)

    started = time.perf_counter()
    response = client.messages.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": _build_prompt(prompt, output_text, tool_trace, repo_urls),
            }
        ],
        temperature=0,
        max_tokens=MAX_JUDGE_TOKENS,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    text = blocks_to_text(getattr(response, "content", []), empty_value="")
    try:
        report = json.loads(text)
        if not isinstance(report, dict):
            report = {"raw": text}
    except json.JSONDecodeError:
        report = {"raw": text}

    return report, model, latency_ms
