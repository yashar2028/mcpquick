"""Shared helpers for extracting text from provider content blocks."""

from __future__ import annotations


def blocks_to_text(blocks: object, *, empty_value: str) -> str:
    if not isinstance(blocks, list):
        return empty_value

    parts: list[str] = []
    for block in blocks:
        if isinstance(block, dict):
            if block.get("type") != "text":
                continue
            text = block.get("text")
            if isinstance(text, str) and text:
                parts.append(text)
            continue

        block_type = getattr(block, "type", None)
        block_text = getattr(block, "text", None)
        if block_type == "text" and isinstance(block_text, str) and block_text:
            parts.append(block_text)

    text = "\n".join(parts).strip()
    return text if text else empty_value
