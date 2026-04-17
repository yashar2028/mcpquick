from __future__ import annotations

from typing import Mapping


def _provider_token_rates(provider: str, model: str) -> tuple[float, float]:
    provider_key = provider.strip().lower()
    model_key = model.strip().lower()

    if provider_key == "openai":
        if "gpt-4o-mini" in model_key:
            return 0.00000015, 0.00000060
        return 0.00000500, 0.00001500

    if provider_key in {"anthropic", "claude"}:
        if "haiku" in model_key:
            return 0.00000080, 0.00000400
        return 0.00000300, 0.00001500

    if provider_key in {"google", "gemini"}:
        if "flash" in model_key:
            return 0.00000035, 0.00000105
        return 0.00000125, 0.00000500

    return 0.00000100, 0.00000300


def _clamp_metric(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def estimate_token_cost_usd(
    provider: str, model: str, token_input: int, token_output: int
) -> float:
    input_rate, output_rate = _provider_token_rates(provider, model)
    total = max(token_input, 0) * input_rate + max(token_output, 0) * output_rate
    return round(total, 6)


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


def build_heuristic_summary(
    total_score: float, metric_scores: Mapping[str, float]
) -> str:
    """Produce deterministic report summary without an AI judge model."""
    if total_score >= 0.8:
        status = "strong overall quality"
    elif total_score >= 0.6:
        status = "acceptable quality with room to improve"
    else:
        status = "low quality and needs corrective tuning"

    weakest_metric = min(metric_scores.items(), key=lambda item: item[1])[0]
    strongest_metric = max(metric_scores.items(), key=lambda item: item[1])[0]

    return (
        f"Heuristic evaluation completed without a judge model: {status}. "
        f"Strongest metric: {strongest_metric}. Weakest metric: {weakest_metric}."
    )


def build_recommendations(metric_scores: Mapping[str, float]) -> list[str]:
    """Produce deterministic recommendations from low-scoring metrics."""
    recommendations: list[str] = []

    if metric_scores.get("tool_correctness", 1.0) < 0.7:
        recommendations.append(
            "Tighten tool call selection and validate tool outputs before final response."
        )
    if metric_scores.get("latency_efficiency", 1.0) < 0.7:
        recommendations.append(
            "Reduce non-essential calls and cap tokens to improve end-to-end latency."
        )
    if metric_scores.get("cost_efficiency", 1.0) < 0.7:
        recommendations.append(
            "Use a cheaper model tier for drafting and reserve premium models for hard cases."
        )
    if metric_scores.get("task_success", 1.0) < 0.7:
        recommendations.append(
            "Improve instruction grounding and add explicit success criteria in prompts."
        )

    if not recommendations:
        recommendations.append(
            "Maintain current setup and monitor regressions with periodic benchmark runs."
        )

    return recommendations
