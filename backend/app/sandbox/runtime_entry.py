"""Sandbox runtime CLI executed inside the isolated boundary process."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Final

from app.sandbox.contracts import (
    parse_execution_request,
)
from app.sandbox.heuristics import build_heuristic_result
from app.sandbox.provider_clients import call_provider


PROVIDER_API_KEY_ENV: Final[str] = "SANDBOX_PROVIDER_API_KEY"


def main() -> int:
    """CLI entrypoint used by Nix runner command."""
    parser = argparse.ArgumentParser(description="Run sandbox task in Nix boundary")
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    request_payload = json.loads(args.request.read_text(encoding="utf-8"))
    request = parse_execution_request(request_payload)

    provider_api_key = os.environ.get(PROVIDER_API_KEY_ENV)

    if not provider_api_key:
        raise RuntimeError("provider API key was not provided to sandbox runtime")

    provider_result = call_provider(
        prompt=request.prompt,
        provider=request.provider,
        model=request.model,
        api_key=provider_api_key,
    )

    result = build_heuristic_result(
        prompt=request.prompt,
        output_text=provider_result.output_text,
        token_input=provider_result.token_input,
        token_output=provider_result.token_output,
        latency_ms=provider_result.latency_ms,
        max_steps=request.max_steps,
        has_external_mcp=bool(request.external_mcp_url),
    )

    args.output.write_text(
        json.dumps(result.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
