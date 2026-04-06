from __future__ import annotations

from typing import Mapping


def _clamp_metric(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def compute_weighted_score(
    metrics: Mapping[str, float], weights: Mapping[str, float]
) -> tuple[float, dict[str, float]]:
    if not weights:
        raise ValueError("weights must not be empty")

    normalized_weights: dict[str, float] = {}
    total_weight = sum(max(value, 0.0) for value in weights.values())
    if total_weight == 0:
        raise ValueError("weights must include at least one positive value")

    for key, value in weights.items():
        normalized_weights[key] = max(value, 0.0) / total_weight

    weighted_score = 0.0
    per_metric_score: dict[str, float] = {}

    for metric_name, weight in normalized_weights.items():
        metric_value = _clamp_metric(float(metrics.get(metric_name, 0.0)))
        per_metric_score[metric_name] = metric_value
        weighted_score += metric_value * weight

    return round(weighted_score, 4), per_metric_score
