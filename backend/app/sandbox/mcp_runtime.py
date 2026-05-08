"""Minimal MCP repo runner for Anthropic tool calling in sandbox."""

from __future__ import annotations

from contextlib import AsyncExitStack
import hashlib
import ipaddress
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.sandbox.provider_clients import (
    MAX_OUTPUT_TOKENS,
    ProviderCallResult,
    _blocks_to_text,
)

MAX_TOOL_CALLS = 3
TOKEN_ESTIMATE_DIVISOR = 4


@dataclass(frozen=True, slots=True)
class McpServerConfig:
    name: str
    transport: str
    command: str
    args: list[str]
    env: dict[str, str]
    url: str | None = None
    headers: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class McpClientImports:
    ClientSession: type
    StdioServerParameters: type
    stdio_client: Any
    StreamableHttpServerParameters: type | None
    streamable_http_client: Any | None


def _sanitize_tool_name(value: str) -> str:
    if not value:
        return "tool"
    cleaned = []
    for char in value:
        if char.isalnum() or char in {"_", "-"}:
            cleaned.append(char)
        else:
            cleaned.append("_")
    normalized = "".join(cleaned).strip("_")
    return normalized or "tool"


def _unique_name(base: str, used: set[str]) -> str:
    if base not in used:
        used.add(base)
        return base
    index = 2
    while f"{base}_{index}" in used:
        index += 1
    name = f"{base}_{index}"
    used.add(name)
    return name


def _make_tool_key(server_name: str, tool_name: str, used: set[str]) -> str:
    base = f"{server_name}__{tool_name}"
    key = _sanitize_tool_name(base)
    if len(key) > 64:
        digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:8]
        key = _sanitize_tool_name(f"{server_name}__{digest}")
    key = key[:64]
    return _unique_name(key, used)


def _sanitize_repo_dir_name(repo_url: str) -> str:
    name = repo_url.rstrip("/").split("/")[-1] or "repo"
    cleaned = []
    for char in name:
        if char.isalnum() or char in {"_", "-"}:
            cleaned.append(char)
        else:
            cleaned.append("_")
    return "".join(cleaned) or "repo"


def _merge_env_overrides(env_overrides: dict[str, str]) -> dict[str, str]:
    merged_env: dict[str, str] = {**os.environ}
    for key, value in env_overrides.items():
        if isinstance(key, str) and isinstance(value, str):
            merged_env[key] = value
    return merged_env


def _validate_remote_url(raw_url: str) -> None:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError("Remote MCP url must use http or https")
    hostname = parsed.hostname or ""
    if not hostname:
        raise RuntimeError("Remote MCP url must include a hostname")
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Remote MCP url must be a public host")
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise RuntimeError("Remote MCP url must be a public host")
    except ValueError:
        pass


def _extract_required_keys(raw_items: object, label: str) -> list[str]:
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        raise RuntimeError(f"server.json {label} must be a list")

    required: list[str] = []
    for entry in raw_items:
        if isinstance(entry, str):
            if entry:
                required.append(entry)
            continue
        if isinstance(entry, dict):
            name = (
                entry.get("name")
                or entry.get("key")
                or entry.get("env")
                or entry.get("header")
            )
            required_flag = entry.get("isRequired")
            if required_flag is None:
                required_flag = entry.get("required", True)
            if isinstance(required_flag, bool) and not required_flag:
                continue
            if isinstance(name, str) and name:
                required.append(name)
                continue
            raise RuntimeError(f"server.json {label} entries must include a name")
        raise RuntimeError(f"server.json {label} entries must be strings or objects")
    return required


def _extract_required_env_vars(package: dict[str, Any]) -> list[str]:
    return _extract_required_keys(
        package.get("environmentVariables"), "environmentVariables"
    )


def _extract_required_headers(remote: dict[str, Any]) -> list[str]:
    return _extract_required_keys(remote.get("headers"), "headers")


def _extract_stdio_package(payload: dict[str, Any]) -> dict[str, Any] | None:
    packages = payload.get("packages")
    if packages is None:
        return None
    if not isinstance(packages, list) or not packages:
        raise RuntimeError("server.json packages must be a non-empty list")

    for package in packages:
        if not isinstance(package, dict):
            continue
        registry = package.get("registryType")
        transport = package.get("transport")
        transport_type = transport.get("type") if isinstance(transport, dict) else None
        if registry == "npm" and transport_type == "stdio":
            return package
    return None


def _extract_remote(payload: dict[str, Any]) -> dict[str, Any] | None:
    remotes = payload.get("remotes")
    if remotes is None:
        return None
    if not isinstance(remotes, list) or not remotes:
        raise RuntimeError("server.json remotes must be a non-empty list")

    for remote in remotes:
        if not isinstance(remote, dict):
            continue
        remote_type = remote.get("type")
        if remote_type is None or remote_type in {"streamable-http", "streamable_http"}:
            return remote
    return None


def prepare_mcp_repo(
    repo_url: str,
    run_dir: Path,
    server_path: str,
    env_overrides: dict[str, str],
    header_overrides: dict[str, str],
    repo_index: int,
) -> McpServerConfig:
    """Clone MCP repo and read validated server.json config."""
    if (
        server_path.startswith("/")
        or server_path.startswith("\\")
        or ".." in server_path
    ):
        raise RuntimeError("server.json path must be a relative path")

    repo_dir = run_dir / f"mcp_repo_{repo_index}_{_sanitize_repo_dir_name(repo_url)}"
    if repo_dir.exists():
        shutil.rmtree(repo_dir, ignore_errors=True)

    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(repo_dir)],
        check=True,
        capture_output=True,
        text=True,
    )

    server_json = repo_dir / server_path
    if not server_json.exists():
        candidates = [path for path in repo_dir.rglob("server.json") if path.is_file()]
        if len(candidates) == 1:
            server_json = candidates[0]
        elif not candidates:
            raise RuntimeError("server.json not found in MCP repo")
        else:
            raise RuntimeError(
                "Multiple server.json files found; please set the server.json path explicitly."
            )

    payload = json.loads(server_json.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("server.json must be a JSON object")

    server_name = payload.get("name")
    if not isinstance(server_name, str) or not server_name:
        server_name = _sanitize_repo_dir_name(repo_url)
    server_name = _sanitize_tool_name(server_name)

    package = _extract_stdio_package(payload)
    remote = _extract_remote(payload)
    if package and remote:
        raise RuntimeError(
            "server.json must define either packages or remotes, not both"
        )
    if not package and not remote:
        raise RuntimeError("server.json must include packages or remotes")

    if package:
        identifier = package.get("identifier")
        if not isinstance(identifier, str) or not identifier:
            raise RuntimeError("server.json package identifier must be a string")
        version = package.get("version")
        package_ref = identifier
        if isinstance(version, str) and version:
            package_ref = f"{identifier}@{version}"

        required_env = _extract_required_env_vars(package)
        merged_env = _merge_env_overrides(env_overrides)
        missing = [name for name in required_env if name not in merged_env]
        if missing:
            missing_list = ", ".join(missing)
            raise RuntimeError(f"Missing required MCP env vars: {missing_list}")

        return McpServerConfig(
            name=server_name,
            transport="stdio",
            command="npx",
            args=["-y", package_ref, "--stdio"],
            env=merged_env,
        )

    if not isinstance(remote, dict):
        raise RuntimeError("server.json remotes must include a streamable-http entry")
    url = remote.get("url")
    if not isinstance(url, str) or not url:
        raise RuntimeError("server.json remote url must be a string")
    _validate_remote_url(url)

    required_headers = _extract_required_headers(remote)
    missing_headers = [
        name for name in required_headers if name not in header_overrides
    ]
    if missing_headers:
        missing_list = ", ".join(missing_headers)
        raise RuntimeError(f"Missing required MCP headers: {missing_list}")

    headers: dict[str, str] = {}
    for key, value in header_overrides.items():
        if isinstance(key, str) and isinstance(value, str):
            headers[key] = value

    return McpServerConfig(
        name=server_name,
        transport="streamable-http",
        command="",
        args=[],
        env={},
        url=url,
        headers=headers,
    )


def _ensure_mcp_imports() -> McpClientImports:
    try:
        from mcp import ClientSession, StdioServerParameters  # type: ignore
        from mcp.client.stdio import stdio_client  # type: ignore

        StreamableHttpServerParameters = None
        streamable_http_client = None
        try:
            from mcp.client.streamable_http import (  # type: ignore
                StreamableHttpServerParameters,
                streamable_http_client,
            )
        except Exception:
            pass

        return McpClientImports(
            ClientSession=ClientSession,
            StdioServerParameters=StdioServerParameters,
            stdio_client=stdio_client,
            StreamableHttpServerParameters=StreamableHttpServerParameters,
            streamable_http_client=streamable_http_client,
        )
    except Exception:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "mcp",
                "--disable-pip-version-check",
                "--no-input",
            ],
            check=True,
        )
        from mcp import ClientSession, StdioServerParameters  # type: ignore
        from mcp.client.stdio import stdio_client  # type: ignore

        StreamableHttpServerParameters = None
        streamable_http_client = None
        try:
            from mcp.client.streamable_http import (  # type: ignore
                StreamableHttpServerParameters,
                streamable_http_client,
            )
        except Exception:
            pass

        return McpClientImports(
            ClientSession=ClientSession,
            StdioServerParameters=StdioServerParameters,
            stdio_client=stdio_client,
            StreamableHttpServerParameters=StreamableHttpServerParameters,
            streamable_http_client=streamable_http_client,
        )


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // TOKEN_ESTIMATE_DIVISOR)


def _tool_result_content(raw: object) -> str:
    if isinstance(raw, str):
        return raw
    return json.dumps(raw, ensure_ascii=True)


def _normalize_content_blocks(content: object) -> list[dict[str, object]]:
    if not isinstance(content, list):
        raise RuntimeError("Anthropic response missing content blocks")

    normalized: list[dict[str, object]] = []
    for block in content:
        if isinstance(block, dict):
            normalized.append(block)
            continue
        model_dump = getattr(block, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump()
            if isinstance(dumped, dict):
                normalized.append(dumped)
                continue
        as_dict = getattr(block, "dict", None)
        if callable(as_dict):
            dumped = as_dict()
            if isinstance(dumped, dict):
                normalized.append(dumped)
                continue

        block_type = getattr(block, "type", None)
        if block_type == "tool_use":
            normalized.append(
                {
                    "type": "tool_use",
                    "id": getattr(block, "id", None),
                    "name": getattr(block, "name", None),
                    "input": getattr(block, "input", None),
                }
            )
            continue
        if block_type == "text":
            normalized.append({"type": "text", "text": getattr(block, "text", "")})
            continue

        normalized.append({"type": "text", "text": str(block)})

    return normalized


def _ensure_anthropic_client():
    try:
        from anthropic import Anthropic  # type: ignore

        return Anthropic
    except ImportError:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "anthropic",
                "--disable-pip-version-check",
                "--no-input",
            ],
            check=True,
        )
        from anthropic import Anthropic  # type: ignore

        return Anthropic


def _call_anthropic(
    prompt_messages: list[dict[str, object]],
    model: str,
    api_key: str,
    tool_defs: list[dict[str, object]],
) -> list[dict[str, object]]:
    Anthropic = _ensure_anthropic_client()
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        messages=prompt_messages,
        temperature=0,
        max_tokens=MAX_OUTPUT_TOKENS,
        tools=tool_defs,
    )
    return _normalize_content_blocks(getattr(response, "content", None))


async def run_anthropic_with_mcp(
    prompt: str,
    model: str,
    api_key: str,
    repo_configs: list[dict[str, Any]],
    max_steps: int,
    run_dir: Path,
) -> ProviderCallResult:
    """Run Anthropic with MCP tools from a repo-backed server.json."""
    started = time.perf_counter()

    if not repo_configs:
        raise RuntimeError("At least one MCP repo is required")

    server_configs: list[McpServerConfig] = []
    for index, repo_config in enumerate(repo_configs, start=1):
        repo_url = repo_config.get("repo_url")
        if not isinstance(repo_url, str) or not repo_url:
            raise RuntimeError("MCP repo url must be a string")
        server_path = repo_config.get("server_path") or "server.json"
        env_overrides = (
            repo_config.get("env") if isinstance(repo_config.get("env"), dict) else {}
        )
        header_overrides = (
            repo_config.get("headers")
            if isinstance(repo_config.get("headers"), dict)
            else {}
        )
        server_configs.append(
            prepare_mcp_repo(
                repo_url=repo_url,
                run_dir=run_dir,
                server_path=str(server_path),
                env_overrides={str(k): str(v) for k, v in env_overrides.items()},
                header_overrides={str(k): str(v) for k, v in header_overrides.items()},
                repo_index=index,
            )
        )

    mcp_imports = _ensure_mcp_imports()

    tool_defs: list[dict[str, object]] = []
    tool_registry: dict[str, tuple[object, str]] = {}
    used_tool_keys: set[str] = set()

    async with AsyncExitStack() as stack:
        sessions: list[tuple[McpServerConfig, object]] = []
        for server_config in server_configs:
            if server_config.transport == "stdio":
                server_params = mcp_imports.StdioServerParameters(
                    command=server_config.command,
                    args=server_config.args,
                    env=server_config.env,
                )
                read, write = await stack.enter_async_context(
                    mcp_imports.stdio_client(server_params)
                )
            elif server_config.transport == "streamable-http":
                if (
                    not mcp_imports.streamable_http_client
                    or not mcp_imports.StreamableHttpServerParameters
                ):
                    raise RuntimeError("MCP streamable-http client not available")
                if not server_config.url:
                    raise RuntimeError("Remote MCP url missing")
                server_params = mcp_imports.StreamableHttpServerParameters(
                    url=server_config.url,
                    headers=server_config.headers,
                )
                read, write = await stack.enter_async_context(
                    mcp_imports.streamable_http_client(server_params)
                )
            else:
                raise RuntimeError("Unsupported MCP transport")

            session = await stack.enter_async_context(
                mcp_imports.ClientSession(read, write)
            )
            await session.initialize()
            sessions.append((server_config, session))

        for server_config, session in sessions:
            tool_response = await session.list_tools()
            tools = tool_response.tools
            for tool in tools:
                tool_name = getattr(tool, "name", None)
                if not isinstance(tool_name, str):
                    continue
                tool_key = _make_tool_key(server_config.name, tool_name, used_tool_keys)
                tool_registry[tool_key] = (session, tool_name)
                description = getattr(tool, "description", "")
                if description:
                    description = f"[{server_config.name}] {description}"
                else:
                    description = f"[{server_config.name}]"
                tool_defs.append(
                    {
                        "name": tool_key,
                        "description": description,
                        "input_schema": getattr(tool, "inputSchema", {}),
                    }
                )

        messages: list[dict[str, object]] = [{"role": "user", "content": prompt}]
        max_tool_calls = max(1, min(MAX_TOOL_CALLS, max_steps))

        for _ in range(max_tool_calls):
            content = _call_anthropic(messages, model, api_key, tool_defs)

            tool_calls = [
                block
                for block in content
                if isinstance(block, dict) and block.get("type") == "tool_use"
            ]

            if not tool_calls:
                output_text = _blocks_to_text(content)
                latency_ms = int((time.perf_counter() - started) * 1000)
                return ProviderCallResult(
                    output_text=output_text,
                    token_input=_estimate_tokens(prompt),
                    token_output=_estimate_tokens(output_text),
                    latency_ms=latency_ms,
                )

            messages.append({"role": "assistant", "content": content})

            for tool_call in tool_calls:
                tool_key = tool_call.get("name")
                tool_args = tool_call.get("input")
                tool_id = tool_call.get("id")
                if not isinstance(tool_key, str) or not tool_id:
                    raise RuntimeError("Invalid tool call shape")

                registry_entry = tool_registry.get(tool_key)
                if not registry_entry:
                    raise RuntimeError("Unknown MCP tool requested")
                session, tool_name = registry_entry

                result = await session.call_tool(tool_name, tool_args or {})
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": _tool_result_content(result.content),
                            }
                        ],
                    }
                )

        content = _call_anthropic(messages, model, api_key, tool_defs)
        output_text = _blocks_to_text(content) if isinstance(content, list) else ""
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ProviderCallResult(
            output_text=output_text,
            token_input=_estimate_tokens(prompt),
            token_output=_estimate_tokens(output_text),
            latency_ms=latency_ms,
        )
