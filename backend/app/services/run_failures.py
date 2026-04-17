"""Run failure classification helpers.

This module converts raw runtime exceptions into user-facing summaries and
next-action guidance that can be persisted to run metadata and events.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RunFailureDiagnostics:
    """Structured failure diagnostics persisted for failed runs."""

    summary: str
    next_action: str
    raw_error: str


def _build_error_summary(error_text: str) -> str:
    lowered = error_text.lower()

    status_match = re.search(r"status\s+(\d{3})", lowered)
    status_code = status_match.group(1) if status_match else None

    if status_code == "401":
        return "Provider authentication failed (401). Check API key validity."
    if status_code == "403":
        return "Provider request was forbidden (403). Check project permissions."
    if status_code == "404":
        return "Requested provider model was not found. Use a supported model name."
    if status_code == "429":
        return (
            "Provider quota/rate limit exceeded (429). Check billing or wait and retry."
        )

    if "timed out" in lowered:
        return "Sandbox execution timed out. Increase timeout or reduce request size."

    return (
        "Sandbox execution failed. Inspect stderr logs for detailed provider response."
    )


def _build_next_action(error_text: str) -> str:
    lowered = error_text.lower()

    if "status 401" in lowered:
        return "Use a valid API key and retry the run."
    if "status 404" in lowered and "model" in lowered:
        return "Switch to a model listed for your provider account and retry."
    if "status 429" in lowered:
        return "Check provider quota/billing, then retry after quota is available."
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
