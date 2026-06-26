"""HTTP helpers for provider API requests used by sandbox runtime."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


class ProviderHttpError(RuntimeError):
    """Raised when provider HTTP request returns non-2xx response."""

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(
            f"provider API request failed with status {status_code}: {body[:300]}"
        )


def post_json(
    url: str,
    payload: dict[str, object],
    headers: dict[str, str],
    timeout_seconds: int,
) -> tuple[dict[str, object], int]:
    """POST JSON and return parsed payload plus request latency in ms."""
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")

    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise ProviderHttpError(exc.code, error_body) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"provider API request failed: {exc.reason}") from exc

    latency_ms = int((time.perf_counter() - started) * 1000)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("provider API returned invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("provider API returned unexpected payload type")

    return parsed, latency_ms


def get_json(
    url: str,
    headers: dict[str, str],
    timeout_seconds: int,
) -> dict[str, object]:
    """GET JSON and return parsed response payload."""
    request = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ProviderHttpError(exc.code, body) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"provider API request failed: {exc.reason}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("provider API returned invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("provider API returned unexpected payload type")

    return parsed
