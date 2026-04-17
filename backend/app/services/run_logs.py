"""Helpers for reading per-run sandbox log tails."""

from __future__ import annotations

from pathlib import Path


DEFAULT_MAX_LOG_TAIL_CHARS = 5000


def _tail_text(file_path: Path, max_chars: int) -> str | None:
    if not file_path.exists() or not file_path.is_file():
        return None

    content = file_path.read_text(encoding="utf-8", errors="replace")
    if len(content) <= max_chars:
        return content
    return content[-max_chars:]


def read_run_log_tails(
    backend_root: Path,
    runs_base_dir: str,
    run_id: str,
    max_chars: int = DEFAULT_MAX_LOG_TAIL_CHARS,
) -> tuple[str | None, str | None]:
    """Return stdout/stderr log tails for one run id."""
    run_dir = (backend_root / runs_base_dir / run_id).resolve()
    stdout_tail = _tail_text(run_dir / "stdout.log", max_chars=max_chars)
    stderr_tail = _tail_text(run_dir / "stderr.log", max_chars=max_chars)
    return stdout_tail, stderr_tail
