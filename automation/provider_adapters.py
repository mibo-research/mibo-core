#!/usr/bin/env python3
"""Protocol-constrained provider API adapters used by MIBO API runtimes.

Exact model IDs and generation settings come from prospectively completed
execution records. Core paired execution uses only its registered providers;
the exploratory API Shadow may additionally use Perplexity Sonar. Network
execution is invoked only by fail-closed executors.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import socket
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


RETRY_ELIGIBLE_FAILURES = {
    "submission_failure",
    "provider_error",
    "timeout",
    "authentication_interruption",
    "rate_limit",
    "incomplete_generation",
    "corrupted_capture",
    "temporary_interface_failure",
}


@dataclass(frozen=True)
class AdapterFailure(Exception):
    kind: str
    message: str
    http_status: int | None = None
    retry_after_seconds: int | None = None
    response_body: str | None = None

    @property
    def retry_eligible(self) -> bool:
        return self.kind in RETRY_ELIGIBLE_FAILURES


@dataclass(frozen=True)
class AdapterResult:
    provider: str
    requested_model: str
    returned_model: str | None
    request_payload: dict[str, Any]
    response_json: dict[str, Any]
    raw_response_text: str
    http_status: int
    started_at_utc: str
    completed_at_utc: str
    duration_ms: int
    usage: Any
    output_text: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _retry_after(headers: Any) -> int | None:
    value = headers.get("Retry-After") if headers else None
    if not value:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _post_json(*, url: str, headers: dict[str, str], payload: dict[str, Any], timeout_s: int) -> tuple[int, str, dict[str, Any], int, str, str]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = Request(url, data=body, headers=headers, method="POST")
    started = _utc_now()
    t0 = time.monotonic()
    try:
        with urlopen(req, timeout=timeout_s) as response:
            status = int(response.status)
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = int(exc.code)
        kind = "rate_limit" if status == 429 else (
            "authentication_interruption" if status in {401, 403} else "provider_error"
        )
        raise AdapterFailure(
            kind=kind,
            message=f"HTTP {status}",
            http_status=status,
            retry_after_seconds=_retry_after(exc.headers),
            response_body=raw,
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise AdapterFailure(kind="timeout", message=str(exc) or "request timed out") from exc
    except URLError as exc:
        raise AdapterFailure(kind="submission_failure", message=str(exc.reason)) from exc
    completed = _utc_now()
    duration_ms = int((time.monotonic() - t0) * 1000)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AdapterFailure(
            kind="corrupted_capture",
            message="provider returned non-JSON response",
            http_status=status,
            response_body=raw,
        ) from exc
    return status, raw, parsed, duration_ms, started, completed


def _api_key(env_name: str) -> str:
    value = os.environ.get(env_name)
    if not value:
        raise AdapterFailure(
            kind="authentication_interruption",
            message=f"required credential environment variable {env_name} is not set",
        )
    return value


def _extract_openai_text(data: dict[str, Any]) -> str:
    chunks: list[str] = []
    for item in data.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content", []) or []:
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    return "\n".join(chunks)


def call_openai(*, model_id: str, prompt: str, profile: dict[str, Any], timeout_s: int = 180) -> AdapterResult:
    endpoint = profile.get("endpoint", "https://api.openai.com/v1/responses")
    payload: dict[str, Any] = {"model": model_id, "input": prompt, "store": False}
    for key in ("max_output_tokens", "temperature", "top_p"):
        if profile.get(key) is not None:
            payload[key] = profile[key]
    if profile.get("reasoning") is not None:
        payload["reasoning"] = profile["reasoning"]
    status, raw, data, duration, started, completed = _post_json(
        url=endpoint,
        headers={"Authorization": f"Bearer {_api_key(profile.get('api_key_env', 'OPENAI_API_KEY'))}", "Content-Type": "application/json"},
        payload=payload,
        timeout_s=timeout_s,
    )
    if data.get("status") == "incomplete" and data.get("error"):
        raise AdapterFailure(kind="incomplete_generation", message="OpenAI response incomplete", http_status=status, response_body=raw)
    return AdapterResult(
        provider="OpenAI", requested_model=model_id, returned_model=data.get("model"),
        request_payload=payload, response_json=data, raw_response_text=raw,
        http_status=status, started_at_utc=started, completed_at_utc=completed,
        duration_ms=duration, usage=data.get("usage"), output_text=_extract_openai_text(data),
    )


def _extract_anthropic_text(data: dict[str, Any]) -> str:
    return "\n".join(
        part.get("text", "") for part in (data.get("content") or [])
        if part.get("type") == "text" and isinstance(part.get("text"), str)
    )


def call_anthropic(*, model_id: str, prompt: str, profile: dict[str, Any], timeout_s: int = 180) -> AdapterResult:
    endpoint = profile.get("endpoint", "https://api.anthropic.com/v1/messages")
    if profile.get("max_output_tokens") is None:
        raise ValueError("Anthropic request profile requires max_output_tokens")
    payload: dict[str, Any] = {
        "model": model_id,
        "max_tokens": int(profile["max_output_tokens"]),
        "messages": [{"role": "user", "content": prompt}],
    }
    for src, dst in (("temperature", "temperature"), ("top_p", "top_p")):
        if profile.get(src) is not None:
            payload[dst] = profile[src]
    status, raw, data, duration, started, completed = _post_json(
        url=endpoint,
        headers={
            "x-api-key": _api_key(profile.get("api_key_env", "ANTHROPIC_API_KEY")),
            "anthropic-version": profile.get("anthropic_version", "2023-06-01"),
            "content-type": "application/json",
        },
        payload=payload,
        timeout_s=timeout_s,
    )
    if data.get("type") == "error":
        raise AdapterFailure(kind="provider_error", message="Anthropic error response", http_status=status, response_body=raw)
    return AdapterResult(
        provider="Anthropic", requested_model=model_id, returned_model=data.get("model"),
        request_payload=payload, response_json=data, raw_response_text=raw,
        http_status=status, started_at_utc=started, completed_at_utc=completed,
        duration_ms=duration, usage=data.get("usage"), output_text=_extract_anthropic_text(data),
    )


def _extract_gemini_text(data: dict[str, Any]) -> str:
    chunks: list[str] = []
    for candidate in data.get("candidates", []) or []:
        for part in ((candidate.get("content") or {}).get("parts") or []):
            if isinstance(part.get("text"), str):
                chunks.append(part["text"])
    return "\n".join(chunks)


def call_gemini(*, model_id: str, prompt: str, profile: dict[str, Any], timeout_s: int = 180) -> AdapterResult:
    base = profile.get("endpoint_base", "https://generativelanguage.googleapis.com/v1beta/models")
    endpoint = f"{base.rstrip('/')}/{quote(model_id, safe='')}:generateContent"
    payload: dict[str, Any] = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    generation: dict[str, Any] = {}
    for src, dst in (("max_output_tokens", "maxOutputTokens"), ("temperature", "temperature"), ("top_p", "topP")):
        if profile.get(src) is not None:
            generation[dst] = profile[src]
    if generation:
        payload["generationConfig"] = generation
    status, raw, data, duration, started, completed = _post_json(
        url=endpoint,
        headers={
            "x-goog-api-key": _api_key(profile.get("api_key_env", "GEMINI_API_KEY")),
            "Content-Type": "application/json",
        },
        payload=payload,
        timeout_s=timeout_s,
    )
    if data.get("error"):
        raise AdapterFailure(kind="provider_error", message="Gemini error response", http_status=status, response_body=raw)
    return AdapterResult(
        provider="Google", requested_model=model_id, returned_model=model_id,
        request_payload=payload, response_json=data, raw_response_text=raw,
        http_status=status, started_at_utc=started, completed_at_utc=completed,
        duration_ms=duration, usage=data.get("usageMetadata"), output_text=_extract_gemini_text(data),
    )


def _extract_perplexity_text(data: dict[str, Any]) -> str:
    chunks: list[str] = []
    for choice in data.get("choices", []) or []:
        message = choice.get("message") or {}
        text = message.get("content")
        if isinstance(text, str):
            chunks.append(text)
    return "\n".join(chunks)


def call_perplexity(*, model_id: str, prompt: str, profile: dict[str, Any], timeout_s: int = 180) -> AdapterResult:
    endpoint = profile.get("endpoint", "https://api.perplexity.ai/v1/sonar")
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    if profile.get("max_output_tokens") is not None:
        payload["max_tokens"] = int(profile["max_output_tokens"])
    for key in ("temperature", "top_p"):
        if profile.get(key) is not None:
            payload[key] = profile[key]
    if "disable_search" in profile:
        payload["web_search_options"] = {"disable_search": bool(profile["disable_search"])}
    status, raw, data, duration, started, completed = _post_json(
        url=endpoint,
        headers={
            "Authorization": f"Bearer {_api_key(profile.get('api_key_env', 'PERPLEXITY_API_KEY'))}",
            "Content-Type": "application/json",
        },
        payload=payload,
        timeout_s=timeout_s,
    )
    if data.get("error"):
        raise AdapterFailure(kind="provider_error", message="Perplexity error response", http_status=status, response_body=raw)
    return AdapterResult(
        provider="Perplexity AI", requested_model=model_id, returned_model=data.get("model"),
        request_payload=payload, response_json=data, raw_response_text=raw,
        http_status=status, started_at_utc=started, completed_at_utc=completed,
        duration_ms=duration, usage=data.get("usage"), output_text=_extract_perplexity_text(data),
    )


def call_provider(*, provider: str, model_id: str, prompt: str, profile: dict[str, Any], timeout_s: int = 180) -> AdapterResult:
    adapter = profile.get("adapter")
    expected = {
        "OpenAI": "openai_responses",
        "Anthropic": "anthropic_messages",
        "Google": "gemini_generate_content",
        "Perplexity": "perplexity_sonar",
        "Perplexity AI": "perplexity_sonar",
    }.get(provider)
    if expected is None:
        raise ValueError(f"no API adapter is registered for provider {provider}")
    if adapter != expected:
        raise ValueError(f"provider {provider} requires adapter {expected}, got {adapter!r}")
    if provider == "OpenAI":
        return call_openai(model_id=model_id, prompt=prompt, profile=profile, timeout_s=timeout_s)
    if provider == "Anthropic":
        return call_anthropic(model_id=model_id, prompt=prompt, profile=profile, timeout_s=timeout_s)
    if provider == "Google":
        return call_gemini(model_id=model_id, prompt=prompt, profile=profile, timeout_s=timeout_s)
    return call_perplexity(model_id=model_id, prompt=prompt, profile=profile, timeout_s=timeout_s)
