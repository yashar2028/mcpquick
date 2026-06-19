from __future__ import annotations

"""Prompt construction helpers that keep instruction files separate from user prompt text."""

from collections.abc import Sequence
from typing import Any

from app.models.run import RunInstructionFile


def build_instruction_file_metadata(
    instruction_files: Sequence[RunInstructionFile],
) -> list[dict[str, Any]]:
    """Return serialized metadata for timeline and judge payloads."""
    ordered = sorted(instruction_files, key=lambda item: item.upload_order)
    return [
        {
            "id": item.id,
            "filename": item.filename,
            "size_bytes": item.size_bytes,
            "content_sha256": item.content_sha256,
            "upload_order": item.upload_order,
        }
        for item in ordered
    ]


def build_execution_prompt(
    user_prompt: str,
    instruction_files: Sequence[RunInstructionFile],
) -> str:
    """Build the final prompt sent to the model with an instruction-file section."""
    ordered = sorted(instruction_files, key=lambda item: item.upload_order)
    if not ordered:
        return user_prompt

    sections = [
        "## Instruction Files",
        "The following instruction files are provided in upload order.",
    ]

    for item in ordered:
        sections.extend(
            [
                "",
                f"### File {item.upload_order + 1}: {item.filename}",
                item.content,
            ]
        )

    sections.extend(["", "## User Prompt", user_prompt])
    return "\n".join(sections)
