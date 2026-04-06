"""Nix process boundary runner for sandbox execution.

The control-plane writes request.json, executes a dedicated process inside a
Nix development shell, then reads/validates result.json.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from app.sandbox.contracts import (
    SandboxExecutionRequest,
    SandboxExecutionResult,
    parse_execution_result,
)


MAX_LOG_CHARS: Final[int] = 4000


class SandboxBoundaryError(RuntimeError):
    """Raised when sandbox boundary setup/execution/validation fails."""

    pass


@dataclass(frozen=True, slots=True)
class NixSandboxRunnerConfig:
    """Configuration required to execute one run in a Nix shell."""

    backend_workdir: Path
    runs_base_dir: Path
    command_prefix: str
    nix_binary: str
    nix_flake_ref: str
    runtime_module: str
    timeout_seconds: int
    allow_local_fallback: bool
    local_python_binary: str


class NixSandboxRunner:
    """Executes sandbox runtime using external Nix shell process."""

    def __init__(self, config: NixSandboxRunnerConfig):
        self._config = config

    async def run(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        """Run one sandbox task and return validated typed result."""
        run_dir = self._config.runs_base_dir / request.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        request_file = run_dir / "request.json"
        result_file = run_dir / "result.json"
        stdout_file = run_dir / "stdout.log"
        stderr_file = run_dir / "stderr.log"

        request_file.write_text(
            json.dumps(request.to_dict(), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

        command_prefix = [
            token for token in self._config.command_prefix.split() if token
        ]
        nix_command = [
            *command_prefix,
            self._config.nix_binary,
            "--extra-experimental-features",
            "nix-command flakes",
            "develop",
            self._config.nix_flake_ref,
            "--command",
            "python",
            "-m",
            self._config.runtime_module,
            "--request",
            str(request_file),
            "--output",
            str(result_file),
        ]

        local_command = [
            self._config.local_python_binary,
            "-m",
            self._config.runtime_module,
            "--request",
            str(request_file),
            "--output",
            str(result_file),
        ]

        fallback_used = False
        fallback_note = ""

        try:
            process = await self._spawn_process(nix_command)
        except FileNotFoundError as exc:
            if not self._config.allow_local_fallback:
                raise SandboxBoundaryError(
                    "Sandbox launcher command was not found in PATH: "
                    f"{nix_command[0]}"
                ) from exc

            try:
                process = await self._spawn_process(local_command)
            except FileNotFoundError as local_exc:
                raise SandboxBoundaryError(
                    "Both nix launcher and local fallback launcher were not found. "
                    f"missing: {nix_command[0]}, {local_command[0]}"
                ) from local_exc
            fallback_used = True
            fallback_note = "nix launcher unavailable; local fallback was used\n"
        except Exception:
            raise SandboxBoundaryError("Failed to start sandbox process")

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self._config.timeout_seconds
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise SandboxBoundaryError(
                f"Sandbox timed out after {self._config.timeout_seconds} seconds"
            ) from exc

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        if fallback_used:
            stderr_text = fallback_note + stderr_text
        stdout_file.write_text(stdout_text, encoding="utf-8")
        stderr_file.write_text(stderr_text, encoding="utf-8")

        if process.returncode != 0:
            raise SandboxBoundaryError(
                "Nix sandbox process failed with exit code "
                f"{process.returncode}. stderr={_trim(stderr_text)}"
            )

        if not result_file.exists():
            raise SandboxBoundaryError(
                "Sandbox process completed without producing result.json"
            )

        try:
            payload = json.loads(result_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SandboxBoundaryError("Sandbox result.json is not valid JSON") from exc

        try:
            return parse_execution_result(payload)
        except ValueError as exc:
            raise SandboxBoundaryError(
                f"Sandbox returned invalid result shape: {exc}"
            ) from exc

    async def _spawn_process(self, command: list[str]) -> asyncio.subprocess.Process:
        """Spawn a subprocess for sandbox execution command."""
        return await asyncio.create_subprocess_exec(
            *command,
            cwd=str(self._config.backend_workdir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )


def _trim(value: str) -> str:
    """Trim long stderr/stdout output for safe exception messages."""
    if len(value) <= MAX_LOG_CHARS:
        return value
    return value[:MAX_LOG_CHARS] + "..."
