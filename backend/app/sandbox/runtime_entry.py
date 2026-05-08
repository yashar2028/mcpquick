"""Sandbox runtime CLI executed inside the isolated boundary process."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Final

from app.sandbox.contracts import (
    parse_execution_request,
)
from app.sandbox.heuristics import build_heuristic_result
from app.sandbox.mcp_runtime import run_anthropic_with_mcp
from app.sandbox.provider_clients import call_provider


PROVIDER_API_KEY_ENV: Final[str] = "SANDBOX_PROVIDER_API_KEY"


def _build_mcp_repo_configs(
    external_mcp_url: str | None,
    mcp_config: dict[str, object] | None,
) -> list[dict[str, object]]:
    configs: list[dict[str, object]] = []
    if isinstance(mcp_config, dict):
        repos_raw = mcp_config.get("repos")
        if isinstance(repos_raw, list):
            for repo in repos_raw:
                if isinstance(repo, dict) and repo.get("repo_url"):
                    configs.append(repo)

    if configs:
        return configs

    if external_mcp_url:
        server_path = "server.json"
        env = {}
        headers = {}
        if isinstance(mcp_config, dict):
            server_path = str(mcp_config.get("server_path") or "server.json")
            env = mcp_config.get("env", {})
            headers = mcp_config.get("headers", {})
        configs.append(
            {
                "repo_url": external_mcp_url,
                "server_path": server_path,
                "env": env,
                "headers": headers,
            }
        )

    return configs


def main() -> int:
    """Execute one sandbox request file and emit a validated result payload.

    This function is intentionally small because it runs inside the isolated
    sandbox process boundary. Control-plane orchestration and persistence are
    handled outside this runtime.
    """
    parser = argparse.ArgumentParser(description="Run sandbox task in Nix boundary")
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    request_payload = json.loads(args.request.read_text(encoding="utf-8"))
    request = parse_execution_request(request_payload)

    provider_api_key = os.environ.get(PROVIDER_API_KEY_ENV)

    if not provider_api_key:
        raise RuntimeError("provider API key was not provided to sandbox runtime")

    provider_result = None
    mcp_config = request.mcp_config if isinstance(request.mcp_config, dict) else {}
    mcp_failure_policy = str(mcp_config.get("failure_policy", "fail")).lower()
    mcp_repos = _build_mcp_repo_configs(request.external_mcp_url, mcp_config)

    if mcp_repos:
        if request.provider != "anthropic":
            raise RuntimeError(
                "MCP tool calling is only supported for Anthropic currently."
            )

        try:
            provider_result = asyncio.run(
                run_anthropic_with_mcp(
                    prompt=request.prompt,
                    model=request.model,
                    api_key=provider_api_key,
                    repo_configs=mcp_repos,
                    max_steps=request.max_steps,
                    run_dir=args.request.parent,
                )
            )
        except Exception:
            if mcp_failure_policy != "continue":
                raise
            provider_result = None

    if provider_result is None:
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
        has_external_mcp=bool(mcp_repos),
    )

    args.output.write_text(
        json.dumps(result.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8"
    )
    return 0


if (
    __name__ == "__main__"
):  # This file is executed inside the sandbox, entry being the main()
    raise SystemExit(main())
