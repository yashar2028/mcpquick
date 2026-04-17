"""Provider invocation layer for sandbox runtime.

Design goals:
- Keep runtime orchestration simple by centralizing provider calls here.
- Use official provider SDKs when available.
- Preserve sandbox reliability by falling back to direct HTTP if an SDK
    is unavailable in the runtime environment.

Provider identifiers accepted by `call_provider`:
- openai
- anthropic / claude
- gemini / google
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import time
from typing import Final

from app.sandbox.http_client import ProviderHttpError, get_json, post_json

HTTP_TIMEOUT_SECONDS = 90
MAX_OUTPUT_TOKENS = 512
TOKEN_ESTIMATE_DIVISOR = 4

PROVIDER_OPENAI: Final[str] = "openai"
PROVIDER_ANTHROPIC: Final[str] = "anthropic"
PROVIDER_GEMINI: Final[str] = "gemini"
PROVIDER_ERROR_MESSAGE: Final[str] = (
    "unsupported provider. use 'openai', 'anthropic'/'claude', or 'google'/'gemini'."
)

PROVIDER_ALIASES: Final[dict[str, str]] = {
    "openai": PROVIDER_OPENAI,
    "gpt": PROVIDER_OPENAI,
    "anthropic": PROVIDER_ANTHROPIC,
    "claude": PROVIDER_ANTHROPIC,
    "google": PROVIDER_GEMINI,
    "gemini": PROVIDER_GEMINI,
}

RECOMMENDED_MODELS: Final[dict[str, list[str]]] = {
    PROVIDER_OPENAI: ["gpt-4o-mini", "gpt-4o"],
    PROVIDER_ANTHROPIC: ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
    PROVIDER_GEMINI: ["gemini-2.0-flash", "gemini-1.5-flash"],
}


@dataclass(frozen=True, slots=True)
class ProviderCallResult:
    """Result of a single model call to an external provider API."""

    output_text: str
    token_input: int
    token_output: int
    latency_ms: int


def normalize_provider(provider: str) -> str:
    """Normalize provider aliases into canonical provider keys."""
    provider_key = provider.strip().lower()
    normalized = PROVIDER_ALIASES.get(provider_key)
    if normalized is not None:
        return normalized
    raise RuntimeError(PROVIDER_ERROR_MESSAGE)


def _safe_int(value: object, fallback: int) -> int:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return fallback


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // TOKEN_ESTIMATE_DIVISOR)


def _normalize_output_text(value: object) -> str:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or "(empty response)"
    if value is None:
        return "(empty response)"
    normalized = str(value).strip()
    return normalized or "(empty response)"


def _blocks_to_text(blocks: object) -> str:
    if not isinstance(blocks, list):
        return "(empty response)"

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

    return _normalize_output_text("\n".join(parts))


def _openai_message_content_to_text(content: object) -> str:
    if isinstance(content, str):
        return _normalize_output_text(content)
    if not isinstance(content, list):
        return _normalize_output_text(content)

    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str) and text:
            parts.append(text)

    return _normalize_output_text("\n".join(parts))


def _gemini_response_to_text(response: dict[str, object]) -> str:
    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("gemini response did not contain candidates")

    candidate0 = candidates[0] if isinstance(candidates[0], dict) else {}
    content = candidate0.get("content") if isinstance(candidate0, dict) else {}
    parts = content.get("parts") if isinstance(content, dict) else []

    text_parts: list[str] = []
    if isinstance(parts, list):
        for part in parts:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str) and text:
                text_parts.append(text)

    return _normalize_output_text("\n".join(text_parts))


def _build_result(
    prompt: str,
    output_text: object,
    token_input: object,
    token_output: object,
    latency_ms: object,
) -> ProviderCallResult:
    normalized_output = _normalize_output_text(output_text)
    fallback_input = _estimate_tokens(prompt)
    fallback_output = _estimate_tokens(normalized_output)

    return ProviderCallResult(
        output_text=normalized_output,
        token_input=max(_safe_int(token_input, fallback_input), 1),
        token_output=max(_safe_int(token_output, fallback_output), 1),
        latency_ms=max(_safe_int(latency_ms, 1), 1),
    )


def _runtime_error_with_status(prefix: str, exc: Exception) -> RuntimeError:
    """Convert provider SDK errors to normalized RuntimeError messages."""
    status = _error_status_code(exc)

    if status is None:
        return RuntimeError(f"{prefix} API request failed: {exc}")
    return RuntimeError(f"{prefix} API request failed with status {status}: {exc}")


def _error_status_code(exc: Exception) -> int | None:
    """Best-effort extraction of HTTP status code from provider SDK exceptions."""
    status = getattr(exc, "status_code", None)
    if status is None:
        code_attr = getattr(exc, "code", None)
        if callable(code_attr):
            try:
                status = code_attr()
            except Exception:
                status = None
        else:
            status = code_attr

    if isinstance(status, int):
        return status
    if isinstance(status, str) and status.isdigit():
        return int(status)
    return None


def _ensure_model(model: str, provider: str) -> str:
    model_name = model.strip()
    if model_name:
        return model_name

    defaults = RECOMMENDED_MODELS.get(provider, [])
    if defaults:
        return defaults[0]
    raise RuntimeError(f"No default model configured for provider '{provider}'")


def _strip_model_prefix(model_name: str) -> str:
    if model_name.startswith("models/"):
        return model_name[7:]
    return model_name


def _call_openai(prompt: str, model: str, api_key: str) -> ProviderCallResult:
    """Call OpenAI using SDK-first strategy with HTTP fallback."""
    model_name = _ensure_model(model, PROVIDER_OPENAI)

    try:
        from openai import OpenAI

        started = time.perf_counter()
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)

        choice = response.choices[0] if response.choices else None
        message = getattr(choice, "message", None)
        content = getattr(message, "content", "") if message is not None else ""

        usage = getattr(response, "usage", None)
        return _build_result(
            prompt=prompt,
            output_text=_openai_message_content_to_text(content),
            token_input=getattr(usage, "prompt_tokens", None),
            token_output=getattr(usage, "completion_tokens", None),
            latency_ms=latency_ms,
        )
    except ImportError:
        pass
    except Exception as exc:
        raise _runtime_error_with_status("openai", exc) from exc

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": MAX_OUTPUT_TOKENS,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response, latency_ms = post_json(
        url="https://api.openai.com/v1/chat/completions",
        payload=payload,
        headers=headers,
        timeout_seconds=HTTP_TIMEOUT_SECONDS,
    )

    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("openai response did not contain choices")

    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else ""

    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    return _build_result(
        prompt=prompt,
        output_text=_openai_message_content_to_text(content),
        token_input=usage.get("prompt_tokens"),
        token_output=usage.get("completion_tokens"),
        latency_ms=latency_ms,
    )


def _call_anthropic(prompt: str, model: str, api_key: str) -> ProviderCallResult:
    """Call Anthropic using SDK-first strategy with HTTP fallback."""
    model_name = _ensure_model(model, PROVIDER_ANTHROPIC)

    try:
        from anthropic import Anthropic

        started = time.perf_counter()
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)

        usage = getattr(response, "usage", None)
        return _build_result(
            prompt=prompt,
            output_text=_blocks_to_text(getattr(response, "content", [])),
            token_input=getattr(usage, "input_tokens", None),
            token_output=getattr(usage, "output_tokens", None),
            latency_ms=latency_ms,
        )
    except ImportError:
        pass
    except Exception as exc:
        raise _runtime_error_with_status("anthropic", exc) from exc

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": MAX_OUTPUT_TOKENS,
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    response, latency_ms = post_json(
        url="https://api.anthropic.com/v1/messages",
        payload=payload,
        headers=headers,
        timeout_seconds=HTTP_TIMEOUT_SECONDS,
    )

    content_blocks = response.get("content")
    if not isinstance(content_blocks, list):
        raise RuntimeError("anthropic response did not contain content blocks")

    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    return _build_result(
        prompt=prompt,
        output_text=_blocks_to_text(content_blocks),
        token_input=usage.get("input_tokens"),
        token_output=usage.get("output_tokens"),
        latency_ms=latency_ms,
    )


def _list_gemini_models(api_key: str) -> list[str]:
    parsed = get_json(
        url="https://generativelanguage.googleapis.com/v1beta/models",
        headers={"x-goog-api-key": api_key},
        timeout_seconds=HTTP_TIMEOUT_SECONDS,
    )

    models_raw = parsed.get("models")
    if not isinstance(models_raw, list):
        return []

    candidates: list[str] = []
    for item in models_raw:
        if not isinstance(item, dict):
            continue

        name = item.get("name")
        methods = item.get("supportedGenerationMethods")
        if not isinstance(name, str) or not name.startswith("models/"):
            continue
        if not isinstance(methods, list) or "generateContent" not in methods:
            continue

        model_id = name.split("/", 1)[1]
        if "gemini" in model_id:
            candidates.append(model_id)

    return candidates


def _pick_gemini_fallback_model(models: list[str]) -> str | None:
    if not models:
        return None

    flash_models = [name for name in models if "flash" in name]
    if flash_models:
        return sorted(flash_models)[0]

    return sorted(models)[0]


def _call_gemini(prompt: str, model: str, api_key: str) -> ProviderCallResult:
    """Call Gemini using SDK-first strategy with HTTP fallback."""
    model_name = _ensure_model(model, PROVIDER_GEMINI)

    try:
        import google.generativeai as genai

        sdk_model = model_name if model_name.startswith("models/") else model_name
        started = time.perf_counter()
        genai.configure(api_key=api_key)
        model_client = genai.GenerativeModel(model_name=sdk_model)
        response = model_client.generate_content(
            prompt,
            generation_config={
                "temperature": 0,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
            },
        )
        latency_ms = int((time.perf_counter() - started) * 1000)

        usage = getattr(response, "usage_metadata", None)
        return _build_result(
            prompt=prompt,
            output_text=getattr(response, "text", None),
            token_input=getattr(usage, "prompt_token_count", None),
            token_output=getattr(usage, "candidates_token_count", None),
            latency_ms=latency_ms,
        )
    except ImportError:
        pass
    except Exception as exc:
        if _error_status_code(exc) != 404:
            raise _runtime_error_with_status("gemini", exc) from exc

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": MAX_OUTPUT_TOKENS},
    }
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    model_id = _strip_model_prefix(model_name)

    try:
        response, latency_ms = post_json(
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent",
            payload=payload,
            headers=headers,
            timeout_seconds=HTTP_TIMEOUT_SECONDS,
        )
    except ProviderHttpError as exc:
        if exc.status_code != 404:
            raise

        fallback_model = _pick_gemini_fallback_model(_list_gemini_models(api_key))
        if fallback_model is None:
            raise RuntimeError(
                "Gemini model was not found and no compatible generateContent model "
                "was discovered for this API key."
            ) from exc

        response, latency_ms = post_json(
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{fallback_model}:generateContent",
            payload=payload,
            headers=headers,
            timeout_seconds=HTTP_TIMEOUT_SECONDS,
        )

    usage = (
        response.get("usageMetadata")
        if isinstance(response.get("usageMetadata"), dict)
        else {}
    )
    return _build_result(
        prompt=prompt,
        output_text=_gemini_response_to_text(response),
        token_input=usage.get("promptTokenCount"),
        token_output=usage.get("candidatesTokenCount"),
        latency_ms=latency_ms,
    )


ProviderCaller = Callable[[str, str, str], ProviderCallResult]
PROVIDER_DISPATCH: Final[dict[str, ProviderCaller]] = {
    PROVIDER_OPENAI: _call_openai,
    PROVIDER_ANTHROPIC: _call_anthropic,
    PROVIDER_GEMINI: _call_gemini,
}


def call_provider(
    prompt: str, provider: str, model: str, api_key: str
) -> ProviderCallResult:
    """Dispatch one prompt to a provider/model pair and return normalized metrics.

    Args:
        prompt: User prompt sent to provider model.
        provider: Provider key/alias (e.g. openai, anthropic, gemini).
        model: Model name used for that provider.
        api_key: Session API key injected by control-plane.
    """
    provider_key = normalize_provider(provider)
    caller = PROVIDER_DISPATCH.get(provider_key)
    if caller is None:
        raise RuntimeError(PROVIDER_ERROR_MESSAGE)
    return caller(prompt, model, api_key)
