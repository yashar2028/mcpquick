"""Run failure classification helpers.

This module converts raw runtime exceptions into user-facing summaries and
next-action guidance that can be persisted to run metadata and events.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


STATUS_SUMMARIES: dict[str, str] = {
    "401": "Provider authentication failed (401). Check API key validity.",
    "403": "Provider request was forbidden (403). Check project permissions.",
    "404": "Requested provider model was not found. Use a supported model name.",
    "429": "Provider quota/rate limit exceeded (429). Check billing or wait and retry.",
}

STATUS_ACTIONS: dict[str, str] = {
    "status 401": "Use a valid API key and retry the run.",
    "status 429": "Check provider quota/billing, then retry after quota is available.",
}


@dataclass(frozen=True, slots=True)
class RunFailureDiagnostics:
    """Structured failure diagnostics persisted for failed runs."""

    summary: str
    next_action: str
    raw_error: str


def _build_error_summary(error_text: str) -> str:
    """Build a concise user-facing summary from raw runtime error text."""
    lowered = error_text.lower()

    # Status extraction is regex-based because upstream SDK and HTTP errors are
    # not uniform across providers and transports.
    status_match = re.search(r"status\s+(\d{3})", lowered)
    status_code = status_match.group(1) if status_match else None

    summary = STATUS_SUMMARIES.get(status_code or "")
    if summary:
        return summary

    if "timed out" in lowered:
        return "Sandbox execution timed out. Increase timeout or reduce request size."

    return (
        "Sandbox execution failed. Inspect stderr logs for detailed provider response."
    )


def _build_next_action(error_text: str) -> str:
    """Suggest one concrete next action based on the detected failure pattern."""
    lowered = error_text.lower()

    if "status 401" in lowered:
        return STATUS_ACTIONS["status 401"]
    if "status 404" in lowered and "model" in lowered:
        return "Switch to a model listed for your provider account and retry."
    if "status 429" in lowered:
        return STATUS_ACTIONS["status 429"]
    if "timed out" in lowered:
        return "Increase SANDBOX_TIMEOUT_SECONDS and try a shorter prompt."

    return "Open /v1/runs/{run_id}/logs and inspect stderr_tail for full context."


def classify_run_failure(error_text: str) -> RunFailureDiagnostics:
    """Classify a raw failure string into structured diagnostics."""
    return RunFailureDiagnostics(
        summary=_build_error_summary(error_text),
        next_action=_build_next_action(error_text),
        raw_error=error_text,
    )
