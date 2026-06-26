"""Metric helper utilities shared across services."""

from __future__ import annotations


def clamp01(value: float) -> float:
    """Clamp value into the inclusive [0.0, 1.0] range."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value
